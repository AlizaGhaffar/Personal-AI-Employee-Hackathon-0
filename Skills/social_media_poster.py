"""
Social Media Poster - Gold Tier
Posts approved content to Facebook and/or Instagram.

HITL Pattern:
  1. Claude generates a post draft → writes to Pending_Approval/
  2. Human reviews and moves file to Approved/
  3. This script reads from Approved/ and executes the post
  4. Moves completed file to Done/
  5. Logs everything to Logs/social.log

Platforms:
  - Facebook  : Page posts (text, photo, link) via Graph API
  - Instagram : Image posts (requires Business account + Facebook Page link)
               Note: Instagram does NOT support text-only posts via API.
               An image_url is required for Instagram.

Usage:
  python Skills/social_media_poster.py                    # process all in Approved/
  python Skills/social_media_poster.py --file <path>      # process a specific file
  python Skills/social_media_poster.py --dry-run          # validate without posting

Post Spec File Format (YAML front-matter in Approved/*.md):
  ---
  type: social_post
  platform: facebook | instagram | both
  caption: "Your post text here"
  image_url: "https://..." (required for Instagram, optional for Facebook)
  link_url: "https://..."  (Facebook only, optional)
  ---
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPROVED_DIR = PROJECT_ROOT / "Approved"
DONE_DIR     = PROJECT_ROOT / "Done"
LOGS_DIR     = PROJECT_ROOT / "Logs"

load_dotenv(PROJECT_ROOT / ".env")

# ── Facebook / Instagram Config ────────────────────────────────────────────────
FB_PAGE_ID      = os.getenv("FACEBOOK_PAGE_ID",       "")
FB_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN",  "")
IG_ACCOUNT_ID   = os.getenv("INSTAGRAM_ACCOUNT_ID",   "")  # IG Business Account ID
GRAPH_VERSION   = os.getenv("FACEBOOK_GRAPH_VERSION", "v20.0")
GRAPH_BASE      = f"https://graph.facebook.com/{GRAPH_VERSION}"

# ── Logging ────────────────────────────────────────────────────────────────────
LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOGS_DIR / "social.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("social_poster")


# ── Graph API Helpers ──────────────────────────────────────────────────────────

def _graph_post(endpoint: str, data: dict) -> dict:
    """POST to Facebook Graph API."""
    data["access_token"] = FB_ACCESS_TOKEN
    resp = requests.post(f"{GRAPH_BASE}/{endpoint}", data=data, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if "error" in result:
        err = result["error"]
        raise RuntimeError(f"Graph API error {err.get('code')}: {err.get('message')}")
    return result


# ── Facebook Posting ───────────────────────────────────────────────────────────

def post_facebook_text(caption: str, link_url: str = "") -> dict:
    """Post text (and optional link) to a Facebook Page."""
    data = {"message": caption}
    if link_url:
        data["link"] = link_url

    result = _graph_post(f"{FB_PAGE_ID}/feed", data)
    post_id = result.get("id", "unknown")
    log.info(f"FB TEXT POST — ID: {post_id}")
    return {"platform": "facebook", "type": "text", "post_id": post_id}


def post_facebook_photo(caption: str, image_url: str) -> dict:
    """Post an image with caption to a Facebook Page."""
    result = _graph_post(
        f"{FB_PAGE_ID}/photos",
        {"caption": caption, "url": image_url},
    )
    post_id = result.get("post_id") or result.get("id", "unknown")
    log.info(f"FB PHOTO POST — ID: {post_id}")
    return {"platform": "facebook", "type": "photo", "post_id": post_id}


# ── Instagram Posting ──────────────────────────────────────────────────────────

def post_instagram_image(caption: str, image_url: str) -> dict:
    """
    Post an image to Instagram Business account.
    Two-step: create media container → publish.

    Requirements:
      - INSTAGRAM_ACCOUNT_ID must be set in .env
      - image_url must be publicly accessible (not localhost)
      - Instagram Business or Creator account linked to Facebook Page
    """
    if not IG_ACCOUNT_ID:
        raise RuntimeError("INSTAGRAM_ACCOUNT_ID not set in .env")
    if not image_url:
        raise RuntimeError("Instagram requires an image_url — text-only posts are not supported")

    # Step 1: Create media container
    container = _graph_post(
        f"{IG_ACCOUNT_ID}/media",
        {"image_url": image_url, "caption": caption},
    )
    container_id = container.get("id")
    if not container_id:
        raise RuntimeError(f"Instagram container creation failed: {container}")

    log.info(f"IG container created: {container_id} — waiting 5s before publish...")
    time.sleep(5)  # Instagram recommends a delay before publishing

    # Step 2: Publish the container
    result = _graph_post(
        f"{IG_ACCOUNT_ID}/media_publish",
        {"creation_id": container_id},
    )
    post_id = result.get("id", "unknown")
    log.info(f"IG IMAGE POST — ID: {post_id}")
    return {"platform": "instagram", "type": "image", "post_id": post_id}


# ── Spec File Parsing ──────────────────────────────────────────────────────────

def parse_post_spec(filepath: Path) -> dict:
    """
    Read a post spec from an Approved/ markdown file.
    Extracts YAML front-matter for post parameters.
    Returns dict with: platform, caption, image_url, link_url
    """
    text = filepath.read_text(encoding="utf-8")

    # Extract YAML front-matter between --- delimiters
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError as exc:
                raise ValueError(f"Invalid YAML front-matter in {filepath.name}: {exc}")
        else:
            meta = {}
    else:
        meta = {}

    # Validate required fields
    platform = meta.get("platform", "facebook").lower()
    caption  = meta.get("caption", "").strip()

    if not caption:
        raise ValueError(f"No 'caption' found in {filepath.name}")

    valid_platforms = {"facebook", "instagram", "both"}
    if platform not in valid_platforms:
        raise ValueError(f"Invalid platform '{platform}' — must be: {valid_platforms}")

    return {
        "platform":  platform,
        "caption":   caption,
        "image_url": meta.get("image_url", "").strip(),
        "link_url":  meta.get("link_url",  "").strip(),
    }


# ── Post Executor ──────────────────────────────────────────────────────────────

def execute_post(spec: dict, dry_run: bool = False) -> list[dict]:
    """
    Execute the post based on the spec dict.
    Returns list of result dicts (one per platform).
    """
    platform  = spec["platform"]
    caption   = spec["caption"]
    image_url = spec.get("image_url", "")
    link_url  = spec.get("link_url", "")

    results = []

    if dry_run:
        log.info(f"[DRY RUN] Would post to: {platform}")
        log.info(f"[DRY RUN] Caption: {caption[:100]}")
        log.info(f"[DRY RUN] Image URL: {image_url or '(none)'}")
        return [{"platform": platform, "type": "dry_run", "post_id": "DRY_RUN"}]

    if platform in ("facebook", "both"):
        if image_url:
            results.append(post_facebook_photo(caption, image_url))
        else:
            results.append(post_facebook_text(caption, link_url))

    if platform in ("instagram", "both"):
        results.append(post_instagram_image(caption, image_url))

    return results


# ── File Pipeline ──────────────────────────────────────────────────────────────

def process_approved_file(filepath: Path, dry_run: bool = False) -> bool:
    """
    Read spec, post content, move file to Done/, log result.
    Returns True on success.
    """
    log.info(f"Processing: {filepath.name}")

    try:
        spec = parse_post_spec(filepath)
    except (ValueError, Exception) as exc:
        log.error(f"Spec parse failed for {filepath.name}: {exc}")
        return False

    log.info(f"Platform: {spec['platform']} | Caption: {spec['caption'][:60]}...")

    try:
        results = execute_post(spec, dry_run=dry_run)
    except RuntimeError as exc:
        log.error(f"Post failed for {filepath.name}: {exc}")
        return False

    # Log results
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for r in results:
        log.info(f"POSTED | platform={r['platform']} | type={r['type']} | post_id={r['post_id']}")

    # Move to Done/ (unless dry-run)
    if not dry_run:
        DONE_DIR.mkdir(exist_ok=True)
        dest = DONE_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filepath.name}"
        filepath.rename(dest)
        log.info(f"Moved → Done/{dest.name}")

    return True


def process_all_approved(dry_run: bool = False) -> int:
    """Process all social post files in Approved/. Returns count of successes."""
    APPROVED_DIR.mkdir(exist_ok=True)
    files = [
        f for f in APPROVED_DIR.iterdir()
        if f.is_file() and f.suffix == ".md" and not f.name.startswith(".")
    ]

    # Filter to social post files only (check front-matter type)
    social_files = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        if "type: social_post" in text:
            social_files.append(f)

    if not social_files:
        log.info("No social_post files found in Approved/")
        return 0

    log.info(f"Found {len(social_files)} social post file(s) to process")
    success = 0
    for f in social_files:
        if process_approved_file(f, dry_run=dry_run):
            success += 1

    return success


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Social Media Poster — HITL post executor")
    parser.add_argument("--file",    help="Path to a specific Approved/ post spec file")
    parser.add_argument("--dry-run", action="store_true", help="Validate and log without posting")
    args = parser.parse_args()

    # Validate config (warn but don't block dry-run)
    if not args.dry_run:
        if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
            log.error("FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN must be set in .env")
            sys.exit(1)

    log.info("=" * 55)
    log.info("SOCIAL MEDIA POSTER — Gold Tier")
    log.info(f"Dry run: {args.dry_run}")
    log.info("=" * 55)

    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            log.error(f"File not found: {filepath}")
            sys.exit(1)
        success = process_approved_file(filepath, dry_run=args.dry_run)
        sys.exit(0 if success else 1)
    else:
        count = process_all_approved(dry_run=args.dry_run)
        log.info(f"Done — {count} post(s) executed")


if __name__ == "__main__":
    main()

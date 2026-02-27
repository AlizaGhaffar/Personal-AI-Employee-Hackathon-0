"""
Twitter Poster - Gold Tier
Posts approved content to Twitter (X) via API v2.

HITL Pattern:
  1. Claude generates a tweet draft → writes to Pending_Approval/
  2. Human reviews and moves file to Approved/
  3. This script reads from Approved/ and executes the post
  4. Moves completed file to Done/
  5. Logs everything to Logs/twitter.log

Supported post types:
  - tweet      : New standalone tweet
  - reply      : Reply to an existing tweet (requires reply_to_tweet_id)

Usage:
  python Skills/twitter_poster.py                    # process all in Approved/
  python Skills/twitter_poster.py --file <path>      # process a specific file
  python Skills/twitter_poster.py --dry-run          # validate without posting

Post Spec File Format (YAML front-matter in Approved/*.md):
  ---
  type: twitter_post
  tweet_type: tweet | reply
  text: "Your tweet text here (max 280 chars)"
  reply_to_tweet_id: "12345"  (required if tweet_type: reply)
  ---
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPROVED_DIR = PROJECT_ROOT / "Approved"
DONE_DIR     = PROJECT_ROOT / "Done"
LOGS_DIR     = PROJECT_ROOT / "Logs"

load_dotenv(PROJECT_ROOT / ".env")

# ── Twitter Config ─────────────────────────────────────────────────────────────
BEARER_TOKEN        = os.getenv("TWITTER_BEARER_TOKEN",         "")
API_KEY             = os.getenv("TWITTER_API_KEY",               "")
API_SECRET          = os.getenv("TWITTER_API_SECRET",            "")
ACCESS_TOKEN        = os.getenv("TWITTER_ACCESS_TOKEN",          "")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET",   "")

# ── Logging ────────────────────────────────────────────────────────────────────
LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOGS_DIR / "twitter.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("twitter_poster")


def _build_client():
    """Build tweepy Client with full OAuth credentials."""
    try:
        import tweepy
    except ImportError:
        log.error("tweepy not installed. Run: pip install tweepy")
        sys.exit(1)

    return tweepy.Client(
        bearer_token=BEARER_TOKEN,
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET,
    )


# ── Spec File Parsing ──────────────────────────────────────────────────────────

def parse_post_spec(filepath: Path) -> dict:
    """
    Read a Twitter post spec from an Approved/ markdown file.
    Returns dict with: tweet_type, text, reply_to_tweet_id
    """
    text_raw = filepath.read_text(encoding="utf-8")

    meta = {}
    if text_raw.startswith("---"):
        parts = text_raw.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError as exc:
                raise ValueError(f"Invalid YAML front-matter in {filepath.name}: {exc}")

    tweet_type = meta.get("tweet_type", "tweet").lower()
    text       = meta.get("text", "").strip()

    if not text:
        raise ValueError(f"No 'text' found in {filepath.name}")

    if len(text) > 280:
        raise ValueError(f"Tweet exceeds 280 characters ({len(text)}) in {filepath.name}")

    valid_types = {"tweet", "reply"}
    if tweet_type not in valid_types:
        raise ValueError(f"Invalid tweet_type '{tweet_type}' — must be: {valid_types}")

    reply_to = str(meta.get("reply_to_tweet_id", "") or "").strip()
    if tweet_type == "reply" and not reply_to:
        raise ValueError(f"tweet_type 'reply' requires 'reply_to_tweet_id' in {filepath.name}")

    return {
        "tweet_type":         tweet_type,
        "text":               text,
        "reply_to_tweet_id":  reply_to,
    }


# ── Post Execution ─────────────────────────────────────────────────────────────

def execute_post(spec: dict, dry_run: bool = False) -> dict:
    """Post to Twitter based on spec. Returns result dict."""
    tweet_type = spec["tweet_type"]
    text       = spec["text"]
    reply_to   = spec.get("reply_to_tweet_id", "")

    if dry_run:
        log.info(f"[DRY RUN] tweet_type={tweet_type} | text={text[:80]}")
        if reply_to:
            log.info(f"[DRY RUN] Replying to: {reply_to}")
        return {"tweet_id": "DRY_RUN", "tweet_type": tweet_type}

    client = _build_client()

    if tweet_type == "reply" and reply_to:
        resp = client.create_tweet(
            text=text,
            in_reply_to_tweet_id=reply_to,
        )
    else:
        resp = client.create_tweet(text=text)

    tweet_id = str(resp.data["id"])
    log.info(f"TWEET POSTED | tweet_type={tweet_type} | tweet_id={tweet_id}")
    return {"tweet_id": tweet_id, "tweet_type": tweet_type}


# ── File Pipeline ──────────────────────────────────────────────────────────────

def process_approved_file(filepath: Path, dry_run: bool = False) -> bool:
    """Read spec, post tweet, move to Done/, log result. Returns True on success."""
    log.info(f"Processing: {filepath.name}")

    try:
        spec = parse_post_spec(filepath)
    except (ValueError, Exception) as exc:
        log.error(f"Spec parse failed for {filepath.name}: {exc}")
        return False

    log.info(f"tweet_type: {spec['tweet_type']} | text: {spec['text'][:60]}...")

    try:
        result = execute_post(spec, dry_run=dry_run)
    except Exception as exc:
        log.error(f"Post failed for {filepath.name}: {exc}")
        return False

    log.info(f"POSTED | tweet_id={result['tweet_id']} | type={result['tweet_type']}")

    if not dry_run:
        DONE_DIR.mkdir(exist_ok=True)
        dest = DONE_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filepath.name}"
        filepath.rename(dest)
        log.info(f"Moved → Done/{dest.name}")

    return True


def process_all_approved(dry_run: bool = False) -> int:
    """Process all Twitter post files in Approved/. Returns count of successes."""
    APPROVED_DIR.mkdir(exist_ok=True)
    files = [
        f for f in APPROVED_DIR.iterdir()
        if f.is_file() and f.suffix == ".md" and not f.name.startswith(".")
    ]

    twitter_files = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        if "type: twitter_post" in text:
            twitter_files.append(f)

    if not twitter_files:
        log.info("No twitter_post files found in Approved/")
        return 0

    log.info(f"Found {len(twitter_files)} Twitter post file(s) to process")
    success = 0
    for f in twitter_files:
        if process_approved_file(f, dry_run=dry_run):
            success += 1

    return success


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Twitter Poster — HITL tweet executor")
    parser.add_argument("--file",    help="Path to a specific Approved/ post spec file")
    parser.add_argument("--dry-run", action="store_true", help="Validate and log without posting")
    args = parser.parse_args()

    if not args.dry_run:
        missing = [v for v in ["TWITTER_API_KEY", "TWITTER_ACCESS_TOKEN"] if not os.getenv(v)]
        if missing:
            log.error(f"Missing .env variables: {', '.join(missing)}")
            sys.exit(1)

    log.info("=" * 55)
    log.info("TWITTER POSTER — Gold Tier")
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
        log.info(f"Done — {count} tweet(s) posted")


if __name__ == "__main__":
    main()

"""
Facebook MCP Server - Gold Tier
Exposes Facebook and Instagram posting tools to Claude Code via MCP.

Tools:
  - fb_get_messages    : Fetch recent Page inbox messages
  - fb_post_text       : Post text (+ optional link) to Facebook Page
  - fb_post_photo      : Post image with caption to Facebook Page
  - ig_post_image      : Post image to Instagram Business account
  - social_draft_post  : Write a HITL draft to Pending_Approval/ (safe — no API call)

Auth:
  FACEBOOK_PAGE_ID      — your Facebook Page ID
  FACEBOOK_ACCESS_TOKEN — long-lived Page Access Token
  INSTAGRAM_ACCOUNT_ID  — Instagram Business Account ID (linked to Facebook Page)

Logging: file only — stdout corrupts MCP stdio transport.
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR     = PROJECT_ROOT / "Logs"
PENDING_DIR  = PROJECT_ROOT / "Pending_Approval"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(PROJECT_ROOT / ".env")

# ── Config ─────────────────────────────────────────────────────────────────────
FB_PAGE_ID      = os.getenv("FACEBOOK_PAGE_ID",       "")
FB_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN",  "")
IG_ACCOUNT_ID   = os.getenv("INSTAGRAM_ACCOUNT_ID",   "")
GRAPH_VERSION   = os.getenv("FACEBOOK_GRAPH_VERSION", "v20.0")
GRAPH_BASE      = f"https://graph.facebook.com/{GRAPH_VERSION}"

# ── Logging (file only) ────────────────────────────────────────────────────────
logger = logging.getLogger("FacebookMCP")
log_file = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_FacebookMCP.log"
_fh = logging.FileHandler(log_file, encoding="utf-8")
_fh.setFormatter(logging.Formatter("[%(asctime)s] %(name)s %(levelname)s: %(message)s"))
logger.addHandler(_fh)
logger.setLevel(logging.INFO)

# ── MCP App ────────────────────────────────────────────────────────────────────
mcp = FastMCP("facebook-mcp")


# ── Graph API Helpers ──────────────────────────────────────────────────────────

def _graph_get(endpoint: str, params: dict = None) -> dict:
    params = params or {}
    params["access_token"] = FB_ACCESS_TOKEN
    resp = requests.get(f"{GRAPH_BASE}/{endpoint}", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Graph API: {data['error'].get('message')}")
    return data


def _graph_post(endpoint: str, data: dict) -> dict:
    data["access_token"] = FB_ACCESS_TOKEN
    resp = requests.post(f"{GRAPH_BASE}/{endpoint}", data=data, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if "error" in result:
        raise RuntimeError(f"Graph API: {result['error'].get('message')}")
    return result


def _log_action(action: str, details: dict):
    social_log = LOGS_DIR / "social.log"
    entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {action} | {json.dumps(details)}\n"
    with social_log.open("a", encoding="utf-8") as f:
        f.write(entry)
    logger.info(f"{action} | {details}")


# ── MCP Tools ──────────────────────────────────────────────────────────────────

@mcp.tool()
def fb_get_messages(limit: int = 10) -> str:
    """
    Fetch recent messages from the Facebook Page inbox.

    Args:
        limit: Number of conversations to return (default 10, max 25)

    Returns: JSON array of recent conversations with sender and preview
    """
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        return json.dumps({"error": "FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN not configured"})

    try:
        data = _graph_get(
            f"{FB_PAGE_ID}/conversations",
            params={
                "platform": "messenger",
                "fields": "id,updated_time,participants,snippet,unread_count",
                "limit": min(limit, 25),
            },
        )
        conversations = data.get("data", [])
        results = []
        for c in conversations:
            participants = c.get("participants", {}).get("data", [])
            sender = next(
                (p["name"] for p in participants if str(p.get("id")) != str(FB_PAGE_ID)),
                "Unknown",
            )
            results.append({
                "id":           c["id"],
                "sender":       sender,
                "preview":      c.get("snippet", ""),
                "unread":       c.get("unread_count", 0),
                "updated":      c.get("updated_time", "")[:19],
            })

        _log_action("FB_GET_MESSAGES", {"count": len(results)})
        return json.dumps(results, indent=2)

    except Exception as exc:
        logger.error(f"fb_get_messages error: {exc}")
        return json.dumps({"error": str(exc)})


@mcp.tool()
def social_draft_post(
    platform: str,
    caption: str,
    image_url: str = "",
    link_url: str = "",
    notes: str = "",
) -> str:
    """
    Create a HITL draft post file in Pending_Approval/ — does NOT post to social media.
    Human must review and move to Approved/ before posting.

    Args:
        platform:  "facebook" | "instagram" | "both"
        caption:   Post text / caption (required)
        image_url: Public URL of image to post (required for Instagram)
        link_url:  Link to include (Facebook only, optional)
        notes:     Internal notes visible in the approval file

    Returns: JSON with path to the created Pending_Approval file
    """
    valid = {"facebook", "instagram", "both"}
    if platform not in valid:
        return json.dumps({"error": f"Invalid platform. Must be one of: {valid}"})
    if not caption.strip():
        return json.dumps({"error": "caption is required"})
    if platform in ("instagram", "both") and not image_url:
        return json.dumps({"error": "image_url is required for Instagram posts"})

    PENDING_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug      = platform[:2].upper()
    filename  = f"SOCIAL_{slug}_{timestamp}.md"
    filepath  = PENDING_DIR / filename
    today     = datetime.now().strftime("%Y-%m-%d")

    content = f"""---
date: {today}
type: social_post
platform: {platform}
caption: "{caption.replace('"', "'")}"
image_url: "{image_url}"
link_url: "{link_url}"
status: pending
requires_approval: true
priority: P2
tags: [social, {platform}, post]
summary: "{platform.title()} post draft — awaiting approval"
---

# Social Post Draft — {platform.title()}

## Post Content

**Platform:** {platform}
**Caption:**

> {caption}

**Image URL:** {image_url or "(none)"}
**Link URL:** {link_url or "(none)"}

## Action Required

- [ ] Review caption for tone, accuracy, and brand voice
- [ ] Verify image URL is publicly accessible (if provided)
- [ ] Move to `Approved/` to publish the post
- [ ] Move to `Rejected/` to cancel

## Notes

{notes or "No additional notes."}

---
*Draft created by Facebook MCP | Requires human approval before posting*
"""

    filepath.write_text(content, encoding="utf-8")
    _log_action("SOCIAL_DRAFT", {"platform": platform, "file": filename})
    return json.dumps({"status": "draft_created", "path": str(filepath), "file": filename})


@mcp.tool()
def fb_post_text(caption: str, link_url: str = "") -> str:
    """
    Post text (and optional link) to the Facebook Page.
    WARNING: This posts immediately. Always prefer social_draft_post for HITL flow.

    Args:
        caption:  Post text (required)
        link_url: Optional URL to attach

    Returns: JSON with post_id on success
    """
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        return json.dumps({"error": "Facebook credentials not configured"})

    try:
        data = {"message": caption}
        if link_url:
            data["link"] = link_url
        result = _graph_post(f"{FB_PAGE_ID}/feed", data)
        post_id = result.get("id", "unknown")
        _log_action("FB_POST_TEXT", {"post_id": post_id, "caption_preview": caption[:60]})
        return json.dumps({"status": "posted", "platform": "facebook", "post_id": post_id})
    except Exception as exc:
        logger.error(f"fb_post_text error: {exc}")
        return json.dumps({"error": str(exc)})


@mcp.tool()
def fb_post_photo(caption: str, image_url: str) -> str:
    """
    Post an image with caption to the Facebook Page.
    WARNING: This posts immediately. Always prefer social_draft_post for HITL flow.

    Args:
        caption:   Post caption (required)
        image_url: Publicly accessible image URL (required)

    Returns: JSON with post_id on success
    """
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        return json.dumps({"error": "Facebook credentials not configured"})
    if not image_url:
        return json.dumps({"error": "image_url is required"})

    try:
        result = _graph_post(
            f"{FB_PAGE_ID}/photos",
            {"caption": caption, "url": image_url},
        )
        post_id = result.get("post_id") or result.get("id", "unknown")
        _log_action("FB_POST_PHOTO", {"post_id": post_id, "image_url": image_url})
        return json.dumps({"status": "posted", "platform": "facebook", "post_id": post_id})
    except Exception as exc:
        logger.error(f"fb_post_photo error: {exc}")
        return json.dumps({"error": str(exc)})


@mcp.tool()
def ig_post_image(caption: str, image_url: str) -> str:
    """
    Post an image to Instagram Business account (two-step: container → publish).
    WARNING: This posts immediately. Always prefer social_draft_post for HITL flow.

    Args:
        caption:   Post caption with hashtags (required)
        image_url: Publicly accessible image URL (required — text-only not supported)

    Returns: JSON with post_id on success
    """
    if not IG_ACCOUNT_ID:
        return json.dumps({"error": "INSTAGRAM_ACCOUNT_ID not set in .env"})
    if not image_url:
        return json.dumps({"error": "image_url is required for Instagram"})

    try:
        # Step 1: Create container
        container = _graph_post(
            f"{IG_ACCOUNT_ID}/media",
            {"image_url": image_url, "caption": caption},
        )
        container_id = container.get("id")
        if not container_id:
            return json.dumps({"error": "Failed to create Instagram media container"})

        logger.info(f"IG container {container_id} — waiting 5s...")
        time.sleep(5)

        # Step 2: Publish
        result = _graph_post(
            f"{IG_ACCOUNT_ID}/media_publish",
            {"creation_id": container_id},
        )
        post_id = result.get("id", "unknown")
        _log_action("IG_POST_IMAGE", {"post_id": post_id, "image_url": image_url})
        return json.dumps({"status": "posted", "platform": "instagram", "post_id": post_id})

    except Exception as exc:
        logger.error(f"ig_post_image error: {exc}")
        return json.dumps({"error": str(exc)})


# ── Server Entry ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()

"""
Twitter MCP Server - Gold Tier
Exposes Twitter (X) tools to Claude Code via MCP.

Tools:
  - twitter_get_mentions   : Fetch recent mentions of your account
  - twitter_draft_post     : Write a HITL draft to Pending_Approval/ (safe — no API call)
  - twitter_post_tweet     : Post a tweet immediately (WARNING: bypasses HITL)
  - twitter_reply_tweet    : Reply to a tweet immediately (WARNING: bypasses HITL)

Auth (.env):
  TWITTER_BEARER_TOKEN        — App-only bearer token (read)
  TWITTER_API_KEY             — Consumer API key
  TWITTER_API_SECRET          — Consumer API secret
  TWITTER_ACCESS_TOKEN        — User access token (write)
  TWITTER_ACCESS_TOKEN_SECRET — User access token secret
  TWITTER_USERNAME            — Your handle without @

Logging: file only — stdout corrupts MCP stdio transport.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR     = PROJECT_ROOT / "Logs"
PENDING_DIR  = PROJECT_ROOT / "Pending_Approval"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
PENDING_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(PROJECT_ROOT / ".env")

# ── Config ─────────────────────────────────────────────────────────────────────
BEARER_TOKEN        = os.getenv("TWITTER_BEARER_TOKEN",         "")
API_KEY             = os.getenv("TWITTER_API_KEY",               "")
API_SECRET          = os.getenv("TWITTER_API_SECRET",            "")
ACCESS_TOKEN        = os.getenv("TWITTER_ACCESS_TOKEN",          "")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET",   "")
TWITTER_USERNAME    = os.getenv("TWITTER_USERNAME",              "")

# ── Logging (file only — never stdout) ────────────────────────────────────────
logger   = logging.getLogger("TwitterMCP")
log_file = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_TwitterMCP.log"
_fh = logging.FileHandler(log_file, encoding="utf-8")
_fh.setFormatter(logging.Formatter("[%(asctime)s] %(name)s %(levelname)s: %(message)s"))
logger.addHandler(_fh)
logger.setLevel(logging.INFO)

# ── Twitter client (lazy) ──────────────────────────────────────────────────────
_client = None


def _get_client():
    global _client
    if _client is None:
        try:
            import tweepy
        except ImportError:
            raise RuntimeError("tweepy not installed — run: pip install tweepy")
        _client = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=False,
        )
    return _client


def _log_action(action: str, details: dict):
    twitter_log = LOGS_DIR / "twitter.log"
    entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {action} | {json.dumps(details)}\n"
    with twitter_log.open("a", encoding="utf-8") as f:
        f.write(entry)
    logger.info(f"{action} | {details}")


def _credentials_ok() -> bool:
    return bool(BEARER_TOKEN and API_KEY and API_SECRET and ACCESS_TOKEN and ACCESS_TOKEN_SECRET)


# ── MCP App ────────────────────────────────────────────────────────────────────
mcp = FastMCP("twitter-mcp")


# ── Tools ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def twitter_get_mentions(max_results: int = 10) -> str:
    """
    Fetch recent tweets that mention your Twitter account.

    Args:
        max_results: Number of mentions to return (5-20, default 10)

    Returns: JSON array of recent mentions with author and text
    """
    if not _credentials_ok():
        return json.dumps({"error": "Twitter credentials not fully configured in .env"})
    if not TWITTER_USERNAME:
        return json.dumps({"error": "TWITTER_USERNAME not set in .env"})

    max_results = max(5, min(max_results, 20))

    try:
        import tweepy
        client = _get_client()
        query = f"@{TWITTER_USERNAME} -is:retweet"
        resp = client.search_recent_tweets(
            query=query,
            max_results=max_results,
            tweet_fields=["author_id", "created_at", "text", "conversation_id", "public_metrics"],
            expansions=["author_id"],
            user_fields=["name", "username"],
        )
    except Exception as exc:
        logger.error(f"twitter_get_mentions error: {exc}")
        return json.dumps({"error": str(exc)})

    if not resp.data:
        _log_action("TWITTER_GET_MENTIONS", {"count": 0})
        return json.dumps([])

    users = {}
    if resp.includes and resp.includes.get("users"):
        for u in resp.includes["users"]:
            users[str(u.id)] = {"name": u.name, "username": u.username}

    results = []
    for tweet in resp.data:
        author = users.get(str(tweet.author_id), {})
        metrics = dict(tweet.public_metrics or {})
        results.append({
            "tweet_id":   str(tweet.id),
            "author":     f"{author.get('name', '?')} (@{author.get('username', '?')})",
            "text":       tweet.text,
            "created_at": str(tweet.created_at or "")[:19],
            "likes":      metrics.get("like_count", 0),
            "replies":    metrics.get("reply_count", 0),
        })

    _log_action("TWITTER_GET_MENTIONS", {"count": len(results)})
    return json.dumps(results, indent=2)


@mcp.tool()
def twitter_draft_post(
    text: str,
    tweet_type: str = "tweet",
    reply_to_tweet_id: str = "",
    notes: str = "",
) -> str:
    """
    Create a HITL draft tweet in Pending_Approval/ — does NOT post to Twitter.
    Human must review and move to Approved/ before posting.

    Args:
        text:               Tweet text (max 280 characters, required)
        tweet_type:         "tweet" (new post) or "reply" (reply to existing tweet)
        reply_to_tweet_id:  Tweet ID to reply to (required if tweet_type="reply")
        notes:              Internal notes visible in the approval file

    Returns: JSON with path to the created Pending_Approval file
    """
    valid_types = {"tweet", "reply"}
    if tweet_type not in valid_types:
        return json.dumps({"error": f"Invalid tweet_type. Must be one of: {valid_types}"})
    if not text.strip():
        return json.dumps({"error": "text is required"})
    if len(text) > 280:
        return json.dumps({"error": f"text exceeds 280 characters ({len(text)})"})
    if tweet_type == "reply" and not reply_to_tweet_id:
        return json.dumps({"error": "reply_to_tweet_id is required when tweet_type='reply'"})

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"TWITTER_{tweet_type.upper()}_{timestamp}.md"
    filepath  = PENDING_DIR / filename
    today     = datetime.now().strftime("%Y-%m-%d")

    content = f"""---
date: {today}
type: twitter_post
tweet_type: {tweet_type}
text: "{text.replace('"', "'")}"
reply_to_tweet_id: "{reply_to_tweet_id}"
status: pending
requires_approval: true
priority: P2
tags: [twitter, {tweet_type}, social]
summary: "Twitter {tweet_type} draft — awaiting approval"
---

# Twitter Post Draft — {tweet_type.title()}

## Tweet Content

**Type:** {tweet_type}
**Text:**

> {text}

**Reply to Tweet ID:** {reply_to_tweet_id or "(none — new tweet)"}
**Character count:** {len(text)} / 280

## Action Required

- [ ] Review text for tone, accuracy, and brand voice
- [ ] Verify reply_to_tweet_id is correct (if replying)
- [ ] Move to `Approved/` to post the tweet
- [ ] Move to `Rejected/` to cancel

## Notes

{notes or "No additional notes."}

---
*Draft created by Twitter MCP | Requires human approval before posting*
"""

    filepath.write_text(content, encoding="utf-8")
    _log_action("TWITTER_DRAFT", {"tweet_type": tweet_type, "file": filename, "chars": len(text)})
    return json.dumps({"status": "draft_created", "path": str(filepath), "file": filename})


@mcp.tool()
def twitter_post_tweet(text: str) -> str:
    """
    Post a new tweet immediately.
    WARNING: This posts immediately. Always prefer twitter_draft_post for HITL flow.

    Args:
        text: Tweet text (max 280 characters, required)

    Returns: JSON with tweet_id on success
    """
    if not _credentials_ok():
        return json.dumps({"error": "Twitter credentials not fully configured in .env"})
    if not text.strip():
        return json.dumps({"error": "text is required"})
    if len(text) > 280:
        return json.dumps({"error": f"text exceeds 280 characters ({len(text)})"})

    try:
        client = _get_client()
        resp   = client.create_tweet(text=text)
        tweet_id = str(resp.data["id"])
        _log_action("TWITTER_POST_TWEET", {"tweet_id": tweet_id, "text_preview": text[:60]})
        return json.dumps({"status": "posted", "platform": "twitter", "tweet_id": tweet_id})
    except Exception as exc:
        logger.error(f"twitter_post_tweet error: {exc}")
        return json.dumps({"error": str(exc)})


@mcp.tool()
def twitter_reply_tweet(text: str, reply_to_tweet_id: str) -> str:
    """
    Reply to an existing tweet immediately.
    WARNING: This posts immediately. Always prefer twitter_draft_post for HITL flow.

    Args:
        text:               Reply text (max 280 characters, required)
        reply_to_tweet_id:  The tweet ID to reply to (required)

    Returns: JSON with tweet_id on success
    """
    if not _credentials_ok():
        return json.dumps({"error": "Twitter credentials not fully configured in .env"})
    if not text.strip():
        return json.dumps({"error": "text is required"})
    if not reply_to_tweet_id:
        return json.dumps({"error": "reply_to_tweet_id is required"})
    if len(text) > 280:
        return json.dumps({"error": f"text exceeds 280 characters ({len(text)})"})

    try:
        client   = _get_client()
        resp     = client.create_tweet(text=text, in_reply_to_tweet_id=reply_to_tweet_id)
        tweet_id = str(resp.data["id"])
        _log_action("TWITTER_REPLY_TWEET", {
            "tweet_id":          tweet_id,
            "reply_to_tweet_id": reply_to_tweet_id,
            "text_preview":      text[:60],
        })
        return json.dumps({
            "status":            "posted",
            "platform":          "twitter",
            "tweet_id":          tweet_id,
            "reply_to_tweet_id": reply_to_tweet_id,
        })
    except Exception as exc:
        logger.error(f"twitter_reply_tweet error: {exc}")
        return json.dumps({"error": str(exc)})


# ── Server Entry ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()

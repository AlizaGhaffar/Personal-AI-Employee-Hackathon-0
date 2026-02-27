"""
Twitter Watcher - Gold Tier
Polls Twitter (X) API v2 for new mentions and DMs,
creates .md files in Needs_Action/ with TWITTER_ prefix.

Follows BaseWatcher pattern exactly (same as FacebookWatcher).

Monitors:
  - Mentions: tweets containing @your_handle (via search_recent_tweets)
  - DMs: direct messages (optional, requires Elevated/Basic API access,
         enabled via TWITTER_WATCH_DMS=true)

Auth:
  - OAuth 2.0 User Context via tweepy.Client
  - Requires: TWITTER_BEARER_TOKEN, TWITTER_API_KEY, TWITTER_API_SECRET,
              TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET

Rate Limits (Free tier): search = 1 req / 15 min → set interval ≥ 900s
Rate Limits (Basic tier): search = 60 req / 15 min → interval 120s is fine

Processed IDs saved to: Watchers/.twitter_processed.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
import os

# ── resolve paths before relative import ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

load_dotenv(PROJECT_ROOT / ".env")

try:
    import tweepy
except ImportError:
    print("[ERROR] tweepy not installed. Run: pip install tweepy")
    sys.exit(1)

from base_watcher import BaseWatcher

# ── Config from .env ───────────────────────────────────────────────────────────
BEARER_TOKEN        = os.getenv("TWITTER_BEARER_TOKEN",         "")
API_KEY             = os.getenv("TWITTER_API_KEY",               "")
API_SECRET          = os.getenv("TWITTER_API_SECRET",            "")
ACCESS_TOKEN        = os.getenv("TWITTER_ACCESS_TOKEN",          "")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET",   "")
TWITTER_USERNAME    = os.getenv("TWITTER_USERNAME",              "")   # without @
WATCH_DMS           = os.getenv("TWITTER_WATCH_DMS", "false").lower() == "true"
CHECK_INTERVAL      = int(os.getenv("TWITTER_CHECK_INTERVAL_SECONDS", "300"))

PROCESSED_FILE = Path(__file__).resolve().parent / ".twitter_processed.json"


def _build_client() -> tweepy.Client:
    """Build a tweepy Client with full read+write credentials."""
    return tweepy.Client(
        bearer_token=BEARER_TOKEN,
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET,
        wait_on_rate_limit=False,
    )


class TwitterWatcher(BaseWatcher):
    """
    Watches Twitter/X for new mentions and DMs.
    Creates one Needs_Action/ file per new mention or DM.
    """

    def __init__(self, vault_path: str):
        super().__init__(vault_path, check_interval=CHECK_INTERVAL)
        self.processed_ids = self._load_processed()
        self._validate_config()
        self.client = _build_client()
        self._twitter_user_id = None  # resolved lazily
        self.logger.info(
            f"TwitterWatcher ready | @{TWITTER_USERNAME} | "
            f"DMs: {WATCH_DMS} | "
            f"Previously seen: {len(self.processed_ids)} item(s)"
        )

    # ── Setup ──────────────────────────────────────────────────────────────────

    def _validate_config(self):
        missing = []
        if not BEARER_TOKEN:
            missing.append("TWITTER_BEARER_TOKEN")
        if not API_KEY:
            missing.append("TWITTER_API_KEY")
        if not API_SECRET:
            missing.append("TWITTER_API_SECRET")
        if not ACCESS_TOKEN:
            missing.append("TWITTER_ACCESS_TOKEN")
        if not ACCESS_TOKEN_SECRET:
            missing.append("TWITTER_ACCESS_TOKEN_SECRET")
        if not TWITTER_USERNAME:
            missing.append("TWITTER_USERNAME")
        if missing:
            self.logger.error(f"Missing .env variables: {', '.join(missing)}")
            self.logger.error("Add them to .env and restart.")
            sys.exit(1)

    def _load_processed(self) -> set:
        if PROCESSED_FILE.exists():
            try:
                return set(json.loads(PROCESSED_FILE.read_text(encoding="utf-8")))
            except Exception:
                return set()
        return set()

    def _save_processed(self):
        PROCESSED_FILE.write_text(
            json.dumps(list(self.processed_ids)), encoding="utf-8"
        )

    def _get_user_id(self) -> str:
        """Resolve @username to numeric user ID (cached)."""
        if not self._twitter_user_id:
            resp = self.client.get_user(username=TWITTER_USERNAME)
            if resp.data:
                self._twitter_user_id = str(resp.data.id)
                self.logger.info(f"Resolved @{TWITTER_USERNAME} → user_id={self._twitter_user_id}")
            else:
                raise RuntimeError(f"Cannot resolve @{TWITTER_USERNAME}: {resp.errors}")
        return self._twitter_user_id

    # ── BaseWatcher Interface ──────────────────────────────────────────────────

    def check_for_updates(self) -> list:
        """
        Fetch new mentions and optionally DMs.
        Returns list of item dicts not yet processed.
        """
        items = []
        items.extend(self._fetch_mentions())
        if WATCH_DMS:
            items.extend(self._fetch_dms())
        if not items:
            self.logger.info("No new Twitter mentions or DMs")
        return items

    def _fetch_mentions(self) -> list:
        """Search recent tweets mentioning @username."""
        try:
            query = f"@{TWITTER_USERNAME} -is:retweet"
            resp = self.client.search_recent_tweets(
                query=query,
                max_results=10,
                tweet_fields=["author_id", "created_at", "text", "conversation_id",
                               "in_reply_to_user_id", "public_metrics"],
                expansions=["author_id"],
                user_fields=["name", "username"],
            )
        except tweepy.errors.TooManyRequests:
            self.logger.warning("Rate limit reached for mentions — skipping this cycle")
            return []
        except tweepy.errors.TweepyException as exc:
            self.logger.error(f"Twitter API error (mentions): {exc}")
            return []

        if not resp.data:
            return []

        # Build user lookup from includes
        users = {}
        if resp.includes and resp.includes.get("users"):
            for u in resp.includes["users"]:
                users[str(u.id)] = {"name": u.name, "username": u.username}

        new = []
        for tweet in resp.data:
            tweet_id = str(tweet.id)
            if tweet_id not in self.processed_ids:
                author = users.get(str(tweet.author_id), {})
                new.append({
                    "kind":        "mention",
                    "id":          tweet_id,
                    "author_id":   str(tweet.author_id),
                    "author_name": author.get("name", "Unknown"),
                    "author_user": author.get("username", "unknown"),
                    "text":        tweet.text,
                    "created_at":  str(tweet.created_at or ""),
                    "conversation_id": str(tweet.conversation_id or tweet_id),
                    "metrics":     dict(tweet.public_metrics or {}),
                })
        return new

    def _fetch_dms(self) -> list:
        """Fetch recent DM events (requires Elevated API access)."""
        try:
            user_id = self._get_user_id()
            resp = self.client.get_dm_events(
                dm_event_fields=["id", "text", "created_at", "sender_id"],
                expansions=["sender_id"],
                user_fields=["name", "username"],
                max_results=5,
            )
        except tweepy.errors.Forbidden:
            self.logger.warning("DM access forbidden — Elevated API access required. Disabling DM watch.")
            global WATCH_DMS
            WATCH_DMS = False
            return []
        except tweepy.errors.TooManyRequests:
            self.logger.warning("Rate limit reached for DMs — skipping this cycle")
            return []
        except tweepy.errors.TweepyException as exc:
            self.logger.error(f"Twitter API error (DMs): {exc}")
            return []

        if not resp.data:
            return []

        users = {}
        if resp.includes and resp.includes.get("users"):
            for u in resp.includes["users"]:
                users[str(u.id)] = {"name": u.name, "username": u.username}

        new = []
        for dm in resp.data:
            dm_id = str(dm.id)
            sender_id = str(dm.sender_id or "")
            # Skip DMs sent by ourselves
            if sender_id == self._twitter_user_id:
                continue
            if dm_id not in self.processed_ids:
                sender = users.get(sender_id, {})
                new.append({
                    "kind":          "dm",
                    "id":            dm_id,
                    "sender_id":     sender_id,
                    "sender_name":   sender.get("name", "Unknown"),
                    "sender_user":   sender.get("username", "unknown"),
                    "text":          dm.text or "",
                    "created_at":    str(dm.created_at or ""),
                })
        return new

    def create_action_file(self, item: dict) -> Path:
        """Create a Needs_Action/ markdown file for a mention or DM."""
        kind = item["kind"]
        item_id = item["id"]

        if kind == "mention":
            return self._create_mention_file(item)
        else:
            return self._create_dm_file(item)

    def _create_mention_file(self, item: dict) -> Path:
        tweet_id    = item["id"]
        author_name = item["author_name"]
        author_user = item["author_user"]
        text        = item["text"]
        created_at  = item["created_at"][:19].replace("T", " ") if item["created_at"] else "Unknown"
        conv_id     = item["conversation_id"]
        metrics     = item.get("metrics", {})

        filepath = self.needs_action / f"TWITTER_{tweet_id}.md"

        content = f"""---
type: twitter_mention
source: twitter_x
tweet_id: "{tweet_id}"
conversation_id: "{conv_id}"
author_name: "{author_name}"
author_username: "@{author_user}"
author_id: "{item['author_id']}"
date: "{created_at}"
priority: P2
status: pending
requires_approval: true
tags: [twitter, mention, social]
summary: "Twitter mention from @{author_user}: {text[:80].replace(chr(10), ' ')}"
---

# Twitter Mention: @{author_user}

| Field           | Value                     |
|-----------------|---------------------------|
| From            | {author_name} (@{author_user}) |
| Tweet ID        | {tweet_id}                |
| Conversation ID | {conv_id}                 |
| Received        | {created_at}              |
| Likes           | {metrics.get('like_count', 0)} |
| Replies         | {metrics.get('reply_count', 0)} |

## Tweet Content

> {text}

## Suggested Actions

- [ ] Reply to mention (use `/draft-reply` or twitter MCP)
- [ ] Like/retweet if relevant
- [ ] Convert to lead / log in CRM if business inquiry
- [ ] Archive after response
"""

        filepath.write_text(content, encoding="utf-8")
        self.processed_ids.add(tweet_id)
        self._save_processed()

        self.logger.info(f"NEW MENTION: from @{author_user} → {filepath.name}")
        return filepath

    def _create_dm_file(self, item: dict) -> Path:
        dm_id       = item["id"]
        sender_name = item["sender_name"]
        sender_user = item["sender_user"]
        text        = item["text"]
        created_at  = item["created_at"][:19].replace("T", " ") if item["created_at"] else "Unknown"

        filepath = self.needs_action / f"TWITTER_DM_{dm_id}.md"

        content = f"""---
type: twitter_dm
source: twitter_x
dm_id: "{dm_id}"
sender_name: "{sender_name}"
sender_username: "@{sender_user}"
sender_id: "{item['sender_id']}"
date: "{created_at}"
priority: P2
status: pending
requires_approval: true
tags: [twitter, dm, social]
summary: "Twitter DM from @{sender_user}: {text[:80].replace(chr(10), ' ')}"
---

# Twitter DM: @{sender_user}

| Field       | Value                        |
|-------------|------------------------------|
| From        | {sender_name} (@{sender_user}) |
| DM ID       | {dm_id}                      |
| Received    | {created_at}                 |

## Message Content

> {text}

## Suggested Actions

- [ ] Reply via Twitter DM (use twitter MCP)
- [ ] Convert to lead / log in CRM if business inquiry
- [ ] Archive after response
"""

        filepath.write_text(content, encoding="utf-8")
        self.processed_ids.add(dm_id)
        self._save_processed()

        self.logger.info(f"NEW DM: from @{sender_user} → {filepath.name}")
        return filepath


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    if not BEARER_TOKEN or not API_KEY or not TWITTER_USERNAME:
        print("[ERROR] TWITTER_BEARER_TOKEN, TWITTER_API_KEY, and TWITTER_USERNAME must be set in .env")
        print("        Get credentials at: https://developer.twitter.com/en/portal/dashboard")
        sys.exit(1)

    print("=" * 55)
    print("  TWITTER WATCHER - Gold Tier")
    print(f"  Handle  : @{TWITTER_USERNAME}")
    print(f"  Interval: {CHECK_INTERVAL}s")
    print(f"  DMs     : {WATCH_DMS}")
    print(f"  Output  : {PROJECT_ROOT / 'Needs_Action'}")
    print("=" * 55)

    watcher = TwitterWatcher(str(PROJECT_ROOT))
    watcher.run()


if __name__ == "__main__":
    main()

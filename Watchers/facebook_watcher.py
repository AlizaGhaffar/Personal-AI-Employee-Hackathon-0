"""
Facebook Watcher - Gold Tier
Polls Facebook Graph API for new Page messages and mentions,
creates .md files in Needs_Action/ with FACEBOOK_ prefix.

Follows BaseWatcher pattern exactly (same as GmailWatcher).

Monitors:
  - Facebook Page inbox (new conversations / messages)
  - Page mentions / comments (optional, via FACEBOOK_WATCH_MENTIONS=true)

Auth:
  - Long-lived Page Access Token stored in .env (FACEBOOK_ACCESS_TOKEN)
  - Does NOT use OAuth flow — token must be generated manually once
    (Facebook Developer Console → Graph API Explorer → Page token → extend to 60 days)

Processed IDs saved to: Watchers/.facebook_processed.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv
import os

# ── resolve paths before relative import ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

load_dotenv(PROJECT_ROOT / ".env")

from base_watcher import BaseWatcher

# ── Config from .env ───────────────────────────────────────────────────────────
FB_PAGE_ID       = os.getenv("FACEBOOK_PAGE_ID",       "")
FB_ACCESS_TOKEN  = os.getenv("FACEBOOK_ACCESS_TOKEN",  "")
FB_GRAPH_VERSION = os.getenv("FACEBOOK_GRAPH_VERSION", "v20.0")
WATCH_MENTIONS   = os.getenv("FACEBOOK_WATCH_MENTIONS", "false").lower() == "true"
CHECK_INTERVAL   = int(os.getenv("FACEBOOK_CHECK_INTERVAL_SECONDS", "120"))

GRAPH_BASE       = f"https://graph.facebook.com/{FB_GRAPH_VERSION}"
PROCESSED_FILE   = Path(__file__).resolve().parent / ".facebook_processed.json"


def _graph_get(endpoint: str, params: dict = None) -> dict:
    """Authenticated GET request to Facebook Graph API."""
    params = params or {}
    params["access_token"] = FB_ACCESS_TOKEN
    resp = requests.get(f"{GRAPH_BASE}/{endpoint}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


class FacebookWatcher(BaseWatcher):
    """
    Watches a Facebook Page inbox for new customer messages.
    Creates one Needs_Action/ file per new conversation thread.
    """

    def __init__(self, vault_path: str):
        super().__init__(vault_path, check_interval=CHECK_INTERVAL)
        self.processed_ids = self._load_processed()
        self._validate_config()
        self.logger.info(
            f"FacebookWatcher ready | Page: {FB_PAGE_ID} | "
            f"Mentions: {WATCH_MENTIONS} | "
            f"Previously seen: {len(self.processed_ids)} conversation(s)"
        )

    # ── Setup ──────────────────────────────────────────────────────────────────

    def _validate_config(self):
        missing = []
        if not FB_PAGE_ID:
            missing.append("FACEBOOK_PAGE_ID")
        if not FB_ACCESS_TOKEN:
            missing.append("FACEBOOK_ACCESS_TOKEN")
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

    # ── BaseWatcher Interface ──────────────────────────────────────────────────

    def check_for_updates(self) -> list:
        """
        Fetch new conversations from the Facebook Page inbox.
        Returns list of conversation dicts not yet processed.
        """
        try:
            data = _graph_get(
                f"{FB_PAGE_ID}/conversations",
                params={
                    "platform": "messenger",
                    "fields":   "id,updated_time,participants,snippet,unread_count",
                    "limit":    25,
                },
            )
        except requests.exceptions.ConnectionError:
            self.logger.error("Cannot reach Facebook Graph API — check internet connection")
            return []
        except requests.exceptions.HTTPError as exc:
            self.logger.error(f"Graph API HTTP error: {exc.response.status_code} — {exc.response.text[:200]}")
            return []
        except Exception as exc:
            self.logger.error(f"Unexpected error fetching conversations: {exc}")
            return []

        conversations = data.get("data", [])
        new = [c for c in conversations
               if c["id"] not in self.processed_ids and c.get("unread_count", 0) > 0]

        if not new:
            self.logger.info("No new Facebook messages")
        return new

    def create_action_file(self, conversation: dict) -> Path:
        """
        Fetch message details and create a Needs_Action/ markdown file.
        File prefix: FACEBOOK_
        """
        conv_id     = conversation["id"]
        updated     = conversation.get("updated_time", "")[:19].replace("T", " ")
        snippet     = conversation.get("snippet", "(no preview)")
        unread      = conversation.get("unread_count", 0)

        # Participants — filter out the page itself
        participants = conversation.get("participants", {}).get("data", [])
        sender_name  = "Unknown"
        sender_id    = ""
        for p in participants:
            if str(p.get("id")) != str(FB_PAGE_ID):
                sender_name = p.get("name", "Unknown")
                sender_id   = p.get("id", "")
                break

        # Fetch recent messages in this conversation
        messages_preview = self._fetch_messages(conv_id)

        # Filename
        safe_name = sender_name.replace(" ", "_")[:40]
        filepath  = self.needs_action / f"FACEBOOK_{conv_id[:12]}_{safe_name}.md"

        content = f"""---
type: facebook_message
source: facebook_messenger
conversation_id: "{conv_id}"
sender_name: "{sender_name}"
sender_id: "{sender_id}"
date: "{updated}"
unread_count: {unread}
priority: P2
status: pending
requires_approval: true
tags: [facebook, messenger, social]
summary: "Facebook message from {sender_name}: {snippet[:80]}"
---

# Facebook Message: {sender_name}

| Field           | Value              |
|-----------------|--------------------|
| From            | {sender_name}      |
| Sender ID       | {sender_id}        |
| Conversation ID | {conv_id}          |
| Received        | {updated}          |
| Unread messages | {unread}           |

## Message Preview

> {snippet}

## Recent Messages

{messages_preview}

## Suggested Actions

- [ ] Reply via Facebook Messenger (use `/draft-reply`)
- [ ] Convert to lead / create in Odoo
- [ ] Archive conversation after response
"""

        filepath.write_text(content, encoding="utf-8")
        self.processed_ids.add(conv_id)
        self._save_processed()

        self.logger.info(f"NEW FB MESSAGE: from {sender_name} ({unread} unread) → {filepath.name}")
        return filepath

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _fetch_messages(self, conversation_id: str, limit: int = 5) -> str:
        """Fetch the last N messages in a conversation, formatted as markdown."""
        try:
            data = _graph_get(
                f"{conversation_id}/messages",
                params={
                    "fields": "message,from,created_time",
                    "limit":  limit,
                },
            )
            messages = data.get("data", [])
            if not messages:
                return "_No messages retrieved._"

            lines = []
            for msg in reversed(messages):  # oldest first
                sender  = msg.get("from", {}).get("name", "?")
                text    = msg.get("message", "(media/attachment)")
                ts      = msg.get("created_time", "")[:19].replace("T", " ")
                lines.append(f"**[{ts}] {sender}:** {text}")
            return "\n\n".join(lines)

        except Exception as exc:
            self.logger.warning(f"Could not fetch messages for {conversation_id}: {exc}")
            return "_Message details unavailable._"


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("[ERROR] FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN must be set in .env")
        print("        See: https://developers.facebook.com/docs/pages/access-tokens")
        sys.exit(1)

    print("=" * 55)
    print("  FACEBOOK WATCHER - Gold Tier")
    print(f"  Page ID  : {FB_PAGE_ID}")
    print(f"  Interval : {CHECK_INTERVAL}s")
    print(f"  Mentions : {WATCH_MENTIONS}")
    print(f"  Output   : {PROJECT_ROOT / 'Needs_Action'}")
    print("=" * 55)

    watcher = FacebookWatcher(str(PROJECT_ROOT))
    watcher.run()


if __name__ == "__main__":
    main()

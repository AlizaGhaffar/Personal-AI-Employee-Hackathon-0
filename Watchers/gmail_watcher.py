"""
Gmail Watcher - Silver Tier
Polls Gmail for unread important emails every 2 minutes,
creates .md files in Needs_Action/ with EMAIL_ prefix.

First run opens browser for Google OAuth consent.
Tokens are stored for reuse (no repeated login).
"""

import os
import sys
import json
import base64
from pathlib import Path
from datetime import datetime
from email.utils import parsedate_to_datetime

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from base_watcher import BaseWatcher

# -- Config --
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

CREDENTIALS_FILE = PROJECT_ROOT / os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = PROJECT_ROOT / os.getenv("GMAIL_TOKEN_FILE", "token.json")
CHECK_INTERVAL = int(os.getenv("GMAIL_CHECK_INTERVAL_SECONDS", "120"))

# Read-only scope (safe - can only read, not send)
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Track processed emails to avoid duplicates
PROCESSED_FILE = Path(__file__).resolve().parent / ".gmail_processed.json"


def authenticate() -> Credentials:
    """Authenticate with Gmail API using OAuth2 with offline access."""
    creds = None

    # Load existing token
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Refresh or create new token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[AUTH] Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print(f"[ERROR] Credentials file not found: {CREDENTIALS_FILE}")
                print("Download it from Google Cloud Console and place in project root.")
                sys.exit(1)

            print("[AUTH] Opening browser for Google OAuth consent...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES,
            )
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
            print("[AUTH] Authentication successful!")

        # Save token for reuse
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"[AUTH] Token saved to {TOKEN_FILE}")

    return creds


class GmailWatcher(BaseWatcher):
    def __init__(self, vault_path: str):
        super().__init__(vault_path, check_interval=CHECK_INTERVAL)
        self.creds = authenticate()
        self.service = build("gmail", "v1", credentials=self.creds)
        self.processed_ids = self._load_processed()
        self.logger.info(f"Connected to Gmail API ({len(self.processed_ids)} previously processed)")

    def _load_processed(self) -> set:
        """Load previously processed email IDs from disk."""
        if PROCESSED_FILE.exists():
            try:
                return set(json.loads(PROCESSED_FILE.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, Exception):
                return set()
        return set()

    def _save_processed(self):
        """Save processed email IDs to disk."""
        PROCESSED_FILE.write_text(
            json.dumps(list(self.processed_ids)), encoding="utf-8"
        )

    def check_for_updates(self) -> list:
        """Check Gmail for unread important emails."""
        # Refresh token if expired
        if self.creds.expired and self.creds.refresh_token:
            self.logger.info("Refreshing expired token...")
            self.creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(self.creds.to_json())

        try:
            results = self.service.users().messages().list(
                userId="me",
                q="is:unread is:important",
                maxResults=10,
            ).execute()
        except Exception as e:
            self.logger.error(f"Gmail API error: {e}")
            return []

        messages = results.get("messages", [])
        new_messages = [m for m in messages if m["id"] not in self.processed_ids]

        if not new_messages:
            self.logger.info("No new unread important emails")

        return new_messages

    def create_action_file(self, message) -> Path:
        """Fetch full email and create markdown file in Needs_Action/."""
        msg = self.service.users().messages().get(
            userId="me", id=message["id"], format="full"
        ).execute()

        # Extract headers
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        subject = headers.get("Subject", "No Subject")
        sender = headers.get("From", "Unknown")
        to = headers.get("To", "Unknown")
        date_str = headers.get("Date", "")
        snippet = msg.get("snippet", "")

        # Parse date
        try:
            email_date = parsedate_to_datetime(date_str)
            date_display = email_date.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            date_display = date_str

        # Extract body
        body = self._extract_body(msg["payload"])

        # Build filename (sanitized)
        safe_subject = self._sanitize(subject)
        filepath = self.needs_action / f"EMAIL_{message['id']}.md"

        content = f"""---
type: email
source: gmail
message_id: {message['id']}
subject: "{subject}"
from: "{sender}"
to: "{to}"
date: "{date_display}"
priority: high
status: pending
---

# Email: {subject}

| Field   | Value |
|---------|-------|
| From    | {sender} |
| To      | {to} |
| Date    | {date_display} |
| Subject | {subject} |

## Snippet

{snippet}

## Body

{body}

## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Archive after processing
"""

        filepath.write_text(content, encoding="utf-8")

        # Mark as processed and save
        self.processed_ids.add(message["id"])
        self._save_processed()

        self.logger.info(f"NEW EMAIL: \"{subject}\" from {sender}")
        return filepath

    def _extract_body(self, payload) -> str:
        """Recursively extract plain text body from email payload."""
        if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(
                payload["body"]["data"]
            ).decode("utf-8", errors="replace")

        if "parts" in payload:
            for part in payload["parts"]:
                result = self._extract_body(part)
                if result:
                    return result

        if payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(
                payload["body"]["data"]
            ).decode("utf-8", errors="replace")

        return "(No text body found)"

    def _sanitize(self, name: str) -> str:
        """Remove characters not safe for filenames."""
        for ch in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
            name = name.replace(ch, '_')
        return name[:80]


def main():
    print("=" * 55)
    print("  GMAIL WATCHER - Silver Tier")
    print(f"  Checking every {CHECK_INTERVAL} seconds")
    print(f"  Query: is:unread is:important")
    print(f"  Output: {PROJECT_ROOT / 'Needs_Action'}")
    print("=" * 55)

    watcher = GmailWatcher(str(PROJECT_ROOT))
    watcher.run()


if __name__ == "__main__":
    main()

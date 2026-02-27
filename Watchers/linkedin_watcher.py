"""
LinkedIn Watcher - Silver Tier (Playwright-based)
Monitors LinkedIn messaging for sales/business keywords,
creates .md files in Needs_Action/ with LINKEDIN_ prefix.

Follows the WhatsApp Watcher pattern from Hackathon Guide exactly:
- Playwright persistent session for login state
- Keyword matching on unread conversations
- BaseWatcher polling loop with check_interval

First run opens browser for manual LinkedIn login.
Session is saved for reuse (no repeated login).
"""

import json
import time
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright
from base_watcher import BaseWatcher


# -- Config --
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHECK_INTERVAL = 60  # seconds between scans
SESSION_DIR = Path(__file__).resolve().parent / ".linkedin_session"

# Track processed conversations to avoid duplicates
PROCESSED_FILE = Path(__file__).resolve().parent / ".linkedin_processed.json"


LOGIN_WAIT_TIMEOUT = 120  # seconds to wait for manual login
PAGE_LOAD_TIMEOUT = 60000  # ms for page navigation
SELECTOR_TIMEOUT = 30000  # ms for element selectors


class LinkedInWatcher(BaseWatcher):
    def __init__(self, vault_path: str, session_path: str):
        super().__init__(vault_path, check_interval=CHECK_INTERVAL)
        self.session_path = Path(session_path)
        self.keywords = ["sales", "client", "project", "business",
                         "invoice", "deal", "partnership", "proposal",
                         "pricing", "budget", "service", "offer"]
        self.processed_ids = self._load_processed()
        self._login_verified = False
        self._playwright = None
        self._browser = None
        self._page = None
        self.logger.info(
            f"LinkedIn Watcher ready ({len(self.processed_ids)} previously processed)"
        )

    # -- Persistence helpers --

    def _load_processed(self) -> set:
        """Load previously processed message IDs from disk."""
        if PROCESSED_FILE.exists():
            try:
                return set(json.loads(PROCESSED_FILE.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, Exception):
                return set()
        return set()

    def _save_processed(self):
        """Save processed message IDs to disk."""
        PROCESSED_FILE.write_text(
            json.dumps(list(self.processed_ids)), encoding="utf-8",
        )

    # -- Browser lifecycle (persistent — stays open across cycles) --

    def _ensure_browser(self):
        """Launch browser once and reuse across polling cycles.
        Browser stays open so session is preserved and user can interact.
        """
        if self._browser and self._page:
            try:
                # Quick health check — if browser was closed externally, reconnect
                _ = self._page.url
                return
            except Exception:
                self.logger.info("Browser was closed externally, relaunching...")
                self._browser = None
                self._page = None

        self.logger.info("Launching persistent browser (stays open)...")
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch_persistent_context(
            str(self.session_path),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self._page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()

    def close_browser(self):
        """Gracefully close browser (called on shutdown)."""
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._page = None
        self._playwright = None

    # -- Login helpers --

    def _wait_for_login(self, page) -> bool:
        """Wait for user to complete manual LinkedIn login.

        Checks every 3 seconds for up to LOGIN_WAIT_TIMEOUT seconds.
        Returns True once logged in, False on timeout.
        """
        self.logger.info(
            "Waiting for LinkedIn login... "
            f"You have {LOGIN_WAIT_TIMEOUT} seconds to log in manually."
        )
        print("\n" + "=" * 58)
        print("  MANUAL LOGIN REQUIRED")
        print("  Please log in to LinkedIn in the browser window.")
        print(f"  Waiting up to {LOGIN_WAIT_TIMEOUT} seconds...")
        print("  Browser will STAY OPEN — take your time.")
        print("=" * 58 + "\n")

        elapsed = 0
        poll_interval = 3  # seconds
        while elapsed < LOGIN_WAIT_TIMEOUT:
            try:
                url = page.url
            except Exception:
                # Browser was closed by user
                return False

            if any(path in url for path in ["/feed", "/messaging", "/mynetwork", "/in/"]):
                self.logger.info("LinkedIn login detected! Session saved.")
                print("  Login successful! Session saved for future runs.\n")
                self._login_verified = True
                return True

            page.wait_for_timeout(poll_interval * 1000)
            elapsed += poll_interval
            remaining = LOGIN_WAIT_TIMEOUT - elapsed
            if remaining > 0 and remaining % 15 == 0:
                print(f"  Still waiting... {remaining}s remaining")

        self.logger.warning("Login wait timed out. Will retry next cycle.")
        print("  Login timed out. Will retry on next cycle.\n")
        return False

    def _is_logged_in(self, page) -> bool:
        """Quick check if the current page shows a logged-in state."""
        url = page.url
        if any(path in url for path in ["/feed", "/messaging", "/mynetwork", "/in/"]):
            return True
        if "/login" in url or "/signup" in url or "linkedin.com/uas" in url:
            return False
        # Check for nav element only visible when logged in
        try:
            nav = page.query_selector("nav.global-nav, header.global-nav")
            return nav is not None
        except Exception:
            return False

    # -- BaseWatcher interface --

    def check_for_updates(self) -> list:
        """Check LinkedIn messaging for unread keyword-matched chats.
        Browser stays open persistently — never auto-closed between cycles.
        """
        self._ensure_browser()
        page = self._page

        try:
            page.goto("https://www.linkedin.com/messaging/",
                      wait_until="domcontentloaded",
                      timeout=PAGE_LOAD_TIMEOUT)

            # Check if login is needed
            if not self._is_logged_in(page):
                if not self._wait_for_login(page):
                    self.logger.info("Not logged in yet — will retry next cycle.")
                    return []
                # After login, navigate to messaging
                page.goto("https://www.linkedin.com/messaging/",
                          wait_until="domcontentloaded",
                          timeout=PAGE_LOAD_TIMEOUT)

            self._login_verified = True

            # Wait for messaging list to load
            page.wait_for_selector(
                "ul.msg-conversations-container__conversations-list",
                timeout=SELECTOR_TIMEOUT,
            )

            # Find unread conversation items
            unread = page.query_selector_all(
                "li.msg-conversation-listitem--unread"
            )

            messages = []
            for chat in unread:
                try:
                    name_el = chat.query_selector(
                        "h3.msg-conversation-listitem__participant-names"
                    )
                    sender = name_el.inner_text().strip() if name_el else "Unknown"

                    preview_el = chat.query_selector(
                        "p.msg-conversation-card__message-snippet"
                    )
                    preview = preview_el.inner_text().strip() if preview_el else ""

                    msg_id = f"{sender}_{hash(preview)}"

                    if msg_id in self.processed_ids:
                        continue

                    text_lower = f"{sender} {preview}".lower()
                    matched = [kw for kw in self.keywords if kw in text_lower]

                    if matched:
                        chat.click()
                        page.wait_for_timeout(2000)

                        msg_bubbles = page.query_selector_all(
                            "div.msg-s-event-listitem__body"
                        )
                        full_text = ""
                        for bubble in msg_bubbles[-5:]:
                            full_text += bubble.inner_text().strip() + "\n"

                        messages.append({
                            "id": msg_id,
                            "sender": sender,
                            "preview": preview,
                            "full_text": full_text.strip() or preview,
                            "keywords": matched,
                        })

                except Exception as e:
                    self.logger.error(f"Error reading chat: {e}")
                    continue

        except Exception as e:
            if "timeout" in str(e).lower() or "selector" in str(e).lower():
                self.logger.warning(
                    "LinkedIn page not ready — will retry next cycle. "
                    "(Browser stays open)"
                )
            elif "target closed" in str(e).lower() or "closed" in str(e).lower():
                self.logger.info("Browser was closed — will relaunch next cycle.")
                self._browser = None
                self._page = None
            else:
                self.logger.error(f"LinkedIn check error: {e}")
            messages = []

        # NOTE: browser is NOT closed here — it stays open!

        if not messages:
            self.logger.info("No new keyword-matched LinkedIn messages")

        return messages

    def create_action_file(self, item) -> Path:
        """Create .md file in Needs_Action/ for a matched LinkedIn message."""
        sender = item["sender"]
        preview = item["preview"]
        full_text = item["full_text"]
        keywords = item["keywords"]
        msg_id = item["id"]

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_slug = datetime.now().strftime("%Y-%m-%d")

        # Sanitize sender name for filename
        safe_sender = self._sanitize(sender)
        filename = f"LINKEDIN_{safe_sender}_{date_slug}.md"
        filepath = self.needs_action / filename

        # Determine priority using keyword hints
        priority = "P3"
        p2_words = ["invoice", "deadline", "proposal", "pricing", "budget"]
        if any(kw in keywords for kw in p2_words):
            priority = "P2"

        content = f"""---
type: linkedin_message
source: linkedin_messaging
sender: "{sender}"
date: "{timestamp}"
priority: {priority}
status: pending
requires_approval: false
keywords_matched: {json.dumps(keywords)}
tags: [linkedin, {', '.join(keywords)}]
summary: "LinkedIn message from {sender} about {', '.join(keywords)}"
---

# LinkedIn Message: {sender}

| Field    | Value |
|----------|-------|
| From     | {sender} |
| Date     | {timestamp} |
| Platform | LinkedIn Messaging |
| Keywords | {', '.join(keywords)} |
| Priority | {priority} |

## Message Preview

{preview}

## Full Conversation (last 5 messages)

{full_text}

## Suggested Actions
- [ ] Review message content
- [ ] Draft LinkedIn post if sales opportunity detected
- [ ] Reply to sender if action needed
- [ ] Archive after processing
"""

        filepath.write_text(content, encoding="utf-8")

        # Mark as processed
        self.processed_ids.add(msg_id)
        self._save_processed()

        # Log to dedicated linkedin log
        self._log_activity(filename, sender, keywords)

        self.logger.info(f'NEW LINKEDIN: "{preview[:50]}..." from {sender}')
        return filepath

    # -- Helpers --

    def _sanitize(self, name: str) -> str:
        """Remove characters not safe for filenames."""
        for ch in ['<', '>', ':', '"', '/', '\\', '|', '?', '*', ' ']:
            name = name.replace(ch, '_')
        return name[:60]

    def _log_activity(self, filename: str, sender: str, keywords: list):
        """Append to Logs/linkedin.log."""
        log_dir = self.vault_path / "Logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "linkedin.log"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (
            f"[{timestamp}] DETECTED: {filename} "
            f"| sender={sender} "
            f"| keywords={','.join(keywords)} "
            f"| status=pending\n"
        )
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)


def main():
    # Ensure session directory exists
    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 58)
    print("  LINKEDIN WATCHER - Silver Tier (Playwright)")
    print(f"  Checking every {CHECK_INTERVAL} seconds")
    print(f"  Login timeout: {LOGIN_WAIT_TIMEOUT} seconds")
    print(f"  Session:  {SESSION_DIR}")
    print(f"  Output:   {PROJECT_ROOT / 'Needs_Action'}")
    print("=" * 58)
    print()
    print("  Browser will STAY OPEN — it does NOT auto-close.")
    print("  First run: log in to LinkedIn manually.")
    print("  Session is saved — next run will auto-login.")
    print("  Press Ctrl+C to stop the watcher.")
    print()

    watcher = LinkedInWatcher(str(PROJECT_ROOT), str(SESSION_DIR))
    try:
        watcher.run()
    except KeyboardInterrupt:
        print("\n  Shutting down LinkedIn Watcher...")
    finally:
        watcher.close_browser()
        print("  Browser closed. Goodbye!")


if __name__ == "__main__":
    main()

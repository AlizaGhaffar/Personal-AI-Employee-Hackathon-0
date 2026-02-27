"""
Social Login — Gold Tier
One-time interactive login to all social media platforms.
Saves Playwright persistent sessions to sessions/{platform}/

Run this once per platform to authenticate.
The orchestrator (social_orchestrator.py) reuses these sessions automatically.

Usage:
  python Skills/social_login.py                     # login to all platforms
  python Skills/social_login.py --platform linkedin
  python Skills/social_login.py --platform facebook
  python Skills/social_login.py --platform instagram
  python Skills/social_login.py --platform twitter
  python Skills/social_login.py --check             # verify existing sessions
"""

import argparse
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSIONS_DIR = PROJECT_ROOT / "sessions"

# ── Config ─────────────────────────────────────────────────────────────────────
LOGIN_TIMEOUT = 120   # seconds to wait for manual login
POLL_INTERVAL = 2     # seconds between login-state checks

PLATFORMS = {
    "linkedin": {
        "name":      "LinkedIn",
        "login_url": "https://www.linkedin.com/login",
        "check_url": "https://www.linkedin.com/feed/",
        "logged_in": lambda url: any(
            p in url for p in ["/feed", "/mynetwork", "/messaging", "/in/"]
        ),
    },
    "facebook": {
        "name":      "Facebook",
        "login_url": "https://www.facebook.com/login",
        "check_url": "https://www.facebook.com/",
        "logged_in": lambda url: (
            "facebook.com" in url
            and "/login" not in url
            and "checkpoint" not in url
            and "recover" not in url
        ),
    },
    "instagram": {
        "name":      "Instagram",
        "login_url": "https://www.instagram.com/accounts/login/",
        "check_url": "https://www.instagram.com/",
        "logged_in": lambda url: (
            "instagram.com" in url
            and "accounts/login" not in url
            and "accounts/emailsignup" not in url
        ),
    },
    "twitter": {
        "name":      "Twitter / X",
        "login_url": "https://twitter.com/login",
        "check_url": "https://twitter.com/home",
        "logged_in": lambda url: "/home" in url or "x.com/home" in url,
    },
}


# ── Login ──────────────────────────────────────────────────────────────────────

def check_session(name: str, config: dict) -> bool:
    """Non-interactively verify a saved session is still valid."""
    session_path = SESSIONS_DIR / name
    if not session_path.exists():
        return False

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(session_path),
            headless=True,
        )
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(config["check_url"], wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            return config["logged_in"](page.url)
        except Exception:
            return False
        finally:
            ctx.close()


def login_platform(name: str, config: dict) -> bool:
    """
    Open a browser window for the given platform, wait for manual login,
    then save the session. Returns True on success.
    """
    session_path = SESSIONS_DIR / name
    session_path.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  LOGIN: {config['name']}")
    print(f"  Session will be saved to: {session_path}")
    print(f"  You have {LOGIN_TIMEOUT} seconds to log in.")
    print(f"  The browser will STAY OPEN — take your time.")
    print(f"{'='*60}\n")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(session_path),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # Navigate to login page
        try:
            page.goto(config["login_url"], wait_until="domcontentloaded", timeout=30000)
        except Exception as exc:
            print(f"  [ERROR] Could not open login page: {exc}")
            ctx.close()
            return False

        # Already logged in?
        if config["logged_in"](page.url):
            print(f"  Already logged in to {config['name']}. Session is valid!")
            ctx.close()
            return True

        # Poll until logged in or timed out
        elapsed = 0
        while elapsed < LOGIN_TIMEOUT:
            time.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

            try:
                url = page.url
            except Exception:
                # Browser was closed by user
                print(f"  Browser was closed early.")
                return False

            if config["logged_in"](url):
                print(f"\n  Logged in to {config['name']}! Session saved.")
                ctx.close()
                return True

            remaining = LOGIN_TIMEOUT - elapsed
            if remaining > 0 and int(elapsed) % 20 == 0:
                print(f"  Still waiting... {int(remaining)}s remaining")

        print(f"\n  Login timed out for {config['name']}.")
        print(f"  Re-run: python Skills/social_login.py --platform {name}")
        try:
            ctx.close()
        except Exception:
            pass
        return False


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Social Login — save Playwright sessions for all platforms"
    )
    parser.add_argument(
        "--platform",
        choices=list(PLATFORMS.keys()),
        help="Login to a specific platform only",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify existing sessions without opening a browser",
    )
    args = parser.parse_args()

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    targets = (
        {args.platform: PLATFORMS[args.platform]}
        if args.platform
        else PLATFORMS
    )

    print("=" * 60)
    print("  SOCIAL LOGIN — Gold Tier")
    print(f"  Sessions dir : {SESSIONS_DIR}")
    if args.check:
        print("  Mode         : CHECK (no browser)")
    else:
        print(f"  Platforms    : {', '.join(targets.keys())}")
    print("=" * 60)

    if args.check:
        print()
        for name, config in PLATFORMS.items():
            ok = check_session(name, config)
            status = "VALID" if ok else "NOT LOGGED IN"
            mark   = "✓" if ok else "✗"
            print(f"  {mark} {name:12} : {status}")
        print()
        return

    results = {}
    for name, config in targets.items():
        results[name] = login_platform(name, config)

    print("\n" + "=" * 60)
    print("  LOGIN SUMMARY")
    print("=" * 60)
    for name, ok in results.items():
        mark   = "OK     " if ok else "FAILED "
        print(f"  {mark} {name}")

    failed = [n for n, ok in results.items() if not ok]
    if failed:
        print(f"\n  Retry failed platforms:")
        for n in failed:
            print(f"    python Skills/social_login.py --platform {n}")
        sys.exit(1)
    else:
        print("\n  All sessions saved. Ready to post!")
        print("  Next: python Skills/social_orchestrator.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

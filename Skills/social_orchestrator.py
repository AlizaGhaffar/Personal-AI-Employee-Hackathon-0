"""
Social Media Orchestrator — Gold Tier
Unified Playwright poster for LinkedIn, Facebook, Instagram, Twitter.

HITL Workflow:
  1. AI writes POST_*.md to Pending_Approval/
  2. Human reviews and moves file to Approved/
  3. This orchestrator detects the file (watchdog)
  4. Posts via Playwright browser (persistent session, no API keys)
  5. Moves file to Done/, logs everything
  6. On failure: retries 3x, saves screenshot, leaves file in Approved/

Session setup (run once per platform):
  python Skills/social_login.py

Post spec file format (YAML front-matter in Approved/*.md):
  ---
  type: social_post
  platform: linkedin | facebook | instagram | twitter
  caption: "Your post text here"
  image_path: "path/to/image.jpg"   # local file — required for Instagram
  ---

Usage:
  python Skills/social_orchestrator.py           # start watching Approved/
  python Skills/social_orchestrator.py --file path/to/file.md   # one-shot
  python Skills/social_orchestrator.py --dry-run # parse + log, no posting
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from playwright.sync_api import sync_playwright

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPROVED_DIR = PROJECT_ROOT / "Approved"
DONE_DIR     = PROJECT_ROOT / "Done"
LOGS_DIR     = PROJECT_ROOT / "Logs"
SESSIONS_DIR = PROJECT_ROOT / "sessions"

# ── Constants ──────────────────────────────────────────────────────────────────
MAX_RETRIES  = 3
RETRY_WAIT   = 5        # seconds between retries
NAV_TIMEOUT  = 60_000   # ms — page navigation
ACT_TIMEOUT  = 15_000   # ms — element wait

# ── Logging ────────────────────────────────────────────────────────────────────
LOGS_DIR.mkdir(exist_ok=True)
_log_file = LOGS_DIR / f"{datetime.now():%Y-%m-%d}_social_orchestrator.log"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(_log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("orchestrator")


# ── Spec Parsing ───────────────────────────────────────────────────────────────

def parse_spec(filepath: Path) -> dict:
    """
    Extract YAML front-matter from a social post spec file.
    Supports both type: social_post (any platform) and legacy type: twitter_post.
    Returns normalized dict: platform, caption, image_path, image_url, link_url.
    Raises ValueError for any missing/invalid field.
    """
    text = filepath.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("No YAML front-matter (file must start with ---)")

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Malformed YAML front-matter (need opening and closing ---)")

    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML parse error: {exc}") from exc

    post_type = str(meta.get("type", "")).strip()

    # Normalize legacy twitter_post type
    if post_type == "twitter_post":
        platform = "twitter"
        caption  = str(meta.get("text", meta.get("caption", ""))).strip()
    elif post_type == "social_post":
        platform = str(meta.get("platform", "")).lower().strip()
        caption  = str(meta.get("caption", meta.get("text", ""))).strip()
    else:
        raise ValueError(f"Not a social post file (type={post_type!r})")

    if not platform:
        raise ValueError("Missing 'platform' in front-matter")

    valid = {"linkedin", "facebook", "instagram", "twitter"}
    if platform not in valid:
        raise ValueError(f"Unknown platform {platform!r} — must be one of: {valid}")

    if not caption:
        raise ValueError("Missing 'caption' (or 'text') in front-matter")

    return {
        "platform":   platform,
        "caption":    caption,
        "image_path": str(meta.get("image_path", "")).strip(),
        "image_url":  str(meta.get("image_url",  "")).strip(),
        "link_url":   str(meta.get("link_url",   "")).strip(),
    }


# ── Playwright Helpers ─────────────────────────────────────────────────────────

def _wait_click(page, selectors: list, label: str, timeout: int = ACT_TIMEOUT):
    """Click the first visible element matching any selector. Raises on total failure."""
    for sel in selectors:
        try:
            el = page.wait_for_selector(sel, timeout=timeout, state="visible")
            if el:
                el.scroll_into_view_if_needed()
                el.click()
                return el
        except Exception:
            continue
    raise RuntimeError(f"Could not find element to click: {label}")


def _type_into(page, selectors: list, text: str, label: str, timeout: int = ACT_TIMEOUT):
    """Type into the first found editable element (waits for each selector)."""
    for sel in selectors:
        try:
            el = page.wait_for_selector(sel, timeout=timeout, state="visible")
            if el:
                el.scroll_into_view_if_needed()
                el.click()
                page.wait_for_timeout(300)
                # Use keyboard for rich text editors (more reliable than fill)
                page.keyboard.type(text, delay=20)
                return el
        except Exception:
            continue
    raise RuntimeError(f"Could not find element to type into: {label}")


def _screenshot(page, tag: str, filepath: Path):
    """Save a debug screenshot to Logs/."""
    try:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"screenshot_{ts}_{tag}_{filepath.stem[:25]}.png"
        dest = LOGS_DIR / name
        page.screenshot(path=str(dest), full_page=False)
        log.info(f"Screenshot → Logs/{name}")
    except Exception as exc:
        log.warning(f"Screenshot failed: {exc}")


def _resolve_image(path_str: str) -> str | None:
    """Return absolute path to image file, or None if not found."""
    if not path_str:
        return None
    p = Path(path_str)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return str(p) if p.exists() else None


# ── Platform Posters ───────────────────────────────────────────────────────────

def post_linkedin(page, spec: dict):
    """
    LinkedIn feed post.
    Flow: Home feed → "Start a post" → type → (optional image) → "Post"
    """
    caption    = spec["caption"]
    image_path = _resolve_image(spec["image_path"])

    page.goto("https://www.linkedin.com/feed/",
              wait_until="domcontentloaded", timeout=NAV_TIMEOUT)

    # Wait until the share-box container is actually in DOM (language-independent)
    try:
        page.wait_for_selector(
            ".share-box-feed-entry, [data-view-name*='share'], .share-box__open",
            timeout=12_000, state="visible"
        )
    except Exception:
        pass
    page.wait_for_timeout(2000)

    # DEBUG: screenshot so we can see what's on screen if click fails
    _screenshot(page, "linkedin_preflight", Path("linkedin_debug"))

    # Open composer — element is an input/div (NOT a button) — no button: prefix
    clicked = False
    for sel in [
        "[placeholder='Start a post']",
        "[placeholder*='Start a post']",
        ".share-box-feed-entry__trigger",           # class only, any tag
        "[data-view-name='share-creation-bar-trigger']",
        "[aria-label*='Start a post']",             # any tag
        ".share-box-feed-entry__top-bar [role='button']",
        ".share-box-feed-entry__top-bar input",
        ".share-box-feed-entry__top-bar div",
        "button.share-box-feed-entry__trigger",
    ]:
        try:
            el = page.wait_for_selector(sel, timeout=3000, state="visible")
            if el:
                el.scroll_into_view_if_needed()
                el.click()
                clicked = True
                log.info(f"LinkedIn composer opened via selector: {sel}")
                break
        except Exception:
            continue

    if not clicked:
        # JS fallback: find element by placeholder or text in the share box
        log.warning("LinkedIn: CSS selectors failed — trying JS click fallback")
        page.evaluate("""
            const candidates = document.querySelectorAll(
                '[class*="share-box"] *, [class*="share-creation"] *'
            );
            for (const el of candidates) {
                const ph = el.placeholder || '';
                const txt = (el.textContent || '').trim();
                if (ph.includes('Start a post') || txt === 'Start a post') {
                    el.click();
                    break;
                }
            }
        """)
        page.wait_for_timeout(1500)
        # verify composer opened (any contenteditable appeared)
        try:
            page.wait_for_selector("div[contenteditable='true']", timeout=5000, state="visible")
            clicked = True
            log.info("LinkedIn composer opened via JS fallback")
        except Exception:
            raise RuntimeError("Could not open LinkedIn post composer — Start a post element not found")

    page.wait_for_timeout(3000)

    # Type caption
    _type_into(page, [
        "div.ql-editor[contenteditable='true']",
        "div[role='textbox'][contenteditable='true']",
        "div.editor-content[contenteditable='true']",
        "div[data-placeholder][contenteditable='true']",
    ], caption, "Post editor")
    page.wait_for_timeout(1000)

    # Optional image
    if image_path:
        try:
            _wait_click(page, [
                "button[aria-label*='Add a photo']",
                "button[aria-label*='photo']",
                "button.share-creation-state__images-button",
                "button[aria-label*='image']",
            ], "Add photo button", timeout=5000)
            page.wait_for_timeout(1000)
            inp = page.query_selector("input[type='file']")
            if inp:
                inp.set_input_files(image_path)
                page.wait_for_timeout(3000)
        except Exception as exc:
            log.warning(f"LinkedIn image upload skipped: {exc}")

    # Submit
    _wait_click(page, [
        "button.share-actions__primary-action",
        "button.artdeco-button--primary:has-text('Post')",
        "button[aria-label='Post']:not([disabled])",
        "button:has-text('Post'):visible",
    ], "Post button")
    page.wait_for_timeout(4000)


def post_facebook(page, spec: dict):
    """
    Facebook home-feed post.
    Flow: Home → "What's on your mind?" → type → "Post"
    """
    caption = spec["caption"]

    page.goto("https://www.facebook.com/",
              wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
    page.wait_for_timeout(3000)

    # DEBUG: screenshot before clicking composer — see feed state
    _screenshot(page, "fb_before_composer", Path("fb_debug"))

    # Open composer — "What's on your mind" trigger
    clicked = False
    for sel in [
        "[aria-label*=\"What's on your mind\"]",
        "[placeholder*=\"What's on your mind\"]",
        "[data-pagelet='FeedComposer'] [role='button']",
        "div[role='button']:has-text(\"What's on your mind\")",
        "div[role='button'][aria-label*='post']",
    ]:
        try:
            el = page.wait_for_selector(sel, timeout=4000, state="visible")
            if el:
                el.click()
                clicked = True
                log.info(f"Facebook: composer opened via '{sel}'")
                break
        except Exception:
            continue

    if not clicked:
        raise RuntimeError("Could not open Facebook composer — 'What's on your mind' not found")

    # Wait for dialog to fully render
    page.wait_for_timeout(3000)
    try:
        page.wait_for_selector("div[role='dialog']", timeout=8000, state="visible")
        page.wait_for_timeout(1000)
    except Exception:
        pass

    # DEBUG: screenshot after dialog opens — see exact editor DOM
    _screenshot(page, "fb_after_dialog", Path("fb_debug"))

    # Type into the dialog editor
    _type_into(page, [
        "div[role='dialog'] div[contenteditable='true']",
        "div[role='dialog'] div[role='textbox']",
        "div[data-lexical-editor='true'][contenteditable='true']",
        "div[role='textbox'][contenteditable='true']",
        "div.notranslate[contenteditable='true']",
        "[aria-label*=\"What's on your mind\"][contenteditable]",
        "div[contenteditable='true']",
    ], caption, "Post editor")
    page.wait_for_timeout(1000)

    # DEBUG: screenshot before Post click — see button state
    _screenshot(page, "fb_before_post", Path("fb_debug"))

    # Submit
    _wait_click(page, [
        "[aria-label='Post'][role='button']",
        "div[aria-label='Post'][role='button']",
        "div[role='button']:has-text('Post')",
        "button[type='submit']:has-text('Post')",
        "button:has-text('Post')",
    ], "Post button")
    page.wait_for_timeout(4000)


def post_instagram(page, spec: dict):
    """
    Instagram image post (image required — text-only not supported via browser).
    Flow: Home → Create (+) → upload image → Next → Next → caption → Share
    """
    caption    = spec["caption"]
    image_path = _resolve_image(spec["image_path"]) or _resolve_image(spec["image_url"])

    if not image_path:
        raise RuntimeError(
            "Instagram requires 'image_path' — text-only posts are not supported. "
            "Add image_path: path/to/image.jpg to your post spec."
        )

    page.goto("https://www.instagram.com/",
              wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
    page.wait_for_timeout(3000)

    # Step 1: Click the "+" (Create) button in left nav
    _wait_click(page, [
        "[aria-label='New post']",
        "svg[aria-label*='New post']",
        "[aria-label*='Create']",
        "svg[aria-label*='Create']",
        "a[href='/create/select/']",
    ], "Create (+) button")
    page.wait_for_timeout(2000)

    # DEBUG screenshot — see the menu that appears after clicking "+"
    _screenshot(page, "instagram_after_plus", Path("instagram_debug"))

    # Step 2: Click "Post" from the dropdown menu that appears
    _wait_click(page, [
        "[aria-label='Post']",
        "span:has-text('Post')",
        "div[role='menuitem']:has-text('Post')",
        "a:has-text('Post')",
        "button:has-text('Post')",
    ], "Post menu item")
    page.wait_for_timeout(2000)

    # DEBUG screenshot — see the file upload dialog
    _screenshot(page, "instagram_after_post_menu", Path("instagram_debug"))

    # Step 3: "Select from computer" button triggers OS file chooser
    uploaded = False
    for sel in [
        "button:has-text('Select from computer')",
        "div[role='button']:has-text('Select from computer')",
        "button:has-text('Select')",
        "[aria-label*='Select']",
    ]:
        try:
            with page.expect_file_chooser(timeout=10_000) as fc_info:
                el = page.wait_for_selector(sel, timeout=5000, state="visible")
                if el:
                    el.click()
            fc_info.value.set_files(image_path)
            uploaded = True
            log.info(f"Instagram: image uploaded via '{sel}'")
            break
        except Exception:
            continue

    if not uploaded:
        # Fallback: hidden file input in DOM
        inputs = page.query_selector_all("input[type='file']")
        if inputs:
            inputs[0].set_input_files(image_path)
            log.info("Instagram: image set on hidden file input (fallback)")
        else:
            _screenshot(page, "instagram_upload_fail", Path("instagram_debug"))
            raise RuntimeError(
                "Instagram image upload failed — check Logs/ screenshots for current UI"
            )
    page.wait_for_timeout(4000)

    # Next selector list — Instagram uses div[role='button'], NOT <button>
    NEXT_SELS = [
        "div[role='button']:has-text('Next')",
        "button:has-text('Next')",
        "[aria-label='Next']",
    ]

    # Advance through crop screen (required)
    _wait_click(page, NEXT_SELS, "Next (crop)")
    page.wait_for_timeout(2000)

    # Advance through Edit/Filter screen (required — do NOT swallow this)
    _wait_click(page, NEXT_SELS, "Next (edit/filter)")
    page.wait_for_timeout(2000)

    # Type caption (now on caption screen)
    try:
        _type_into(page, [
            "div[aria-label*='Write a caption']",
            "textarea[aria-label*='Write a caption']",
            "div[role='textbox'][contenteditable]",
            "div[contenteditable='true']",
        ], caption, "Caption editor")
        page.wait_for_timeout(1000)
    except Exception as exc:
        log.warning(f"Instagram caption entry issue: {exc} — continuing to Share")

    # Dismiss hashtag/mention autocomplete dropdown if open (blocks Share click)
    page.keyboard.press("Escape")
    page.wait_for_timeout(800)

    # Share — div[role='button'] in modal header (not a <button> tag)
    _wait_click(page, [
        "div[role='button']:has-text('Share')",
        "button:has-text('Share')",
        "[aria-label='Share']",
    ], "Share button")
    page.wait_for_timeout(6000)


def post_twitter(page, spec: dict):
    """
    Twitter/X new tweet.
    Flow: Home → click compose area → type → "Post"
    """
    text       = spec["caption"]
    image_path = _resolve_image(spec["image_path"])

    if len(text) > 280:
        raise RuntimeError(
            f"Tweet is {len(text)} characters — max is 280. "
            "Trim the caption and re-approve."
        )

    page.goto("https://twitter.com/home",
              wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
    page.wait_for_timeout(3000)

    # Click into the compose box
    _wait_click(page, [
        "[data-testid='tweetTextarea_0']",
        "[aria-label='Post text']",
        "[placeholder*='What is happening']",
        "div.public-DraftStyleDefault-block",
        "[aria-label*='Tweet']",
    ], "Tweet compose box")
    page.wait_for_timeout(500)
    page.keyboard.type(text, delay=15)
    page.wait_for_timeout(1500)

    # Optional image
    if image_path:
        try:
            inp = page.query_selector("[data-testid='fileInput']")
            if inp:
                inp.set_input_files(image_path)
                page.wait_for_timeout(3000)
        except Exception as exc:
            log.warning(f"Twitter image upload skipped: {exc}")

    # DEBUG: screenshot to see Post button state
    _screenshot(page, "twitter_before_post", Path("twitter_debug"))

    # Wait for Post button to become enabled
    for btn_sel in ["[data-testid='tweetButtonInline']", "[data-testid='tweetButton']"]:
        try:
            page.wait_for_function(
                f"document.querySelector(\"{btn_sel}\")?.getAttribute('aria-disabled') !== 'true'",
                timeout=5000
            )
            break
        except Exception:
            continue

    # Focus the inner contenteditable div precisely before submitting
    try:
        inner = page.query_selector(
            "[data-testid='tweetTextarea_0'] div[contenteditable='true']"
        ) or page.query_selector("[data-testid='tweetTextarea_0']")
        if inner:
            inner.click()
            page.wait_for_timeout(400)
    except Exception:
        pass

    submitted = False

    # Try 1: force=True click on Post button — bypasses pointer-event / overlay blocks
    for sel in ["[data-testid='tweetButtonInline']", "[data-testid='tweetButton']"]:
        try:
            page.locator(sel).click(force=True, timeout=5000)
            page.wait_for_timeout(2500)
            submitted = True
            log.info(f"Twitter: posted via force click ({sel})")
            break
        except Exception:
            continue

    # Try 2: Ctrl+Enter keyboard shortcut
    if not submitted:
        log.warning("Twitter: force click failed — trying Ctrl+Enter")
        try:
            inner = page.query_selector(
                "[data-testid='tweetTextarea_0'] div[contenteditable='true']"
            ) or page.query_selector("[data-testid='tweetTextarea_0']")
            if inner:
                inner.click()
                page.wait_for_timeout(300)
            page.keyboard.press("Control+Return")
            page.wait_for_timeout(2500)
            submitted = True
            log.info("Twitter: posted via Ctrl+Enter")
        except Exception:
            pass

    # Try 3: JS dispatch click event
    if not submitted:
        log.warning("Twitter: trying JS dispatchEvent click")
        for sel in ["[data-testid='tweetButtonInline']", "[data-testid='tweetButton']"]:
            try:
                page.evaluate(f"""
                    const btn = document.querySelector('{sel}');
                    if (btn) btn.dispatchEvent(new MouseEvent('click', {{bubbles:true, cancelable:true}}));
                """)
                page.wait_for_timeout(2500)
                submitted = True
                log.info(f"Twitter: posted via dispatchEvent ({sel})")
                break
            except Exception:
                continue

    if not submitted:
        raise RuntimeError("Twitter post did not submit — all 3 methods failed, check Logs/ screenshot")

    page.wait_for_timeout(2000)


# ── Platform Dispatch ──────────────────────────────────────────────────────────
HANDLERS = {
    "linkedin":  post_linkedin,
    "facebook":  post_facebook,
    "instagram": post_instagram,
    "twitter":   post_twitter,
}


# ── Core Execution ─────────────────────────────────────────────────────────────

def execute_post(spec: dict, filepath: Path, dry_run: bool = False) -> bool:
    """
    Post to the platform specified in spec.
    Retries MAX_RETRIES times on failure with screenshots.
    Returns True on success.
    """
    platform = spec["platform"]
    handler  = HANDLERS[platform]

    session_path = SESSIONS_DIR / platform
    if not session_path.exists():
        log.error(
            f"No session found for '{platform}'. "
            f"Run: python Skills/social_login.py --platform {platform}"
        )
        return False

    if dry_run:
        log.info(f"[DRY RUN] platform={platform} | caption={spec['caption'][:80]}...")
        return True

    for attempt in range(1, MAX_RETRIES + 1):
        log.info(f"Attempt {attempt}/{MAX_RETRIES} → {platform}")
        ctx  = None
        page = None

        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    str(session_path),
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                    viewport={"width": 1280, "height": 900},
                    ignore_https_errors=True,
                )
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                handler(page, spec)
                log.info(f"SUCCESS: posted to {platform} | {filepath.name}")
                return True

        except Exception as exc:
            log.error(f"Attempt {attempt} FAILED [{platform}]: {exc}")
            if page:
                _screenshot(page, f"fail_{attempt}_{platform}", filepath)
            if attempt < MAX_RETRIES:
                log.info(f"Retrying in {RETRY_WAIT}s...")
                time.sleep(RETRY_WAIT)

        finally:
            try:
                if ctx:
                    ctx.close()
            except Exception:
                pass

    log.error(f"All {MAX_RETRIES} attempts exhausted — {platform} | {filepath.name}")
    return False


# ── File Pipeline ──────────────────────────────────────────────────────────────

def process_file(filepath: Path, dry_run: bool = False) -> bool:
    """Parse spec, execute post, move to Done/. Returns True on success."""
    log.info(f"Processing: {filepath.name}")

    try:
        spec = parse_spec(filepath)
    except ValueError as exc:
        log.warning(f"Skipping {filepath.name}: {exc}")
        return False
    except Exception as exc:
        log.error(f"Unexpected parse error for {filepath.name}: {exc}")
        return False

    log.info(f"Platform: {spec['platform']} | Caption: {spec['caption'][:60]}...")

    success = execute_post(spec, filepath, dry_run=dry_run)

    if success and not dry_run:
        DONE_DIR.mkdir(exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = DONE_DIR / f"{ts}_{filepath.name}"
        try:
            filepath.rename(dest)
            log.info(f"Moved → Done/{dest.name}")
        except Exception as exc:
            log.error(f"Could not move file to Done/: {exc}")

    return success


# ── Watchdog Handler ───────────────────────────────────────────────────────────

class ApprovedHandler(FileSystemEventHandler):
    """Watches Approved/ and dispatches new social post files to process_file."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._seen: set[str] = set()

    def on_created(self, event):
        if event.is_directory:
            return

        # Deduplicate Windows double-fire events
        key = os.path.normcase(event.src_path)
        if key in self._seen:
            return
        self._seen.add(key)

        filepath = Path(event.src_path)

        # Only process .md files; skip hidden/temp
        if filepath.suffix.lower() != ".md" or filepath.name.startswith((".", "~")):
            return

        # Wait for file to finish writing (Windows rename lag)
        time.sleep(1.5)
        if not filepath.exists():
            return

        # Quick pre-screen: must contain a recognized post type
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            return

        if "type: social_post" not in content and "type: twitter_post" not in content:
            return

        log.info(f"Approved file detected: {filepath.name}")
        process_file(filepath, dry_run=self.dry_run)


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Social Orchestrator — Playwright-based multi-platform poster"
    )
    parser.add_argument(
        "--file",
        help="Process a single file (one-shot mode)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and log without actually posting",
    )
    args = parser.parse_args()

    # Ensure all directories exist
    for d in (APPROVED_DIR, DONE_DIR, LOGS_DIR, SESSIONS_DIR):
        d.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("SOCIAL ORCHESTRATOR — Gold Tier")
    log.info(f"  Sessions : {SESSIONS_DIR}")
    log.info(f"  Approved : {APPROVED_DIR}")
    log.info(f"  Done     : {DONE_DIR}")
    log.info(f"  Logs     : {_log_file.name}")
    log.info(f"  Dry run  : {args.dry_run}")
    log.info(f"  Retries  : {MAX_RETRIES}")
    log.info("=" * 60)

    # ── One-shot mode ────────────────────────────────────────────────────────
    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            log.error(f"File not found: {filepath}")
            sys.exit(1)
        success = process_file(filepath, dry_run=args.dry_run)
        sys.exit(0 if success else 1)

    # ── Watch mode ───────────────────────────────────────────────────────────
    log.info("Watching Approved/ for social post files...")
    log.info("  → Copy approved posts to Approved/ to trigger posting")
    log.info("  → Press Ctrl+C to stop\n")

    # Also process any files already sitting in Approved/ at startup
    existing = [
        f for f in APPROVED_DIR.iterdir()
        if f.is_file()
        and f.suffix.lower() == ".md"
        and not f.name.startswith(".")
    ]
    if existing:
        log.info(f"Found {len(existing)} existing file(s) in Approved/ — processing now...")
        for f in existing:
            content = f.read_text(encoding="utf-8")
            if "type: social_post" in content or "type: twitter_post" in content:
                process_file(f, dry_run=args.dry_run)

    observer = Observer()
    observer.schedule(ApprovedHandler(dry_run=args.dry_run), str(APPROVED_DIR), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Shutdown requested...")
        observer.stop()

    observer.join()
    log.info("Orchestrator stopped.")


if __name__ == "__main__":
    main()

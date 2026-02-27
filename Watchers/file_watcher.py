"""
File System Watcher - Gold Tier
Watches two folders:
  1. Drop_Folder   → copies new files to Needs_Action/ (Bronze behaviour)
  2. Approved/     → auto-executes social_media_poster.py or twitter_poster.py
                     when an approved post file lands there (Gold auto-posting)
"""

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys
import time
import os


# -- Configuration --
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DROP_FOLDER  = Path("D:/Drop_Folder")
NEEDS_ACTION = PROJECT_ROOT / "Needs_Action"
APPROVED_DIR = PROJECT_ROOT / "Approved"
LOGS         = PROJECT_ROOT / "Logs"
PYTHON       = sys.executable


def log(message: str):
    """Log to console and daily log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line, flush=True)

    LOGS.mkdir(parents=True, exist_ok=True)
    log_file = LOGS / f"{datetime.now().strftime('%Y-%m-%d')}_watcher.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


class DropFolderHandler(FileSystemEventHandler):
    def __init__(self, project_path: str):
        self.needs_action = Path(project_path) / "Needs_Action"
        self._seen: set[str] = set()

    def on_created(self, event):
        if event.is_directory:
            return

        # Deduplicate Windows double-fire events
        key = os.path.normcase(event.src_path)
        if key in self._seen:
            return
        self._seen.add(key)

        source = Path(event.src_path)

        # Skip temp/hidden files
        if source.name.startswith(("~", ".")) or source.suffix.lower() in (
            ".tmp", ".crdownload", ".part"
        ):
            return

        # Wait for file to finish writing
        time.sleep(1)
        if not source.exists():
            return

        dest = self.needs_action / f"FILE_{source.name}"
        self.needs_action.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(source, dest)
            log(f"COPIED: {source.name} -> Needs_Action/FILE_{source.name}")
        except Exception as e:
            log(f"ERROR: Failed to copy {source.name}: {e}")
            return

        self.create_metadata(source, dest)
        log(f"READY: FILE_{source.name} awaiting processing")

    def create_metadata(self, source: Path, dest: Path):
        meta_path = dest.with_suffix(".md")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        size = source.stat().st_size

        meta_path.write_text(
            f"""---
type: file_drop
original_name: {source.name}
size: {size}
timestamp: {timestamp}
priority: P3
status: pending
---

New file dropped for processing.

| Field         | Value                     |
|---------------|---------------------------|
| Original      | `{source.name}`           |
| Location      | `Needs_Action/FILE_{source.name}` |
| Size          | {size} bytes              |
| Detected      | {timestamp}               |
| Source         | `{source}`                |
""",
            encoding="utf-8",
        )
        log(f"METADATA: Created FILE_{source.stem}.md")


class ApprovedFolderHandler(FileSystemEventHandler):
    """
    Watches Approved/ for social/twitter post files and auto-executes them.
    Triggered when human moves a file from Pending_Approval/ to Approved/.

    Detects by YAML front-matter type:
      type: social_post   → Skills/social_media_poster.py (Facebook + Instagram)
      type: twitter_post  → Skills/twitter_poster.py      (Twitter / X)
    """

    def __init__(self):
        self._seen: set[str] = set()

    def on_created(self, event):
        if event.is_directory:
            return

        key = os.path.normcase(event.src_path)
        if key in self._seen:
            return
        self._seen.add(key)

        filepath = Path(event.src_path)

        if filepath.suffix.lower() != ".md" or filepath.name.startswith("."):
            return

        # Wait for file to be fully written
        time.sleep(1)
        if not filepath.exists():
            return

        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception as exc:
            log(f"APPROVED WATCHER: Cannot read {filepath.name}: {exc}")
            return

        if "type: social_post" in content or "type: twitter_post" in content:
            self._run_poster(
                script=str(PROJECT_ROOT / "Skills" / "social_orchestrator.py"),
                filepath=filepath,
                label="SOCIAL",
            )

    def _run_poster(self, script: str, filepath: Path, label: str):
        log(f"{label}: Approved file detected → {filepath.name}")
        try:
            result = subprocess.run(
                [PYTHON, script, "--file", str(filepath)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                log(f"{label}: POST SUCCESS → {filepath.name}")
            else:
                log(f"{label}: POST FAILED → {filepath.name}")
                log(f"{label}: stderr: {result.stderr[:300]}")
        except subprocess.TimeoutExpired:
            log(f"{label}: TIMEOUT — poster script took too long for {filepath.name}")
        except Exception as exc:
            log(f"{label}: ERROR running poster: {exc}")


def main():
    DROP_FOLDER.mkdir(parents=True, exist_ok=True)
    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    log("=" * 50)
    log("FILE WATCHER STARTED — Gold Tier")
    log(f"  Drop Folder : {DROP_FOLDER}")
    log(f"  Needs Action: {NEEDS_ACTION}")
    log(f"  Approved    : {APPROVED_DIR} (auto-post trigger)")
    log("=" * 50)

    observer = Observer()
    observer.schedule(DropFolderHandler(str(PROJECT_ROOT)), str(DROP_FOLDER), recursive=False)
    observer.schedule(ApprovedFolderHandler(), str(APPROVED_DIR), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("SHUTDOWN: Watcher stopped by user")
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()

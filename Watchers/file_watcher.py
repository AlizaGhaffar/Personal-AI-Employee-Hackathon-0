"""
File System Watcher - Bronze Tier
Follows hackathon reference architecture: watches Drop_Folder,
copies to Needs_Action/ with FILE_ prefix, creates metadata .md.
"""

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from datetime import datetime
import shutil
import time
import os


# -- Configuration --
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DROP_FOLDER = Path("D:/Drop_Folder")
NEEDS_ACTION = PROJECT_ROOT / "Needs_Action"
LOGS = PROJECT_ROOT / "Logs"


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


def main():
    DROP_FOLDER.mkdir(parents=True, exist_ok=True)
    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    log("=" * 50)
    log("FILE WATCHER STARTED")
    log(f"  Watch:  {DROP_FOLDER}")
    log(f"  Target: {NEEDS_ACTION}")
    log("=" * 50)

    observer = Observer()
    handler = DropFolderHandler(str(PROJECT_ROOT))
    observer.schedule(handler, str(DROP_FOLDER), recursive=False)
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

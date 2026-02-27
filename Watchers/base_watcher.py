"""
Base Watcher - Core Pattern from Hackathon Guide
All watchers inherit from this class and implement
check_for_updates() and create_action_file() methods.
"""

import time
import logging
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime


class BaseWatcher(ABC):
    def __init__(self, vault_path: str, check_interval: int = 60):
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.logs_dir = self.vault_path / "Logs"
        self.check_interval = check_interval

        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_logging()

    def _setup_logging(self):
        """Configure file + console logging."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = self.logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}_{self.__class__.__name__}.log"

        formatter = logging.Formatter("[%(asctime)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        # File handler
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        self.logger.setLevel(logging.INFO)

    @abstractmethod
    def check_for_updates(self) -> list:
        """Return list of new items to process."""
        pass

    @abstractmethod
    def create_action_file(self, item) -> Path:
        """Create .md file in Needs_Action folder."""
        pass

    def run(self):
        """Main polling loop with error handling."""
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Starting {self.__class__.__name__} (interval: {self.check_interval}s)")

        while True:
            try:
                items = self.check_for_updates()
                if items:
                    self.logger.info(f"Found {len(items)} new item(s) to process")
                for item in items:
                    try:
                        path = self.create_action_file(item)
                        self.logger.info(f"Created: {path.name}")
                    except Exception as e:
                        self.logger.error(f"Failed to create action file: {e}")
            except KeyboardInterrupt:
                self.logger.info("Shutdown requested by user")
                break
            except Exception as e:
                self.logger.error(f"Error in check cycle: {e}")

            time.sleep(self.check_interval)

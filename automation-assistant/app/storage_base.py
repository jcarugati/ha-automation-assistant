"""Shared JSON storage helpers."""

import asyncio
import copy
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class JsonStorageBase:
    """Base class for JSON-backed storage files."""

    def __init__(self, storage_dir: str, filename: str, default_data: dict[str, Any]):
        self.storage_dir = Path(storage_dir)
        self.storage_file = self.storage_dir / filename
        self._default_data = default_data
        self._lock = asyncio.Lock()
        self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        """Ensure the storage directory exists."""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("Could not create storage directory: %s", exc)

    def _default_payload(self) -> dict[str, Any]:
        """Return a fresh copy of the default payload."""
        return copy.deepcopy(self._default_data)

    def _load_data(self) -> dict[str, Any]:
        """Load data from the JSON file."""
        if not self.storage_file.exists():
            return self._default_payload()
        try:
            with open(self.storage_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                return data
            logger.error("Storage file %s did not contain a dict", self.storage_file)
            return self._default_payload()
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Failed to load storage file %s: %s", self.storage_file, exc)
            return self._default_payload()

    def _save_data(self, data: dict[str, Any]) -> None:
        """Save data to the JSON file."""
        try:
            self._ensure_storage_dir()
            with open(self.storage_file, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, default=str)
        except OSError as exc:
            logger.error("Failed to save storage file %s: %s", self.storage_file, exc)
            raise

    def get_storage_file(self) -> Path:
        """Return the storage file path."""
        return self.storage_file

    def get_storage_dir(self) -> Path:
        """Return the storage directory path."""
        return self.storage_dir

"""Storage manager for saved automations."""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages persistent storage of saved automations."""

    def __init__(self, storage_dir: str = "/config/automation_assistant"):
        self.storage_dir = Path(storage_dir)
        self.storage_file = self.storage_dir / "saved_automations.json"
        self._lock = asyncio.Lock()
        self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        """Ensure the storage directory exists."""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create storage directory: {e}")

    def _load_data(self) -> dict[str, Any]:
        """Load data from the JSON file."""
        if not self.storage_file.exists():
            return {"automations": []}
        try:
            with open(self.storage_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load storage file: {e}")
            return {"automations": []}

    def _save_data(self, data: dict[str, Any]) -> None:
        """Save data to the JSON file."""
        try:
            self._ensure_storage_dir()
            with open(self.storage_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save storage file: {e}")
            raise

    async def save(self, name: str, prompt: str, yaml_content: str) -> dict[str, Any]:
        """Save a new automation."""
        async with self._lock:
            data = self._load_data()
            automation = {
                "id": str(uuid.uuid4()),
                "name": name,
                "prompt": prompt,
                "yaml_content": yaml_content,
                "created_at": datetime.utcnow().isoformat(),
            }
            data["automations"].insert(0, automation)
            self._save_data(data)
            return automation

    async def list(self) -> list[dict[str, Any]]:
        """List all saved automations."""
        async with self._lock:
            data = self._load_data()
            return data.get("automations", [])

    async def get(self, automation_id: str) -> dict[str, Any] | None:
        """Get a specific automation by ID."""
        async with self._lock:
            data = self._load_data()
            for automation in data.get("automations", []):
                if automation.get("id") == automation_id:
                    return automation
            return None

    async def delete(self, automation_id: str) -> bool:
        """Delete an automation by ID."""
        async with self._lock:
            data = self._load_data()
            automations = data.get("automations", [])
            original_length = len(automations)
            data["automations"] = [a for a in automations if a.get("id") != automation_id]
            if len(data["automations"]) < original_length:
                self._save_data(data)
                return True
            return False


# Global instance
storage_manager = StorageManager()

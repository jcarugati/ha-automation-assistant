"""Storage manager for saved automations."""

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from .storage_base import JsonStorageBase

logger = logging.getLogger(__name__)


class StorageManager(JsonStorageBase):
    """Manages persistent storage of saved automations."""

    def __init__(self, storage_dir: str = "/config/automation_assistant"):
        super().__init__(
            storage_dir=storage_dir,
            filename="saved_automations.json",
            default_data={"automations": []},
        )

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

    async def get(self, automation_id: str) -> Optional[dict[str, Any]]:
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
            data["automations"] = [
                automation
                for automation in automations
                if automation.get("id") != automation_id
            ]
            if len(data["automations"]) < original_length:
                self._save_data(data)
                return True
            return False

    async def update(
        self, automation_id: str, prompt: str, yaml_content: str
    ) -> Optional[dict[str, Any]]:
        """Update an existing automation."""
        async with self._lock:
            data = self._load_data()
            for automation in data.get("automations", []):
                if automation.get("id") == automation_id:
                    automation["prompt"] = prompt
                    automation["yaml_content"] = yaml_content
                    self._save_data(data)
                    return automation
            return None


# Global instance
storage_manager = StorageManager()

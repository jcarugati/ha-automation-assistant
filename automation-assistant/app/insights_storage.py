"""Storage manager for deduplicated insights from diagnosis runs."""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class InsightsStorage:
    """Stores deduplicated insights from diagnosis runs."""

    def __init__(self, storage_dir: str = "/config/automation_assistant"):
        self.storage_dir = Path(storage_dir)
        self.storage_file = self.storage_dir / "insights.json"
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
            return {"insights": []}
        try:
            with open(self.storage_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load insights storage file: {e}")
            return {"insights": []}

    def _save_data(self, data: dict[str, Any]) -> None:
        """Save data to the JSON file."""
        try:
            self._ensure_storage_dir()
            with open(self.storage_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save insights storage file: {e}")
            raise

    def _generate_insight_id(self, insight: dict[str, Any]) -> str:
        """Generate unique ID for deduplication.

        The ID is based on:
        - category (single/multi)
        - insight_type (error, conflict, etc.)
        - sorted automation_ids
        - sorted affected_entities
        """
        automation_ids = sorted(insight.get("automation_ids", []))
        affected_entities = sorted(insight.get("affected_entities", []))

        key = (
            f"{insight.get('category', '')}:"
            f"{insight.get('insight_type', '')}:"
            f"{':'.join(automation_ids)}:"
            f"{':'.join(affected_entities)}"
        )
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    async def add_insights(self, insights: list[dict[str, Any]]) -> int:
        """Add insights, updating last_seen for duplicates.

        Returns the number of new insights added.
        """
        if not insights:
            return 0

        async with self._lock:
            data = self._load_data()
            existing = data.get("insights", [])

            # Build a lookup map for existing insights
            existing_map = {i.get("insight_id"): i for i in existing}

            new_count = 0
            now = datetime.utcnow().isoformat()

            for insight in insights:
                # Generate ID for deduplication
                insight_id = self._generate_insight_id(insight)
                insight["insight_id"] = insight_id

                if insight_id in existing_map:
                    # Update existing insight's last_seen
                    existing_map[insight_id]["last_seen"] = now
                    # Also update title/description/recommendation if changed
                    existing_map[insight_id]["title"] = insight.get("title", existing_map[insight_id]["title"])
                    existing_map[insight_id]["description"] = insight.get("description", existing_map[insight_id]["description"])
                    existing_map[insight_id]["recommendation"] = insight.get("recommendation", existing_map[insight_id]["recommendation"])
                    logger.debug(f"Updated existing insight: {insight_id}")
                else:
                    # Add new insight
                    insight["first_seen"] = now
                    insight["last_seen"] = now
                    insight["resolved"] = False
                    existing_map[insight_id] = insight
                    new_count += 1
                    logger.debug(f"Added new insight: {insight_id}")

            # Convert back to list, sorted by last_seen descending
            data["insights"] = sorted(
                existing_map.values(),
                key=lambda x: x.get("last_seen", ""),
                reverse=True,
            )
            self._save_data(data)
            logger.info(f"Processed {len(insights)} insights, {new_count} new")
            return new_count

    async def get_all(self, category: str | None = None) -> list[dict[str, Any]]:
        """Get all insights, optionally filtered by category (single/multi)."""
        async with self._lock:
            data = self._load_data()
            insights = data.get("insights", [])

            if category:
                insights = [i for i in insights if i.get("category") == category]

            return insights

    async def get_single_automation_insights(self) -> list[dict[str, Any]]:
        """Get insights affecting single automations."""
        return await self.get_all(category="single")

    async def get_multi_automation_insights(self) -> list[dict[str, Any]]:
        """Get insights affecting multiple automations (conflicts)."""
        return await self.get_all(category="multi")

    async def get_unresolved_count(self) -> int:
        """Get count of unresolved insights."""
        async with self._lock:
            data = self._load_data()
            insights = data.get("insights", [])
            return sum(1 for i in insights if not i.get("resolved", False))

    async def mark_resolved(self, insight_id: str, resolved: bool = True) -> bool:
        """Mark an insight as resolved/unresolved."""
        async with self._lock:
            data = self._load_data()
            insights = data.get("insights", [])

            for insight in insights:
                if insight.get("insight_id") == insight_id:
                    insight["resolved"] = resolved
                    self._save_data(data)
                    logger.info(f"Marked insight {insight_id} as resolved={resolved}")
                    return True
            return False

    async def delete_insight(self, insight_id: str) -> bool:
        """Delete an insight permanently."""
        async with self._lock:
            data = self._load_data()
            insights = data.get("insights", [])
            original_length = len(insights)
            data["insights"] = [i for i in insights if i.get("insight_id") != insight_id]
            if len(data["insights"]) < original_length:
                self._save_data(data)
                logger.info(f"Deleted insight: {insight_id}")
                return True
            return False

    async def clear_resolved(self) -> int:
        """Clear all resolved insights. Returns count of deleted insights."""
        async with self._lock:
            data = self._load_data()
            insights = data.get("insights", [])
            original_length = len(insights)
            data["insights"] = [i for i in insights if not i.get("resolved", False)]
            deleted_count = original_length - len(data["insights"])
            if deleted_count > 0:
                self._save_data(data)
                logger.info(f"Cleared {deleted_count} resolved insights")
            return deleted_count


# Global instance
insights_storage = InsightsStorage()

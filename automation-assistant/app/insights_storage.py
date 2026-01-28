"""Storage manager for deduplicated insights from diagnosis runs."""

import hashlib
import logging
from datetime import datetime
from typing import Any, Optional

from .storage_base import JsonStorageBase

logger = logging.getLogger(__name__)


class InsightsStorage(JsonStorageBase):
    """Stores deduplicated insights from diagnosis runs."""

    def __init__(self, storage_dir: str = "/config/automation_assistant"):
        super().__init__(
            storage_dir=storage_dir,
            filename="insights.json",
            default_data={"insights": []},
        )

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
                    existing_map[insight_id]["title"] = insight.get(
                        "title", existing_map[insight_id]["title"]
                    )
                    existing_map[insight_id]["description"] = insight.get(
                        "description", existing_map[insight_id]["description"]
                    )
                    existing_map[insight_id]["recommendation"] = insight.get(
                        "recommendation", existing_map[insight_id]["recommendation"]
                    )
                    logger.debug("Updated existing insight: %s", insight_id)
                else:
                    # Add new insight
                    insight["first_seen"] = now
                    insight["last_seen"] = now
                    insight["resolved"] = False
                    existing_map[insight_id] = insight
                    new_count += 1
                    logger.debug("Added new insight: %s", insight_id)

            # Convert back to list, sorted by last_seen descending
            data["insights"] = sorted(
                existing_map.values(),
                key=lambda x: x.get("last_seen", ""),
                reverse=True,
            )
            self._save_data(data)
            logger.info(
                "Processed %s insights, %s new",
                len(insights),
                new_count,
            )
            return new_count

    async def get_all(self, category: Optional[str] = None) -> list[dict[str, Any]]:
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
                    logger.info(
                        "Marked insight %s as resolved=%s", insight_id, resolved
                    )
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
                logger.info("Deleted insight: %s", insight_id)
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
                logger.info("Cleared %s resolved insights", deleted_count)
            return deleted_count


# Global instance
insights_storage = InsightsStorage()

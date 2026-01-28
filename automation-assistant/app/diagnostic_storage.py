"""Storage manager for batch diagnosis reports."""

import logging
from typing import Any, Optional

from .storage_base import JsonStorageBase

logger = logging.getLogger(__name__)


class DiagnosticStorage(JsonStorageBase):
    """Stores batch diagnosis reports with retention policy."""

    MAX_REPORTS = 30  # Keep last 30 reports

    def __init__(self, storage_dir: str = "/config/automation_assistant"):
        super().__init__(
            storage_dir=storage_dir,
            filename="diagnosis_reports.json",
            default_data={"reports": []},
        )

    async def save_report(self, report: dict[str, Any]) -> None:
        """Save a diagnosis report, keeping last N reports."""
        async with self._lock:
            data = self._load_data()
            reports = data.get("reports", [])

            # Insert new report at the beginning
            reports.insert(0, report)

            # Keep only the last MAX_REPORTS
            if len(reports) > self.MAX_REPORTS:
                reports = reports[: self.MAX_REPORTS]

            data["reports"] = reports
            self._save_data(data)
            logger.info(
                "Saved diagnosis report: %s", report.get("run_id", "unknown")
            )

    async def get_latest_report(self) -> Optional[dict[str, Any]]:
        """Get most recent report."""
        async with self._lock:
            data = self._load_data()
            reports = data.get("reports", [])
            return reports[0] if reports else None

    async def get_report(self, run_id: str) -> Optional[dict[str, Any]]:
        """Get specific report by ID."""
        async with self._lock:
            data = self._load_data()
            for report in data.get("reports", []):
                if report.get("run_id") == run_id:
                    return report
            return None

    async def list_reports(self) -> list[dict[str, Any]]:
        """List all reports (summary only, without full_analyses for size)."""
        async with self._lock:
            data = self._load_data()
            reports = data.get("reports", [])

            # Return summaries without the full_analyses field
            summaries = []
            for report in reports:
                summary = {
                    "run_id": report.get("run_id"),
                    "run_at": report.get("run_at"),
                    "scheduled": report.get("scheduled", False),
                    "total_automations": report.get("total_automations", 0),
                    "automations_with_errors": report.get("automations_with_errors", 0),
                    "conflicts_found": report.get("conflicts_found", 0),
                    "insights_added": report.get("insights_added", 0),
                }
                summaries.append(summary)
            return summaries

    async def delete_report(self, run_id: str) -> bool:
        """Delete a report by ID."""
        async with self._lock:
            data = self._load_data()
            reports = data.get("reports", [])
            original_length = len(reports)
            data["reports"] = [r for r in reports if r.get("run_id") != run_id]
            if len(data["reports"]) < original_length:
                self._save_data(data)
                return True
            return False


# Global instance
diagnostic_storage = DiagnosticStorage()

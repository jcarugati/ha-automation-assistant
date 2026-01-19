"""Scheduler for automated diagnosis runs."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class DiagnosisScheduler:
    """Manages scheduled diagnosis runs."""

    JOB_ID = "daily_diagnosis"
    CONFIG_FILE = "/config/automation_assistant/scheduler_config.json"

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._config = self._load_config()
        self._running = False

    def _load_config(self) -> dict[str, Any]:
        """Load scheduler configuration."""
        config_path = Path(self.CONFIG_FILE)
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load scheduler config: {e}")
        return {"enabled": True, "time": "03:00"}

    def _save_config(self) -> None:
        """Save scheduler configuration."""
        config_path = Path(self.CONFIG_FILE)
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(self._config, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save scheduler config: {e}")

    def start(self) -> None:
        """Start the scheduler with configured job."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        if self._config.get("enabled", True):
            self._schedule_job()

        self.scheduler.start()
        self._running = True
        logger.info("Diagnosis scheduler started")

    def _schedule_job(self) -> None:
        """Schedule the daily diagnosis job."""
        time_str = self._config.get("time", "03:00")
        try:
            hour, minute = map(int, time_str.split(":"))
        except ValueError:
            logger.error(f"Invalid time format: {time_str}, using default 03:00")
            hour, minute = 3, 0

        # Remove existing job if any
        if self.scheduler.get_job(self.JOB_ID):
            self.scheduler.remove_job(self.JOB_ID)

        trigger = CronTrigger(hour=hour, minute=minute)
        self.scheduler.add_job(
            self._run_scheduled_diagnosis,
            trigger=trigger,
            id=self.JOB_ID,
            name="Daily Automation Diagnosis",
            replace_existing=True,
        )
        logger.info(f"Scheduled daily diagnosis at {time_str}")

    async def _run_scheduled_diagnosis(self) -> None:
        """Called by scheduler to run diagnosis."""
        logger.info("Starting scheduled diagnosis run")
        try:
            # Import here to avoid circular imports
            from .batch_doctor import batch_diagnosis_service

            result = await batch_diagnosis_service.run_batch_diagnosis(scheduled=True)
            logger.info(
                f"Scheduled diagnosis complete: {result.run_id} - "
                f"{result.automations_analyzed} automations, "
                f"{result.automations_with_errors} with errors, "
                f"{result.conflicts_found} conflicts"
            )
        except Exception as e:
            logger.error(f"Scheduled diagnosis failed: {e}")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Diagnosis scheduler stopped")

    def get_schedule(self) -> dict[str, Any]:
        """Get current schedule configuration."""
        job = self.scheduler.get_job(self.JOB_ID)
        next_run = None
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()

        return {
            "enabled": self._config.get("enabled", True),
            "time": self._config.get("time", "03:00"),
            "next_run": next_run,
        }

    def update_schedule(self, time: str | None = None, enabled: bool | None = None) -> dict[str, Any]:
        """Update schedule configuration.

        Args:
            time: New time in HH:MM format
            enabled: Whether scheduling is enabled

        Returns:
            Updated configuration
        """
        if time is not None:
            # Validate time format
            try:
                hour, minute = map(int, time.split(":"))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("Invalid time range")
                self._config["time"] = time
            except ValueError as e:
                raise ValueError(f"Invalid time format. Use HH:MM (24-hour): {e}")

        if enabled is not None:
            self._config["enabled"] = enabled

        self._save_config()

        # Update the scheduled job
        if self._running:
            if self._config.get("enabled", True):
                self._schedule_job()
            else:
                # Remove the job if disabled
                if self.scheduler.get_job(self.JOB_ID):
                    self.scheduler.remove_job(self.JOB_ID)
                    logger.info("Diagnosis schedule disabled")

        return self.get_schedule()

    def trigger_now(self) -> None:
        """Trigger a diagnosis run immediately (outside of schedule)."""
        asyncio.create_task(self._run_scheduled_diagnosis())


# Global instance
diagnosis_scheduler = DiagnosisScheduler()

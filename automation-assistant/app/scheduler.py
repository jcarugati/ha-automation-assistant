"""Scheduler for automated diagnosis runs."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class DiagnosisScheduler:
    """Manages scheduled diagnosis runs."""

    JOB_ID = "daily_diagnosis"
    DEFAULT_CONFIG = {
        "enabled": True,
        "time": "03:00",
        "frequency": "daily",
        "day_of_week": "mon",
        "day_of_month": 1,
    }
    VALID_FREQUENCIES = {"daily", "weekly", "monthly"}
    VALID_WEEKDAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    WEEKDAY_ALIASES = {
        "monday": "mon",
        "tuesday": "tue",
        "wednesday": "wed",
        "thursday": "thu",
        "friday": "fri",
        "saturday": "sat",
        "sunday": "sun",
    }
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
                    data = json.load(f)
                    if isinstance(data, dict):
                        config = dict(self.DEFAULT_CONFIG)
                        config.update(data)
                        if config.get("frequency") not in self.VALID_FREQUENCIES:
                            config["frequency"] = self.DEFAULT_CONFIG["frequency"]
                        if config.get("day_of_week") not in self.VALID_WEEKDAYS:
                            config["day_of_week"] = self.DEFAULT_CONFIG["day_of_week"]
                        try:
                            day_of_month = int(config.get("day_of_month", 1))
                        except (TypeError, ValueError):
                            day_of_month = self.DEFAULT_CONFIG["day_of_month"]
                        if not 1 <= day_of_month <= 31:
                            day_of_month = self.DEFAULT_CONFIG["day_of_month"]
                        config["day_of_month"] = day_of_month
                        return config
                    logger.error("Scheduler config is not a dictionary, using defaults")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load scheduler config: {e}")
        return dict(self.DEFAULT_CONFIG)

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
        """Schedule the diagnosis job."""
        time_str = self._config.get("time", "03:00")
        try:
            hour, minute = map(int, time_str.split(":"))
        except ValueError:
            logger.error(f"Invalid time format: {time_str}, using default 03:00")
            hour, minute = 3, 0

        # Remove existing job if any
        if self.scheduler.get_job(self.JOB_ID):
            self.scheduler.remove_job(self.JOB_ID)

        frequency = str(self._config.get("frequency", "daily")).lower()
        if frequency not in self.VALID_FREQUENCIES:
            logger.error(f"Invalid frequency: {frequency}, defaulting to daily")
            frequency = "daily"

        if frequency == "weekly":
            day_of_week = str(self._config.get("day_of_week", "mon")).lower()
            if day_of_week not in self.VALID_WEEKDAYS:
                logger.error(f"Invalid day_of_week: {day_of_week}, defaulting to mon")
                day_of_week = "mon"
            trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
            schedule_label = f"weekly on {day_of_week}"
        elif frequency == "monthly":
            day_of_month = self._config.get("day_of_month", 1)
            try:
                day_of_month_int = int(day_of_month)
            except (TypeError, ValueError):
                logger.error(f"Invalid day_of_month: {day_of_month}, defaulting to 1")
                day_of_month_int = 1
            if not 1 <= day_of_month_int <= 31:
                logger.error(
                    f"Invalid day_of_month: {day_of_month_int}, defaulting to 1"
                )
                day_of_month_int = 1
            trigger = CronTrigger(day=day_of_month_int, hour=hour, minute=minute)
            schedule_label = f"monthly on day {day_of_month_int}"
        else:
            trigger = CronTrigger(hour=hour, minute=minute)
            schedule_label = "daily"

        self.scheduler.add_job(
            self._run_scheduled_diagnosis,
            trigger=trigger,
            id=self.JOB_ID,
            name="Scheduled Automation Diagnosis",
            replace_existing=True,
        )
        logger.info(f"Scheduled {schedule_label} diagnosis at {time_str}")

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
            "frequency": self._config.get("frequency", "daily"),
            "day_of_week": self._config.get("day_of_week", "mon"),
            "day_of_month": self._config.get("day_of_month", 1),
            "next_run": next_run,
        }

    def update_schedule(
        self,
        time: Optional[str] = None,
        enabled: Optional[bool] = None,
        frequency: Optional[str] = None,
        day_of_week: Optional[str] = None,
        day_of_month: Optional[int] = None,
    ) -> dict[str, Any]:
        """Update schedule configuration.

        Args:
            time: New time in HH:MM format
            enabled: Whether scheduling is enabled
            frequency: daily, weekly, or monthly
            day_of_week: Day of week for weekly schedule (mon-sun)
            day_of_month: Day of month for monthly schedule (1-31)

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

        if frequency is not None:
            normalized_frequency = frequency.strip().lower()
            if normalized_frequency not in self.VALID_FREQUENCIES:
                raise ValueError("Invalid frequency. Use daily, weekly, or monthly.")
            self._config["frequency"] = normalized_frequency

        if day_of_week is not None:
            normalized_day = self._normalize_day_of_week(day_of_week)
            self._config["day_of_week"] = normalized_day

        if day_of_month is not None:
            try:
                day_of_month_int = int(day_of_month)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid day of month: {e}")
            if not 1 <= day_of_month_int <= 31:
                raise ValueError("Day of month must be between 1 and 31.")
            self._config["day_of_month"] = day_of_month_int

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

    def _normalize_day_of_week(self, day_of_week: str) -> str:
        """Normalize day of week strings to cron-compatible values."""
        if not day_of_week:
            raise ValueError("Day of week cannot be empty.")

        parts = [part.strip().lower() for part in day_of_week.split(",") if part.strip()]
        if not parts:
            raise ValueError("Day of week cannot be empty.")

        normalized: list[str] = []
        for part in parts:
            if part in self.VALID_WEEKDAYS:
                normalized.append(part)
                continue
            alias = self.WEEKDAY_ALIASES.get(part)
            if alias:
                normalized.append(alias)
                continue
            raise ValueError(f"Invalid day of week: {part}")

        return ",".join(normalized)

    def trigger_now(self) -> None:
        """Trigger a diagnosis run immediately (outside of schedule)."""
        asyncio.create_task(self._run_scheduled_diagnosis())


# Global instance
diagnosis_scheduler = DiagnosisScheduler()

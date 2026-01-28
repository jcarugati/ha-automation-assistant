"""Batch Diagnosis Service - analyzes all automations in a single Claude call."""

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Optional

from aiohttp import ClientError

from .config import config
from .diagnostic_storage import diagnostic_storage
from .ha_automations import ha_automation_reader
from .ha_client import ha_client
from .insights_storage import insights_storage
from .llm.claude import AsyncClaudeClient
from .models import (
    AutomationConflict,
    AutomationDiagnosisSummary,
    BatchDiagnosisReport,
)
from .prompts import build_batch_analysis_prompt

logger = logging.getLogger(__name__)


class CancelledException(Exception):
    """Raised when a diagnosis run is cancelled by the user."""


class BatchDiagnosisService:
    """Analyzes all automations with a single Claude API call."""

    # Maximum automations to analyze in one batch (to avoid token limits)
    MAX_BATCH_SIZE = 30

    def __init__(self):
        self.llm_client = AsyncClaudeClient(model=config.doctor_model_or_default)
        self._cancel_requested = False
        self._is_running = False

    def cancel(self) -> bool:
        """Request cancellation of the current diagnosis run."""
        if self._is_running:
            self._cancel_requested = True
            logger.info("Cancellation requested for batch diagnosis")
            return True
        return False

    @property
    def is_running(self) -> bool:
        """Check if a diagnosis is currently running."""
        return self._is_running

    async def run_batch_diagnosis(
        self, scheduled: bool = False
    ) -> BatchDiagnosisReport:
        """Run batch diagnosis on all automations.

        Uses a single Claude API call (or batched calls for large sets) to analyze
        all automations at once, rather than one call per automation.

        Args:
            scheduled: Whether this is a scheduled run (vs manual trigger)

        Returns:
            BatchDiagnosisReport with all results
        """
        if self._is_running:
            raise RuntimeError("A diagnosis is already running")

        self._is_running = True
        self._cancel_requested = False

        run_id = str(uuid.uuid4())[:8]
        run_at = datetime.utcnow()
        logger.info(
            "Starting batch diagnosis run: %s (scheduled=%s)",
            run_id,
            scheduled,
        )

        try:
            report = await self._run_analysis(run_id, run_at, scheduled)
            await diagnostic_storage.save_report(report.model_dump())
            logger.info(
                "Batch diagnosis complete: %s - %s analyzed, %s with errors, "
                "%s conflicts",
                run_id,
                report.automations_analyzed,
                report.automations_with_errors,
                report.conflicts_found,
            )
            return report

        finally:
            self._is_running = False
            self._cancel_requested = False

    def _check_cancelled(self, stage: str) -> None:
        """Raise if a cancellation was requested."""
        if self._cancel_requested:
            logger.info("Diagnosis cancelled %s", stage)
            raise CancelledException("Diagnosis was cancelled")

    async def _run_analysis(
        self, run_id: str, run_at: datetime, scheduled: bool
    ) -> BatchDiagnosisReport:
        """Run the full diagnosis flow and return the report."""
        automations_list = await ha_automation_reader.list_automations()
        total_automations = len(automations_list)
        logger.info("Found %s automations to analyze", total_automations)

        if total_automations == 0:
            return self._build_empty_report(run_id, run_at, scheduled)

        self._check_cancelled("before fetching automations")
        full_automations = await self._collect_full_automations(automations_list)
        available_entities = await self._get_entity_list()
        self._check_cancelled("before analysis")

        summaries, conflicts, overall_summary = await self._analyze_automations(
            full_automations,
            available_entities,
            total_automations,
        )

        automations_with_errors = sum(1 for s in summaries if s.has_errors)
        insights = self._extract_insights(summaries, conflicts)
        insights_added = await insights_storage.add_insights(insights)
        logger.info("Added %s new insights", insights_added)

        return BatchDiagnosisReport(
            run_id=run_id,
            run_at=run_at,
            scheduled=scheduled,
            total_automations=total_automations,
            automations_analyzed=len(summaries),
            automations_with_errors=automations_with_errors,
            conflicts_found=len(conflicts),
            insights_added=insights_added,
            automation_summaries=summaries,
            conflicts=conflicts,
            overall_summary=overall_summary,
            full_analyses=[],  # Not populated in batch mode
        )

    def _build_empty_report(
        self, run_id: str, run_at: datetime, scheduled: bool
    ) -> BatchDiagnosisReport:
        """Build an empty report when no automations exist."""
        return BatchDiagnosisReport(
            run_id=run_id,
            run_at=run_at,
            scheduled=scheduled,
            total_automations=0,
            automations_analyzed=0,
            automations_with_errors=0,
            conflicts_found=0,
            insights_added=0,
            automation_summaries=[],
            conflicts=[],
            overall_summary="No automations found in Home Assistant.",
            full_analyses=[],
        )

    async def _collect_full_automations(
        self, automations_list: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Fetch full configs for each automation."""
        full_automations: list[dict[str, Any]] = []
        for auto_info in automations_list:
            self._check_cancelled("while fetching automations")
            automation_id = auto_info.get("id", "")
            if not automation_id:
                continue
            auto = await ha_automation_reader.get_automation(automation_id)
            if auto:
                full_automations.append(auto)
        return full_automations

    async def _analyze_automations(
        self,
        full_automations: list[dict[str, Any]],
        available_entities: Optional[list[str]],
        total_automations: int,
    ) -> tuple[list[AutomationDiagnosisSummary], list[AutomationConflict], str]:
        """Analyze automations in batches and return summaries, conflicts, summary."""
        if len(full_automations) <= self.MAX_BATCH_SIZE:
            summaries, conflicts, summary = await self._analyze_batch(
                full_automations, available_entities
            )
            return summaries, conflicts, summary

        logger.info(
            "Splitting %s automations into batches", len(full_automations)
        )
        all_summaries: list[AutomationDiagnosisSummary] = []
        all_conflicts: list[AutomationConflict] = []
        overall_summary = ""

        for index in range(0, len(full_automations), self.MAX_BATCH_SIZE):
            self._check_cancelled(
                f"after {len(all_summaries)} automations"
            )
            batch = full_automations[index:index + self.MAX_BATCH_SIZE]
            logger.info(
                "Analyzing batch %s: %s automations",
                index // self.MAX_BATCH_SIZE + 1,
                len(batch),
            )
            summaries, conflicts, summary = await self._analyze_batch(
                batch, available_entities
            )
            all_summaries.extend(summaries)
            all_conflicts.extend(conflicts)
            if not overall_summary:
                overall_summary = summary

        overall_summary = self._generate_combined_summary(
            all_summaries, all_conflicts, total_automations
        )
        return all_summaries, all_conflicts, overall_summary

    async def _get_entity_list(self) -> Optional[list[str]]:
        """Get list of available entity IDs for validation."""
        try:
            states = await ha_client.get_states()
            return [s.get("entity_id") for s in states if s.get("entity_id")]
        except (ClientError, RuntimeError, TimeoutError, ValueError) as exc:
            logger.warning("Could not fetch entity list: %s", exc)
            return None

    async def _analyze_batch(
        self,
        automations: list[dict[str, Any]],
        available_entities: Optional[list[str]],
    ) -> tuple[list[AutomationDiagnosisSummary], list[AutomationConflict], str]:
        """Analyze a batch of automations with a single Claude call.

        Returns:
            Tuple of (summaries, conflicts, overall_summary)
        """
        try:
            # Build prompt
            prompt = build_batch_analysis_prompt(automations, available_entities)

            # Make single Claude API call
            logger.debug(
                "Sending batch of %s automations to Claude", len(automations)
            )
            response = await self.llm_client.generate_automation(
                "You are a Home Assistant automation expert. Respond only with "
                "valid JSON.",
                prompt,
            )

            # Parse JSON response
            return self._parse_batch_response(response, automations)

        except (ClientError, RuntimeError, TimeoutError, ValueError) as exc:
            logger.error("Batch analysis failed: %s", exc)
            # Return empty results on failure
            summaries = [
                AutomationDiagnosisSummary(
                    automation_id=automation.get("id", ""),
                    automation_alias=automation.get("alias", "Unknown"),
                    has_errors=False,
                    error_count=0,
                    warning_count=0,
                    brief_summary="Analysis failed",
                )
                for automation in automations
            ]
            return summaries, [], f"Batch analysis failed: {exc}"

    def _parse_batch_response(
        self,
        response: str,
        automations: list[dict[str, Any]],
    ) -> tuple[list[AutomationDiagnosisSummary], list[AutomationConflict], str]:
        """Parse Claude's JSON response into structured data."""
        summaries: list[AutomationDiagnosisSummary] = []
        conflicts: list[AutomationConflict] = []
        overall_summary = ""

        try:
            data = self._extract_batch_json(response)
            summaries = self._parse_batch_summaries(data.get("automations", []))
            conflicts = self._parse_batch_conflicts(data.get("conflicts", []))
            overall_summary = data.get("overall_summary", "Analysis complete.")

        except json.JSONDecodeError as exc:
            logger.error("Failed to parse JSON response: %s", exc)
            logger.debug("Response was: %s...", response[:500])

            # Create basic summaries from automation list
            for auto in automations:
                summaries.append(
                    AutomationDiagnosisSummary(
                        automation_id=auto.get("id", ""),
                        automation_alias=auto.get("alias", "Unknown"),
                        has_errors=False,
                        error_count=0,
                        warning_count=0,
                        brief_summary="Could not parse analysis",
                    )
                )
            overall_summary = "Analysis completed but response parsing failed."

        return summaries, conflicts, overall_summary

    def _extract_batch_json(self, response: str) -> dict[str, Any]:
        """Extract JSON payload from a batch response."""
        json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response.strip()
        return json.loads(json_str)

    def _parse_batch_summaries(
        self, items: list[dict[str, Any]]
    ) -> list[AutomationDiagnosisSummary]:
        """Parse automation summaries from batch response data."""
        summaries: list[AutomationDiagnosisSummary] = []
        for auto_data in items:
            status = auto_data.get("status", "ok")
            issues = auto_data.get("issues", [])
            has_errors = status == "error" or len(issues) > 0
            summaries.append(
                AutomationDiagnosisSummary(
                    automation_id=auto_data.get("id", ""),
                    automation_alias=auto_data.get("alias", "Unknown"),
                    has_errors=has_errors,
                    error_count=len(issues) if status == "error" else 0,
                    warning_count=len(issues) if status == "warning" else 0,
                    brief_summary=auto_data.get("summary", ""),
                )
            )
        return summaries

    def _parse_batch_conflicts(
        self, items: list[dict[str, Any]]
    ) -> list[AutomationConflict]:
        """Parse conflict summaries from batch response data."""
        conflicts: list[AutomationConflict] = []
        for conflict_data in items:
            conflicts.append(
                AutomationConflict(
                    conflict_type=conflict_data.get("type", "unknown"),
                    severity=conflict_data.get("severity", "info"),
                    automation_ids=conflict_data.get("automation_ids", []),
                    automation_names=conflict_data.get("automation_names", []),
                    description=conflict_data.get("description", ""),
                    affected_entities=conflict_data.get("affected_entities", []),
                )
            )
        return conflicts

    def _generate_combined_summary(
        self,
        summaries: list[AutomationDiagnosisSummary],
        conflicts: list[AutomationConflict],
        total: int,
    ) -> str:
        """Generate summary for multiple batches."""
        with_errors = sum(1 for s in summaries if s.has_errors)
        critical_conflicts = sum(1 for c in conflicts if c.severity == "critical")

        if with_errors == 0 and len(conflicts) == 0:
            return (
                f"All {total} automations analyzed successfully with no issues "
                "detected."
            )

        parts = [f"Analyzed {total} automations."]
        if with_errors > 0:
            parts.append(f"Found issues in {with_errors} automation(s).")
        if len(conflicts) > 0:
            parts.append(f"Detected {len(conflicts)} potential conflict(s)")
            if critical_conflicts > 0:
                parts.append(f"({critical_conflicts} critical).")
            else:
                parts[-1] += "."

        return " ".join(parts)

    def _extract_insights(
        self,
        summaries: list[AutomationDiagnosisSummary],
        conflicts: list[AutomationConflict],
    ) -> list[dict[str, Any]]:
        """Extract insights from diagnosis results."""
        insights: list[dict[str, Any]] = []

        # Single automation insights
        for summary in summaries:
            if summary.has_errors:
                insights.append(
                    {
                        "category": "single",
                        "insight_type": "error",
                        "severity": (
                            "warning" if summary.error_count < 3 else "critical"
                        ),
                        "title": f"Issues in '{summary.automation_alias}'",
                        "description": summary.brief_summary,
                        "automation_ids": [summary.automation_id],
                        "automation_names": [summary.automation_alias],
                        "affected_entities": [],
                        "recommendation": (
                            "Review the automation for the identified issues."
                        ),
                    }
                )

        # Multi-automation insights (conflicts)
        for conflict in conflicts:
            insights.append(
                {
                    "category": "multi",
                    "insight_type": "conflict",
                    "severity": conflict.severity,
                    "title": (
                        f"{conflict.conflict_type.replace('_', ' ').title()}"
                    ),
                    "description": conflict.description,
                    "automation_ids": conflict.automation_ids,
                    "automation_names": conflict.automation_names,
                    "affected_entities": conflict.affected_entities,
                    "recommendation": self._get_conflict_recommendation(
                        conflict.conflict_type
                    ),
                }
            )

        return insights

    def _get_conflict_recommendation(self, conflict_type: str) -> str:
        """Get recommendation text for a conflict type."""
        recommendations = {
            "shared_trigger": (
                "Consider using conditions to differentiate when each automation "
                "should run, or consolidate into a single automation."
            ),
            "state_conflict": (
                "Review which automation should take precedence, or add "
                "conditions to prevent conflicting actions."
            ),
            "resource_contention": (
                "Verify this is intentional. If automations should not run "
                "simultaneously, add mutual exclusion conditions."
            ),
            "timing_race": (
                "Add delays or conditions to ensure proper sequencing of "
                "automations."
            ),
        }
        return recommendations.get(
            conflict_type,
            "Review the conflict and adjust automation logic as needed.",
        )


# Global instance
batch_diagnosis_service = BatchDiagnosisService()

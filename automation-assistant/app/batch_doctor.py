"""Batch Diagnosis Service - analyzes all automations in a single Claude call."""

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any

from .diagnostic_storage import diagnostic_storage
from .ha_automations import ha_automation_reader
from .ha_client import ha_client
from .insights_storage import insights_storage
from .llm.claude import AsyncClaudeClient
from .models import (
    AutomationConflict,
    AutomationDiagnosisSummary,
    BatchDiagnosisReport,
    DiagnosisResponse,
)
from .prompts import build_batch_analysis_prompt

logger = logging.getLogger(__name__)


class CancelledException(Exception):
    """Raised when a diagnosis run is cancelled by the user."""
    pass


class BatchDiagnosisService:
    """Analyzes all automations with a single Claude API call."""

    # Maximum automations to analyze in one batch (to avoid token limits)
    MAX_BATCH_SIZE = 30

    def __init__(self):
        self.llm_client = AsyncClaudeClient()
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

    async def run_batch_diagnosis(self, scheduled: bool = False) -> BatchDiagnosisReport:
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
        logger.info(f"Starting batch diagnosis run: {run_id} (scheduled={scheduled})")

        try:
            # 1. Get all automations
            automations_list = await ha_automation_reader.list_automations()
            total_automations = len(automations_list)
            logger.info(f"Found {total_automations} automations to analyze")

            if total_automations == 0:
                report = BatchDiagnosisReport(
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
                await diagnostic_storage.save_report(report.model_dump())
                return report

            # Check for cancellation
            if self._cancel_requested:
                logger.info("Diagnosis cancelled before fetching automations")
                raise CancelledException("Diagnosis was cancelled")

            # 2. Get full automation configs
            full_automations = []
            for auto_info in automations_list:
                if self._cancel_requested:
                    logger.info("Diagnosis cancelled while fetching automations")
                    raise CancelledException("Diagnosis was cancelled")
                auto = await ha_automation_reader.get_automation(auto_info["id"])
                if auto:
                    full_automations.append(auto)

            # 3. Get entity list for validation (optional, may fail for large registries)
            available_entities = await self._get_entity_list()

            # Check for cancellation before Claude call
            if self._cancel_requested:
                logger.info("Diagnosis cancelled before analysis")
                raise CancelledException("Diagnosis was cancelled")

            # 4. Analyze automations in batches (single call for most cases)
            all_summaries: list[AutomationDiagnosisSummary] = []
            all_conflicts: list[AutomationConflict] = []
            overall_summary = ""

            if len(full_automations) <= self.MAX_BATCH_SIZE:
                # Single batch - one Claude call
                summaries, conflicts, summary = await self._analyze_batch(
                    full_automations, available_entities
                )
                all_summaries = summaries
                all_conflicts = conflicts
                overall_summary = summary
            else:
                # Multiple batches for very large automation sets
                logger.info(f"Splitting {len(full_automations)} automations into batches")
                for i in range(0, len(full_automations), self.MAX_BATCH_SIZE):
                    # Check for cancellation between batches
                    if self._cancel_requested:
                        logger.info(f"Diagnosis cancelled after {len(all_summaries)} automations")
                        raise CancelledException("Diagnosis was cancelled")

                    batch = full_automations[i:i + self.MAX_BATCH_SIZE]
                    logger.info(f"Analyzing batch {i // self.MAX_BATCH_SIZE + 1}: {len(batch)} automations")
                    summaries, conflicts, summary = await self._analyze_batch(
                        batch, available_entities
                    )
                    all_summaries.extend(summaries)
                    all_conflicts.extend(conflicts)
                    if not overall_summary:
                        overall_summary = summary

                # Generate combined summary for multiple batches
                if len(full_automations) > self.MAX_BATCH_SIZE:
                    overall_summary = self._generate_combined_summary(
                        all_summaries, all_conflicts, total_automations
                    )

            # 5. Count automations with errors
            automations_with_errors = sum(1 for s in all_summaries if s.has_errors)

            # 6. Extract insights for storage
            insights = self._extract_insights(all_summaries, all_conflicts)
            insights_added = await insights_storage.add_insights(insights)
            logger.info(f"Added {insights_added} new insights")

            # 7. Create report (without full_analyses since we don't have them in batch mode)
            report = BatchDiagnosisReport(
                run_id=run_id,
                run_at=run_at,
                scheduled=scheduled,
                total_automations=total_automations,
                automations_analyzed=len(all_summaries),
                automations_with_errors=automations_with_errors,
                conflicts_found=len(all_conflicts),
                insights_added=insights_added,
                automation_summaries=all_summaries,
                conflicts=all_conflicts,
                overall_summary=overall_summary,
                full_analyses=[],  # Not populated in batch mode
            )

            await diagnostic_storage.save_report(report.model_dump())
            logger.info(f"Batch diagnosis complete: {run_id} - {len(all_summaries)} analyzed, "
                       f"{automations_with_errors} with errors, {len(all_conflicts)} conflicts")

            return report

        finally:
            self._is_running = False
            self._cancel_requested = False

    async def _get_entity_list(self) -> list[str] | None:
        """Get list of available entity IDs for validation."""
        try:
            states = await ha_client.get_states()
            return [s.get("entity_id") for s in states if s.get("entity_id")]
        except Exception as e:
            logger.warning(f"Could not fetch entity list: {e}")
            return None

    async def _analyze_batch(
        self,
        automations: list[dict[str, Any]],
        available_entities: list[str] | None,
    ) -> tuple[list[AutomationDiagnosisSummary], list[AutomationConflict], str]:
        """Analyze a batch of automations with a single Claude call.

        Returns:
            Tuple of (summaries, conflicts, overall_summary)
        """
        try:
            # Build prompt
            prompt = build_batch_analysis_prompt(automations, available_entities)

            # Make single Claude API call
            logger.debug(f"Sending batch of {len(automations)} automations to Claude")
            response = await self.llm_client.generate_automation(
                "You are a Home Assistant automation expert. Respond only with valid JSON.",
                prompt,
            )

            # Parse JSON response
            result = self._parse_batch_response(response, automations)
            return result

        except Exception as e:
            logger.error(f"Batch analysis failed: {e}")
            # Return empty results on failure
            summaries = [
                AutomationDiagnosisSummary(
                    automation_id=a.get("id", ""),
                    automation_alias=a.get("alias", "Unknown"),
                    has_errors=False,
                    error_count=0,
                    warning_count=0,
                    brief_summary="Analysis failed",
                )
                for a in automations
            ]
            return summaries, [], f"Batch analysis failed: {str(e)}"

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
            # Extract JSON from response (may be wrapped in ```json ... ```)
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON
                json_str = response.strip()

            data = json.loads(json_str)

            # Parse automation summaries
            for auto_data in data.get("automations", []):
                status = auto_data.get("status", "ok")
                issues = auto_data.get("issues", [])
                has_errors = status == "error" or len(issues) > 0

                summaries.append(AutomationDiagnosisSummary(
                    automation_id=auto_data.get("id", ""),
                    automation_alias=auto_data.get("alias", "Unknown"),
                    has_errors=has_errors,
                    error_count=len(issues) if status == "error" else 0,
                    warning_count=len(issues) if status == "warning" else 0,
                    brief_summary=auto_data.get("summary", ""),
                ))

            # Parse conflicts
            for conflict_data in data.get("conflicts", []):
                conflicts.append(AutomationConflict(
                    conflict_type=conflict_data.get("type", "unknown"),
                    severity=conflict_data.get("severity", "info"),
                    automation_ids=conflict_data.get("automation_ids", []),
                    automation_names=conflict_data.get("automation_names", []),
                    description=conflict_data.get("description", ""),
                    affected_entities=conflict_data.get("affected_entities", []),
                ))

            overall_summary = data.get("overall_summary", "Analysis complete.")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response was: {response[:500]}...")

            # Create basic summaries from automation list
            for auto in automations:
                summaries.append(AutomationDiagnosisSummary(
                    automation_id=auto.get("id", ""),
                    automation_alias=auto.get("alias", "Unknown"),
                    has_errors=False,
                    error_count=0,
                    warning_count=0,
                    brief_summary="Could not parse analysis",
                ))
            overall_summary = "Analysis completed but response parsing failed."

        return summaries, conflicts, overall_summary

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
            return f"All {total} automations analyzed successfully with no issues detected."

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
                insights.append({
                    "category": "single",
                    "insight_type": "error",
                    "severity": "warning" if summary.error_count < 3 else "critical",
                    "title": f"Issues in '{summary.automation_alias}'",
                    "description": summary.brief_summary,
                    "automation_ids": [summary.automation_id],
                    "automation_names": [summary.automation_alias],
                    "affected_entities": [],
                    "recommendation": "Review the automation for the identified issues.",
                })

        # Multi-automation insights (conflicts)
        for conflict in conflicts:
            insights.append({
                "category": "multi",
                "insight_type": "conflict",
                "severity": conflict.severity,
                "title": f"{conflict.conflict_type.replace('_', ' ').title()}",
                "description": conflict.description,
                "automation_ids": conflict.automation_ids,
                "automation_names": conflict.automation_names,
                "affected_entities": conflict.affected_entities,
                "recommendation": self._get_conflict_recommendation(conflict.conflict_type),
            })

        return insights

    def _get_conflict_recommendation(self, conflict_type: str) -> str:
        """Get recommendation text for a conflict type."""
        recommendations = {
            "shared_trigger": "Consider using conditions to differentiate when each automation should run, or consolidate into a single automation.",
            "state_conflict": "Review which automation should take precedence, or add conditions to prevent conflicting actions.",
            "resource_contention": "Verify this is intentional. If automations should not run simultaneously, add mutual exclusion conditions.",
            "timing_race": "Add delays or conditions to ensure proper sequencing of automations.",
        }
        return recommendations.get(conflict_type, "Review the conflict and adjust automation logic as needed.")


# Global instance
batch_diagnosis_service = BatchDiagnosisService()

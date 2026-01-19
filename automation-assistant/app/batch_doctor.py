"""Batch Diagnosis Service - runs diagnosis on all automations and detects conflicts."""

import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

import yaml

from .diagnostic_storage import diagnostic_storage
from .doctor import automation_doctor
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
from .prompts import build_batch_summary_prompt

logger = logging.getLogger(__name__)


class BatchDiagnosisService:
    """Runs diagnosis on all automations and detects conflicts."""

    def __init__(self):
        self.llm_client = AsyncClaudeClient()

    async def run_batch_diagnosis(self, scheduled: bool = False) -> BatchDiagnosisReport:
        """Run batch diagnosis on all automations.

        Args:
            scheduled: Whether this is a scheduled run (vs manual trigger)

        Returns:
            BatchDiagnosisReport with all results
        """
        run_id = str(uuid.uuid4())[:8]
        run_at = datetime.utcnow()
        logger.info(f"Starting batch diagnosis run: {run_id} (scheduled={scheduled})")

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

        # 2. Get HA context once for all analyses
        context = await ha_client.get_full_context()

        # 3. Get full automation configs for conflict detection
        full_automations = []
        for auto_info in automations_list:
            auto = await ha_automation_reader.get_automation(auto_info["id"])
            if auto:
                full_automations.append(auto)

        # 4. Analyze each automation
        full_analyses: list[DiagnosisResponse] = []
        automation_summaries: list[AutomationDiagnosisSummary] = []
        automations_with_errors = 0

        for auto_info in automations_list:
            try:
                logger.debug(f"Diagnosing automation: {auto_info['alias']}")
                result = await automation_doctor.diagnose(auto_info["id"])
                full_analyses.append(result)

                # Extract summary from the analysis
                summary = self._extract_summary(result)
                automation_summaries.append(summary)

                if summary.has_errors:
                    automations_with_errors += 1

            except Exception as e:
                logger.error(f"Failed to diagnose {auto_info['alias']}: {e}")
                # Create error summary
                summary = AutomationDiagnosisSummary(
                    automation_id=auto_info["id"],
                    automation_alias=auto_info["alias"],
                    has_errors=True,
                    error_count=1,
                    warning_count=0,
                    brief_summary=f"Failed to analyze: {str(e)[:100]}",
                )
                automation_summaries.append(summary)
                automations_with_errors += 1

        # 5. Detect conflicts between automations
        conflicts = self._detect_conflicts(full_automations)
        logger.info(f"Detected {len(conflicts)} conflicts between automations")

        # 6. Extract insights (single + multi automation)
        insights = self._extract_insights(automation_summaries, full_analyses, conflicts)

        # 7. Store insights with deduplication
        insights_added = await insights_storage.add_insights(insights)
        logger.info(f"Added {insights_added} new insights")

        # 8. Generate overall summary with Claude
        overall_summary = await self._generate_overall_summary(
            automation_summaries, conflicts, total_automations, automations_with_errors
        )

        # 9. Create and save report
        report = BatchDiagnosisReport(
            run_id=run_id,
            run_at=run_at,
            scheduled=scheduled,
            total_automations=total_automations,
            automations_analyzed=len(full_analyses),
            automations_with_errors=automations_with_errors,
            conflicts_found=len(conflicts),
            insights_added=insights_added,
            automation_summaries=automation_summaries,
            conflicts=conflicts,
            overall_summary=overall_summary,
            full_analyses=full_analyses,
        )

        await diagnostic_storage.save_report(report.model_dump())
        logger.info(f"Batch diagnosis complete: {run_id}")

        return report

    def _extract_summary(self, diagnosis: DiagnosisResponse) -> AutomationDiagnosisSummary:
        """Extract summary from a diagnosis response."""
        analysis = diagnosis.analysis.lower()

        # Simple heuristics to count errors and warnings
        error_patterns = [
            r"\b(?:error|issue|problem|fail|invalid|missing|unavailable)\b",
        ]
        warning_patterns = [
            r"\b(?:warning|recommend|suggest|consider|improve|could be|might)\b",
        ]

        error_count = 0
        warning_count = 0

        for pattern in error_patterns:
            error_count += len(re.findall(pattern, analysis))
        for pattern in warning_patterns:
            warning_count += len(re.findall(pattern, analysis))

        # Cap counts at reasonable values
        error_count = min(error_count, 10)
        warning_count = min(warning_count, 10)

        has_errors = error_count > 0 or not diagnosis.success

        # Extract first sentence as brief summary
        brief_summary = ""
        if diagnosis.analysis:
            sentences = diagnosis.analysis.split(".")
            if sentences:
                brief_summary = sentences[0].strip()[:200]

        return AutomationDiagnosisSummary(
            automation_id=diagnosis.automation_id,
            automation_alias=diagnosis.automation_alias,
            has_errors=has_errors,
            error_count=error_count,
            warning_count=warning_count,
            brief_summary=brief_summary,
        )

    def _detect_conflicts(
        self, automations: list[dict[str, Any]]
    ) -> list[AutomationConflict]:
        """Detect conflicts between automations.

        Checks for:
        - shared_trigger: Multiple automations triggered by same entity state change
        - state_conflict: Automation A sets entity ON, Automation B sets it OFF
        - resource_contention: Multiple automations control same device/entity
        """
        conflicts: list[AutomationConflict] = []

        # Build maps for conflict detection
        trigger_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
        action_map: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for auto in automations:
            auto_id = auto.get("id", "")
            auto_alias = auto.get("alias", "Unnamed")

            # Extract triggers
            triggers = self._extract_triggers(auto)
            for trigger in triggers:
                entity_id = trigger.get("entity_id")
                if entity_id:
                    if isinstance(entity_id, list):
                        for eid in entity_id:
                            trigger_map[eid].append({"id": auto_id, "alias": auto_alias, "trigger": trigger})
                    else:
                        trigger_map[entity_id].append({"id": auto_id, "alias": auto_alias, "trigger": trigger})

            # Extract action targets
            targets = self._extract_target_entities(auto)
            for entity_id in targets:
                action_map[entity_id].append({"id": auto_id, "alias": auto_alias, "automation": auto})

        # Check for shared triggers
        for entity_id, trigger_list in trigger_map.items():
            if len(trigger_list) > 1:
                auto_ids = list(set(t["id"] for t in trigger_list))
                auto_names = list(set(t["alias"] for t in trigger_list))

                # Only report if actually different automations
                if len(auto_ids) > 1:
                    conflicts.append(
                        AutomationConflict(
                            conflict_type="shared_trigger",
                            severity="warning",
                            automation_ids=auto_ids,
                            automation_names=auto_names,
                            description=f"Multiple automations are triggered by the same entity: {entity_id}",
                            affected_entities=[entity_id],
                        )
                    )

        # Check for resource contention (same entity targeted by multiple automations)
        for entity_id, action_list in action_map.items():
            if len(action_list) > 1:
                auto_ids = list(set(a["id"] for a in action_list))
                auto_names = list(set(a["alias"] for a in action_list))

                if len(auto_ids) > 1:
                    # Check for state conflicts (opposing actions)
                    state_conflict = self._check_state_conflict(entity_id, action_list)

                    if state_conflict:
                        conflicts.append(
                            AutomationConflict(
                                conflict_type="state_conflict",
                                severity="critical",
                                automation_ids=auto_ids,
                                automation_names=auto_names,
                                description=f"Automations may set opposing states for {entity_id}: {state_conflict}",
                                affected_entities=[entity_id],
                            )
                        )
                    else:
                        conflicts.append(
                            AutomationConflict(
                                conflict_type="resource_contention",
                                severity="info",
                                automation_ids=auto_ids,
                                automation_names=auto_names,
                                description=f"Multiple automations control the same entity: {entity_id}",
                                affected_entities=[entity_id],
                            )
                        )

        return conflicts

    def _extract_triggers(self, automation: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract trigger information from automation."""
        triggers = automation.get("trigger", automation.get("triggers", []))
        if isinstance(triggers, dict):
            triggers = [triggers]
        return triggers or []

    def _extract_target_entities(self, automation: dict[str, Any]) -> set[str]:
        """Extract entities targeted by actions."""
        entities: set[str] = set()

        actions = automation.get("action", automation.get("actions", []))
        if isinstance(actions, dict):
            actions = [actions]

        for action in actions or []:
            # Direct entity_id in action
            entity_id = action.get("entity_id")
            if entity_id:
                if isinstance(entity_id, list):
                    entities.update(entity_id)
                else:
                    entities.add(entity_id)

            # Target with entity_id
            target = action.get("target", {})
            if isinstance(target, dict):
                target_entity = target.get("entity_id")
                if target_entity:
                    if isinstance(target_entity, list):
                        entities.update(target_entity)
                    else:
                        entities.add(target_entity)

            # Data with entity_id
            data = action.get("data", {})
            if isinstance(data, dict):
                data_entity = data.get("entity_id")
                if data_entity:
                    if isinstance(data_entity, list):
                        entities.update(data_entity)
                    else:
                        entities.add(data_entity)

            # Check for service call targets
            service = action.get("service", "")
            if service and "." in service:
                # Service calls like light.turn_on
                pass  # Entity ID would be in target/entity_id

        return entities

    def _check_state_conflict(
        self, entity_id: str, action_list: list[dict[str, Any]]
    ) -> str | None:
        """Check if automations set opposing states for an entity."""
        states_set = set()

        for action_info in action_list:
            auto = action_info.get("automation", {})
            actions = auto.get("action", auto.get("actions", []))
            if isinstance(actions, dict):
                actions = [actions]

            for action in actions or []:
                target_entity = action.get("entity_id")
                if not target_entity:
                    target = action.get("target", {})
                    target_entity = target.get("entity_id") if isinstance(target, dict) else None

                # Check if this action targets our entity
                if target_entity:
                    targets = [target_entity] if isinstance(target_entity, str) else target_entity
                    if entity_id in targets:
                        service = action.get("service", "")
                        if "turn_on" in service:
                            states_set.add("ON")
                        elif "turn_off" in service:
                            states_set.add("OFF")
                        elif "toggle" in service:
                            states_set.add("TOGGLE")

        if "ON" in states_set and "OFF" in states_set:
            return "One automation turns ON, another turns OFF"
        if "TOGGLE" in states_set and len(states_set) > 1:
            return "One automation toggles while others set specific states"

        return None

    def _extract_insights(
        self,
        summaries: list[AutomationDiagnosisSummary],
        analyses: list[DiagnosisResponse],
        conflicts: list[AutomationConflict],
    ) -> list[dict[str, Any]]:
        """Extract insights from diagnosis results."""
        insights: list[dict[str, Any]] = []

        # Single automation insights
        for summary, analysis in zip(summaries, analyses):
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
                    "recommendation": "Review the diagnosis details for specific fixes.",
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
            "shared_trigger": "Consider using conditions to differentiate when each automation should run, or consolidate into a single automation with choose/conditions.",
            "state_conflict": "Review which automation should take precedence, or add conditions to prevent conflicting actions.",
            "resource_contention": "Verify this is intentional. If automations should not run simultaneously, add mutual exclusion conditions.",
            "timing_race": "Add delays or conditions to ensure proper sequencing of automations.",
            "circular_dependency": "Review the automation chain to break the circular dependency.",
        }
        return recommendations.get(conflict_type, "Review the conflict and adjust automation logic as needed.")

    async def _generate_overall_summary(
        self,
        summaries: list[AutomationDiagnosisSummary],
        conflicts: list[AutomationConflict],
        total_automations: int,
        automations_with_errors: int,
    ) -> str:
        """Generate overall summary using Claude."""
        try:
            prompt = build_batch_summary_prompt(
                [s.model_dump() for s in summaries],
                [c.model_dump() for c in conflicts],
                total_automations,
                automations_with_errors,
            )

            summary = await self.llm_client.generate_automation(
                "You are a Home Assistant automation expert providing concise summaries.",
                prompt,
            )
            return summary

        except Exception as e:
            logger.error(f"Failed to generate overall summary: {e}")
            # Fallback to basic summary
            if automations_with_errors == 0 and len(conflicts) == 0:
                return f"All {total_automations} automations analyzed successfully with no issues detected."
            return (
                f"Analyzed {total_automations} automations. "
                f"Found issues in {automations_with_errors} automation(s) and "
                f"detected {len(conflicts)} potential conflict(s)."
            )


# Global instance
batch_diagnosis_service = BatchDiagnosisService()

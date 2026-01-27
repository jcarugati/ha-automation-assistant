"""Automation Doctor - diagnoses and analyzes existing automations."""

import logging
from typing import Any

from .ha_automations import ha_automation_reader
from .ha_client import ha_client
from .config import config
from .llm.claude import AsyncClaudeClient
from .models import DiagnosisResponse
from .prompts import build_debug_system_prompt, build_debug_user_prompt

logger = logging.getLogger(__name__)


class AutomationDoctor:
    """Diagnoses and analyzes Home Assistant automations."""

    def __init__(self):
        self.llm_client = AsyncClaudeClient(model=config.doctor_model_or_default)

    async def diagnose(self, automation_id: str) -> DiagnosisResponse:
        """Diagnose an automation and provide analysis.

        Args:
            automation_id: The ID of the automation to diagnose.

        Returns:
            DiagnosisResponse with the analysis and recommendations.
        """
        try:
            # Fetch automation and traces
            data = await ha_automation_reader.get_automation_with_traces(automation_id)

            automation = data.get("automation")
            if not automation:
                return DiagnosisResponse(
                    automation_id=automation_id,
                    automation_alias="Unknown",
                    automation_yaml="",
                    traces_summary=[],
                    analysis="",
                    success=False,
                    error=f"Automation with ID '{automation_id}' not found",
                )

            yaml_content = data.get("yaml", "")
            traces = data.get("traces", [])
            alias = automation.get("alias", "Unnamed Automation")

            # Fetch HA context for entity/service validation
            context = await ha_client.get_full_context()

            # Build prompts
            system_prompt = build_debug_system_prompt(context)
            user_prompt = build_debug_user_prompt(yaml_content, traces, alias)

            logger.debug(f"Diagnosing automation: {alias} ({automation_id})")
            logger.debug(f"System prompt length: {len(system_prompt)}")

            # Call LLM for analysis
            analysis = await self.llm_client.generate_automation(
                system_prompt, user_prompt
            )

            return DiagnosisResponse(
                automation_id=automation_id,
                automation_alias=alias,
                automation_yaml=yaml_content,
                traces_summary=traces,
                analysis=analysis,
                success=True,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to diagnose automation: {e}")
            return DiagnosisResponse(
                automation_id=automation_id,
                automation_alias="Unknown",
                automation_yaml="",
                traces_summary=[],
                analysis="",
                success=False,
                error=str(e),
            )

    async def list_automations(self) -> list[dict[str, Any]]:
        """List all available automations."""
        return await ha_automation_reader.list_automations()

    async def get_automation_details(self, automation_id: str) -> dict[str, Any]:
        """Get automation details including traces."""
        return await ha_automation_reader.get_automation_with_traces(automation_id)


# Singleton instance
automation_doctor = AutomationDoctor()

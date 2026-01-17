"""Automation generation logic."""

import logging
import re
from typing import Any

import yaml

from .ha_client import ha_client
from .llm.claude import AsyncClaudeClient
from .models import AutomationResponse, ValidationResponse
from .prompts import build_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)


def extract_yaml_from_response(response: str) -> str | None:
    """Extract YAML content from an LLM response.

    Looks for YAML in code blocks (```yaml ... ``` or ``` ... ```).
    """
    # Try to find YAML in code blocks
    patterns = [
        r"```yaml\s*(.*?)\s*```",
        r"```\s*(alias:.*?)\s*```",
    ]

    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()

    return None


def validate_automation_yaml(yaml_content: str) -> ValidationResponse:
    """Validate automation YAML syntax and structure."""
    errors = []

    try:
        data = yaml.safe_load(yaml_content)

        if not isinstance(data, dict):
            errors.append("YAML must be a dictionary/mapping")
            return ValidationResponse(valid=False, errors=errors)

        # Check for required fields
        if "alias" not in data:
            errors.append("Missing 'alias' field")

        # Check for trigger, condition, or action
        has_trigger = "trigger" in data or "triggers" in data
        has_action = "action" in data or "actions" in data

        if not has_trigger:
            errors.append("Missing 'trigger' or 'triggers' field")

        if not has_action:
            errors.append("Missing 'action' or 'actions' field")

    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML syntax: {e}")

    return ValidationResponse(valid=len(errors) == 0, errors=errors)


class AutomationGenerator:
    """Generates Home Assistant automations using LLM."""

    def __init__(self):
        self.llm_client = AsyncClaudeClient()

    async def generate(self, user_request: str) -> AutomationResponse:
        """Generate an automation from a natural language request.

        Args:
            user_request: The user's natural language description of the automation.

        Returns:
            AutomationResponse with the generated YAML and explanation.
        """
        try:
            # Fetch HA context
            context = await ha_client.get_full_context()

            # Build prompts
            system_prompt = build_system_prompt(context)
            user_prompt = build_user_prompt(user_request)

            logger.debug(f"System prompt length: {len(system_prompt)}")
            logger.debug(f"User prompt: {user_prompt}")

            # Call LLM
            response = await self.llm_client.generate_automation(
                system_prompt, user_prompt
            )

            # Extract YAML
            yaml_content = extract_yaml_from_response(response)

            return AutomationResponse(
                success=True,
                response=response,
                yaml_content=yaml_content,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to generate automation: {e}")
            return AutomationResponse(
                success=False,
                response="",
                yaml_content=None,
                error=str(e),
            )

    async def get_context_summary(self) -> dict[str, Any]:
        """Get a summary of the available HA context."""
        context = await ha_client.get_full_context()

        states = context.get("states", [])
        domains = set()
        for state in states:
            entity_id = state.get("entity_id", "")
            if "." in entity_id:
                domains.add(entity_id.split(".")[0])

        services = context.get("services", [])
        service_count = sum(
            len(s.get("services", {})) for s in services
        )

        return {
            "entity_count": len(states),
            "device_count": len(context.get("devices", [])),
            "area_count": len(context.get("areas", [])),
            "service_count": service_count,
            "domains": sorted(domains),
        }


# Singleton instance
automation_generator = AutomationGenerator()

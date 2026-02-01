"""Automation generation logic."""

import logging
import re
from typing import Any, Optional

import yaml
from aiohttp import ClientError

from .ha_client import ha_client
from .llm.claude import AsyncClaudeClient
from .models import AutomationResponse, ValidationResponse
from .prompts import build_modify_user_prompt, build_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)


def _parse_yaml_payload(payload: str) -> Optional[Any]:
    """Parse a YAML payload safely."""
    try:
        return yaml.safe_load(payload)
    except yaml.YAMLError:
        return None


def _normalize_automation_yaml(payload: str) -> Optional[str]:
    """Normalize a YAML payload into a single automation mapping."""
    parsed = _parse_yaml_payload(payload)
    if parsed is None:
        return None
    if isinstance(parsed, list):
        if len(parsed) == 1 and isinstance(parsed[0], dict):
            parsed = parsed[0]
        else:
            return None
    if not isinstance(parsed, dict):
        return None
    return yaml.dump(parsed, default_flow_style=False, sort_keys=False)


def _extract_yaml_from_text(response: str) -> Optional[str]:
    """Extract YAML-like content from a plain text response."""
    lines = response.splitlines()
    start_index = None
    key_pattern = re.compile(
        r"^\s*(?:-\s*)?(alias|id|description|trigger|action|condition|mode)\s*:",
        re.IGNORECASE,
    )
    for index, line in enumerate(lines):
        if key_pattern.match(line):
            start_index = index
            break
    if start_index is None:
        return None
    candidate = "\n".join(lines[start_index:]).strip()
    if not candidate:
        return None
    return candidate


def extract_yaml_from_response(response: str) -> Optional[str]:
    """Extract YAML content from an LLM response.

    Looks for YAML in code blocks (```yaml ... ``` or ``` ... ```),
    then falls back to scanning the response for YAML-like content.
    """
    code_block_pattern = re.compile(r"```(?:yaml)?\s*(.*?)\s*```", re.DOTALL)
    for match in code_block_pattern.findall(response):
        candidate = match.strip()
        normalized = _normalize_automation_yaml(candidate)
        if normalized:
            return normalized

    text_candidate = _extract_yaml_from_text(response)
    if text_candidate:
        normalized = _normalize_automation_yaml(text_candidate)
        if normalized:
            return normalized

    return None


def _looks_like_action_list(payload: Any) -> bool:
    """Heuristic to detect action-only YAML payloads."""
    if not isinstance(payload, list) or not payload:
        return False
    action_keys = {
        "action",
        "service",
        "device_id",
        "domain",
        "type",
        "delay",
        "choose",
        "repeat",
        "wait_for_trigger",
        "wait_template",
        "target",
        "data",
    }
    for item in payload:
        if not isinstance(item, dict):
            return False
        if not action_keys & item.keys():
            return False
    return True


def _coerce_updated_config(
    updated_config: Any,
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Normalize an updated automation payload into a mapping."""
    if isinstance(updated_config, list):
        if len(updated_config) == 1 and isinstance(updated_config[0], dict):
            return updated_config[0], None
        if _looks_like_action_list(updated_config):
            return {"action": updated_config}, None
        return (
            None,
            "Modified YAML must be a single automation mapping. "
            "The model returned a list instead.",
        )
    if not isinstance(updated_config, dict):
        return None, "Modified YAML must be a mapping of a single automation."
    return updated_config, None


def _merge_automation_configs(
    existing_config: dict[str, Any], updated_config: dict[str, Any]
) -> dict[str, Any]:
    """Merge updated fields into an existing automation config."""
    merged_config = {**existing_config, **updated_config}
    existing_id = existing_config.get("id")
    if existing_id:
        merged_config["id"] = existing_id
    if "alias" not in updated_config and existing_config.get("alias"):
        merged_config["alias"] = existing_config.get("alias")
    if "description" not in updated_config and existing_config.get("description"):
        merged_config["description"] = existing_config.get("description")
    return merged_config


def _prepare_modified_yaml(
    existing_yaml: str, response: str
) -> tuple[Optional[str], Optional[str]]:
    """Build a merged automation YAML payload from a model response."""
    existing_config = _parse_yaml_payload(existing_yaml)
    if not isinstance(existing_config, dict):
        return None, "Existing automation YAML is invalid or not a mapping."

    yaml_content = extract_yaml_from_response(response)
    if not yaml_content:
        return (
            None,
            "Could not extract automation YAML from the model response. "
            "Ask for the full automation YAML in a code block.",
        )

    updated_config = _parse_yaml_payload(yaml_content)
    if updated_config is None:
        return None, "Modified YAML could not be parsed."

    normalized_config, error = _coerce_updated_config(updated_config)
    if error:
        return yaml_content, error

    merged_config = _merge_automation_configs(existing_config, normalized_config)
    merged_yaml = yaml.dump(merged_config, default_flow_style=False, sort_keys=False)
    validation = validate_automation_yaml(merged_yaml)
    if not validation.valid:
        return (
            merged_yaml,
            "Modified YAML failed validation: "
            f"{'; '.join(validation.errors)}",
        )

    return merged_yaml, None


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

            logger.debug("System prompt length: %s", len(system_prompt))
            logger.debug("User prompt: %s", user_prompt)

            # Call LLM
            response = await self.llm_client.generate_automation(
                system_prompt, user_prompt
            )

            # Extract YAML
            yaml_content = extract_yaml_from_response(response)
            if not yaml_content:
                return AutomationResponse(
                    success=False,
                    response=response,
                    yaml_content=None,
                    error=(
                        "Could not extract automation YAML from the model response. "
                        "Ask for the full automation YAML in a code block."
                    ),
                )

            validation = validate_automation_yaml(yaml_content)
            if not validation.valid:
                return AutomationResponse(
                    success=False,
                    response=response,
                    yaml_content=yaml_content,
                    error=(
                        "Generated YAML failed validation: "
                        f"{'; '.join(validation.errors)}"
                    ),
                )

            return AutomationResponse(
                success=True,
                response=response,
                yaml_content=yaml_content,
                error=None,
            )

        except (ClientError, RuntimeError, TimeoutError, ValueError) as exc:
            logger.error("Failed to generate automation: %s", exc)
            return AutomationResponse(
                success=False,
                response="",
                yaml_content=None,
                error=str(exc),
            )

    async def modify(
        self, existing_yaml: str, modification_request: str
    ) -> AutomationResponse:
        """Modify an existing automation based on a natural language request.

        Args:
            existing_yaml: The current YAML of the automation.
            modification_request: The user's natural language modification request.

        Returns:
            AutomationResponse with the modified YAML and explanation.
        """
        response = ""
        yaml_content: Optional[str] = None
        error: Optional[str] = None

        try:
            # Fetch HA context
            context = await ha_client.get_full_context()

            # Build prompts
            system_prompt = build_system_prompt(context)
            user_prompt = build_modify_user_prompt(existing_yaml, modification_request)

            logger.debug("System prompt length: %s", len(system_prompt))
            logger.debug("Modification request: %s", modification_request)

            # Call LLM
            response = await self.llm_client.generate_automation(
                system_prompt, user_prompt
            )
            yaml_content, error = _prepare_modified_yaml(existing_yaml, response)

        except (ClientError, RuntimeError, TimeoutError, ValueError) as exc:
            logger.error("Failed to modify automation: %s", exc)
            response = response or ""
            yaml_content = None
            error = str(exc)

        return AutomationResponse(
            success=error is None,
            response=response,
            yaml_content=yaml_content,
            error=error,
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
        service_count = sum(len(s.get("services", {})) for s in services)

        return {
            "entity_count": len(states),
            "device_count": len(context.get("devices", [])),
            "area_count": len(context.get("areas", [])),
            "service_count": service_count,
            "domains": sorted(domains),
        }


# Singleton instance
automation_generator = AutomationGenerator()

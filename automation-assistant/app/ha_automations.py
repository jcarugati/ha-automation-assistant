"""Reader for Home Assistant automations and traces."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

from .ha_client import ha_client

logger = logging.getLogger(__name__)

# Allow overriding config path for local development
HA_CONFIG_PATH = os.environ.get("HA_CONFIG_PATH", "/config")


class HAAutomationReader:
    """Reads automations and execution traces from Home Assistant config files."""

    def __init__(self, config_path: str = "/config"):
        self.config_path = Path(config_path)
        self.automations_file = self.config_path / "automations.yaml"
        self.traces_file = self.config_path / ".storage" / "trace.saved_traces"

    def _read_automations_file(self) -> list[dict[str, Any]]:
        """Read and parse automations.yaml."""
        if not self.automations_file.exists():
            logger.warning(f"Automations file not found: {self.automations_file}")
            return []
        try:
            content = self.automations_file.read_text()
            if not content.strip():
                return []
            automations = yaml.safe_load(content)
            if automations is None:
                return []
            if isinstance(automations, list):
                return automations
            return []
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse automations.yaml: {e}")
            return []

    def _read_traces_file(self) -> dict[str, Any]:
        """Read and parse trace.saved_traces."""
        if not self.traces_file.exists():
            logger.warning(f"Traces file not found: {self.traces_file}")
            return {}
        try:
            content = self.traces_file.read_text()
            if not content.strip():
                return {}
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse traces file: {e}")
            return {}

    async def list_automations(self) -> list[dict[str, Any]]:
        """List all automations with basic info including area data and state."""
        automations = self._read_automations_file()

        # Fall back to API if file doesn't exist (local development)
        if not automations and not self.automations_file.exists():
            logger.info("Automations file not found, fetching via API...")
            automations = await ha_client.list_automations()

        # Fetch entity registry and areas for enrichment
        try:
            entity_registry = await ha_client.get_entity_registry()
            areas = await ha_client.get_areas()
            states = await ha_client.get_states()
            logger.info(f"Enrichment data: {len(entity_registry)} entities, {len(areas)} areas, {len(states)} states")
        except Exception as e:
            logger.warning(f"Failed to fetch enrichment data: {e}")
            entity_registry = []
            areas = []
            states = []

        # Build lookup maps
        area_map = {a.get("area_id"): a.get("name", "") for a in areas}
        entity_map = {
            e.get("entity_id"): e
            for e in entity_registry
            if e.get("entity_id", "").startswith("automation.")
        }
        unique_id_map = {
            e.get("unique_id"): e.get("entity_id")
            for e in entity_registry
            if e.get("entity_id", "").startswith("automation.") and e.get("unique_id")
        }
        state_map = {
            s.get("entity_id"): s.get("state", "unknown")
            for s in states
            if s.get("entity_id", "").startswith("automation.")
        }
        state_id_map = {
            s.get("attributes", {}).get("id"): s.get("entity_id")
            for s in states
            if s.get("entity_id", "").startswith("automation.")
            and s.get("attributes", {}).get("id")
        }

        result = []
        for auto in automations:
            auto_id = auto.get("id", "")
            # Prefer entity_id from API response or registry/state mappings
            entity_id = (
                auto.get("_entity_id")
                or unique_id_map.get(auto_id)
                or state_id_map.get(auto_id)
                or (f"automation.{auto_id}" if auto_id else None)
            )

            # Get area info from entity registry
            entity_info = entity_map.get(entity_id, {}) if entity_id else {}
            area_id = entity_info.get("area_id")
            area_name = area_map.get(area_id) if area_id else None

            # Get state (on/off)
            state = state_map.get(entity_id, "unknown") if entity_id else "unknown"

            result.append({
                "id": auto_id,
                "alias": auto.get("alias", "Unnamed Automation"),
                "description": auto.get("description", ""),
                "mode": auto.get("mode", "single"),
                "area_id": area_id,
                "area_name": area_name,
                "state": state,
            })
        return result

    async def get_automation(self, automation_id: str) -> Optional[dict[str, Any]]:
        """Get a specific automation by ID."""
        automations = self._read_automations_file()
        for auto in automations:
            if auto.get("id") == automation_id:
                return auto

        # Fall back to API if not found in file (local development)
        if not self.automations_file.exists():
            return await ha_client.get_automation_config(automation_id)
        return None

    async def get_automation_yaml(self, automation_id: str) -> Optional[str]:
        """Get automation as YAML string."""
        automation = await self.get_automation(automation_id)
        if automation:
            return yaml.dump(automation, default_flow_style=False, sort_keys=False)
        return None

    async def get_traces(self, automation_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Get execution traces, optionally filtered by automation ID."""
        traces_data = self._read_traces_file()
        data = traces_data.get("data", {})

        if automation_id:
            # Try both with and without automation. prefix
            key = f"automation.{automation_id}" if not automation_id.startswith("automation.") else automation_id
            traces = data.get(key, [])
            # Also try just the ID
            if not traces:
                traces = data.get(automation_id, [])
            return traces

        # Return all traces
        all_traces = []
        for entity_id, traces in data.items():
            for trace in traces:
                trace["entity_id"] = entity_id
                all_traces.append(trace)
        return all_traces

    async def get_automation_with_traces(self, automation_id: str) -> dict[str, Any]:
        """Get automation config along with its recent traces."""
        automation = await self.get_automation(automation_id)
        if not automation:
            return {"automation": None, "traces": [], "yaml": None}

        traces = await self.get_traces(automation_id)
        yaml_content = await self.get_automation_yaml(automation_id)

        # Parse traces into a simpler format
        parsed_traces = []
        for trace in traces:
            parsed_trace = {
                "run_id": trace.get("run_id", ""),
                "state": trace.get("state", "unknown"),
                "script_execution": trace.get("script_execution"),
                "trigger": trace.get("trigger", "Unknown trigger"),
            }

            # Handle timestamp
            timestamp = trace.get("timestamp", {})
            if isinstance(timestamp, dict):
                parsed_trace["timestamp_start"] = timestamp.get("start")
                parsed_trace["timestamp_finish"] = timestamp.get("finish")
            else:
                parsed_trace["timestamp_start"] = None
                parsed_trace["timestamp_finish"] = None

            # Check for errors in the trace
            trace_data = trace.get("trace", {})
            error = None
            for step, steps in trace_data.items():
                if isinstance(steps, list):
                    for step_data in steps:
                        if step_data.get("error"):
                            error = step_data.get("error")
                            break
                if error:
                    break
            parsed_trace["error"] = error

            parsed_traces.append(parsed_trace)

        return {
            "automation": automation,
            "traces": parsed_traces,
            "yaml": yaml_content,
        }


# Global instance - uses HA_CONFIG_PATH env var for local development
ha_automation_reader = HAAutomationReader(config_path=HA_CONFIG_PATH)

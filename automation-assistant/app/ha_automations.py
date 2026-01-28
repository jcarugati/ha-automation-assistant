"""Reader for Home Assistant automations and traces."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from aiohttp import ClientError
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
            logger.warning(
                "Automations file not found: %s", self.automations_file
            )
            return []
        try:
            content = self.automations_file.read_text(encoding="utf-8")
            if not content.strip():
                return []
            automations = yaml.safe_load(content)
            if automations is None:
                return []
            if isinstance(automations, list):
                return automations
            return []
        except (OSError, yaml.YAMLError) as exc:
            logger.error("Failed to parse automations.yaml: %s", exc)
            return []

    def _read_traces_file(self) -> tuple[dict[str, Any], str]:
        """Read and parse trace.saved_traces."""
        if not self.traces_file.exists():
            logger.warning("Traces file not found: %s", self.traces_file)
            return {}, "missing_file"
        try:
            content = self.traces_file.read_text(encoding="utf-8")
            if not content.strip():
                return {}, "empty_file"
            return json.loads(content), "ok"
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to parse traces file: %s", exc)
            return {}, "invalid_json"

    def _extract_time_fields(
        self, payload: dict[str, Any]
    ) -> tuple[Optional[str], Optional[str]]:
        """Extract start/finish values from a timestamp payload."""
        start = payload.get("start") or payload.get("started") or payload.get(
            "start_time"
        )
        finish = (
            payload.get("finish")
            or payload.get("end")
            or payload.get("finished")
            or payload.get("end_time")
        )
        return start, finish

    def _extract_timestamp_from_trace_data(
        self, trace_data: dict[str, Any]
    ) -> tuple[Optional[str], Optional[str]]:
        """Find timestamp values inside nested trace payloads."""
        for key, value in trace_data.items():
            if "timestamp" not in str(key).lower():
                continue
            if isinstance(value, dict):
                start, finish = self._extract_time_fields(value)
                if start:
                    return start, finish
        return None, None

    def _extract_timestamp(self, trace: dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        """Extract start/finish timestamps from a trace, if present."""
        start = None
        finish = None

        timestamp = trace.get("timestamp")
        if isinstance(timestamp, dict):
            start, finish = self._extract_time_fields(timestamp)
        elif isinstance(timestamp, str):
            start = timestamp

        start = (
            start
            or trace.get("timestamp_start")
            or trace.get("start")
            or trace.get("start_time")
        )
        finish = (
            finish
            or trace.get("timestamp_finish")
            or trace.get("finish")
            or trace.get("end")
            or trace.get("end_time")
        )

        if not start:
            trace_data = trace.get("trace", {})
            if isinstance(trace_data, dict):
                start, finish = self._extract_timestamp_from_trace_data(trace_data)

        return start, finish

    def _extract_trigger_from_step(self, step: dict[str, Any]) -> Optional[Any]:
        """Extract trigger info from a step-like payload."""
        if step.get("trigger"):
            return step.get("trigger")
        if step.get("description") or step.get("platform") or step.get("entity_id"):
            return {
                "description": step.get("description"),
                "platform": step.get("platform"),
                "entity_id": step.get("entity_id"),
            }
        return None

    def _extract_trigger_from_steps(self, steps: Any) -> Optional[Any]:
        """Extract trigger info from steps in trace data."""
        if isinstance(steps, list):
            for step in steps:
                if not isinstance(step, dict):
                    continue
                trigger = self._extract_trigger_from_step(step)
                if trigger:
                    return trigger
            return None
        if isinstance(steps, dict):
            return self._extract_trigger_from_step(steps)
        return None

    def _unwrap_trace_payload(self, trace: dict[str, Any]) -> dict[str, Any]:
        """Extract the real trace payload when stored under short_dict/extended_dict."""
        payload = trace.get("extended_dict") or trace.get("short_dict")
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, str):
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                return {}
        return {}

    def _extract_trigger(self, trace: dict[str, Any]) -> Any:
        """Extract trigger info from a trace if not present on the root object."""
        trace_data = trace.get("trace", {})
        if not isinstance(trace_data, dict):
            return None

        # Direct trigger fields sometimes appear on the trace payload
        for direct_key in ("trigger", "trigger_data", "trigger_description"):
            if direct_key in trace_data:
                return trace_data.get(direct_key)

        # Look for trigger-like steps in the trace data
        for key, steps in trace_data.items():
            if "trigger" not in str(key).lower():
                continue
            trigger = self._extract_trigger_from_steps(steps)
            if trigger:
                return trigger
        return None

    def _extract_trace_error(self, trace: dict[str, Any]) -> Optional[Any]:
        """Extract error info from a trace."""
        trace_data = trace.get("trace", {})
        error = trace.get("error")
        if not isinstance(trace_data, dict):
            return error
        for _step_key, steps in trace_data.items():
            if isinstance(steps, list):
                for step_data in steps:
                    if step_data.get("error"):
                        return step_data.get("error")
            if error:
                return error
        return error

    def _parse_trace_entry(
        self, trace: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Parse a trace into a compact summary and stats updates."""
        payload = self._unwrap_trace_payload(trace)
        source = payload if payload else trace
        source_dict = source if isinstance(source, dict) else trace

        trigger = source_dict.get("trigger") if isinstance(source_dict, dict) else None
        if not trigger:
            trigger = self._extract_trigger(source_dict)

        state = self._extract_state(source_dict)
        script_execution = None
        if isinstance(source_dict, dict):
            script_execution = source_dict.get("script_execution") or source_dict.get(
                "script"
            )

        timestamp_start, timestamp_finish = self._extract_timestamp(source_dict)
        error = self._extract_trace_error(trace)

        parsed_trace = {
            "run_id": self._extract_run_id(source_dict),
            "state": state,
            "script_execution": script_execution,
            "trigger": trigger,
            "timestamp_start": timestamp_start,
            "timestamp_finish": timestamp_finish,
            "error": error,
        }

        stats = {
            "missing_timestamps": 1 if not timestamp_start else 0,
            "missing_triggers": 1 if not trigger else 0,
            "missing_states": 1 if not state and not script_execution else 0,
            "sample_keys": sorted([str(k) for k in trace.keys()])
            if isinstance(trace, dict)
            else [],
            "sample_payload_keys": sorted([str(k) for k in payload.keys()])
            if isinstance(payload, dict)
            else [],
        }
        return parsed_trace, stats

    def _extract_state(self, trace: dict[str, Any]) -> Optional[str]:
        """Extract execution state from a trace if present."""
        for key in ("state", "status", "result"):
            value = trace.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    def _extract_run_id(self, trace: dict[str, Any]) -> str:
        """Extract a run ID from a trace payload if available."""
        for key in ("run_id", "id", "trace_id"):
            value = trace.get(key)
            if isinstance(value, str) and value:
                return value
        return ""

    def _build_lookup_maps(
        self,
        entity_registry: list[dict[str, Any]],
        areas: list[dict[str, Any]],
        states: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Build lookup maps for area/entity/state enrichment."""
        area_map = {area.get("area_id"): area.get("name", "") for area in areas}
        entity_map = {
            entity.get("entity_id"): entity
            for entity in entity_registry
            if entity.get("entity_id", "").startswith("automation.")
        }
        unique_id_map = {
            entity.get("unique_id"): entity.get("entity_id")
            for entity in entity_registry
            if entity.get("entity_id", "").startswith("automation.")
            and entity.get("unique_id")
        }
        state_map = {
            state.get("entity_id"): state.get("state", "unknown")
            for state in states
            if state.get("entity_id", "").startswith("automation.")
        }
        state_id_map = {
            state.get("attributes", {}).get("id"): state.get("entity_id")
            for state in states
            if state.get("entity_id", "").startswith("automation.")
            and state.get("attributes", {}).get("id")
        }
        return {
            "area_map": area_map,
            "entity_map": entity_map,
            "unique_id_map": unique_id_map,
            "state_map": state_map,
            "state_id_map": state_id_map,
        }

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
            logger.info(
                "Enrichment data: %s entities, %s areas, %s states",
                len(entity_registry),
                len(areas),
                len(states),
            )
        except (ClientError, RuntimeError, TimeoutError, ValueError) as exc:
            logger.warning("Failed to fetch enrichment data: %s", exc)
            entity_registry = []
            areas = []
            states = []

        lookup = self._build_lookup_maps(entity_registry, areas, states)

        result = []
        for auto in automations:
            auto_id = auto.get("id", "")
            # Prefer entity_id from API response or registry/state mappings
            entity_id = (
                auto.get("_entity_id")
                or lookup["unique_id_map"].get(auto_id)
                or lookup["state_id_map"].get(auto_id)
                or (f"automation.{auto_id}" if auto_id else None)
            )

            # Get area info from entity registry
            entity_info = lookup["entity_map"].get(entity_id, {}) if entity_id else {}
            area_id = entity_info.get("area_id")
            area_name = (
                lookup["area_map"].get(area_id) if area_id else None
            )

            # Get state (on/off)
            state = (
                lookup["state_map"].get(entity_id, "unknown")
                if entity_id
                else "unknown"
            )

            result.append(
                {
                    "id": auto_id,
                    "alias": auto.get("alias", "Unnamed Automation"),
                    "description": auto.get("description", ""),
                    "mode": auto.get("mode", "single"),
                    "area_id": area_id,
                    "area_name": area_name,
                    "state": state,
                }
            )
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

    async def get_traces(
        self, automation_id: Optional[str] = None
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Get execution traces, optionally filtered by automation ID."""
        traces_data, status = self._read_traces_file()
        data = traces_data.get("data", {})

        meta = {
            "status": status,
            "source": "file",
            "path": str(self.traces_file),
        }

        if automation_id:
            # Try both with and without automation. prefix
            if automation_id.startswith("automation."):
                key = automation_id
            else:
                key = f"automation.{automation_id}"
            traces = data.get(key, [])
            # Also try just the ID
            if not traces:
                traces = data.get(automation_id, [])
            meta["count"] = len(traces)
            return traces, meta

        # Return all traces
        all_traces = []
        for entity_id, traces in data.items():
            for trace in traces:
                trace["entity_id"] = entity_id
                all_traces.append(trace)
        meta["count"] = len(all_traces)
        return all_traces, meta

    async def get_automation_with_traces(self, automation_id: str) -> dict[str, Any]:
        """Get automation config along with its recent traces."""
        automation = await self.get_automation(automation_id)
        if not automation:
            return {"automation": None, "traces": [], "yaml": None}

        traces, traces_meta = await self.get_traces(automation_id)
        yaml_content = await self.get_automation_yaml(automation_id)

        # Parse traces into a simpler format
        parsed_traces: list[dict[str, Any]] = []
        stats = {
            "missing_timestamps": 0,
            "missing_triggers": 0,
            "missing_states": 0,
            "sample_keys": [],
            "sample_payload_keys": [],
        }

        for trace in traces:
            parsed_trace, updates = self._parse_trace_entry(trace)
            stats["missing_timestamps"] += updates["missing_timestamps"]
            stats["missing_triggers"] += updates["missing_triggers"]
            stats["missing_states"] += updates["missing_states"]
            if not stats["sample_keys"] and updates["sample_keys"]:
                stats["sample_keys"] = updates["sample_keys"]
            if not stats["sample_payload_keys"] and updates["sample_payload_keys"]:
                stats["sample_payload_keys"] = updates["sample_payload_keys"]
            parsed_traces.append(parsed_trace)

        if traces:
            logger.debug(
                "Trace parse summary for %s: %s traces, missing timestamps=%s, "
                "missing triggers=%s, missing state=%s, sample keys=%s, sample "
                "payload keys=%s",
                automation_id,
                len(traces),
                stats["missing_timestamps"],
                stats["missing_triggers"],
                stats["missing_states"],
                stats["sample_keys"],
                stats["sample_payload_keys"],
            )

        return {
            "automation": automation,
            "traces": parsed_traces,
            "yaml": yaml_content,
            "traces_meta": traces_meta,
        }


# Global instance - uses HA_CONFIG_PATH env var for local development
ha_automation_reader = HAAutomationReader(config_path=HA_CONFIG_PATH)

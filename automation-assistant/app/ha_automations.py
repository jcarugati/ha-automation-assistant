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

    def _read_traces_file(self) -> tuple[dict[str, Any], str]:
        """Read and parse trace.saved_traces."""
        if not self.traces_file.exists():
            logger.warning(f"Traces file not found: {self.traces_file}")
            return {}, "missing_file"
        try:
            content = self.traces_file.read_text()
            if not content.strip():
                return {}, "empty_file"
            return json.loads(content), "ok"
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse traces file: {e}")
            return {}, "invalid_json"

    def _extract_timestamp(self, trace: dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        """Extract start/finish timestamps from a trace, if present."""
        start = None
        finish = None

        timestamp = trace.get("timestamp")
        if isinstance(timestamp, dict):
            start = timestamp.get("start") or timestamp.get("started") or timestamp.get("start_time")
            finish = (
                timestamp.get("finish")
                or timestamp.get("end")
                or timestamp.get("finished")
                or timestamp.get("end_time")
            )
        elif isinstance(timestamp, str):
            start = timestamp

        start = start or trace.get("timestamp_start") or trace.get("start") or trace.get("start_time")
        finish = finish or trace.get("timestamp_finish") or trace.get("finish") or trace.get("end") or trace.get("end_time")

        if not start:
            trace_data = trace.get("trace", {})
            if isinstance(trace_data, dict):
                for key, value in trace_data.items():
                    if "timestamp" not in str(key).lower():
                        continue
                    if isinstance(value, dict):
                        start = value.get("start") or value.get("started") or value.get("start_time")
                        finish = (
                            finish
                            or value.get("finish")
                            or value.get("end")
                            or value.get("finished")
                            or value.get("end_time")
                        )
                        if start:
                            break

        return start, finish

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
            if isinstance(steps, list):
                for step in steps:
                    if not isinstance(step, dict):
                        continue
                    if step.get("trigger"):
                        return step.get("trigger")
                    if step.get("description") or step.get("platform") or step.get("entity_id"):
                        return {
                            "description": step.get("description"),
                            "platform": step.get("platform"),
                            "entity_id": step.get("entity_id"),
                        }
            elif isinstance(steps, dict):
                if steps.get("trigger"):
                    return steps.get("trigger")
                if steps.get("description") or steps.get("platform") or steps.get("entity_id"):
                    return {
                        "description": steps.get("description"),
                        "platform": steps.get("platform"),
                        "entity_id": steps.get("entity_id"),
                    }
        return None

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

    async def get_traces(self, automation_id: Optional[str] = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
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
            key = f"automation.{automation_id}" if not automation_id.startswith("automation.") else automation_id
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
        parsed_traces = []
        missing_timestamps = 0
        missing_triggers = 0
        missing_states = 0
        sample_keys: list[str] = []
        sample_payload_keys: list[str] = []

        for trace in traces:
            payload = self._unwrap_trace_payload(trace)
            source = payload or trace

            trigger = source.get("trigger") if isinstance(source, dict) else None
            if not trigger:
                trigger = self._extract_trigger(source if isinstance(source, dict) else trace)

            state = self._extract_state(source if isinstance(source, dict) else trace)
            script_execution = (
                (source.get("script_execution") if isinstance(source, dict) else None)
                or (source.get("script") if isinstance(source, dict) else None)
            )

            parsed_trace = {
                "run_id": self._extract_run_id(source if isinstance(source, dict) else trace),
                "state": state,
                "script_execution": script_execution,
                "trigger": trigger,
            }

            # Handle timestamp
            timestamp_start, timestamp_finish = self._extract_timestamp(source if isinstance(source, dict) else trace)
            parsed_trace["timestamp_start"] = timestamp_start
            parsed_trace["timestamp_finish"] = timestamp_finish
            if not timestamp_start:
                missing_timestamps += 1

            # Check for errors in the trace
            trace_data = trace.get("trace", {})
            error = trace.get("error")
            for step, steps in trace_data.items():
                if isinstance(steps, list):
                    for step_data in steps:
                        if step_data.get("error"):
                            error = step_data.get("error")
                            break
                if error:
                    break
            parsed_trace["error"] = error
            if not parsed_trace["trigger"]:
                missing_triggers += 1
            if not state and not script_execution:
                missing_states += 1
            if not sample_keys and isinstance(trace, dict):
                sample_keys = sorted([str(k) for k in trace.keys()])
            if not sample_payload_keys and isinstance(payload, dict):
                sample_payload_keys = sorted([str(k) for k in payload.keys()])

            parsed_traces.append(parsed_trace)

        if traces:
            logger.debug(
                "Trace parse summary for %s: %s traces, missing timestamps=%s, missing triggers=%s, missing state=%s, sample keys=%s, sample payload keys=%s",
                automation_id,
                len(traces),
                missing_timestamps,
                missing_triggers,
                missing_states,
                sample_keys,
                sample_payload_keys,
            )

        return {
            "automation": automation,
            "traces": parsed_traces,
            "yaml": yaml_content,
            "traces_meta": traces_meta,
        }


# Global instance - uses HA_CONFIG_PATH env var for local development
ha_automation_reader = HAAutomationReader(config_path=HA_CONFIG_PATH)

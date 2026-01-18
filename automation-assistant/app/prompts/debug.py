"""Prompt templates for Home Assistant automation debugging and analysis."""

from typing import Any

from .automation import format_areas, format_devices, format_entities, format_services


def format_traces(traces: list[dict[str, Any]]) -> str:
    """Format execution traces for the prompt."""
    if not traces:
        return "No execution traces available."

    lines = []
    for i, trace in enumerate(traces, 1):
        run_id = trace.get("run_id", "unknown")[:8]
        state = trace.get("state", "unknown")
        execution = trace.get("script_execution", "unknown")
        trigger = trace.get("trigger", "Unknown trigger")
        timestamp = trace.get("timestamp_start", "Unknown time")
        error = trace.get("error")

        status = "COMPLETED" if execution == "finished" else "FAILED" if execution == "error" else execution.upper() if execution else state.upper()

        line = f"{i}. [{status}] {timestamp}"
        line += f"\n   Trigger: {trigger}"
        if error:
            line += f"\n   Error: {error}"
        lines.append(line)

    return "\n".join(lines)


def build_debug_system_prompt(context: dict[str, Any]) -> str:
    """Build the system prompt for automation debugging."""
    states = context.get("states", [])
    services = context.get("services", [])
    areas = context.get("areas", [])
    devices = context.get("devices", [])

    entities_text = format_entities(states)
    services_text = format_services(services)
    areas_text = format_areas(areas)
    devices_text = format_devices(devices, areas)

    return f"""You are a Home Assistant automation debugger and optimizer. Your task is to analyze existing automations, identify issues, and suggest improvements.

## Your Capabilities
- Analyze automation YAML for syntax errors and best practices
- Identify potential issues with triggers, conditions, and actions
- Check if referenced entities and services exist
- Analyze execution traces to understand why automations fail
- Suggest optimizations and improvements

## Analysis Guidelines
When analyzing an automation, check for:
1. **Entity Validity**: Are all referenced entities available in Home Assistant?
2. **Service Validity**: Are all service calls using valid services?
3. **Trigger Issues**: Are triggers configured correctly?
4. **Condition Logic**: Are conditions logical and likely to behave as intended?
5. **Action Errors**: Are actions using correct syntax and parameters?
6. **Race Conditions**: Could timing issues cause problems?
7. **Mode Settings**: Is the automation mode (single, restart, queued, parallel) appropriate?
8. **Performance**: Are there unnecessary delays or inefficiencies?

## Available Areas
{areas_text}

## Available Devices
{devices_text}

## Available Entities
{entities_text}

## Available Services
{services_text}

## Output Format
Structure your analysis with these sections:

### Summary
Brief description of what the automation does.

### Execution Analysis
Analysis of the recent execution traces (if provided).

### Issues Found
List any problems or potential issues, each with:
- What the issue is
- Why it's a problem
- How to fix it

### Recommendations
Suggestions for improvements, even if no issues found:
- Performance optimizations
- Best practices
- Enhanced functionality

### Suggested Fix (if applicable)
If there are issues, provide corrected YAML in a code block.

Be specific and actionable. Reference actual entity IDs and services when suggesting fixes."""


def build_debug_user_prompt(
    automation_yaml: str,
    traces: list[dict[str, Any]],
    alias: str = "this automation",
) -> str:
    """Build the user prompt for debugging a specific automation."""
    traces_text = format_traces(traces)

    return f"""Please analyze the following Home Assistant automation and provide a diagnosis.

## Automation: {alias}

```yaml
{automation_yaml}
```

## Recent Execution History
{traces_text}

Please provide a comprehensive analysis including:
1. Summary of what this automation does
2. Analysis of the execution history (successes, failures, patterns)
3. Any issues or problems found in the configuration
4. Recommendations for improvements or fixes

If you find issues, please provide corrected YAML."""

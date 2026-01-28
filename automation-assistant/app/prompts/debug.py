"""Prompt templates for Home Assistant automation debugging and analysis."""

from typing import Any

from .automation import build_toon_context
from .common import build_toon_section


def format_traces(traces: list[dict[str, Any]]) -> str:
    """Format execution traces for the prompt."""
    if not traces:
        return "No execution traces available."

    lines = []
    for i, trace in enumerate(traces, 1):
        state = trace.get("state", "unknown")
        execution = trace.get("script_execution", "unknown")
        trigger = trace.get("trigger", "Unknown trigger")
        timestamp = trace.get("timestamp_start", "Unknown time")
        error = trace.get("error")

        if execution == "finished":
            status = "COMPLETED"
        elif execution == "error":
            status = "FAILED"
        elif execution:
            status = execution.upper()
        else:
            status = state.upper()

        line = f"{i}. [{status}] {timestamp}"
        line += f"\n   Trigger: {trigger}"
        if error:
            line += f"\n   Error: {error}"
        lines.append(line)

    return "\n".join(lines)


def build_debug_system_prompt(context: dict[str, Any]) -> str:
    """Build the system prompt for automation debugging."""
    toon_context = build_toon_context(context)
    toon_section = build_toon_section(toon_context)

    return (
        "You are a Home Assistant automation debugger and optimizer. Your task "
        "is to analyze existing automations, identify issues, and suggest "
        "improvements.\n\n"
        "## Your Capabilities\n"
        "- Analyze automation YAML for syntax errors and best practices\n"
        "- Identify potential issues with triggers, conditions, and actions\n"
        "- Check if referenced entities and services exist\n"
        "- Analyze execution traces to understand why automations fail\n"
        "- Suggest optimizations and improvements\n\n"
        "## Analysis Guidelines\n"
        "When analyzing an automation, check for:\n"
        "1. **Entity Validity**: Are all referenced entities available in Home "
        "Assistant?\n"
        "2. **Service Validity**: Are all service calls using valid services?\n"
        "3. **Trigger Issues**: Are triggers configured correctly?\n"
        "4. **Condition Logic**: Are conditions logical and likely to behave as "
        "intended?\n"
        "5. **Action Errors**: Are actions using correct syntax and parameters?\n"
        "6. **Race Conditions**: Could timing issues cause problems?\n"
        "7. **Mode Settings**: Is the automation mode (single, restart, queued, "
        "parallel) appropriate?\n"
        "8. **Performance**: Are there unnecessary delays or inefficiencies?\n\n"
        f"{toon_section}"
        "## Output Format\n"
        "Structure your analysis with these sections:\n\n"
        "### Summary\n"
        "Brief description of what the automation does.\n\n"
        "### Execution Analysis\n"
        "Analysis of the recent execution traces (if provided).\n\n"
        "### Issues Found\n"
        "List any problems or potential issues, each with:\n"
        "- What the issue is\n"
        "- Why it's a problem\n"
        "- How to fix it\n\n"
        "### Recommendations\n"
        "Suggestions for improvements, even if no issues found:\n"
        "- Performance optimizations\n"
        "- Best practices\n"
        "- Enhanced functionality\n\n"
        "### Suggested Fix (if applicable)\n"
        "If there are issues, provide corrected YAML in a code block.\n\n"
        "Be specific and actionable. Reference actual entity IDs and services "
        "when suggesting fixes."
    )


def build_debug_user_prompt(
    automation_yaml: str,
    traces: list[dict[str, Any]],
    alias: str = "this automation",
) -> str:
    """Build the user prompt for debugging a specific automation."""
    traces_text = format_traces(traces)

    return (
        "Please analyze the following Home Assistant automation and provide a "
        "diagnosis.\n\n"
        f"## Automation: {alias}\n\n"
        "```yaml\n"
        f"{automation_yaml}\n"
        "```\n\n"
        "## Recent Execution History\n"
        f"{traces_text}\n\n"
        "Please provide a comprehensive analysis including:\n"
        "1. Summary of what this automation does\n"
        "2. Analysis of the execution history (successes, failures, patterns)\n"
        "3. Any issues or problems found in the configuration\n"
        "4. Recommendations for improvements or fixes\n\n"
        "If you find issues, please provide corrected YAML."
    )

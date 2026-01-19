"""Prompt templates for automation conflict detection and batch analysis."""

from typing import Any

import yaml


def build_batch_summary_prompt(
    automation_summaries: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    total_automations: int,
    automations_with_errors: int,
) -> str:
    """Build prompt for Claude to generate an overall batch diagnosis summary.

    Args:
        automation_summaries: List of per-automation diagnosis summaries
        conflicts: List of detected conflicts between automations
        total_automations: Total number of automations analyzed
        automations_with_errors: Count of automations with issues

    Returns:
        Prompt string for generating summary
    """
    # Format automation summaries
    summaries_text = ""
    for summary in automation_summaries:
        status = "HAS ISSUES" if summary.get("has_errors") else "OK"
        summaries_text += f"- {summary.get('automation_alias', 'Unknown')} [{status}]\n"
        if summary.get("brief_summary"):
            summaries_text += f"  Summary: {summary.get('brief_summary')}\n"
        if summary.get("error_count", 0) > 0:
            summaries_text += f"  Errors: {summary.get('error_count')}\n"
        if summary.get("warning_count", 0) > 0:
            summaries_text += f"  Warnings: {summary.get('warning_count')}\n"
        summaries_text += "\n"

    # Format conflicts
    conflicts_text = ""
    if conflicts:
        for conflict in conflicts:
            conflicts_text += f"- {conflict.get('conflict_type', 'unknown').upper()}: "
            conflicts_text += f"{', '.join(conflict.get('automation_names', []))}\n"
            conflicts_text += f"  Description: {conflict.get('description', '')}\n"
            conflicts_text += f"  Affected entities: {', '.join(conflict.get('affected_entities', []))}\n"
            conflicts_text += f"  Severity: {conflict.get('severity', 'unknown')}\n\n"
    else:
        conflicts_text = "No conflicts detected between automations.\n"

    return f"""You are analyzing a batch diagnosis of Home Assistant automations. Provide a concise overall summary.

## Statistics
- Total automations analyzed: {total_automations}
- Automations with issues: {automations_with_errors}
- Conflicts detected: {len(conflicts)}

## Per-Automation Status
{summaries_text}

## Conflicts Between Automations
{conflicts_text}

## Your Task
Provide a brief overall summary (2-4 sentences) that:
1. States the overall health of the automation system
2. Highlights the most critical issues if any
3. Mentions any important conflicts that need attention

Keep your response concise and actionable. Do not repeat the details above - synthesize them into useful insights."""


def build_conflict_analysis_prompt(
    automations: list[dict[str, Any]],
    detected_conflicts: list[dict[str, Any]],
) -> str:
    """Build prompt for Claude to analyze conflicts in depth.

    Args:
        automations: List of automation configurations involved in conflicts
        detected_conflicts: Pre-detected conflicts from code analysis

    Returns:
        Prompt string for deeper analysis
    """
    # Format automations YAML
    automations_text = ""
    for auto in automations:
        auto_yaml = yaml.dump(auto, default_flow_style=False, sort_keys=False)
        automations_text += f"### {auto.get('alias', 'Unnamed')}\n```yaml\n{auto_yaml}```\n\n"

    # Format detected conflicts
    conflicts_text = ""
    for conflict in detected_conflicts:
        conflicts_text += f"- **{conflict.get('conflict_type', 'unknown').upper()}**\n"
        conflicts_text += f"  Automations: {', '.join(conflict.get('automation_names', []))}\n"
        conflicts_text += f"  Description: {conflict.get('description', '')}\n"
        conflicts_text += f"  Affected entities: {', '.join(conflict.get('affected_entities', []))}\n\n"

    return f"""You are a Home Assistant automation expert analyzing potential conflicts between automations.

## Automations Involved
{automations_text}

## Pre-Detected Conflicts
{conflicts_text}

## Your Task
Analyze these conflicts and provide:
1. Whether each conflict is a real problem or a false positive
2. The potential consequences if not addressed
3. Specific recommendations to resolve each conflict

Be concise and practical in your recommendations."""


def build_single_diagnosis_summary_prompt(
    automation_alias: str,
    analysis: str,
) -> str:
    """Build prompt to extract brief summary and issue counts from a full diagnosis.

    Args:
        automation_alias: Name of the automation
        analysis: Full diagnosis text from Claude

    Returns:
        Prompt string
    """
    return f"""Extract a brief summary from this automation diagnosis.

## Automation: {automation_alias}

## Full Analysis
{analysis}

## Your Task
Provide a JSON response with:
1. "brief_summary": One sentence describing the automation's status
2. "error_count": Number of errors/issues found (integer)
3. "warning_count": Number of warnings/recommendations (integer)
4. "has_errors": true if there are any errors, false otherwise

Respond with only valid JSON, no other text."""

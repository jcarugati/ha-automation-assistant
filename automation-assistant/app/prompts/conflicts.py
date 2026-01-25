"""Prompt templates for automation conflict detection and batch analysis."""

import json
from typing import Any, Optional

import yaml


def compact_automation(auto: dict[str, Any]) -> str:
    """Convert an automation to a compact, token-efficient format.

    Reduces tokens by ~60% while preserving all essential information.
    """
    lines = []

    # Header
    alias = auto.get("alias", "Unnamed")
    auto_id = auto.get("id", "unknown")
    mode = auto.get("mode", "single")
    lines.append(f"[{alias}] id={auto_id} mode={mode}")

    # Check if this is a blueprint-based automation
    use_blueprint = auto.get("use_blueprint")
    if use_blueprint:
        blueprint_path = use_blueprint.get("path", "unknown")
        lines.append(f"  BLUEPRINT: {blueprint_path}")
        inputs = use_blueprint.get("input", {})
        if inputs:
            # Show blueprint inputs (these define the automation's behavior)
            for key, value in inputs.items():
                value_str = str(value)
                if len(value_str) > 60:
                    value_str = value_str[:57] + "..."
                lines.append(f"    input.{key}: {value_str}")
        lines.append("  (Blueprint automation - triggers/actions defined in blueprint)")
        return "\n".join(lines)

    # Triggers
    triggers = auto.get("trigger", auto.get("triggers", []))
    if isinstance(triggers, dict):
        triggers = [triggers]

    for t in triggers:
        lines.append(f"  TRIGGER: {_compact_trigger(t)}")

    # Conditions
    conditions = auto.get("condition", auto.get("conditions", []))
    if isinstance(conditions, dict):
        conditions = [conditions]

    for c in conditions:
        lines.append(f"  CONDITION: {_compact_condition(c)}")

    # Actions
    actions = auto.get("action", auto.get("actions", []))
    if isinstance(actions, dict):
        actions = [actions]

    for a in actions:
        compact = _compact_action(a)
        if compact:
            lines.append(f"  ACTION: {compact}")

    return "\n".join(lines)


def _compact_trigger(t: dict[str, Any]) -> str:
    """Compact a single trigger."""
    platform = t.get("platform", t.get("trigger", "unknown"))

    if platform == "state":
        entity = t.get("entity_id", "?")
        if isinstance(entity, list):
            entity = ",".join(entity)
        to_state = t.get("to", "*")
        from_state = t.get("from", "")
        result = f"state({entity})→{to_state}"
        if from_state:
            result = f"state({entity}) {from_state}→{to_state}"
        if t.get("for"):
            result += f" for={t['for']}"
        return result

    elif platform == "time":
        return f"time({t.get('at', '?')})"

    elif platform == "sun":
        event = t.get("event", "?")
        offset = t.get("offset", "")
        return f"sun.{event}" + (f" offset={offset}" if offset else "")

    elif platform == "numeric_state":
        entity = t.get("entity_id", "?")
        above = t.get("above", "")
        below = t.get("below", "")
        cond = []
        if above:
            cond.append(f">{above}")
        if below:
            cond.append(f"<{below}")
        return f"numeric({entity}) {' '.join(cond)}"

    elif platform == "event":
        event_type = t.get("event_type", "?")
        return f"event({event_type})"

    elif platform == "homeassistant":
        return f"ha.{t.get('event', '?')}"

    elif platform == "mqtt":
        return f"mqtt({t.get('topic', '?')})"

    elif platform == "webhook":
        return f"webhook({t.get('webhook_id', '?')})"

    elif platform == "zone":
        entity = t.get("entity_id", "?")
        zone = t.get("zone", "?")
        event = t.get("event", "enter")
        return f"zone({entity}) {event} {zone}"

    elif platform == "device":
        device = t.get("device_id", "?")[:8] if t.get("device_id") else "?"
        domain = t.get("domain", "?")
        dtype = t.get("type", "?")
        return f"device({domain}.{dtype}) dev={device}..."

    elif platform == "template":
        tmpl = t.get("value_template", "?")
        if len(tmpl) > 50:
            tmpl = tmpl[:47] + "..."
        return f"template({tmpl})"

    elif platform == "time_pattern":
        hours = t.get("hours", "*")
        minutes = t.get("minutes", "*")
        seconds = t.get("seconds", "*")
        return f"time_pattern({hours}:{minutes}:{seconds})"

    else:
        # Generic fallback
        return f"{platform}({json.dumps(t, default=str)[:60]})"


def _compact_condition(c: dict[str, Any]) -> str:
    """Compact a single condition."""
    cond_type = c.get("condition", "unknown")

    if cond_type == "state":
        entity = c.get("entity_id", "?")
        state = c.get("state", "?")
        return f"state({entity})={state}"

    elif cond_type == "numeric_state":
        entity = c.get("entity_id", "?")
        above = c.get("above", "")
        below = c.get("below", "")
        cond = []
        if above:
            cond.append(f">{above}")
        if below:
            cond.append(f"<{below}")
        return f"numeric({entity}) {' '.join(cond)}"

    elif cond_type == "time":
        after = c.get("after", "")
        before = c.get("before", "")
        return f"time({after}-{before})"

    elif cond_type == "sun":
        after = c.get("after", "")
        before = c.get("before", "")
        return f"sun({after} to {before})"

    elif cond_type == "zone":
        entity = c.get("entity_id", "?")
        zone = c.get("zone", "?")
        return f"zone({entity} in {zone})"

    elif cond_type == "template":
        tmpl = c.get("value_template", "?")
        if len(tmpl) > 50:
            tmpl = tmpl[:47] + "..."
        return f"template({tmpl})"

    elif cond_type in ("and", "or", "not"):
        sub = c.get("conditions", [])
        return f"{cond_type}([{len(sub)} conditions])"

    else:
        return f"{cond_type}(...)"


def _compact_action(a: dict[str, Any]) -> str:
    """Compact a single action."""
    # Service call
    if "service" in a:
        service = a.get("service", "?")
        target = a.get("target", {})
        entity = target.get("entity_id", a.get("entity_id", ""))
        if isinstance(entity, list):
            entity = ",".join(entity[:3]) + ("..." if len(entity) > 3 else "")
        data = a.get("data", {})
        data_str = ""
        if data:
            # Only show key names, not values (to save tokens)
            data_str = " {" + ",".join(data.keys()) + "}"
        target_str = f" → {entity}" if entity else ""
        return f"{service}{target_str}{data_str}"

    # Delay
    elif "delay" in a:
        return f"delay({a['delay']})"

    # Wait
    elif "wait_template" in a:
        return f"wait_template(...)"

    elif "wait_for_trigger" in a:
        return f"wait_for_trigger(...)"

    # Conditions in actions
    elif "condition" in a:
        return f"condition: {_compact_condition(a)}"

    # Choose
    elif "choose" in a:
        choices = a.get("choose", [])
        return f"choose([{len(choices)} options])"

    # Repeat
    elif "repeat" in a:
        return f"repeat(...)"

    # If-then
    elif "if" in a:
        return f"if-then-else(...)"

    # Parallel
    elif "parallel" in a:
        return f"parallel([{len(a.get('parallel', []))} actions])"

    # Scene
    elif "scene" in a:
        return f"scene({a['scene']})"

    # Event
    elif "event" in a:
        return f"fire_event({a['event']})"

    # Variables
    elif "variables" in a:
        return f"variables({list(a['variables'].keys())})"

    # Stop
    elif "stop" in a:
        return f"stop({a.get('stop', '')})"

    else:
        # Unknown action type
        keys = list(a.keys())
        return f"action({keys})"


def build_batch_analysis_prompt(
    automations: list[dict[str, Any]],
    available_entities: Optional[list[str]] = None,
) -> str:
    """Build prompt for Claude to analyze ALL automations in a single request.

    Uses compact format to reduce tokens by ~60%.

    Args:
        automations: List of all automation configurations
        available_entities: Optional list of valid entity IDs for validation

    Returns:
        Prompt string for comprehensive batch analysis
    """
    # Format all automations in compact format
    automations_text = ""
    for i, auto in enumerate(automations, 1):
        automations_text += f"---{i}---\n{compact_automation(auto)}\n\n"

    entities_text = ""
    if available_entities:
        # Only include a sample if there are too many
        if len(available_entities) > 200:
            entities_text = f"\nKnown entities ({len(available_entities)} total): {', '.join(available_entities[:30])}..."
        else:
            entities_text = f"\nKnown entities: {', '.join(available_entities)}"

    return f"""Analyze {len(automations)} HA automations. Find issues and conflicts.
{entities_text}

{automations_text}
Respond with JSON only:
{{"automations":[{{"id":"...","alias":"...","status":"ok|warning|error","issues":[],"summary":"..."}}],
"conflicts":[{{"type":"shared_trigger|state_conflict|resource_contention|timing_race","severity":"info|warning|critical","automation_ids":[],"automation_names":[],"description":"...","affected_entities":[],"recommendation":"..."}}],
"overall_summary":"..."}}

IMPORTANT: Blueprint automations (marked with BLUEPRINT:) are VALID. Their triggers/actions are defined in the blueprint file, not shown here. Do NOT flag them as empty or missing triggers/actions.

Check: invalid entities, logic problems, shared triggers, opposing actions on same entity. Only real issues."""


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

"""Prompt templates for automation conflict detection and batch analysis."""

import json
from typing import Any, Optional

import yaml


def _append_blueprint_lines(lines: list[str], auto: dict[str, Any]) -> bool:
    """Append blueprint-specific lines when automation uses a blueprint."""
    use_blueprint = auto.get("use_blueprint")
    if not use_blueprint:
        return False
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
    return True


def _append_compact_triggers(lines: list[str], auto: dict[str, Any]) -> None:
    """Append compact trigger lines."""
    triggers = auto.get("trigger", auto.get("triggers", []))
    if isinstance(triggers, dict):
        triggers = [triggers]
    for trigger in triggers:
        lines.append(f"  TRIGGER: {_compact_trigger(trigger)}")


def _append_compact_conditions(lines: list[str], auto: dict[str, Any]) -> None:
    """Append compact condition lines."""
    conditions = auto.get("condition", auto.get("conditions", []))
    if isinstance(conditions, dict):
        conditions = [conditions]
    for condition in conditions:
        lines.append(f"  CONDITION: {_compact_condition(condition)}")


def _append_compact_actions(lines: list[str], auto: dict[str, Any]) -> None:
    """Append compact action lines."""
    actions = auto.get("action", auto.get("actions", []))
    if isinstance(actions, dict):
        actions = [actions]
    for action in actions:
        compact = _compact_action(action)
        if compact:
            lines.append(f"  ACTION: {compact}")


def compact_automation(auto: dict[str, Any]) -> str:
    """Convert an automation to a compact, token-efficient format.

    Reduces tokens by ~60% while preserving all essential information.
    """
    lines = [
        (
            f"[{auto.get('alias', 'Unnamed')}] id={auto.get('id', 'unknown')} "
            f"mode={auto.get('mode', 'single')}"
        )
    ]

    if _append_blueprint_lines(lines, auto):
        return "\n".join(lines)

    _append_compact_triggers(lines, auto)
    _append_compact_conditions(lines, auto)
    _append_compact_actions(lines, auto)

    return "\n".join(lines)


def _compact_state_trigger(trigger: dict[str, Any]) -> str:
    entity = trigger.get("entity_id", "?")
    if isinstance(entity, list):
        entity = ",".join(entity)
    to_state = trigger.get("to", "*")
    from_state = trigger.get("from", "")
    result = f"state({entity})→{to_state}"
    if from_state:
        result = f"state({entity}) {from_state}→{to_state}"
    if trigger.get("for"):
        result += f" for={trigger['for']}"
    return result


def _compact_time_trigger(trigger: dict[str, Any]) -> str:
    return f"time({trigger.get('at', '?')})"


def _compact_sun_trigger(trigger: dict[str, Any]) -> str:
    event = trigger.get("event", "?")
    offset = trigger.get("offset", "")
    return f"sun.{event}" + (f" offset={offset}" if offset else "")


def _compact_numeric_state_trigger(trigger: dict[str, Any]) -> str:
    entity = trigger.get("entity_id", "?")
    above = trigger.get("above", "")
    below = trigger.get("below", "")
    cond = []
    if above:
        cond.append(f">{above}")
    if below:
        cond.append(f"<{below}")
    return f"numeric({entity}) {' '.join(cond)}"


def _compact_event_trigger(trigger: dict[str, Any]) -> str:
    event_type = trigger.get("event_type", "?")
    return f"event({event_type})"


def _compact_homeassistant_trigger(trigger: dict[str, Any]) -> str:
    return f"ha.{trigger.get('event', '?')}"


def _compact_mqtt_trigger(trigger: dict[str, Any]) -> str:
    return f"mqtt({trigger.get('topic', '?')})"


def _compact_webhook_trigger(trigger: dict[str, Any]) -> str:
    return f"webhook({trigger.get('webhook_id', '?')})"


def _compact_zone_trigger(trigger: dict[str, Any]) -> str:
    entity = trigger.get("entity_id", "?")
    zone = trigger.get("zone", "?")
    event = trigger.get("event", "enter")
    return f"zone({entity}) {event} {zone}"


def _compact_device_trigger(trigger: dict[str, Any]) -> str:
    device_id = trigger.get("device_id")
    device = device_id[:8] if device_id else "?"
    domain = trigger.get("domain", "?")
    dtype = trigger.get("type", "?")
    return f"device({domain}.{dtype}) dev={device}..."


def _compact_template_trigger(trigger: dict[str, Any]) -> str:
    tmpl = trigger.get("value_template", "?")
    if len(tmpl) > 50:
        tmpl = tmpl[:47] + "..."
    return f"template({tmpl})"


def _compact_time_pattern_trigger(trigger: dict[str, Any]) -> str:
    hours = trigger.get("hours", "*")
    minutes = trigger.get("minutes", "*")
    seconds = trigger.get("seconds", "*")
    return f"time_pattern({hours}:{minutes}:{seconds})"


_TRIGGER_HANDLERS = {
    "state": _compact_state_trigger,
    "time": _compact_time_trigger,
    "sun": _compact_sun_trigger,
    "numeric_state": _compact_numeric_state_trigger,
    "event": _compact_event_trigger,
    "homeassistant": _compact_homeassistant_trigger,
    "mqtt": _compact_mqtt_trigger,
    "webhook": _compact_webhook_trigger,
    "zone": _compact_zone_trigger,
    "device": _compact_device_trigger,
    "template": _compact_template_trigger,
    "time_pattern": _compact_time_pattern_trigger,
}


def _compact_trigger(trigger: dict[str, Any]) -> str:
    """Compact a single trigger."""
    platform = trigger.get("platform", trigger.get("trigger", "unknown"))
    handler = _TRIGGER_HANDLERS.get(platform)
    if handler:
        return handler(trigger)
    return f"{platform}({json.dumps(trigger, default=str)[:60]})"


def _compact_state_condition(condition: dict[str, Any]) -> str:
    entity = condition.get("entity_id", "?")
    state = condition.get("state", "?")
    return f"state({entity})={state}"


def _compact_numeric_state_condition(condition: dict[str, Any]) -> str:
    entity = condition.get("entity_id", "?")
    above = condition.get("above", "")
    below = condition.get("below", "")
    cond = []
    if above:
        cond.append(f">{above}")
    if below:
        cond.append(f"<{below}")
    return f"numeric({entity}) {' '.join(cond)}"


def _compact_time_condition(condition: dict[str, Any]) -> str:
    after = condition.get("after", "")
    before = condition.get("before", "")
    return f"time({after}-{before})"


def _compact_sun_condition(condition: dict[str, Any]) -> str:
    after = condition.get("after", "")
    before = condition.get("before", "")
    return f"sun({after} to {before})"


def _compact_zone_condition(condition: dict[str, Any]) -> str:
    entity = condition.get("entity_id", "?")
    zone = condition.get("zone", "?")
    return f"zone({entity} in {zone})"


def _compact_template_condition(condition: dict[str, Any]) -> str:
    tmpl = condition.get("value_template", "?")
    if len(tmpl) > 50:
        tmpl = tmpl[:47] + "..."
    return f"template({tmpl})"


def _compact_logical_condition(condition: dict[str, Any]) -> str:
    sub = condition.get("conditions", [])
    cond_type = condition.get("condition", "unknown")
    return f"{cond_type}([{len(sub)} conditions])"


_CONDITION_HANDLERS = {
    "state": _compact_state_condition,
    "numeric_state": _compact_numeric_state_condition,
    "time": _compact_time_condition,
    "sun": _compact_sun_condition,
    "zone": _compact_zone_condition,
    "template": _compact_template_condition,
    "and": _compact_logical_condition,
    "or": _compact_logical_condition,
    "not": _compact_logical_condition,
}


def _compact_condition(condition: dict[str, Any]) -> str:
    """Compact a single condition."""
    cond_type = condition.get("condition", "unknown")
    handler = _CONDITION_HANDLERS.get(cond_type)
    if handler:
        return handler(condition)
    return f"{cond_type}(...)"


def _action_service(action: dict[str, Any]) -> str:
    service = action.get("service", "?")
    target = action.get("target", {})
    entity = target.get("entity_id", action.get("entity_id", ""))
    if isinstance(entity, list):
        entity = ",".join(entity[:3]) + ("..." if len(entity) > 3 else "")
    data = action.get("data", {})
    data_str = ""
    if data:
        # Only show key names, not values (to save tokens)
        data_str = " {" + ",".join(data.keys()) + "}"
    target_str = f" → {entity}" if entity else ""
    return f"{service}{target_str}{data_str}"


def _action_delay(action: dict[str, Any]) -> str:
    return f"delay({action['delay']})"


def _action_wait_template(_action: dict[str, Any]) -> str:
    return "wait_template(...)"


def _action_wait_for_trigger(_action: dict[str, Any]) -> str:
    return "wait_for_trigger(...)"


def _action_condition(action: dict[str, Any]) -> str:
    return f"condition: {_compact_condition(action)}"


def _action_choose(action: dict[str, Any]) -> str:
    choices = action.get("choose", [])
    return f"choose([{len(choices)} options])"


def _action_repeat(_action: dict[str, Any]) -> str:
    return "repeat(...)"


def _action_if(_action: dict[str, Any]) -> str:
    return "if-then-else(...)"


def _action_parallel(action: dict[str, Any]) -> str:
    return f"parallel([{len(action.get('parallel', []))} actions])"


def _action_scene(action: dict[str, Any]) -> str:
    return f"scene({action['scene']})"


def _action_event(action: dict[str, Any]) -> str:
    return f"fire_event({action['event']})"


def _action_variables(action: dict[str, Any]) -> str:
    return f"variables({list(action['variables'].keys())})"


def _action_stop(action: dict[str, Any]) -> str:
    return f"stop({action.get('stop', '')})"


_ACTION_HANDLERS = [
    ("service", _action_service),
    ("delay", _action_delay),
    ("wait_template", _action_wait_template),
    ("wait_for_trigger", _action_wait_for_trigger),
    ("condition", _action_condition),
    ("choose", _action_choose),
    ("repeat", _action_repeat),
    ("if", _action_if),
    ("parallel", _action_parallel),
    ("scene", _action_scene),
    ("event", _action_event),
    ("variables", _action_variables),
    ("stop", _action_stop),
]


def _compact_action(action: dict[str, Any]) -> str:
    """Compact a single action."""
    for key, handler in _ACTION_HANDLERS:
        if key in action:
            return handler(action)
    # Unknown action type
    keys = list(action.keys())
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
            sample = ", ".join(available_entities[:30])
            entities_text = (
                f"\nKnown entities ({len(available_entities)} total): {sample}..."
            )
        else:
            entities_text = f"\nKnown entities: {', '.join(available_entities)}"

    return (
        f"Analyze {len(automations)} HA automations. Find issues and conflicts.\n"
        f"{entities_text}\n\n"
        f"{automations_text}\n"
        "Respond with JSON only:\n"
        '{"automations":[{"id":"...","alias":"...","status":"ok|warning|error",'
        '"issues":[],"summary":"..."}],\n'
        '"conflicts":[{"type":"shared_trigger|state_conflict|resource_contention|'
        'timing_race","severity":"info|warning|critical","automation_ids":[],'
        '"automation_names":[],"description":"...","affected_entities":[],'
        '"recommendation":"..."}],\n'
        '"overall_summary":"..."}\n\n'
        "IMPORTANT: Blueprint automations (marked with BLUEPRINT:) are VALID. "
        "Their triggers/actions are defined in the blueprint file, not shown "
        "here. Do NOT flag them as empty or missing triggers/actions.\n\n"
        "Check: invalid entities, logic problems, shared triggers, opposing "
        "actions on same entity. Only real issues."
    )


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
        summaries_text += (
            f"- {summary.get('automation_alias', 'Unknown')} [{status}]\n"
        )
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
            conflicts_text += (
                f"{', '.join(conflict.get('automation_names', []))}\n"
            )
            conflicts_text += f"  Description: {conflict.get('description', '')}\n"
            affected_entities = ", ".join(
                conflict.get("affected_entities", [])
            )
            conflicts_text += f"  Affected entities: {affected_entities}\n"
            conflicts_text += f"  Severity: {conflict.get('severity', 'unknown')}\n\n"
    else:
        conflicts_text = "No conflicts detected between automations.\n"

    return (
        "You are analyzing a batch diagnosis of Home Assistant automations. "
        "Provide a concise overall summary.\n\n"
        "## Statistics\n"
        f"- Total automations analyzed: {total_automations}\n"
        f"- Automations with issues: {automations_with_errors}\n"
        f"- Conflicts detected: {len(conflicts)}\n\n"
        "## Per-Automation Status\n"
        f"{summaries_text}\n"
        "## Conflicts Between Automations\n"
        f"{conflicts_text}\n"
        "## Your Task\n"
        "Provide a brief overall summary (2-4 sentences) that:\n"
        "1. States the overall health of the automation system\n"
        "2. Highlights the most critical issues if any\n"
        "3. Mentions any important conflicts that need attention\n\n"
        "Keep your response concise and actionable. Do not repeat the details "
        "above - synthesize them into useful insights."
    )


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
        automations_text += (
            f"### {auto.get('alias', 'Unnamed')}\n```yaml\n{auto_yaml}```\n\n"
        )

    # Format detected conflicts
    conflicts_text = ""
    for conflict in detected_conflicts:
        conflicts_text += f"- **{conflict.get('conflict_type', 'unknown').upper()}**\n"
        conflicts_text += (
            f"  Automations: {', '.join(conflict.get('automation_names', []))}\n"
        )
        conflicts_text += f"  Description: {conflict.get('description', '')}\n"
        affected_entities = ", ".join(
            conflict.get("affected_entities", [])
        )
        conflicts_text += f"  Affected entities: {affected_entities}\n\n"

    return (
        "You are a Home Assistant automation expert analyzing potential "
        "conflicts between automations.\n\n"
        "## Automations Involved\n"
        f"{automations_text}\n"
        "## Pre-Detected Conflicts\n"
        f"{conflicts_text}\n"
        "## Your Task\n"
        "Analyze these conflicts and provide:\n"
        "1. Whether each conflict is a real problem or a false positive\n"
        "2. The potential consequences if not addressed\n"
        "3. Specific recommendations to resolve each conflict\n\n"
        "Be concise and practical in your recommendations."
    )


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
    return (
        "Extract a brief summary from this automation diagnosis.\n\n"
        f"## Automation: {automation_alias}\n\n"
        "## Full Analysis\n"
        f"{analysis}\n\n"
        "## Your Task\n"
        "Provide a JSON response with:\n"
        '1. "brief_summary": One sentence describing the automation\'s status\n'
        '2. "error_count": Number of errors/issues found (integer)\n'
        '3. "warning_count": Number of warnings/recommendations (integer)\n'
        '4. "has_errors": true if there are any errors, false otherwise\n\n'
        "Respond with only valid JSON, no other text."
    )

"""Prompt templates for Home Assistant automation generation."""

from typing import Any

from toon_format import encode


def format_entities(states: list[dict[str, Any]]) -> str:
    """Format entity states for the prompt."""
    if not states:
        return "No entities available."

    lines = []
    # Group by domain
    domains: dict[str, list[dict[str, Any]]] = {}
    for state in states:
        entity_id = state.get("entity_id", "")
        domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
        if domain not in domains:
            domains[domain] = []
        domains[domain].append(state)

    for domain in sorted(domains.keys()):
        lines.append(f"\n## {domain.upper()} entities:")
        for entity in domains[domain][:50]:  # Limit per domain to avoid token explosion
            entity_id = entity.get("entity_id", "")
            friendly_name = entity.get("attributes", {}).get("friendly_name", entity_id)
            state_value = entity.get("state", "unknown")
            lines.append(f"- {entity_id} ({friendly_name}): {state_value}")

    return "\n".join(lines)


def format_services(services: list[dict[str, Any]]) -> str:
    """Format available services for the prompt."""
    if not services:
        return "No services available."

    lines = []
    for domain_data in services:
        domain = domain_data.get("domain", "unknown")
        domain_services = domain_data.get("services", {})
        if domain_services:
            lines.append(f"\n## {domain}:")
            for service_name, service_info in list(domain_services.items())[:20]:
                description = service_info.get("description", "No description")
                lines.append(f"- {domain}.{service_name}: {description}")

    return "\n".join(lines)


def format_areas(areas: list[dict[str, Any]]) -> str:
    """Format area registry for the prompt."""
    if not areas:
        return "No areas defined."

    lines = []
    for area in areas:
        name = area.get("name", "Unknown")
        area_id = area.get("area_id", "")
        lines.append(f"- {name} (id: {area_id})")

    return "\n".join(lines)


def format_devices(
    devices: list[dict[str, Any]], areas: list[dict[str, Any]]
) -> str:
    """Format device registry for the prompt."""
    if not devices:
        return "No devices registered."

    # Create area lookup
    area_lookup = {a.get("area_id"): a.get("name") for a in areas}

    lines = []
    for device in devices[:100]:  # Limit devices
        name = device.get("name_by_user") or device.get("name", "Unknown")
        manufacturer = device.get("manufacturer", "")
        model = device.get("model", "")
        area_id = device.get("area_id")
        area_name = area_lookup.get(area_id, "No area")

        device_info = f"- {name}"
        if manufacturer or model:
            device_info += f" ({manufacturer} {model})".strip()
        device_info += f" - Area: {area_name}"
        lines.append(device_info)

    return "\n".join(lines)


def build_toon_context(context: dict[str, Any]) -> str:
    """Build a compact TOON-encoded context payload."""
    states = context.get("states", [])
    services = context.get("services", [])
    areas = context.get("areas", [])
    devices = context.get("devices", [])

    compact_areas = [
        {
            "area_id": area.get("area_id", ""),
            "name": area.get("name", "Unknown"),
        }
        for area in areas
    ]

    area_lookup = {a.get("area_id"): a.get("name", "") for a in areas}
    compact_devices = []
    for device in devices[:100]:
        name = device.get("name_by_user") or device.get("name", "Unknown")
        compact_devices.append(
            {
                "name": name,
                "manufacturer": device.get("manufacturer", ""),
                "model": device.get("model", ""),
                "area": area_lookup.get(device.get("area_id"), ""),
            }
        )

    domain_entities: dict[str, list[dict[str, Any]]] = {}
    for state in states:
        entity_id = state.get("entity_id")
        if not entity_id:
            continue
        domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
        domain_list = domain_entities.setdefault(domain, [])
        if len(domain_list) >= 50:
            continue
        domain_list.append(
            {
                "entity_id": entity_id,
                "name": state.get("attributes", {}).get("friendly_name", entity_id),
                "state": state.get("state", "unknown"),
                "domain": domain,
            }
        )

    compact_entities: list[dict[str, Any]] = []
    for domain in sorted(domain_entities.keys()):
        compact_entities.extend(domain_entities[domain])

    compact_services = []
    for domain_data in services:
        domain = domain_data.get("domain", "unknown")
        domain_services = domain_data.get("services", {})
        if not domain_services:
            continue
        for service_name, service_info in list(domain_services.items())[:20]:
            compact_services.append(
                {
                    "domain": domain,
                    "service": service_name,
                    "description": service_info.get("description", "No description"),
                }
            )

    payload = {
        "areas": compact_areas,
        "devices": compact_devices,
        "entities": compact_entities,
        "services": compact_services,
    }

    return encode(payload)


def build_system_prompt(context: dict[str, Any]) -> str:
    """Build the system prompt with Home Assistant context."""
    toon_context = build_toon_context(context)

    return f"""You are a Home Assistant automation expert. Your task is to generate valid Home Assistant automation YAML based on user requests.

## Your Capabilities
- Create automations with triggers, conditions, and actions
- Use the available entities, services, areas, and devices in this Home Assistant instance
- Generate syntactically correct YAML that can be directly copied into Home Assistant

## Available Context (TOON format)
The following data is encoded in TOON (a compact JSON-like format). Decode it to access areas, devices, entities, and services.
```toon
{toon_context}
```

## Output Format
Always respond with:
1. A brief explanation of what the automation does
2. The complete automation YAML in a code block
3. Any notes or suggestions for the user

## YAML Requirements
- Use proper indentation (2 spaces)
- Include an `alias` field with a descriptive name
- Include a `description` field
- Use appropriate trigger types (state, time, event, etc.)
- Include conditions when relevant
- Use the correct service calls and entity IDs from the available list

## Example Automation
```yaml
alias: "Turn on lights at sunset"
description: "Automatically turn on living room lights when the sun sets"
trigger:
  - platform: sun
    event: sunset
condition:
  - condition: state
    entity_id: binary_sensor.someone_home
    state: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
    data:
      brightness_pct: 80
mode: single
```

Remember to only use entities and services that exist in this Home Assistant instance."""


def build_user_prompt(user_request: str) -> str:
    """Build the user prompt from the request."""
    return f"""Please create a Home Assistant automation for the following request:

{user_request}

Provide a complete, ready-to-use automation YAML that I can copy directly into my Home Assistant configuration."""


def build_modify_user_prompt(existing_yaml: str, modification_request: str) -> str:
    """Build the user prompt for modifying an existing automation."""
    return f"""I have an existing Home Assistant automation that I want to modify. Please update it according to my request while preserving its core functionality, ID, and alias (unless I specifically ask to change them).

## Current Automation YAML:
```yaml
{existing_yaml}
```

## Modification Request:
{modification_request}

Please provide:
1. A brief explanation of what changes you made
2. The complete updated automation YAML in a code block (not just the changes, but the full automation)
3. Any notes about the modifications

IMPORTANT: Keep the same automation ID and preserve the general structure unless the modification specifically requires changing it."""

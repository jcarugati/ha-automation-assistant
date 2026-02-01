# Home Assistant trace.saved_traces schema (observed)

Source: `.examples/traces` (downloaded from Home Assistant `.storage/trace.saved_traces`).

This describes the observed shape of the stored traces so we can parse them reliably. It is based on the example file and may not include every field Home Assistant can emit.

## Top-level document

```json
{
  "version": 1,
  "minor_version": 1,
  "key": "trace.saved_traces",
  "data": {
    "automation.<item_id>": [TraceEntry, ...],
    "script.<item_id>": [TraceEntry, ...]
  }
}
```

Notes:
- `data` is a map of `entity_id` -> list of trace entries.
- `entity_id` suffix matches `item_id` inside the trace payload.

## TraceEntry

Each entry contains both a short and an extended payload:

```json
{
  "extended_dict": TracePayload,
  "short_dict": TracePayloadShort
}
```

Observed: entries only contain these two keys.

### TracePayloadShort

Subset of the extended payload. Observed keys:

```json
{
  "domain": "automation" | "script",
  "item_id": "<string>",
  "run_id": "<string>",
  "state": "<string>",
  "script_execution": "<string>",
  "last_step": "<string>",
  "trigger": "<string>" | null,
  "timestamp": { "start": "<iso>", "finish": "<iso>" },
  "error": "<string>" | null
}
```

### TracePayload (extended)

Superset of `TracePayloadShort`:

```json
{
  "domain": "automation" | "script",
  "item_id": "<string>",
  "run_id": "<string>",
  "state": "<string>",
  "script_execution": "<string>",
  "last_step": "<string>",
  "trigger": "<string>" | null,
  "timestamp": { "start": "<iso>", "finish": "<iso>" },
  "error": "<string>" | null,
  "context": { "id": "<string>", "parent_id": "<string>" | null, "user_id": "<string>" | null },
  "trace": { "<path>": [TraceStep, ...] },
  "config": AutomationConfig | ScriptConfig,
  "blueprint_inputs": BlueprintInputs | null
}
```

Notes:
- For scripts in this sample, `trigger` is always null.
- `error` is usually null, but may be a string when failures occur.
- `blueprint_inputs` appears for scripts in this sample; automations show null.

## TraceStep

Each trace step is one event in a path list inside `trace`:

```json
{
  "path": "<path>",
  "timestamp": "<iso>",
  "changed_variables": { "<var>": <value>, ... },
  "result": { "<key>": <value>, ... },
  "child_id": "<string>",
  "error": "<string>"
}
```

Notes:
- `changed_variables`, `result`, `child_id`, and `error` are optional.
- `changed_variables` is highly dynamic and depends on the automation/script variables.
- `result` is also dynamic; commonly includes `result` (bool), `entities` (list), and action-specific details (delay, wait, etc).

### Trace path structure

Observed path prefixes (not exhaustive):
- `trigger/<index>`
- `condition/<index>`
- `action/<index>`
- `sequence/<index>`

Paths can be nested (examples):
- `action/0/choose/0/conditions/0`
- `action/0/choose/0/sequence/0`
- `action/0/choose/0/sequence/0/choose/0/conditions/0`

## Config shapes

### AutomationConfig (observed)

```json
{
  "id": "<string>",
  "alias": "<string>",
  "description": "<string>",
  "mode": "single" | "restart" | "queued" | "parallel",
  "variables": { "<name>": <value>, ... },
  "triggers": [Trigger, ...],
  "conditions": [Condition, ...],
  "actions": [Action, ...]
}
```

Additional optional keys observed in some automations:
- `trigger`
- `condition`
- `action`

### ScriptConfig (observed)

```json
{
  "alias": "<string>",
  "description": "<string>",
  "sequence": [Action, ...],
  "fields": { "<field>": <field_def>, ... },
  "icon": "<string>"
}
```

### BlueprintInputs (observed)

```json
{
  "id": "<string>",
  "alias": "<string>",
  "description": "<string>",
  "use_blueprint": { "path": "<string>", "input": { "<key>": <value>, ... } }
}
```

## Trigger/Condition/Action (observed keys)

These structures vary per automation/script. The sample file includes keys such as:

- Trigger: `platform`, `entity_id`, `to`, `from`, `for`, `event`, `device_id`, `zone`, `type`, `offset`, `minutes`, `hours`, `webhook_id`, `allowed_methods`, `local_only`, `attribute`, `options`, `trigger`, `target`, `domain`
- Condition: `condition`, `entity_id`, `state`, `before`, `after`, `below`, `value_template`, `device_id`, `target`, `options`, `domain`, `conditions`, `type`
- Action: `action`, `domain`, `service`, `entity_id`, `target`, `data`, `choose`, `then`, `else`, `delay`, `wait_for_trigger`, `timeout`, `continue_on_timeout`, `repeat`, `enabled`, `if`, `metadata`, `type`, `device_id`

These lists are not exhaustive and should be treated as hints for parsing.

## Parsing notes

- `short_dict` and `extended_dict` can be present together; parse `extended_dict` when available and fall back to `short_dict`.
- Some Home Assistant builds store these payloads as JSON strings; be prepared to `json.loads` when needed.
- Use `domain` + `item_id` (or the `entity_id` map key) to relate a trace to its automation or script.
- Timestamps are ISO 8601 strings with timezone (UTC in the sample).

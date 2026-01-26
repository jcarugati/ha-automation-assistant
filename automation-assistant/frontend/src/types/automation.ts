export interface Automation {
  id: string
  alias: string
  description?: string
  mode?: string
  area_id?: string
  area_name?: string
  state?: 'on' | 'off' | string
}

export interface Trigger {
  platform?: string
  description?: string
  entity_id?: string
}

export interface TracesMeta {
  status?: 'missing_file' | 'empty_file' | 'invalid_json' | 'ok'
  path?: string
  count?: number
}

export interface ExecutionTrace {
  run_id?: string
  timestamp_start?: string
  timestamp_finish?: string
  state?: string
  script_execution?: string
  trigger?: Trigger | string
  error?: string | { message?: string; error?: string }
}

export interface AutomationDetails {
  automation: Automation
  yaml: string
  traces: ExecutionTrace[]
  traces_meta: TracesMeta
}

export interface HAAutomationList {
  automations: Automation[]
  count: number
}

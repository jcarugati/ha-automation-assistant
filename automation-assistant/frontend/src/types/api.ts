// Generation
export interface GenerateRequest {
  prompt: string
}

export interface ModifyRequest {
  prompt: string
  existing_yaml: string
}

export interface GenerateResponse {
  success: boolean
  response: string
  yaml_content?: string
  error?: string
}

// Validation
export interface ValidationRequest {
  yaml_content: string
}

export interface ValidationResponse {
  valid: boolean
  errors: string[]
}

// Deploy
export interface DeployRequest {
  yaml_content: string
  automation_id?: string
}

export interface DeployResponse {
  success: boolean
  automation_id: string
  message: string
  is_new: boolean
}

// Diagnosis
export interface DiagnoseRequest {
  automation_id: string
}

export interface DiagnosisResponse {
  automation_id: string
  automation_alias: string
  automation_yaml: string
  traces_summary: Record<string, unknown>[]
  analysis: string
  success: boolean
  error?: string
}

// Batch diagnosis
export interface BatchReportSummary {
  run_id: string
  run_at: string
  scheduled: boolean
  total_automations: number
  automations_with_errors: number
  conflicts_found: number
  insights_added: number
}

export interface BatchDiagnosisReport extends BatchReportSummary {
  automations_analyzed: number
  automation_summaries: AutomationDiagnosisSummary[]
  conflicts: AutomationConflict[]
  overall_summary: string
  full_analyses: DiagnosisResponse[]
}

export interface AutomationDiagnosisSummary {
  automation_id: string
  automation_alias: string
  has_errors: boolean
  error_count: number
  warning_count: number
  brief_summary: string
}

export interface AutomationConflict {
  conflict_type: string
  severity: string
  automation_ids: string[]
  automation_names: string[]
  description: string
  affected_entities: string[]
}

// Schedule
export interface ScheduleConfig {
  enabled: boolean
  time: string
  next_run?: string
}

export interface ScheduleUpdateRequest {
  time?: string
  enabled?: boolean
}

// Version
export interface VersionResponse {
  version: string
}

// Insight actions
export interface InsightFixResponse {
  insight_id: string
  automation_ids: string[]
  automation_names: string[]
  issue: string
  fix_suggestion: string
}

export interface ApplyFixRequest {
  yaml_content: string
}

export interface ApplyFixResponse {
  success: boolean
  automation_ids: string[]
  message: string
  errors: string[]
}

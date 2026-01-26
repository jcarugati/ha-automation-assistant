export type InsightSeverity = 'info' | 'warning' | 'critical'

export type InsightCategory = 'single' | 'multi'

export type InsightType = 'error' | 'warning' | 'conflict' | 'best_practice'

export interface Insight {
  insight_id: string
  category: InsightCategory
  insight_type: InsightType
  severity: InsightSeverity
  title: string
  description: string
  automation_ids: string[]
  automation_names: string[]
  affected_entities: string[]
  recommendation: string
  first_seen: string
  last_seen: string
  resolved: boolean
}

export interface InsightsList {
  single_automation: Insight[]
  multi_automation: Insight[]
  total_count: number
  unresolved_count: number
}

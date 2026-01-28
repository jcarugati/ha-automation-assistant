import { apiGet, apiPost, apiPut, apiDelete } from './client'
import type {
  InsightsList,
  DiagnoseRequest,
  DiagnosisResponse,
  BatchDiagnosisReport,
  BatchReportSummary,
  ScheduleConfig,
  ScheduleUpdateRequest,
  InsightFixResponse,
  ApplyFixRequest,
  ApplyFixResponse,
} from '@/types'

// Insights
export async function getInsights(): Promise<InsightsList> {
  return apiGet<InsightsList>('/doctor/insights')
}

export async function resolveInsight(
  insightId: string,
  resolved: boolean
): Promise<{ success: boolean; insight_id: string; resolved: boolean }> {
  return apiPut(`/doctor/insights/${encodeURIComponent(insightId)}/resolve`, undefined, {
    params: { resolved: String(resolved) },
  })
}

export async function deleteInsight(
  insightId: string
): Promise<{ success: boolean; insight_id: string }> {
  return apiDelete(`/doctor/insights/${encodeURIComponent(insightId)}`)
}

export async function getInsightFix(insightId: string): Promise<InsightFixResponse> {
  return apiPost<InsightFixResponse>(`/doctor/insights/${encodeURIComponent(insightId)}/fix`)
}

export async function applyInsightFix(
  insightId: string,
  request: ApplyFixRequest
): Promise<ApplyFixResponse> {
  return apiPost<ApplyFixResponse>(
    `/doctor/insights/${encodeURIComponent(insightId)}/apply`,
    request
  )
}

// Single diagnosis
export async function diagnoseAutomation(request: DiagnoseRequest): Promise<DiagnosisResponse> {
  return apiPost<DiagnosisResponse>('/doctor/diagnose', request)
}

// Batch diagnosis
export async function runBatchDiagnosis(): Promise<BatchDiagnosisReport> {
  return apiPost<BatchDiagnosisReport>('/doctor/run-batch')
}

export async function cancelBatchDiagnosis(): Promise<{ success: boolean; message: string }> {
  return apiPost('/doctor/cancel')
}

export async function getDiagnosisStatus(): Promise<{ is_running: boolean }> {
  return apiGet('/doctor/status')
}

// Reports
export async function listDiagnosisReports(): Promise<{
  reports: BatchReportSummary[]
  count: number
}> {
  return apiGet('/doctor/reports')
}

export async function getLatestReport(): Promise<BatchDiagnosisReport> {
  return apiGet('/doctor/reports/latest')
}

export async function getReport(runId: string): Promise<BatchDiagnosisReport> {
  return apiGet(`/doctor/reports/${encodeURIComponent(runId)}`)
}

// Schedule
export async function getSchedule(): Promise<ScheduleConfig> {
  return apiGet<ScheduleConfig>('/doctor/schedule')
}

export async function updateSchedule(request: ScheduleUpdateRequest): Promise<ScheduleConfig> {
  return apiPut<ScheduleConfig>('/doctor/schedule', request)
}

import { apiGet, apiPost } from './client'
import type {
  HAAutomationList,
  AutomationDetails,
  GenerateRequest,
  GenerateResponse,
  ModifyRequest,
  ValidationRequest,
  ValidationResponse,
  DeployRequest,
  DeployResponse,
  VersionResponse,
} from '@/types'

export async function getVersion(): Promise<VersionResponse> {
  return apiGet<VersionResponse>('/version')
}

export async function listHAAutomations(): Promise<HAAutomationList> {
  return apiGet<HAAutomationList>('/ha-automations')
}

export async function getHAAutomation(id: string): Promise<AutomationDetails> {
  return apiGet<AutomationDetails>(`/ha-automations/${encodeURIComponent(id)}`)
}

export async function generateAutomation(request: GenerateRequest): Promise<GenerateResponse> {
  return apiPost<GenerateResponse, GenerateRequest>('/generate', request)
}

export async function modifyAutomation(request: ModifyRequest): Promise<GenerateResponse> {
  return apiPost<GenerateResponse, ModifyRequest>('/modify', request)
}

export async function validateYaml(request: ValidationRequest): Promise<ValidationResponse> {
  return apiPost<ValidationResponse, ValidationRequest>('/validate', request)
}

export async function deployAutomation(request: DeployRequest): Promise<DeployResponse> {
  return apiPost<DeployResponse, DeployRequest>('/deploy', request)
}

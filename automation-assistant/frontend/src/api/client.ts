const API_BASE = '/api'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

interface FetchOptions extends RequestInit {
  params?: Record<string, string>
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail: string | undefined
    try {
      const data = await response.json() as { detail?: string; error?: string }
      detail = data.detail ?? data.error
    } catch {
      // Response body not JSON
    }
    throw new ApiError(
      response.status,
      `HTTP ${response.status}`,
      detail
    )
  }
  return response.json() as Promise<T>
}

export async function apiGet<T>(endpoint: string, options?: FetchOptions): Promise<T> {
  let url = `${API_BASE}${endpoint}`
  if (options?.params) {
    const searchParams = new URLSearchParams(options.params)
    url += `?${searchParams.toString()}`
  }
  const response = await fetch(url, {
    method: 'GET',
    ...options,
  })
  return handleResponse<T>(response)
}

export async function apiPost<T, B = unknown>(
  endpoint: string,
  body?: B,
  options?: FetchOptions
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    body: body ? JSON.stringify(body) : undefined,
    ...options,
  })
  return handleResponse<T>(response)
}

export async function apiPut<T, B = unknown>(
  endpoint: string,
  body?: B,
  options?: FetchOptions
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    body: body ? JSON.stringify(body) : undefined,
    ...options,
  })
  return handleResponse<T>(response)
}

export async function apiDelete<T>(endpoint: string, options?: FetchOptions): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'DELETE',
    ...options,
  })
  return handleResponse<T>(response)
}

import { useState, useEffect, useCallback } from 'react'
import type { ScheduleConfig } from '@/types'
import { getSchedule, updateSchedule as apiUpdateSchedule } from '@/api'

interface UseScheduleReturn {
  schedule: ScheduleConfig | null
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
  updateSchedule: (request: {
    enabled?: boolean
    time?: string
    frequency?: ScheduleConfig['frequency']
    day_of_week?: string
    day_of_month?: number
  }) => Promise<void>
}

export function useSchedule(): UseScheduleReturn {
  const [schedule, setSchedule] = useState<ScheduleConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getSchedule()
      setSchedule(data)
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to load schedule'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  const updateSchedule = useCallback(
    async (request: {
      enabled?: boolean
      time?: string
      frequency?: ScheduleConfig['frequency']
      day_of_week?: string
      day_of_month?: number
    }) => {
      try {
        const data = await apiUpdateSchedule(request)
        setSchedule(data)
      } catch (e) {
        console.error('Failed to update schedule:', e)
        throw e
      }
    },
    []
  )

  useEffect(() => {
    void refresh()
  }, [refresh])

  return {
    schedule,
    loading,
    error,
    refresh,
    updateSchedule,
  }
}

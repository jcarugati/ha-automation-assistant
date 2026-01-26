import { useState, useEffect, useCallback } from 'react'
import type { Automation, AutomationDetails } from '@/types'
import { listHAAutomations, getHAAutomation } from '@/api'

interface UseAutomationsReturn {
  automations: Automation[]
  loading: boolean
  error: string | null
  current: AutomationDetails | null
  currentLoading: boolean
  refresh: () => Promise<void>
  selectAutomation: (id: string) => Promise<void>
  clearCurrent: () => void
}

export function useAutomations(): UseAutomationsReturn {
  const [automations, setAutomations] = useState<Automation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [current, setCurrent] = useState<AutomationDetails | null>(null)
  const [currentLoading, setCurrentLoading] = useState(false)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listHAAutomations()
      setAutomations(data.automations)
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to load automations'
      setError(message)
      setAutomations([])
    } finally {
      setLoading(false)
    }
  }, [])

  const selectAutomation = useCallback(async (id: string) => {
    setCurrentLoading(true)
    try {
      const details = await getHAAutomation(id)
      setCurrent(details)
    } catch (e) {
      console.error('Failed to load automation details:', e)
      setCurrent(null)
    } finally {
      setCurrentLoading(false)
    }
  }, [])

  const clearCurrent = useCallback(() => {
    setCurrent(null)
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return {
    automations,
    loading,
    error,
    current,
    currentLoading,
    refresh,
    selectAutomation,
    clearCurrent,
  }
}

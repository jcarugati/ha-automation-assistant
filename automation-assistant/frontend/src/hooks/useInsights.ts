import { useState, useEffect, useCallback } from 'react'
import type { Insight, InsightsList, InsightSeverity } from '@/types'
import { getInsights, resolveInsight as apiResolveInsight } from '@/api'

interface UseInsightsReturn {
  insights: InsightsList
  loading: boolean
  error: string | null
  unresolvedCount: number
  automationIdsWithIssues: Set<string>
  getIssuesForAutomation: (id: string) => Insight[]
  refresh: () => Promise<void>
  resolveInsight: (insightId: string, resolved: boolean) => Promise<void>
  getSeverityForAutomation: (id: string) => InsightSeverity | null
}

const emptyInsights: InsightsList = {
  single_automation: [],
  multi_automation: [],
  total_count: 0,
  unresolved_count: 0,
}

export function useInsights(): UseInsightsReturn {
  const [insights, setInsights] = useState<InsightsList>(emptyInsights)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getInsights()
      setInsights(data)
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to load insights'
      setError(message)
      setInsights(emptyInsights)
    } finally {
      setLoading(false)
    }
  }, [])

  const resolveInsight = useCallback(
    async (insightId: string, resolved: boolean) => {
      try {
        await apiResolveInsight(insightId, resolved)
        await refresh()
      } catch (e) {
        console.error('Failed to resolve insight:', e)
      }
    },
    [refresh]
  )

  const automationIdsWithIssues = (() => {
    const ids = new Set<string>()
    const allInsights = [...insights.single_automation, ...insights.multi_automation]
    for (const insight of allInsights) {
      if (!insight.resolved) {
        for (const id of insight.automation_ids) {
          ids.add(id)
        }
      }
    }
    return ids
  })()

  const getIssuesForAutomation = useCallback(
    (id: string): Insight[] => {
      const allInsights = [...insights.single_automation, ...insights.multi_automation]
      return allInsights.filter((i) => i.automation_ids.includes(id) && !i.resolved)
    },
    [insights]
  )

  const getSeverityForAutomation = useCallback(
    (id: string): InsightSeverity | null => {
      const issues = getIssuesForAutomation(id)
      if (issues.length === 0) return null
      if (issues.some((i) => i.severity === 'critical')) return 'critical'
      if (issues.some((i) => i.severity === 'warning')) return 'warning'
      return 'info'
    },
    [getIssuesForAutomation]
  )

  useEffect(() => {
    void refresh()
  }, [refresh])

  return {
    insights,
    loading,
    error,
    unresolvedCount: insights.unresolved_count,
    automationIdsWithIssues,
    getIssuesForAutomation,
    refresh,
    resolveInsight,
    getSeverityForAutomation,
  }
}

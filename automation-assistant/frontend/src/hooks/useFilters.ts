import { useState, useMemo, useCallback } from 'react'
import type { Automation } from '@/types'

export type FilterType = 'all' | 'issues' | 'disabled'
export type GroupByType = 'area' | 'state' | 'alpha' | 'none'

interface UseFiltersReturn {
  searchQuery: string
  setSearchQuery: (query: string) => void
  filter: FilterType
  setFilter: (filter: FilterType) => void
  groupBy: GroupByType
  setGroupBy: (groupBy: GroupByType) => void
  filterAutomations: (
    automations: Automation[],
    automationIdsWithIssues: Set<string>
  ) => Automation[]
  groupAutomations: (automations: Automation[]) => Record<string, Automation[]>
}

export function useFilters(): UseFiltersReturn {
  const [searchQuery, setSearchQuery] = useState('')
  const [filter, setFilter] = useState<FilterType>('all')
  const [groupBy, setGroupBy] = useState<GroupByType>('area')

  const filterAutomations = useCallback(
    (automations: Automation[], automationIdsWithIssues: Set<string>): Automation[] => {
      let filtered = automations

      // Search filter
      if (searchQuery) {
        const q = searchQuery.toLowerCase()
        filtered = filtered.filter(
          (a) =>
            a.alias.toLowerCase().includes(q) || a.id.toLowerCase().includes(q)
        )
      }

      // Status filter
      if (filter === 'issues') {
        filtered = filtered.filter((a) => automationIdsWithIssues.has(a.id))
      } else if (filter === 'disabled') {
        filtered = filtered.filter((a) => a.state === 'off')
      }

      return filtered
    },
    [searchQuery, filter]
  )

  const groupAutomations = useCallback(
    (automations: Automation[]): Record<string, Automation[]> => {
      const groups: Record<string, Automation[]> = {}

      if (groupBy === 'none') {
        groups['All Automations'] = automations
        return groups
      }

      for (const auto of automations) {
        let key: string
        if (groupBy === 'area') {
          key = auto.area_name ?? 'No Area'
        } else if (groupBy === 'state') {
          key =
            auto.state === 'on'
              ? 'Enabled'
              : auto.state === 'off'
                ? 'Disabled'
                : 'Unknown'
        } else {
          // alpha
          key = auto.alias[0]?.toUpperCase() ?? '#'
        }

        const existing = groups[key]
        if (existing) {
          existing.push(auto)
        } else {
          groups[key] = [auto]
        }
      }

      // Sort groups alphabetically and sort items within each group
      const sorted: Record<string, Automation[]> = {}
      for (const key of Object.keys(groups).sort()) {
        const items = groups[key]
        if (items) {
          sorted[key] = items.sort((a, b) => a.alias.localeCompare(b.alias))
        }
      }

      return sorted
    },
    [groupBy]
  )

  return useMemo(
    () => ({
      searchQuery,
      setSearchQuery,
      filter,
      setFilter,
      groupBy,
      setGroupBy,
      filterAutomations,
      groupAutomations,
    }),
    [searchQuery, filter, groupBy, filterAutomations, groupAutomations]
  )
}

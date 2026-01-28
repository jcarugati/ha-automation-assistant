import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { AutomationItem } from './AutomationItem'
import type { Automation, InsightSeverity } from '@/types'

interface AutomationListProps {
  groups: Record<string, Automation[]>
  selectedId: string | null
  onSelect: (id: string) => void
  getSeverity: (id: string) => InsightSeverity | null
}

export function AutomationList({ groups, selectedId, onSelect, getSeverity }: AutomationListProps) {
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set())

  const toggleGroup = (groupName: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev)
      if (next.has(groupName)) {
        next.delete(groupName)
      } else {
        next.add(groupName)
      }
      return next
    })
  }

  const groupNames = Object.keys(groups)

  if (groupNames.length === 0) {
    return <div className="p-4 text-center text-sm text-muted-foreground">No automations found</div>
  }

  return (
    <div className="space-y-1">
      {groupNames.map((groupName) => {
        const items = groups[groupName] ?? []
        const isCollapsed = collapsedGroups.has(groupName)

        return (
          <div key={groupName}>
            <button
              onClick={() => {
                toggleGroup(groupName)
              }}
              className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider hover:text-foreground"
            >
              <span className="flex items-center gap-2">
                <span>{groupName}</span>
                <span className="text-muted-foreground/60">({items.length})</span>
              </span>
              <ChevronDown
                className={cn('h-4 w-4 transition-transform', isCollapsed && '-rotate-90')}
              />
            </button>
            {!isCollapsed && (
              <div className="space-y-0.5 pb-2">
                {items.map((automation) => (
                  <AutomationItem
                    key={automation.id}
                    automation={automation}
                    isSelected={selectedId === automation.id}
                    severity={getSeverity(automation.id)}
                    onClick={() => {
                      onSelect(automation.id)
                    }}
                  />
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

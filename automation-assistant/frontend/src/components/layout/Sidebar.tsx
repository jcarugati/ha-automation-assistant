import { Home, Plus, Shield } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { SearchInput, FilterButtons, AutomationList } from '@/components/sidebar'
import type { Automation, InsightSeverity } from '@/types'
import type { FilterType, GroupByType } from '@/hooks/useFilters'

export type ViewType = 'welcome' | 'create' | 'insights' | 'detail'

interface SidebarProps {
  version: string
  currentView: ViewType
  onViewChange: (view: ViewType) => void
  automations: Automation[]
  automationsLoading: boolean
  selectedAutomationId: string | null
  onAutomationSelect: (id: string) => void
  searchQuery: string
  onSearchChange: (query: string) => void
  filter: FilterType
  onFilterChange: (filter: FilterType) => void
  groupBy: GroupByType
  onGroupByChange: (groupBy: GroupByType) => void
  groups: Record<string, Automation[]>
  getSeverity: (id: string) => InsightSeverity | null
  unresolvedInsightsCount: number
}

const navItems = [
  { view: 'welcome' as const, label: 'Overview', icon: Home },
  { view: 'create' as const, label: 'Create New', icon: Plus },
  { view: 'insights' as const, label: 'Insights', icon: Shield },
]

export function Sidebar({
  version,
  currentView,
  onViewChange,
  automationsLoading,
  selectedAutomationId,
  onAutomationSelect,
  searchQuery,
  onSearchChange,
  filter,
  onFilterChange,
  groupBy,
  onGroupByChange,
  groups,
  getSeverity,
  unresolvedInsightsCount,
}: SidebarProps) {
  return (
    <aside className="w-80 border-r border-border bg-card flex flex-col h-screen">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <h1 className="text-lg font-semibold">Automation Assistant</h1>
        <p className="text-xs text-muted-foreground">
          Home Assistant Automations {version && <span className="opacity-60">v{version}</span>}
        </p>
      </div>

      {/* Search */}
      <div className="p-4 pb-2">
        <SearchInput value={searchQuery} onChange={onSearchChange} />
      </div>

      {/* Group By Select */}
      <div className="px-4 pb-2">
        <Select
          value={groupBy}
          onValueChange={(v) => {
            onGroupByChange(v as GroupByType)
          }}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Group by..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="area">Group by Area</SelectItem>
            <SelectItem value="state">Group by Status</SelectItem>
            <SelectItem value="alpha">Alphabetical</SelectItem>
            <SelectItem value="none">No Grouping</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Filter Buttons */}
      <div className="px-4 pb-3">
        <FilterButtons filter={filter} onFilterChange={onFilterChange} />
      </div>

      <Separator />

      {/* Navigation */}
      <nav className="p-2">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = currentView === item.view
          return (
            <button
              key={item.view}
              onClick={() => {
                onViewChange(item.view)
              }}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent'
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
              {item.view === 'insights' && unresolvedInsightsCount > 0 && (
                <span className="ml-auto bg-destructive text-destructive-foreground text-xs px-2 py-0.5 rounded-full">
                  {unresolvedInsightsCount}
                </span>
              )}
            </button>
          )
        })}
      </nav>

      <Separator />

      {/* Automation List */}
      <ScrollArea className="flex-1">
        <div className="p-2">
          {automationsLoading ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <div className="h-6 w-6 border-2 border-border border-t-primary rounded-full animate-spin mb-2" />
              <span className="text-sm">Loading...</span>
            </div>
          ) : (
            <AutomationList
              groups={groups}
              selectedId={selectedAutomationId}
              onSelect={onAutomationSelect}
              getSeverity={getSeverity}
            />
          )}
        </div>
      </ScrollArea>
    </aside>
  )
}

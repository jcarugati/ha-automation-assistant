import { cn } from '@/lib/utils'
import type { FilterType } from '@/hooks/useFilters'

interface FilterButtonsProps {
  filter: FilterType
  onFilterChange: (filter: FilterType) => void
}

const filters: { value: FilterType; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'issues', label: 'Issues' },
  { value: 'disabled', label: 'Disabled' },
]

export function FilterButtons({ filter, onFilterChange }: FilterButtonsProps) {
  return (
    <div className="flex gap-1">
      {filters.map((f) => (
        <button
          key={f.value}
          onClick={() => onFilterChange(f.value)}
          className={cn(
            'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
            filter === f.value
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent'
          )}
        >
          {f.label}
        </button>
      ))}
    </div>
  )
}

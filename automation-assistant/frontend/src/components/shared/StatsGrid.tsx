import { cn } from '@/lib/utils'

interface StatCardProps {
  value: string | number
  label: string
  variant?: 'default' | 'issues'
}

function StatCard({ value, label, variant = 'default' }: StatCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-card p-4',
        variant === 'issues' && 'border-warning/30'
      )}
    >
      <div
        className={cn(
          'text-3xl font-bold mb-1',
          variant === 'issues' ? 'text-warning' : 'text-foreground'
        )}
      >
        {value}
      </div>
      <div className="text-sm text-muted-foreground">{label}</div>
    </div>
  )
}

interface StatsGridProps {
  total: number
  healthy: number
  withIssues: number
  disabled: number
}

export function StatsGrid({ total, healthy, withIssues, disabled }: StatsGridProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard value={total} label="Total Automations" />
      <StatCard value={healthy} label="Healthy" />
      <StatCard value={withIssues} label="With Issues" variant="issues" />
      <StatCard value={disabled} label="Disabled" />
    </div>
  )
}

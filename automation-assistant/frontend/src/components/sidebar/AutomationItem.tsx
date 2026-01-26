import { cn } from '@/lib/utils'
import type { Automation, InsightSeverity } from '@/types'

interface AutomationItemProps {
  automation: Automation
  isSelected: boolean
  severity: InsightSeverity | null
  onClick: () => void
}

function getStatusColor(automation: Automation, severity: InsightSeverity | null): string {
  if (automation.state === 'off') return 'bg-muted-foreground'
  if (automation.state !== 'on') return 'bg-warning'
  if (severity === 'critical') return 'bg-destructive'
  if (severity === 'warning') return 'bg-warning'
  return 'bg-success'
}

function getTooltip(automation: Automation, severity: InsightSeverity | null): string {
  const stateText = automation.state === 'on' ? 'Enabled' : automation.state === 'off' ? 'Disabled' : 'Unknown'
  let healthText = 'Healthy'
  if (automation.state === 'off') healthText = 'Disabled'
  else if (automation.state !== 'on') healthText = 'State unknown'
  else if (severity === 'critical') healthText = 'Critical issues'
  else if (severity === 'warning') healthText = 'Warnings detected'
  return `Health: ${healthText}. State: ${stateText}.`
}

export function AutomationItem({ automation, isSelected, severity, onClick }: AutomationItemProps) {
  const stateText = automation.state === 'on' ? 'Enabled' : automation.state === 'off' ? 'Disabled' : 'Unknown'

  return (
    <button
      onClick={onClick}
      title={getTooltip(automation, severity)}
      className={cn(
        'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors',
        isSelected
          ? 'bg-primary/10 text-primary'
          : 'hover:bg-accent text-foreground'
      )}
    >
      <div
        className={cn('w-2 h-2 rounded-full shrink-0', getStatusColor(automation, severity))}
        aria-label={getTooltip(automation, severity)}
      />
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium">{automation.alias}</div>
        <div className="truncate text-xs text-muted-foreground">{stateText}</div>
      </div>
    </button>
  )
}

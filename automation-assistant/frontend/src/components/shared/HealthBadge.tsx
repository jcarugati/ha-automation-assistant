import { Check, X, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Insight } from '@/types'

interface HealthBadgeProps {
  issues: Insight[]
}

export function HealthBadge({ issues }: HealthBadgeProps) {
  const hasCritical = issues.some((i) => i.severity === 'critical')
  const hasIssues = issues.length > 0

  return (
    <div className="rounded-lg border border-border bg-secondary p-4">
      <div className="flex items-center gap-3 mb-3">
        <div
          className={cn(
            'w-10 h-10 rounded-full flex items-center justify-center',
            hasCritical
              ? 'bg-destructive/10 text-destructive'
              : hasIssues
                ? 'bg-warning/10 text-warning'
                : 'bg-success/10 text-success'
          )}
        >
          {hasCritical ? (
            <X className="h-5 w-5" />
          ) : hasIssues ? (
            <AlertTriangle className="h-5 w-5" />
          ) : (
            <Check className="h-5 w-5" />
          )}
        </div>
        <div className="text-sm">
          {hasIssues
            ? `${issues.length} issue${issues.length > 1 ? 's' : ''} found`
            : 'No issues detected'}
        </div>
      </div>
      {hasIssues && (
        <div className="space-y-2">
          {issues.map((issue) => (
            <div
              key={issue.insight_id}
              className="text-sm text-muted-foreground flex items-start gap-2"
            >
              <span className="text-warning">•</span>
              <span>{issue.title}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

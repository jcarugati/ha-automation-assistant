import { useState } from 'react'
import { Check, X, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDuration, truncateText } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import type { ExecutionTrace, TracesMeta, Trigger } from '@/types'

interface ExecutionListProps {
  traces: ExecutionTrace[]
  tracesMeta?: TracesMeta
  loading?: boolean
}

function formatTrigger(trigger: Trigger | string | undefined): string {
  if (!trigger) return 'Trigger details unavailable'
  if (typeof trigger === 'string') return trigger
  const parts: string[] = []
  if (trigger.description) {
    parts.push(trigger.description)
  } else if (trigger.platform) {
    parts.push(trigger.platform)
  }
  if (trigger.entity_id) {
    parts.push(trigger.entity_id)
  }
  return parts.length ? parts.join(' • ') : 'Trigger details unavailable'
}

function formatError(error: ExecutionTrace['error']): string {
  if (!error) return ''
  if (typeof error === 'string') return truncateText(error, 140)
  if (typeof error === 'object') {
    const message = error.message ?? error.error ?? ''
    if (message) return truncateText(message, 140)
    try {
      return truncateText(JSON.stringify(error), 140)
    } catch {
      return ''
    }
  }
  return ''
}

function formatMetaMessage(meta: TracesMeta | undefined, totalCount: number, displayedCount: number): string {
  if (!meta || typeof meta !== 'object') return ''
  if (meta.status === 'missing_file') {
    return `Trace history file not found at ${meta.path ?? 'unknown path'}. For local runs, set HA_CONFIG_PATH or mount /config.`
  }
  if (meta.status === 'empty_file') {
    return 'Trace history file is empty.'
  }
  if (meta.status === 'invalid_json') {
    return 'Trace history file could not be parsed.'
  }
  const count = typeof meta.count === 'number' ? meta.count : totalCount
  if (displayedCount && count > displayedCount) {
    return `Showing ${displayedCount} of ${count} recent executions.`
  }
  if (count) {
    return `${count} recent execution${count === 1 ? '' : 's'}.`
  }
  return ''
}

export function ExecutionList({ traces, tracesMeta, loading }: ExecutionListProps) {
  const [displayLimit, setDisplayLimit] = useState(2)

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <div className="h-6 w-6 border-2 border-border border-t-primary rounded-full animate-spin mb-2" />
        <span className="text-sm">Loading executions...</span>
      </div>
    )
  }

  if (!traces || traces.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-muted-foreground">
        No recent executions
      </div>
    )
  }

  const sorted = traces
    .slice(0, 50)
    .sort((a, b) => {
      const timeA = a.timestamp_start ? new Date(a.timestamp_start).getTime() : 0
      const timeB = b.timestamp_start ? new Date(b.timestamp_start).getTime() : 0
      return timeB - timeA
    })

  const visible = sorted.slice(0, displayLimit)
  const metaMessage = formatMetaMessage(tracesMeta, traces.length, visible.length)

  return (
    <div className="space-y-2">
      {metaMessage && (
        <p className="text-xs text-muted-foreground mb-3">{metaMessage}</p>
      )}
      {visible.map((trace, index) => {
        const startDate = trace.timestamp_start ? new Date(trace.timestamp_start) : null
        const finishDate = trace.timestamp_finish ? new Date(trace.timestamp_finish) : null
        const time = startDate && !isNaN(startDate.getTime()) ? startDate.toLocaleString() : 'Time not recorded'
        const hasState = Boolean(trace.state ?? trace.script_execution)
        const isError = Boolean(trace.error) || trace.state === 'error'
        const statusLabel = isError ? 'Error' : hasState ? 'Success' : 'Status not recorded'
        const iconClass = isError ? 'error' : hasState ? 'success' : 'warning'
        const durationMs =
          startDate && finishDate && !isNaN(startDate.getTime()) && !isNaN(finishDate.getTime())
            ? finishDate.getTime() - startDate.getTime()
            : null
        const duration = durationMs !== null && durationMs >= 0 ? formatDuration(durationMs) : null

        const details: string[] = []
        if (trace.run_id) details.push(`Run ${trace.run_id.slice(0, 8)}`)
        const execution = trace.script_execution ?? trace.state
        if (execution) details.push(`Execution ${execution}`)
        if (duration) details.push(`Duration ${duration}`)
        const errorText = formatError(trace.error)
        if (errorText) details.push(`Error ${errorText}`)
        if (!errorText && !execution) details.push('No execution details recorded')

        return (
          <div
            key={trace.run_id ?? index}
            className="flex items-center gap-3 p-3 rounded-lg bg-secondary"
          >
            <div
              className={cn(
                'w-6 h-6 rounded-full flex items-center justify-center text-xs',
                iconClass === 'error' && 'bg-destructive/10 text-destructive',
                iconClass === 'success' && 'bg-success/10 text-success',
                iconClass === 'warning' && 'bg-warning/10 text-warning'
              )}
            >
              {isError ? <X className="h-3 w-3" /> : hasState ? <Check className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm">
                {time} - {statusLabel}
              </div>
              <div className="text-xs text-muted-foreground truncate">
                {formatTrigger(trace.trigger)}
              </div>
              {details.length > 0 && (
                <div className="text-xs text-muted-foreground mt-1">
                  {details.join(' • ')}
                </div>
              )}
            </div>
          </div>
        )
      })}
      {sorted.length > displayLimit && (
        <div className="flex justify-center pt-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setDisplayLimit((prev) => Math.min(prev + 5, 50))}
          >
            Show more ({sorted.length - displayLimit} more)
          </Button>
        </div>
      )}
      {displayLimit > 2 && sorted.length <= displayLimit && (
        <div className="flex justify-center pt-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setDisplayLimit(2)}
          >
            Show fewer
          </Button>
        </div>
      )}
    </div>
  )
}

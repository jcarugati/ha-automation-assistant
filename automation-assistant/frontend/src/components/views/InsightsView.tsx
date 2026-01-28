import { useState, useEffect } from 'react'
import { Shield } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/shared'
import { getLatestReport } from '@/api'
import type { Insight, InsightSeverity } from '@/types'

interface InsightsViewProps {
  insights: Insight[]
  onRunDiagnosis: () => void
  diagnosisRunning: boolean
  onViewAutomation: (id: string) => void
  onResolveInsight: (insightId: string, resolved: boolean) => void
  onGetFix: (insightId: string) => void
}

const severityFilters: { value: InsightSeverity | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'critical', label: 'Critical' },
  { value: 'warning', label: 'Warning' },
  { value: 'info', label: 'Info' },
]

export function InsightsView({
  insights,
  onRunDiagnosis,
  diagnosisRunning,
  onViewAutomation,
  onResolveInsight,
  onGetFix,
}: InsightsViewProps) {
  const [severityFilter, setSeverityFilter] = useState<InsightSeverity | 'all'>('all')
  const [lastRunInfo, setLastRunInfo] = useState<string>('')

  useEffect(() => {
    async function loadLastReport() {
      try {
        const report = await getLatestReport()
        const runAt = new Date(report.run_at)
        setLastRunInfo(`Last: ${runAt.toLocaleString()}`)
      } catch {
        // Ignore
      }
    }
    void loadLastReport()
  }, [])

  const filtered =
    severityFilter === 'all' ? insights : insights.filter((i) => i.severity === severityFilter)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Insights Dashboard</h2>
        <div className="flex items-center gap-3">
          {lastRunInfo && <span className="text-sm text-muted-foreground">{lastRunInfo}</span>}
          <Button onClick={onRunDiagnosis} disabled={diagnosisRunning}>
            {diagnosisRunning ? 'Running...' : 'Run Full Diagnosis'}
          </Button>
        </div>
      </div>

      {diagnosisRunning && (
        <Card>
          <CardContent className="pt-6">
            <LoadingSpinner message="Analyzing all automations..." />
          </CardContent>
        </Card>
      )}

      <div className="flex gap-1">
        {severityFilters.map((f) => (
          <button
            key={f.value}
            onClick={() => {
              setSeverityFilter(f.value)
            }}
            className={cn(
              'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
              severityFilter === f.value
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent'
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>No insights found. Run a full diagnosis to find issues.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((insight) => (
            <Card
              key={insight.insight_id}
              className={cn(
                'border-l-4',
                insight.severity === 'critical' && 'border-l-destructive',
                insight.severity === 'warning' && 'border-l-warning',
                insight.severity === 'info' && 'border-l-primary'
              )}
            >
              <CardContent className="pt-5">
                <div className="flex items-start justify-between mb-3">
                  <Badge
                    variant={
                      insight.severity === 'critical'
                        ? 'critical'
                        : insight.severity === 'warning'
                          ? 'warning'
                          : 'info'
                    }
                  >
                    {insight.severity}
                  </Badge>
                </div>
                <h3 className="font-medium mb-2">{insight.title}</h3>
                <p className="text-sm text-muted-foreground mb-3 leading-relaxed">
                  {insight.description}
                </p>
                <p className="text-sm text-muted-foreground mb-4">
                  <strong className="text-secondary-foreground">Affected:</strong>{' '}
                  {insight.automation_names.join(', ')}
                </p>
                <div className="flex flex-wrap gap-2">
                  {insight.automation_ids.length === 1 ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        const id = insight.automation_ids[0]
                        if (id) onViewAutomation(id)
                      }}
                    >
                      View Automation
                    </Button>
                  ) : (
                    insight.automation_ids.map((id) => (
                      <Button
                        key={id}
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          onViewAutomation(id)
                        }}
                      >
                        View
                      </Button>
                    ))
                  )}
                  <Button
                    size="sm"
                    onClick={() => {
                      onGetFix(insight.insight_id)
                    }}
                  >
                    Get AI Fix
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      onResolveInsight(insight.insight_id, !insight.resolved)
                    }}
                  >
                    {insight.resolved ? 'Unresolve' : 'Mark Resolved'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

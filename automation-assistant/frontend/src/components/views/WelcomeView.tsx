import { useState, useEffect } from 'react'
import { Plus, Shield, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { StatsGrid } from '@/components/shared/StatsGrid'
import type { Automation, ScheduleConfig } from '@/types'
import { getLatestReport } from '@/api'

interface WelcomeViewProps {
  automations: Automation[]
  automationIdsWithIssues: Set<string>
  schedule: ScheduleConfig | null
  onCreateClick: () => void
  onInsightsClick: () => void
  onRunDiagnosis: () => void
  onScheduleClick: () => void
  diagnosisRunning: boolean
}

export function WelcomeView({
  automations,
  automationIdsWithIssues,
  schedule,
  onCreateClick,
  onInsightsClick,
  onRunDiagnosis,
  onScheduleClick,
  diagnosisRunning,
}: WelcomeViewProps) {
  const [lastDiagnosisInfo, setLastDiagnosisInfo] = useState<string>('No diagnosis run yet')

  const total = automations.length
  const disabled = automations.filter((a) => a.state === 'off').length
  const withIssues = automations.filter((a) => automationIdsWithIssues.has(a.id)).length
  const healthy = total - disabled - withIssues

  useEffect(() => {
    async function loadLastReport() {
      try {
        const report = await getLatestReport()
        const runAt = new Date(report.run_at)
        setLastDiagnosisInfo(`Last diagnosis: ${runAt.toLocaleString()}`)
      } catch {
        // Ignore - no report available
        if (schedule?.next_run) {
          const next = new Date(schedule.next_run)
          setLastDiagnosisInfo(`Next scheduled: ${next.toLocaleString()}`)
        }
      }
    }
    void loadLastReport()
  }, [schedule?.next_run])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-2">Welcome to Automation Assistant</h1>
        <p className="text-muted-foreground">
          Manage, diagnose, and create Home Assistant automations with AI
        </p>
      </div>

      <StatsGrid
        total={total}
        healthy={healthy}
        withIssues={withIssues}
        disabled={disabled}
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">System Health</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">{lastDiagnosisInfo}</p>
          <div className="flex gap-3">
            <Button onClick={onRunDiagnosis} disabled={diagnosisRunning}>
              {diagnosisRunning ? 'Running...' : 'Run Full Diagnosis'}
            </Button>
            <Button variant="secondary" onClick={onScheduleClick}>
              <Settings className="h-4 w-4 mr-2" />
              Configure Schedule
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <Button onClick={onCreateClick}>
              <Plus className="h-4 w-4 mr-2" />
              Create New Automation
            </Button>
            <Button variant="secondary" onClick={onInsightsClick}>
              <Shield className="h-4 w-4 mr-2" />
              View All Insights
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Message,
  YamlEditor,
  HealthBadge,
  ExecutionList,
  LoadingSpinner,
} from '@/components/shared'
import { diagnoseAutomation, modifyAutomation, deployAutomation } from '@/api'
import { copyToClipboard, formatMarkdown } from '@/lib/utils'
import type { AutomationDetails, Insight } from '@/types'

interface DetailViewProps {
  details: AutomationDetails
  detailsLoading: boolean
  issues: Insight[]
  onRefresh: () => Promise<void>
  onDelete: () => void
}

export function DetailView({
  details,
  detailsLoading,
  issues,
  onRefresh,
  onDelete,
}: DetailViewProps) {
  const [yaml, setYaml] = useState(details.yaml)
  const [modifyPrompt, setModifyPrompt] = useState('')
  const [modifyLoading, setModifyLoading] = useState(false)
  const [diagnoseLoading, setDiagnoseLoading] = useState(false)
  const [diagnosisResult, setDiagnosisResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<{
    type: 'success' | 'error'
    text: string
  } | null>(null)
  const [saving, setSaving] = useState(false)

  // Update yaml when details change
  if (details.yaml !== yaml && !saving && !modifyLoading) {
    setYaml(details.yaml)
  }

  const automation = details.automation

  const handleDiagnose = async () => {
    setDiagnoseLoading(true)
    setDiagnosisResult(null)

    try {
      const data = await diagnoseAutomation({ automation_id: automation.id })
      if (data.success) {
        setDiagnosisResult(data.analysis)
      } else {
        setError(data.error ?? 'Diagnosis failed')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to diagnose automation')
    } finally {
      setDiagnoseLoading(false)
    }
  }

  const handleModify = async () => {
    if (!modifyPrompt.trim()) return

    setModifyLoading(true)
    setError(null)

    try {
      const data = await modifyAutomation({
        prompt: modifyPrompt,
        existing_yaml: yaml,
      })
      if (data.success && data.yaml_content) {
        setYaml(data.yaml_content)
        setModifyPrompt('')
        setSuccess('Automation modified. Review and save changes.')
        setTimeout(() => setSuccess(null), 5000)
      } else {
        setError(data.error ?? 'Failed to modify automation')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to connect to server')
    } finally {
      setModifyLoading(false)
    }
  }

  const handleSave = async () => {
    if (!yaml.trim()) {
      setActionMessage({ type: 'error', text: 'YAML is empty' })
      return
    }

    setSaving(true)
    setActionMessage({ type: 'success', text: 'Saving changes...' })

    try {
      const data = await deployAutomation({
        yaml_content: yaml,
        automation_id: automation.id,
      })
      if (data.success) {
        setSuccess(data.message)
        setActionMessage({ type: 'success', text: 'Saved to Home Assistant' })
        await onRefresh()
      } else {
        setError('Failed to save')
        setActionMessage({ type: 'error', text: 'Failed to save' })
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to save automation'
      setError(message)
      setActionMessage({ type: 'error', text: message })
    } finally {
      setSaving(false)
      setTimeout(() => setActionMessage(null), 2500)
    }
  }

  const handleCopy = async () => {
    if (!yaml.trim()) {
      setActionMessage({ type: 'error', text: 'Nothing to copy' })
      return
    }
    try {
      await copyToClipboard(yaml)
      setActionMessage({ type: 'success', text: 'Copied to clipboard' })
      setTimeout(() => setActionMessage(null), 2500)
    } catch {
      setActionMessage({ type: 'error', text: 'Copy failed' })
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold">{automation.alias}</h1>
          <p className="text-sm text-muted-foreground">automation.{automation.id}</p>
        </div>
        <Badge variant={automation.state === 'on' ? 'success' : automation.state === 'off' ? 'secondary' : 'warning'}>
          {automation.state === 'on' ? 'Enabled' : automation.state === 'off' ? 'Disabled' : 'Unknown'}
        </Badge>
      </div>

      {error && <Message type="error">{error}</Message>}
      {success && <Message type="success">{success}</Message>}

      {/* Health Status */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Health Status
          </h2>
          <Button variant="secondary" size="sm" onClick={handleDiagnose} disabled={diagnoseLoading}>
            {diagnoseLoading ? 'Analyzing...' : 'Diagnose'}
          </Button>
        </div>
        <HealthBadge issues={issues} />
      </section>

      {/* Recent Executions */}
      <section>
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
          Recent Executions
        </h2>
        <ExecutionList
          traces={details.traces}
          tracesMeta={details.traces_meta}
          loading={detailsLoading}
        />
      </section>

      {/* Modify with AI */}
      <section>
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
          Modify with AI
        </h2>
        <div className="flex gap-3">
          <Textarea
            value={modifyPrompt}
            onChange={(e) => setModifyPrompt(e.target.value)}
            placeholder="Describe the changes you want, e.g., 'Add a 5 minute delay before turning off' or 'Only trigger when it's dark outside'"
            className="flex-1 min-h-[60px]"
          />
          <Button onClick={handleModify} disabled={modifyLoading || !modifyPrompt.trim()}>
            {modifyLoading ? 'Modifying...' : 'Modify'}
          </Button>
        </div>
        {modifyLoading && (
          <div className="mt-3">
            <LoadingSpinner message="Modifying..." />
          </div>
        )}
      </section>

      {/* YAML */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            YAML
          </h2>
          <Button variant="secondary" size="sm" onClick={handleCopy}>
            Copy
          </Button>
        </div>
        <YamlEditor value={yaml} onChange={setYaml} />
        {actionMessage && (
          <Message type={actionMessage.type} className="mt-3">
            {actionMessage.text}
          </Message>
        )}
        <div className="flex gap-3 mt-4">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
          <Button variant="destructive" onClick={onDelete}>
            Delete
          </Button>
        </div>
      </section>

      {/* Diagnosis Results */}
      {diagnosisResult && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Diagnosis Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className="text-sm text-muted-foreground leading-relaxed"
              dangerouslySetInnerHTML={{ __html: formatMarkdown(diagnosisResult) }}
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}

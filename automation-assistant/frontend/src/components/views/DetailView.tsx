import { useEffect, useMemo, useState } from 'react'
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
import { copyToClipboard, formatMarkdown, truncateText } from '@/lib/utils'
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
  const [diagnosisOpen, setDiagnosisOpen] = useState(false)
  const [fixLoading, setFixLoading] = useState(false)
  const [selectedIssueIds, setSelectedIssueIds] = useState<string[]>([])
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
  const unresolvedIssues = useMemo(() => issues.filter((issue) => !issue.resolved), [issues])
  const hasChanges = useMemo(() => yaml !== details.yaml, [yaml, details.yaml])

  const handleDiagnose = async () => {
    setDiagnoseLoading(true)
    setDiagnosisResult(null)
    setError(null)

    try {
      const data = await diagnoseAutomation({ automation_id: automation.id })
      if (data.success) {
        setDiagnosisResult(data.analysis)
        setDiagnosisOpen(true)
      } else {
        setError(data.error ?? 'Diagnosis failed')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to diagnose automation')
    } finally {
      setDiagnoseLoading(false)
    }
  }

  useEffect(() => {
    if (unresolvedIssues.length === 0) {
      setSelectedIssueIds([])
      return
    }
    setSelectedIssueIds((prev) => {
      const unresolvedIds = new Set(unresolvedIssues.map((issue) => issue.insight_id))
      const filtered = prev.filter((id) => unresolvedIds.has(id))
      if (filtered.length > 0) {
        return filtered
      }
      return Array.from(unresolvedIds)
    })
  }, [unresolvedIssues])

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
        setTimeout(() => {
          setSuccess(null)
        }, 5000)
      } else {
        setError(data.error ?? 'Failed to modify automation')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to connect to server')
    } finally {
      setModifyLoading(false)
    }
  }

  const handleFixIssues = async () => {
    if (selectedIssueIds.length === 0) return
    setFixLoading(true)
    setError(null)

    try {
      const selectedIssues = unresolvedIssues.filter((issue) =>
        selectedIssueIds.includes(issue.insight_id)
      )
      const issueList = selectedIssues
        .map(
          (issue, index) =>
            `${String(index + 1)}. ${issue.title}\n- ${issue.description}\n- Recommendation: ${issue.recommendation}`
        )
        .join('\n\n')

      const data = await modifyAutomation({
        prompt: `Fix the following issues in this automation. Return only the updated YAML.\n\n${issueList}`,
        existing_yaml: yaml,
      })

      if (data.success && data.yaml_content) {
        setYaml(data.yaml_content)
        setSuccess('Fix suggestions applied. Review and save changes.')
        setTimeout(() => {
          setSuccess(null)
        }, 5000)
      } else {
        setError(data.error ?? 'Failed to apply fixes')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to apply fixes')
    } finally {
      setFixLoading(false)
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
      setTimeout(() => {
        setActionMessage(null)
      }, 2500)
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
      setTimeout(() => {
        setActionMessage(null)
      }, 2500)
    } catch {
      setActionMessage({ type: 'error', text: 'Copy failed' })
    }
  }

  const handleToggleIssue = (issueId: string) => {
    setSelectedIssueIds((prev) =>
      prev.includes(issueId) ? prev.filter((id) => id !== issueId) : [...prev, issueId]
    )
  }

  const handleToggleAllIssues = () => {
    if (selectedIssueIds.length === unresolvedIssues.length) {
      setSelectedIssueIds([])
      return
    }
    setSelectedIssueIds(unresolvedIssues.map((issue) => issue.insight_id))
  }

  const diagnosisPreview = diagnosisResult ? formatMarkdown(truncateText(diagnosisResult, 400)) : ''

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold">{automation.alias}</h1>
          <p className="text-sm text-muted-foreground">automation.{automation.id}</p>
        </div>
        <Badge
          variant={
            automation.state === 'on'
              ? 'success'
              : automation.state === 'off'
                ? 'secondary'
                : 'warning'
          }
        >
          {automation.state === 'on'
            ? 'Enabled'
            : automation.state === 'off'
              ? 'Disabled'
              : 'Unknown'}
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
          <Button
            variant="secondary"
            size="sm"
            onClick={() => void handleDiagnose()}
            disabled={diagnoseLoading}
          >
            {diagnoseLoading ? 'Analyzing...' : 'Diagnose'}
          </Button>
        </div>
        <HealthBadge issues={issues} />
        {diagnosisResult && (
          <Card className="mt-4">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Diagnosis Results</CardTitle>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setDiagnosisOpen((prev) => !prev)
                }}
              >
                {diagnosisOpen ? 'Collapse' : 'Expand'}
              </Button>
            </CardHeader>
            <CardContent>
              {diagnosisOpen ? (
                <div
                  className="text-sm text-muted-foreground leading-relaxed space-y-3 [&_h1]:text-base [&_h1]:font-semibold [&_h2]:text-sm [&_h2]:font-semibold [&_h3]:text-sm [&_h3]:font-semibold [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:mb-1 [&_code]:font-mono [&_code]:text-xs [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_pre]:bg-muted [&_pre]:p-3 [&_pre]:rounded [&_pre]:overflow-x-auto"
                  dangerouslySetInnerHTML={{ __html: formatMarkdown(diagnosisResult) }}
                />
              ) : (
                <div
                  className="text-sm text-muted-foreground leading-relaxed"
                  dangerouslySetInnerHTML={{ __html: diagnosisPreview }}
                />
              )}
            </CardContent>
          </Card>
        )}
        {unresolvedIssues.length > 0 && (
          <Card className="mt-4">
            <CardHeader>
              <CardTitle className="text-base">Issues to Fix</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Select the issues you want to fix.
                  </p>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      handleToggleAllIssues()
                    }}
                  >
                    {selectedIssueIds.length === unresolvedIssues.length
                      ? 'Clear all'
                      : 'Select all'}
                  </Button>
                </div>
                <div className="space-y-3">
                  {unresolvedIssues.map((issue) => (
                    <label key={issue.insight_id} className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        className="mt-1 h-4 w-4"
                        checked={selectedIssueIds.includes(issue.insight_id)}
                        onChange={() => {
                          handleToggleIssue(issue.insight_id)
                        }}
                      />
                      <div>
                        <p className="text-sm font-medium">{issue.title}</p>
                        <p className="text-xs text-muted-foreground">{issue.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
                <Button
                  onClick={() => void handleFixIssues()}
                  disabled={fixLoading || selectedIssueIds.length === 0}
                >
                  {fixLoading ? 'Fixing...' : 'Fix selected issues'}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
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
            onChange={(e) => {
              setModifyPrompt(e.target.value)
            }}
            placeholder="Describe the changes you want, e.g., 'Add a 5 minute delay before turning off' or 'Only trigger when it's dark outside'"
            className="flex-1 min-h-[60px]"
          />
          <Button
            onClick={() => void handleModify()}
            disabled={modifyLoading || !modifyPrompt.trim()}
          >
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
          <Button variant="secondary" size="sm" onClick={() => void handleCopy()}>
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
          <Button
            onClick={() => void handleSave()}
            disabled={saving || !hasChanges || !yaml.trim()}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
          <Button variant="destructive" onClick={onDelete}>
            Delete
          </Button>
        </div>
      </section>
    </div>
  )
}

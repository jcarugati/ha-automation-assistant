import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'
import { Message, YamlDisplay, LoadingSpinner } from '@/components/shared'
import { generateAutomation, validateYaml } from '@/api'
import { copyToClipboard, formatMarkdown } from '@/lib/utils'

interface CreateViewProps {
  onDeployClick: (yaml: string) => void
}

export function CreateView({ onDeployClick }: CreateViewProps) {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [result, setResult] = useState<{ explanation: string; yaml: string } | null>(null)
  const [validationMessage, setValidationMessage] = useState<{
    type: 'success' | 'error'
    text: string
  } | null>(null)
  const [actionMessage, setActionMessage] = useState<{
    type: 'success' | 'error'
    text: string
  } | null>(null)

  const handleGenerate = async () => {
    if (!prompt.trim()) return

    setLoading(true)
    setError(null)
    setSuccess(null)
    setResult(null)
    setValidationMessage(null)
    setActionMessage(null)

    try {
      const data = await generateAutomation({ prompt })
      if (data.success) {
        setResult({
          explanation: data.response,
          yaml: data.yaml_content ?? '',
        })
      } else {
        setError(data.error ?? 'Failed to generate automation')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to connect to server')
    } finally {
      setLoading(false)
    }
  }

  const handleValidate = async () => {
    if (!result?.yaml) return

    try {
      const data = await validateYaml({ yaml_content: result.yaml })
      if (data.valid) {
        setValidationMessage({ type: 'success', text: 'Valid YAML syntax' })
      } else {
        setValidationMessage({
          type: 'error',
          text: data.errors.join(', ') || 'Invalid YAML',
        })
      }
    } catch {
      setValidationMessage({ type: 'error', text: 'Failed to validate' })
    }
  }

  const handleCopy = async () => {
    if (!result?.yaml) {
      setActionMessage({ type: 'error', text: 'Nothing to copy' })
      return
    }
    try {
      await copyToClipboard(result.yaml)
      setActionMessage({ type: 'success', text: 'Copied to clipboard' })
      setTimeout(() => setActionMessage(null), 2500)
    } catch {
      setActionMessage({ type: 'error', text: 'Copy failed' })
    }
  }

  const handleDeploy = () => {
    if (result?.yaml) {
      onDeployClick(result.yaml)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Create New Automation</h2>

      {error && <Message type="error">{error}</Message>}
      {success && <Message type="success">{success}</Message>}

      <Card>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <label className="text-sm font-medium">
              Describe the automation you want to create
            </label>
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Example: Turn on the living room lights when motion is detected after sunset and turn them off after 5 minutes of no motion"
              className="min-h-[120px]"
            />
            <Button onClick={handleGenerate} disabled={loading || !prompt.trim()}>
              Generate Automation
            </Button>
          </div>
        </CardContent>
      </Card>

      {loading && (
        <Card>
          <CardContent className="pt-6">
            <LoadingSpinner message="Generating your automation..." />
          </CardContent>
        </Card>
      )}

      {result && (
        <Card>
          <CardContent className="pt-6 space-y-6">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                Explanation
              </h3>
              <div
                className="text-sm text-muted-foreground leading-relaxed"
                dangerouslySetInnerHTML={{ __html: formatMarkdown(result.explanation) }}
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Generated YAML
                </h3>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" onClick={handleValidate}>
                    Validate
                  </Button>
                  <Button variant="secondary" size="sm" onClick={handleCopy}>
                    Copy
                  </Button>
                  <Button size="sm" onClick={handleDeploy}>
                    Deploy to HA
                  </Button>
                </div>
              </div>
              <YamlDisplay value={result.yaml} />
              {validationMessage && (
                <Message type={validationMessage.type} className="mt-3">
                  {validationMessage.text}
                </Message>
              )}
              {actionMessage && (
                <Message type={actionMessage.type} className="mt-3">
                  {actionMessage.text}
                </Message>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

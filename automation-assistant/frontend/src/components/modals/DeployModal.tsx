import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { YamlDisplay } from '@/components/shared'
import { deployAutomation } from '@/api'

interface DeployModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  yaml: string
  onSuccess: (message: string) => void
  onError: (message: string) => void
}

export function DeployModal({ open, onOpenChange, yaml, onSuccess, onError }: DeployModalProps) {
  const [automationId, setAutomationId] = useState('')
  const [deploying, setDeploying] = useState(false)

  const handleDeploy = async () => {
    setDeploying(true)
    try {
      const data = await deployAutomation({
        yaml_content: yaml,
        automation_id: automationId || undefined,
      })
      if (data.success) {
        onSuccess(data.message)
        onOpenChange(false)
      } else {
        onError('Failed to deploy')
      }
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Failed to deploy automation')
    } finally {
      setDeploying(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Deploy to Home Assistant</DialogTitle>
          <DialogDescription>
            This will create or update the automation directly in Home Assistant.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Automation ID (optional)</label>
            <Input
              value={automationId}
              onChange={(e) => {
                setAutomationId(e.target.value)
              }}
              placeholder="Leave empty to use ID from YAML"
            />
          </div>
          <YamlDisplay value={yaml} className="max-h-[300px] overflow-y-auto" />
        </div>
        <DialogFooter>
          <Button
            variant="secondary"
            onClick={() => {
              onOpenChange(false)
            }}
          >
            Cancel
          </Button>
          <Button onClick={() => void handleDeploy()} disabled={deploying}>
            {deploying ? 'Deploying...' : 'Deploy'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

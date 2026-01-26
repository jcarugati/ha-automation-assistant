import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { ScheduleConfig } from '@/types'

interface ScheduleModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  schedule: ScheduleConfig | null
  onSave: (enabled: boolean, time: string) => Promise<void>
}

export function ScheduleModal({
  open,
  onOpenChange,
  schedule,
  onSave,
}: ScheduleModalProps) {
  const [enabled, setEnabled] = useState(schedule?.enabled ?? true)
  const [time, setTime] = useState(schedule?.time ?? '03:00')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (schedule) {
      setEnabled(schedule.enabled)
      setTime(schedule.time)
    }
  }, [schedule])

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(enabled, time)
      onOpenChange(false)
    } catch (e) {
      console.error('Failed to save schedule:', e)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Schedule Settings</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Enable daily diagnosis</label>
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                className="h-4 w-4"
              />
              <span className="text-sm text-muted-foreground">
                Run automatic diagnosis daily
              </span>
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Run at time (24h format)</label>
            <Input
              value={time}
              onChange={(e) => setTime(e.target.value)}
              placeholder="HH:MM"
              className="w-32"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

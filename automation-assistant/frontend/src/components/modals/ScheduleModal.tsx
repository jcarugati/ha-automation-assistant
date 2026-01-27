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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { ScheduleConfig } from '@/types'

interface ScheduleModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  schedule: ScheduleConfig | null
  onSave: (request: {
    enabled: boolean
    time: string
    frequency: ScheduleConfig['frequency']
    day_of_week: string
    day_of_month: number
  }) => Promise<void>
}

export function ScheduleModal({
  open,
  onOpenChange,
  schedule,
  onSave,
}: ScheduleModalProps) {
  const [enabled, setEnabled] = useState(schedule?.enabled ?? true)
  const [time, setTime] = useState(schedule?.time ?? '03:00')
  const [frequency, setFrequency] = useState<ScheduleConfig['frequency']>(
    schedule?.frequency ?? 'daily'
  )
  const [dayOfWeek, setDayOfWeek] = useState(schedule?.day_of_week ?? 'mon')
  const [dayOfMonth, setDayOfMonth] = useState(
    String(schedule?.day_of_month ?? 1)
  )
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (schedule) {
      setEnabled(schedule.enabled)
      setTime(schedule.time)
      setFrequency(schedule.frequency ?? 'daily')
      setDayOfWeek(schedule.day_of_week ?? 'mon')
      setDayOfMonth(String(schedule.day_of_month ?? 1))
    }
  }, [schedule])

  const handleSave = async () => {
    setSaving(true)
    try {
      const parsedDayOfMonth = Number(dayOfMonth)
      await onSave({
        enabled,
        time,
        frequency,
        day_of_week: dayOfWeek,
        day_of_month: Number.isFinite(parsedDayOfMonth) ? parsedDayOfMonth : 1,
      })
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
            <label className="text-sm font-medium">Enable scheduled diagnosis</label>
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                className="h-4 w-4"
              />
              <span className="text-sm text-muted-foreground">
                Run automatic diagnosis on a schedule
              </span>
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Frequency</label>
            <Select value={frequency} onValueChange={(value) => setFrequency(value as ScheduleConfig['frequency'])}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Select frequency" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
              </SelectContent>
            </Select>
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
          {frequency === 'weekly' && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Day of week</label>
              <Select value={dayOfWeek} onValueChange={setDayOfWeek}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Select day" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="mon">Monday</SelectItem>
                  <SelectItem value="tue">Tuesday</SelectItem>
                  <SelectItem value="wed">Wednesday</SelectItem>
                  <SelectItem value="thu">Thursday</SelectItem>
                  <SelectItem value="fri">Friday</SelectItem>
                  <SelectItem value="sat">Saturday</SelectItem>
                  <SelectItem value="sun">Sunday</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
          {frequency === 'monthly' && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Day of month</label>
              <Input
                value={dayOfMonth}
                onChange={(e) => setDayOfMonth(e.target.value)}
                placeholder="1"
                type="number"
                min={1}
                max={31}
                className="w-32"
              />
            </div>
          )}
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

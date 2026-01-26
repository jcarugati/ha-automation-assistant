import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

interface YamlEditorProps {
  value: string
  onChange?: (value: string) => void
  readOnly?: boolean
  className?: string
}

export function YamlEditor({ value, onChange, readOnly, className }: YamlEditorProps) {
  return (
    <Textarea
      value={value}
      onChange={onChange ? (e) => onChange(e.target.value) : undefined}
      readOnly={readOnly}
      className={cn(
        'yaml-editor min-h-[300px] bg-background font-mono text-sm',
        className
      )}
    />
  )
}

import { cn } from '@/lib/utils'

interface YamlDisplayProps {
  value: string
  className?: string
}

export function YamlDisplay({ value, className }: YamlDisplayProps) {
  return (
    <pre
      className={cn(
        'p-4 rounded-lg bg-background border border-border overflow-x-auto font-mono text-sm',
        className
      )}
    >
      {value}
    </pre>
  )
}

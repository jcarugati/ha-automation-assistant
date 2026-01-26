import { cn } from '@/lib/utils'

interface LoadingSpinnerProps {
  message?: string
  className?: string
}

export function LoadingSpinner({ message, className }: LoadingSpinnerProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12', className)}>
      <div className="h-8 w-8 border-2 border-border border-t-primary rounded-full animate-spin mb-3" />
      {message && <span className="text-sm text-muted-foreground">{message}</span>}
    </div>
  )
}

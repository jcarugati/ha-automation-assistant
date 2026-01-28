import { cn } from '@/lib/utils'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface MessageProps {
  type: 'success' | 'error'
  children: React.ReactNode
  className?: string
}

export function Message({ type, children, className }: MessageProps) {
  return (
    <Alert variant={type === 'error' ? 'destructive' : 'success'} className={cn(className)}>
      <AlertDescription>{children}</AlertDescription>
    </Alert>
  )
}

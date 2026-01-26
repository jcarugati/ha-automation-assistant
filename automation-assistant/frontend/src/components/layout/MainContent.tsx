import { ScrollArea } from '@/components/ui/scroll-area'

interface MainContentProps {
  children: React.ReactNode
}

export function MainContent({ children }: MainContentProps) {
  return (
    <main className="flex-1 h-screen overflow-hidden">
      <ScrollArea className="h-full">
        <div className="p-6 max-w-4xl mx-auto">{children}</div>
      </ScrollArea>
    </main>
  )
}

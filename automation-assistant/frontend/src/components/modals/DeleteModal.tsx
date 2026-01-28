import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

interface DeleteModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  automationName: string
  onConfirm: () => void
}

export function DeleteModal({ open, onOpenChange, automationName, onConfirm }: DeleteModalProps) {
  const handleDelete = () => {
    onConfirm()
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Automation</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete &quot;{automationName}&quot;?
          </DialogDescription>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">This cannot be undone.</p>
        <DialogFooter>
          <Button
            variant="secondary"
            onClick={() => {
              onOpenChange(false)
            }}
          >
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

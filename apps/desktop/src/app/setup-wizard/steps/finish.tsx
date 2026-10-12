import { Button } from '@/components/ui/button'

interface FinishStepProps {
  onOpenWorkspace: () => void
  onStartChat: () => void
  onCreateProject: () => void
  onViewDocs: () => void
}

export function FinishStep({ onOpenWorkspace, onStartChat, onCreateProject, onViewDocs }: FinishStepProps) {
  return (
    <div className="mx-auto flex max-w-lg flex-col items-center justify-center gap-10 py-16 text-center">
      <div className="flex flex-col items-center gap-4">
        <div className="flex h-24 w-24 items-center justify-center rounded-full bg-green-500/20 ring-1 ring-green-500/30">
          <svg className="h-12 w-12 text-green-500" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <h1 className="text-4xl font-bold tracking-tight">Setup Complete</h1>
        <p className="max-w-md text-muted-foreground">
          AetherOS is ready to use. Your workspace has been configured and your providers are set up.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <Button className="h-12 px-8 text-base font-medium" onClick={onOpenWorkspace}>
          Open Workspace
        </Button>
        <Button className="h-12 px-8 text-base font-medium" onClick={onStartChat} variant="secondary">
          Start Chat
        </Button>
        <Button className="h-12 px-8 text-base font-medium" onClick={onCreateProject} variant="outline">
          Create First Project
        </Button>
        <Button className="text-sm text-muted-foreground" onClick={onViewDocs} variant="ghost">
          View Documentation
        </Button>
      </div>
    </div>
  )
}

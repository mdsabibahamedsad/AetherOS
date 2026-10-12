import { useStore } from '@nanostores/react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { $runtimeStatus } from '@/store/dashboard'

interface RuntimeRowProps {
  name: string
  version: string
  path: string
  installed: boolean
}

function RuntimeRow({ name, version, path, installed }: RuntimeRowProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-(--ui-control-hover-background)">
      <span className={cn(
        'codicon text-base',
        installed ? 'codicon-check text-emerald-500' : 'codicon-circle-slash text-(--ui-text-tertiary)'
      )} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{name}</span>
          <Badge variant={installed ? 'default' : 'muted'}>{installed ? version : 'Not installed'}</Badge>
        </div>
        <div className="truncate text-xs text-(--ui-text-tertiary)">{path}</div>
      </div>
    </div>
  )
}

export function RuntimePanel() {
  const runtime = useStore($runtimeStatus)

  if (!runtime) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Runtime Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="codicon codicon-loading codicon-modifier-spin text-xl text-(--ui-text-tertiary)" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Runtime Status</CardTitle>
        <Badge variant={runtime.dependencies.installed ? 'default' : 'warn'}>
          {runtime.dependencies.count} deps
        </Badge>
      </CardHeader>
      <CardContent>
        <div className="space-y-1">
          <RuntimeRow installed={runtime.node.installed} name="Node.js" path={runtime.node.path} version={runtime.node.version} />
          <RuntimeRow installed={runtime.python.installed} name="Python" path={runtime.python.path} version={runtime.python.version} />
          <RuntimeRow installed={runtime.git.installed} name="Git" path={runtime.git.path} version={runtime.git.version} />
        </div>
        <div className="mt-3 flex items-center gap-2 border-t border-(--ui-stroke-tertiary)/50 pt-3">
          <Button size="sm" variant="outline">
            Verify Installation
          </Button>
          <Button size="sm" variant="ghost">
            Install Dependencies
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

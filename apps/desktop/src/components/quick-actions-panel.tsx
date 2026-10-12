import { useStore } from '@nanostores/react'
import { useNavigate } from 'react-router-dom'

import { Codicon } from '@/components/ui/codicon'
import { $quickActions } from '@/store/quick-actions'

export function QuickActionsPanel() {
  const navigate = useNavigate()
  const actions = useStore($quickActions)

  const defaults = [
    { id: 'new-chat', label: 'New Chat', icon: 'add', route: '/new' },
    { id: 'open-project', label: 'Open Project', icon: 'file-directory', route: '/projects' },
    { id: 'settings', label: 'Settings', icon: 'settings-gear', route: '/settings' },
    { id: 'help', label: 'Help', icon: 'question', route: '/help' }
  ]

  return (
    <div className="flex items-center gap-1">
      {defaults.map(action => (
        <button
          className="inline-flex size-7 items-center justify-center rounded-md text-(--ui-text-tertiary) transition-colors hover:bg-(--ui-control-hover-background) hover:text-foreground"
          key={action.id}
          onClick={() => navigate(action.route)}
          title={action.label}
          type="button"
        >
          <Codicon name={action.icon as any} size="1rem" />
        </button>
      ))}
      {actions.map(action => (
        <button
          className="inline-flex size-7 items-center justify-center rounded-md text-(--ui-text-tertiary) transition-colors hover:bg-(--ui-control-hover-background) hover:text-foreground"
          key={action.id}
          onClick={action.action}
          title={action.label}
          type="button"
        >
          <Codicon name={action.icon as any} size="1rem" />
        </button>
      ))}
    </div>
  )
}

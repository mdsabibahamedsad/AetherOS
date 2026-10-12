import { useStore } from '@nanostores/react'
import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Input } from '@/components/ui/input'
import { Kbd } from '@/components/ui/kbd'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import { openCommandPalette } from '@/store/command-palette'
import { $sidebarOpen } from '@/store/navigation'
import { $activeProfile } from '@/store/profile'
import { $searchQuery } from '@/store/quick-actions'
import { setSearchQuery } from '@/store/quick-actions'
import { $currentModel, $currentProvider, $gatewayState } from '@/store/session'
import { openActivityDrawer } from '@/store/activity-drawer'
import { $allApprovalRequests } from '@/store/prompts'
import { $backgroundTaskCount } from '@/store/system'
import { $workingSessionIds } from '@/store/session'
import { $healthStatus, $systemStats } from '@/store/system'
import { $gateway } from '@/store/gateway'

export function TopBar() {
  const navigate = useNavigate()
  const sidebarOpen = useStore($sidebarOpen)
  const searchRef = useRef<HTMLInputElement>(null)
  const [focused, setFocused] = useState(false)
  const model = useStore($currentModel)
  const provider = useStore($currentProvider)
  const activeProfile = useStore($activeProfile)
  const gatewayState = useStore($gatewayState)
  const approvals = useStore($allApprovalRequests)
  const backgroundTasks = useStore($backgroundTaskCount)
  const workingIds = useStore($workingSessionIds)

  const handleSearch = (value: string) => {
    setSearchQuery(value)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // The topbar field is an intent affordance, not a route: Enter hands off
    // to the real universal command layer (Cmd/Ctrl+K palette). There is no
    // '/search' route — navigating there would open a bogus session.
    if (e.key === 'Enter') {
      openCommandPalette()
    }

    if (e.key === 'Escape') {
      searchRef.current?.blur()
      setSearchQuery('')
    }
  }

  const gatewayConnected = gatewayState === 'open' || gatewayState === 'connected'
  const pendingApprovals = Object.keys(approvals).length
  const runningSessions = workingIds.length
  const totalActivity = pendingApprovals + runningSessions + backgroundTasks
  const health = useStore($healthStatus)
  const stats = useStore($systemStats)

  const getSystemStatus = () => {
    if (!gatewayConnected) return 'offline'
    if (health?.overall === 'unhealthy') return 'error'
    if (health?.overall === 'degraded') return 'warning'
    if (runningSessions > 0) return 'working'
    if (pendingApprovals > 0) return 'attention'
    return 'ready'
  }

  const systemStatus = getSystemStatus()

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'ready': return 'Ready'
      case 'working': return 'Working'
      case 'attention': return 'Attention Needed'
      case 'warning': return 'Degraded'
      case 'error': return 'Error'
      case 'offline': return 'Offline'
      default: return 'Unknown'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready': return 'bg-emerald-500'
      case 'working': return 'bg-blue-500'
      case 'attention': return 'bg-amber-500'
      case 'warning': return 'bg-amber-500'
      case 'error': return 'bg-red-500'
      case 'offline': return 'bg-(--ui-text-tertiary)'
      default: return 'bg-(--ui-text-tertiary)'
    }
  }

  return (
    <header
      className={cn(
        'flex h-10 shrink-0 items-center gap-2 border-b border-(--ui-stroke-tertiary) bg-(--ui-sidebar-surface-background) px-3',
        '[-webkit-app-region:no-drag]'
      )}
    >
      <div className="flex items-center gap-2">
        <Codicon name="aetheros" size="1.125rem" className="text-foreground" />
      </div>

      <div className="relative flex min-w-0 flex-1 items-center mx-4">
        <Codicon
          className="pointer-events-none absolute left-2.5 text-(--ui-text-tertiary)"
          name="search"
          size="0.875rem"
        />
        <Input
          aria-label="Search commands, files, and chats"
          className={cn(
            'h-7 w-full max-w-md border border-transparent bg-(--ui-bg-tertiary)/40 pl-8 pr-28 text-xs transition-all placeholder:text-(--ui-text-tertiary)',
            focused && 'border-(--dt-ring) ring-1 ring-(--dt-ring)/30'
          )}
          onBlur={() => setFocused(false)}
          onChange={e => handleSearch(e.target.value)}
          onFocus={() => setFocused(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search commands, files, chats…"
          ref={searchRef}
          role="searchbox"
          title="Search — press Enter for the command palette (⌘K)"
          type="text"
          value={useStore($searchQuery)}
        />
        <Kbd className="absolute right-2 hidden shrink-0 text-[0.625rem] sm:inline-flex text-(--ui-text-tertiary)">⌘K</Kbd>
      </div>

      <div className="flex items-center gap-1 ml-auto">
        {/* System Status with Popover */}
        <Popover>
          <PopoverTrigger asChild>
            <Button
              aria-label={`System: ${getStatusLabel(systemStatus)}`}
              className="size-7"
              size="icon-sm"
              variant="ghost"
            >
              <span
                aria-label={getStatusLabel(systemStatus)}
                className={cn(
                  'size-1.5 rounded-full',
                  getStatusColor(systemStatus)
                )}
                role="status"
              />
            </Button>
          </PopoverTrigger>
          <PopoverContent align="end" side="bottom" sideOffset={8} className="w-64">
            <div className="p-2 space-y-2">
              <div className="flex items-center gap-2">
                <span className={cn('size-2 rounded-full', getStatusColor(systemStatus))} />
                <span className="text-sm font-medium">{getStatusLabel(systemStatus)}</span>
              </div>
              <Separator />
              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between text-(--ui-text-tertiary)">
                  <span>Gateway</span>
                  <span className={gatewayConnected ? 'text-emerald-500' : 'text-amber-500'}>
                    {gatewayConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
                <div className="flex justify-between text-(--ui-text-tertiary)">
                  <span>Backend</span>
                  <span className="text-emerald-500">Running</span>
                </div>
                {stats && (
                  <>
                    <Separator />
                    <div className="flex justify-between text-(--ui-text-tertiary)">
                      <span>CPU</span>
                      <span>{stats.cpu}%</span>
                    </div>
                    <div className="flex justify-between text-(--ui-text-tertiary)">
                      <span>Memory</span>
                      <span>{Math.round(stats.memory.used / 1024)}GB / {Math.round(stats.memory.total / 1024)}GB</span>
                    </div>
                  </>
                )}
                {health && health.overall !== 'healthy' && (
                  <>
                    <Separator />
                    <div className="flex justify-between text-(--ui-text-tertiary)">
                      <span>Health</span>
                      <span className={health.overall === 'degraded' ? 'text-amber-500' : 'text-red-500'}>
                        {health.overall}
                      </span>
                    </div>
                    {health.services.length > 0 && (
                      <div className="text-(--ui-text-tertiary)">
                        {health.services.length} service{health.services.length === 1 ? '' : 's'} reporting
                      </div>
                    )}
                  </>
                )}
                <Separator />
                <Button
                  onClick={() => navigate('/diagnostics')}
                  variant="ghost"
                  className="w-full justify-start text-xs px-2 py-1"
                >
                  <Codicon name="check" size="0.875rem" className="mr-2" />
                  Open Diagnostics
                </Button>
              </div>
            </div>
          </PopoverContent>
        </Popover>

        {/* Workspace selector — opens profile/workspace management */}
        <Button
          aria-label={`Workspace: ${activeProfile}`}
          className="hidden md:flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-(--ui-text-secondary) hover:text-foreground hover:bg-(--ui-control-hover-background)"
          onClick={() => navigate('/profiles')}
          title="Current workspace — open workspace management"
          variant="ghost"
        >
          <Codicon name="account" size="0.875rem" className="text-(--ui-text-tertiary)" />
          <span className="truncate max-w-[120px]">{activeProfile}</span>
        </Button>

        {/* Model selector */}
        <Button
          aria-label={`Model: ${model || 'Not configured'}`}
          className="hidden md:flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-(--ui-text-secondary) hover:text-foreground hover:bg-(--ui-control-hover-background)"
          onClick={() => navigate('/models')}
          variant="ghost"
        >
          <Codicon name="symbol-method" size="0.875rem" className="text-(--ui-text-tertiary)" />
          <span className="truncate max-w-[160px]">{model || 'No model'}</span>
          <Codicon name="chevron-down" size="0.75rem" className="text-(--ui-text-tertiary)" />
        </Button>

        {/* New Chat */}
        <Button
          aria-label="New Chat"
          className="size-7"
          onClick={() => navigate('/')}
          size="icon-sm"
          title="New Chat (⌘N)"
          variant="ghost"
        >
          <Codicon name="add" size="1rem" />
        </Button>

        {/* Notifications */}
        <Button
          aria-label="Notifications"
          className="size-7"
          onClick={() => navigate('/communications')}
          size="icon-sm"
          variant="ghost"
        >
          <Codicon name="bell" size="1rem" />
        </Button>

        {/* Activity Drawer */}
        <Button
          aria-label={totalActivity > 0 ? `${totalActivity} active items` : 'Activity'}
          className="relative size-7"
          onClick={openActivityDrawer}
          size="icon-sm"
          variant="ghost"
        >
          <Codicon name="pulse" size="1rem" />
          {totalActivity > 0 && (
            <span className="absolute -top-0.5 -right-0.5 size-4 rounded-full bg-amber-500 text-[0.5rem] font-semibold text-white flex items-center justify-center">
              {totalActivity > 9 ? '9+' : totalActivity}
            </span>
          )}
        </Button>

        {/* Avatar/Menu placeholder */}
        <div className="w-7 h-7 ml-1 rounded-full bg-(--ui-control-hover-background) flex items-center justify-center">
          <Codicon name="person" size="1rem" className="text-(--ui-text-tertiary)" />
        </div>
      </div>
    </header>
  )
}

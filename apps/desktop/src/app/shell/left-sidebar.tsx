import { useStore } from '@nanostores/react'
import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { appViewForPath } from '@/app/routes'
import { BrandMark } from '@/components/brand-mark'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip'
import { BRAND_WORDMARK } from '@/lib/brand'
import { cn } from '@/lib/utils'
import { $activeNavSection, $sidebarCollapsed, NAV_GROUP_META, NAV_SECTIONS, type NavSection, type NavSectionId, setActiveNavSection, toggleSidebarCollapsed } from '@/store/navigation'

/** Map the current route to its sidebar section so the active highlight
 *  follows real navigation (deep links, refresh, back/forward) instead of
 *  only the last clicked item. Session routes (/:sessionId) belong to Chat. */
export function navIdForPathname(pathname: string): NavSectionId | null {
  const all: NavSection[] = []

  for (const s of NAV_SECTIONS) {
    all.push(s)

    if (s.children) {
      all.push(...s.children)
    }
  }

  const exact = all.find(s => s.route === pathname)

  if (exact) {
    return exact.id
  }

  const view = appViewForPath(pathname)

  // Fall through to the view table for non-nav routes (e.g. overlays).
  // Views with no sidebar entry resolve to null so the previous highlight
  // persists instead of pointing at the wrong section.
  const VIEW_TO_NAV: Partial<Record<ReturnType<typeof appViewForPath>, NavSectionId>> = {
    chat: 'chat',
    home: 'home',
    'jarvis-mode': 'jarvis-mode',
    projects: 'projects',
    agents: 'agents',
    models: 'models',
    memory: 'memory',
    knowledge: 'knowledge',
    files: 'files',
    browser: 'browser',
    automation: 'automation',
    tasks: 'tasks',
    communications: 'communications',
    history: 'history',
    'task-orchestrator': 'task-orchestrator',
    extensions: 'extensions',
    'mcp-manager': 'mcp',
    'security-center': 'security',
    services: 'services',
    diagnostics: 'diagnostics',
    settings: 'settings'
  }

  return VIEW_TO_NAV[view] ?? null
}

export function LeftSidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const storedSection = useStore($activeNavSection)
  const collapsed = useStore($sidebarCollapsed)
  const [moreOpen, setMoreOpen] = useState(false)

  // Active highlight follows the real route (refresh, deep link, back/forward),
  // not just the last clicked item. Clicks still persist the atom for
  // non-nav views (overlays) that have no sidebar entry.
  const routedSection = navIdForPathname(location.pathname)
  const activeSection = routedSection ?? storedSection

  useEffect(() => {
    if (routedSection && routedSection !== storedSection) {
      setActiveNavSection(routedSection)
    }
  }, [routedSection, storedSection])

  const handleNavigate = (section: NavSection) => {
    setActiveNavSection(section.id)
    navigate(section.route)
  }

  const primaryGroups = NAV_GROUP_META.filter(g => g.id !== 'more')
  const moreGroup = NAV_GROUP_META.find(g => g.id === 'more')
  const moreSections = NAV_SECTIONS.filter(s => s.group === 'more')

  // Build flat list of all navigable sections (including children) for keyboard navigation
  const allNavItems: Array<{ section: NavSection; group: string }> = []
  primaryGroups.forEach(group => {
    const entries = NAV_SECTIONS.filter(s => s.group === group.id)
    entries.forEach(section => {
      allNavItems.push({ section, group: group.id })
      section.children?.forEach(child => allNavItems.push({ section: child, group: group.id }))
    })
  })
  if (moreGroup && moreSections.length > 0 && !collapsed) {
    moreSections.forEach(section => {
      allNavItems.push({ section, group: 'more' })
      section.children?.forEach(child => allNavItems.push({ section: child, group: 'more' }))
    })
  }

  const handleKeyDown = (e: React.KeyboardEvent, currentIndex: number) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      const nextIndex = (currentIndex + 1) % allNavItems.length
      allNavItems[nextIndex]?.section && setActiveNavSection(allNavItems[nextIndex].section.id)
      // Focus the next button
      const nextButton = document.querySelector(`[data-nav-index="${nextIndex}"]`) as HTMLElement
      nextButton?.focus()
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      const prevIndex = (currentIndex - 1 + allNavItems.length) % allNavItems.length
      allNavItems[prevIndex]?.section && setActiveNavSection(allNavItems[prevIndex].section.id)
      const prevButton = document.querySelector(`[data-nav-index="${prevIndex}"]`) as HTMLElement
      prevButton?.focus()
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      allNavItems[currentIndex]?.section && handleNavigate(allNavItems[currentIndex].section)
    } else if (e.key === 'Escape' && collapsed) {
      // Allow escape to potentially expand sidebar (handled by parent)
    }
  }

  return (
    <nav
      aria-label="Primary navigation"
      className={cn(
        'flex flex-col border-r border-(--ui-stroke-tertiary) bg-(--ui-sidebar-surface-background) transition-all duration-200 ease-out',
        collapsed ? 'w-12' : 'w-56'
      )}
    >
      <div className={cn('flex h-10 items-center border-b border-(--ui-stroke-tertiary) px-2', collapsed && 'justify-center')}>
        {!collapsed ? (
          <span className="flex min-w-0 items-center gap-2">
            <BrandMark className="size-6 shrink-0 rounded-[6px]" />
            <span className="truncate text-xs font-semibold tracking-wide text-foreground">{BRAND_WORDMARK}</span>
          </span>
        ) : (
          <BrandMark className="size-6 shrink-0 rounded-[6px]" />
        )}
        <Button
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className={cn('ml-auto size-6', collapsed && 'ml-0')}
          onClick={toggleSidebarCollapsed}
          size="icon-sm"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          variant="ghost"
        >
          <Codicon name={collapsed ? 'chevron-right' : 'chevron-left'} size="0.875rem" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-3 p-1">
          {primaryGroups.map(group => {
            const entries = NAV_SECTIONS.filter(s => s.group === group.id)

            if (entries.length === 0) {
              return null
            }

            return (
              <section aria-label={group.label} key={group.id}>
                {!collapsed && (
                  <h2 className="px-2 pb-1 text-[0.625rem] font-semibold uppercase tracking-widest text-(--ui-text-tertiary)">
                    {group.label}
                  </h2>
                )}
                <div className="space-y-0.5" role="list">
                  {entries.map((section, sectionIndex) => {
                    const itemIndex = allNavItems.findIndex(item => item.section.id === section.id && item.group === group.id)
                    return (
                      <SidebarNavItem
                        active={activeSection === section.id}
                        collapsed={collapsed}
                        key={section.id}
                        onNavigate={handleNavigate}
                        section={section}
                        index={itemIndex}
                        totalItems={allNavItems.length}
                        onKeyDown={handleKeyDown}
                      />
                    )
                  })}
                </div>
              </section>
            )
          })}

          {/* More section — collapsible progressive disclosure */}
          {moreGroup && moreSections.length > 0 && !collapsed && (
            <section aria-label={moreGroup.label} key="more">
              <div className="space-y-0.5">
                <button
                  className={cn(
                    'relative flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-(--dt-ring)',
                    'text-(--ui-text-tertiary) hover:bg-(--ui-control-hover-background) hover:text-foreground justify-between'
                  )}
                  onClick={() => setMoreOpen(!moreOpen)}
                  type="button"
                  aria-expanded={moreOpen}
                >
                  <span aria-hidden className="codicon codicon-ellipsis text-(--ui-text-tertiary)" />
                  <span className="flex-1 truncate font-medium">{moreGroup.label}</span>
                  <Codicon
                    className={cn('shrink-0 transition-transform', moreOpen && 'rotate-90')}
                    name="chevron-right"
                    size="0.75rem"
                  />
                </button>
                {moreOpen && (
                  <div className="ml-4 space-y-0.5 border-l border-(--ui-stroke-tertiary) pl-1">
                    {moreSections.map((section, sectionIndex) => {
                      const itemIndex = allNavItems.findIndex(item => item.section.id === section.id && item.group === 'more')
                      return (
                        <SidebarNavItem
                          active={activeSection === section.id}
                          collapsed={false}
                          key={section.id}
                          onNavigate={handleNavigate}
                          section={section}
                          index={itemIndex}
                          totalItems={allNavItems.length}
                          onKeyDown={handleKeyDown}
                        />
                      )
                    })}
                  </div>
                )}
              </div>
            </section>
          )}
        </div>
      </ScrollArea>
    </nav>
  )
}

function SidebarNavItem({
  section,
  active,
  collapsed,
  onNavigate,
  index,
  totalItems,
  onKeyDown
}: {
  section: NavSection
  active: boolean
  collapsed: boolean
  onNavigate: (section: NavSection) => void
  index: number
  totalItems: number
  onKeyDown: (e: React.KeyboardEvent, idx: number) => void
}) {
  const buttonRef = useRef<HTMLButtonElement>(null)

  return (
    <div role="listitem">
      {collapsed ? (
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                ref={buttonRef}
                data-nav-index={index}
                aria-current={active ? 'page' : undefined}
                aria-label={section.label}
                className={cn(
                  'relative flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-(--dt-ring)',
                  active
                    ? 'bg-(--ui-control-hover-background) font-medium text-foreground justify-center px-0'
                    : 'text-(--ui-text-tertiary) hover:bg-(--ui-control-hover-background) hover:text-foreground justify-center px-0'
                )}
                onClick={() => onNavigate(section)}
                onKeyDown={(e) => onKeyDown(e, index)}
                type="button"
              >
                <span
                  aria-hidden
                  className={cn(
                    'absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-(--dt-ring) transition-opacity',
                    active ? 'opacity-100' : 'opacity-0'
                  )}
                />
                <Codicon className="shrink-0" name={section.icon as any} size="1rem" />
              </button>
            </TooltipTrigger>
            <TooltipContent align="center" side="right" sideOffset={8}>
              <span className="text-sm font-medium">{section.label}</span>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      ) : (
        <button
          ref={buttonRef}
          data-nav-index={index}
          aria-current={active ? 'page' : undefined}
          className={cn(
            'relative flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-(--dt-ring)',
            active
              ? 'bg-(--ui-control-hover-background) font-medium text-foreground'
              : 'text-(--ui-text-tertiary) hover:bg-(--ui-control-hover-background) hover:text-foreground'
          )}
          onClick={() => onNavigate(section)}
          onKeyDown={(e) => onKeyDown(e, index)}
          type="button"
        >
          <span
            aria-hidden
            className={cn(
              'absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-(--dt-ring) transition-opacity',
              active ? 'opacity-100' : 'opacity-0'
            )}
          />
          <Codicon className="shrink-0" name={section.icon as any} size="1rem" />
          <span className="flex-1 truncate">{section.label}</span>
          {section.badge !== undefined && section.badge > 0 && (
            <span className="flex size-4 items-center justify-center rounded-full bg-primary text-[0.625rem] font-semibold text-primary-foreground">
              {section.badge}
            </span>
          )}
        </button>
      )}
      {!collapsed && section.children && (
        <div className="ml-4 space-y-0.5 border-l border-(--ui-stroke-tertiary) pl-1">
          {section.children.map(child => (
            <button
              className="flex w-full items-center gap-2 rounded-md px-2 py-1 text-left text-xs text-(--ui-text-tertiary) transition-colors hover:bg-(--ui-control-hover-background) hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-(--dt-ring)"
              key={child.id}
              onClick={() => onNavigate(child)}
              type="button"
            >
              <Codicon className="shrink-0" name={child.icon as any} size="0.75rem" />
              <span className="truncate">{child.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

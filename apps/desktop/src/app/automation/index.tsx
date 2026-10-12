import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import {
  $automation,
  autoLayout,
  type AutomationState,
  copySelection,
  createWorkflow,
  deleteSelection,
  deleteWorkflow,
  duplicateWorkflow,
  pasteClipboard,
  redo,
  resetCanvas,
  selectAll,
  setActiveTab,
  setActiveWorkflow,
  setShowMiniMap,
  setSnapToGrid,
  toggleWorkflowEnabled,
  undo,
} from '@/store/automation'

import { WorkflowCanvas } from './canvas/workflow-canvas'
import { ActionConfigModal } from './nodes/action-config'
import { ConditionConfigModal } from './nodes/condition-config'
import { TriggerConfigModal } from './nodes/trigger-config'
import { NodePalette } from './panels/node-palette'
import { SecretsPanel } from './panels/secrets-panel'
import { VariablesPanel } from './panels/variables-panel'
import { WorkflowHistory } from './panels/workflow-history'
import { WorkflowScheduler } from './panels/workflow-scheduler'
import { MarketplaceView } from './templates/marketplace-view'
import { TemplatesGallery } from './templates/templates-gallery'

type TabId = AutomationState['activeTab']

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'editor', label: 'Editor', icon: 'type-hierarchy' },
  { id: 'scheduler', label: 'Schedule', icon: 'calendar' },
  { id: 'history', label: 'History', icon: 'history' },
  { id: 'templates', label: 'Templates', icon: 'library' },
  { id: 'secrets', label: 'Secrets', icon: 'lock' },
  { id: 'marketplace', label: 'Marketplace', icon: 'package' },
]

export function AutomationView() {
  const state = useStore($automation)
  const activeWorkflow = state.workflows.find(w => w.id === state.activeWorkflowId)
  const [workflowName, setWorkflowName] = useState('')
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null)

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'z' && !e.shiftKey) { e.preventDefault(); undo() }

    if ((e.metaKey || e.ctrlKey) && e.key === 'z' && e.shiftKey) { e.preventDefault(); redo() }

    if ((e.metaKey || e.ctrlKey) && e.key === 'a') { e.preventDefault(); selectAll() }

    if ((e.metaKey || e.ctrlKey) && e.key === 'c') { e.preventDefault(); copySelection() }

    if ((e.metaKey || e.ctrlKey) && e.key === 'v') { e.preventDefault(); pasteClipboard() }

    if (e.key === 'Delete' || e.key === 'Backspace') { deleteSelection() }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-background" onKeyDown={handleKeyDown} tabIndex={0}>
      <header className="flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold tracking-tight">Automation</h1>
          <Separator className="h-5" orientation="vertical" />
          <div className="flex items-center gap-1">
            {TABS.map(tab => (
              <button
                className={cn(
                  'flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
                  state.activeTab === tab.id
                    ? 'bg-(--ui-control-hover-background) text-foreground'
                    : 'text-(--ui-text-tertiary) hover:text-foreground'
                )}
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                type="button"
              >
                <Codicon name={tab.icon as any} size="0.875rem" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {state.activeTab === 'editor' && activeWorkflow && (
            <>
              <button
                className={cn('rounded p-1 text-(--ui-text-tertiary) hover:text-foreground', state.snapToGrid && 'text-foreground')}
                onClick={() => setSnapToGrid(!state.snapToGrid)}
                title="Toggle Snap to Grid"
                type="button"
              >
                <Codicon name="grid" size="0.875rem" />
              </button>
              <button
                className={cn('rounded p-1 text-(--ui-text-tertiary) hover:text-foreground', state.showMiniMap && 'text-foreground')}
                onClick={() => setShowMiniMap(!state.showMiniMap)}
                title="Toggle Mini Map"
                type="button"
              >
                <Codicon name="map" size="0.875rem" />
              </button>
              <button className="rounded p-1 text-(--ui-text-tertiary) hover:text-foreground" onClick={autoLayout} title="Auto Layout" type="button">
                <Codicon name="layout" size="0.875rem" />
              </button>
              <button className="rounded p-1 text-(--ui-text-tertiary) hover:text-foreground" onClick={resetCanvas} title="Reset View" type="button">
                <Codicon name="screen-normal" size="0.875rem" />
              </button>
              <Separator className="h-5" orientation="vertical" />
              <button className="rounded p-1 text-(--ui-text-tertiary) hover:text-foreground" onClick={undo} title="Undo" type="button">
                <Codicon name="undo" size="0.875rem" />
              </button>
              <button className="rounded p-1 text-(--ui-text-tertiary) hover:text-foreground" onClick={redo} title="Redo" type="button">
                <Codicon name="redo" size="0.875rem" />
              </button>
            </>
          )}
        </div>
      </header>

      <div className="flex items-center gap-2 border-b border-(--ui-stroke-tertiary) px-4 py-1.5">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Codicon className="text-(--ui-text-tertiary)" name="run-all" size="1rem" />
          <select
            className="max-w-[240px] truncate rounded border-0 bg-transparent text-sm font-medium text-foreground focus:outline-none focus:ring-0"
            onChange={e => setActiveWorkflow(e.target.value || null)}
            value={state.activeWorkflowId ?? ''}
          >
            {state.workflows.map(w => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
          {activeWorkflow && (
            <span className={cn(
              'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium',
              activeWorkflow.enabled
                ? 'bg-green-500/10 text-green-400'
                : 'bg-(--ui-stroke-tertiary) text-(--ui-text-tertiary)'
            )}>
              {activeWorkflow.enabled ? 'Active' : 'Disabled'}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            className="flex items-center gap-1 rounded-md bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground hover:opacity-90"
            onClick={() => setShowCreateDialog(true)}
            type="button"
          >
            <Codicon name="add" size="0.875rem" />
            New
          </button>
          {activeWorkflow && (
            <>
              <button
                className={cn(
                  'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
                  activeWorkflow.enabled
                    ? 'bg-destructive/10 text-destructive hover:bg-destructive/20'
                    : 'bg-primary/10 text-primary hover:bg-primary/20'
                )}
                onClick={() => toggleWorkflowEnabled(activeWorkflow.id)}
                type="button"
              >
                {activeWorkflow.enabled ? 'Disable' : 'Enable'}
              </button>
              <button
                className="rounded-md px-2 py-1 text-xs text-(--ui-text-tertiary) hover:text-foreground"
                onClick={() => { const d = duplicateWorkflow(activeWorkflow.id);

 if (d) {setActiveWorkflow(d.id)} }}
                type="button"
              >
                <Codicon name="copy" size="0.875rem" />
              </button>
              <button
                className="rounded-md px-2 py-1 text-xs text-(--ui-text-tertiary) hover:text-destructive"
                onClick={() => setShowDeleteConfirm(activeWorkflow.id)}
                type="button"
              >
                <Codicon name="trash" size="0.875rem" />
              </button>
            </>
          )}
        </div>
      </div>

      {state.activeTab === 'editor' && (
        <div className="flex flex-1 overflow-hidden">
          {state.showNodePalette && <NodePalette />}
          <div className="relative flex-1 overflow-hidden">
            {activeWorkflow ? (
              <WorkflowCanvas />
            ) : (
              <div className="flex h-full items-center justify-center">
                <div className="text-center">
                  <Codicon className="mx-auto mb-3 text-(--ui-text-tertiary)" name="run-all" size="2rem" />
                  <p className="text-sm text-(--ui-text-tertiary)">No workflow selected</p>
                  <button
                    className="mt-3 rounded-md bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90"
                    onClick={() => setShowCreateDialog(true)}
                    type="button"
                  >
                    Create Workflow
                  </button>
                </div>
              </div>
            )}
          </div>
          {state.showVariablesPanel && <VariablesPanel />}
          {state.showSecretsPanel && <SecretsPanel />}
        </div>
      )}

      {state.activeTab === 'scheduler' && <WorkflowScheduler />}
      {state.activeTab === 'history' && <WorkflowHistory />}
      {state.activeTab === 'templates' && <TemplatesGallery />}
      {state.activeTab === 'secrets' && <SecretsPanel />}
      {state.activeTab === 'marketplace' && <MarketplaceView />}

      {state.editingNodeId && activeWorkflow && (
        <>
          {activeWorkflow.nodes.find(n => n.id === state.editingNodeId)?.type === 'trigger' && (
            <TriggerConfigModal nodeId={state.editingNodeId} />
          )}
          {activeWorkflow.nodes.find(n => n.id === state.editingNodeId)?.type === 'action' && (
            <ActionConfigModal nodeId={state.editingNodeId} />
          )}
          {activeWorkflow.nodes.find(n => n.id === state.editingNodeId)?.type === 'condition' && (
            <ConditionConfigModal nodeId={state.editingNodeId} />
          )}
        </>
      )}

      {showCreateDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowCreateDialog(false)}>
          <div className="w-96 rounded-xl border bg-background p-6 shadow-xl" onClick={e => e.stopPropagation()}>
            <h2 className="mb-4 text-base font-semibold">Create Workflow</h2>
            <input
              autoFocus
              className="mb-4 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-2 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary"
              onChange={e => setWorkflowName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && workflowName.trim()) { const w = createWorkflow(workflowName.trim()); setWorkflowName(''); setShowCreateDialog(false); setActiveWorkflow(w.id) } }}
              placeholder="Enter workflow name..."
              type="text"
              value={workflowName}
            />
            <div className="flex justify-end gap-2">
              <Button onClick={() => { setShowCreateDialog(false); setWorkflowName('') }} size="sm" variant="ghost">Cancel</Button>
              <Button onClick={() => { if (workflowName.trim()) { const w = createWorkflow(workflowName.trim()); setWorkflowName(''); setShowCreateDialog(false); setActiveWorkflow(w.id) } }} size="sm">Create</Button>
            </div>
          </div>
        </div>
      )}

      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowDeleteConfirm(null)}>
          <div className="w-80 rounded-xl border bg-background p-6 shadow-xl" onClick={e => e.stopPropagation()}>
            <h2 className="mb-2 text-base font-semibold">Delete Workflow?</h2>
            <p className="mb-4 text-sm text-(--ui-text-tertiary)">This action cannot be undone.</p>
            <div className="flex justify-end gap-2">
              <Button onClick={() => setShowDeleteConfirm(null)} size="sm" variant="ghost">Cancel</Button>
              <Button onClick={() => { deleteWorkflow(showDeleteConfirm); setShowDeleteConfirm(null) }} size="sm" variant="destructive">Delete</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

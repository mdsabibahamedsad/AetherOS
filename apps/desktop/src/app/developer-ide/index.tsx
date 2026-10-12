import { useStore } from '@nanostores/react'

import { $ide, setIDEMode, toggleBottomPanel, togglePanel, toggleRightPanel, toggleSidebar } from '../../store/developer-ide'

import { AIAssistant } from './ai-assistant'
import { BuildPanel } from './build-panel'
import { ChangePreview } from './change-preview'
import { CodeEditor } from './code-editor'
import { CodeSearch } from './code-search'
import { DebugPanel } from './debug-panel'
import { GitPanel } from './git-panel'
import { OutputPanel } from './output-panel'
import { ProblemsPanel } from './problems-panel'
import { ProjectExplorer } from './project-explorer'
import { TerminalPanel } from './terminal-panel'
import { TestPanel } from './test-panel'

const modes = [
  { id: 'code' as const, label: 'Code', icon: 'code' },
  { id: 'diff' as const, label: 'Diff', icon: 'diff' },
  { id: 'review' as const, label: 'Review', icon: 'check' },
  { id: 'debug' as const, label: 'Debug', icon: 'bug' },
  { id: 'build' as const, label: 'Build', icon: 'gear' },
  { id: 'test' as const, label: 'Tests', icon: 'beaker' },
  { id: 'git' as const, label: 'Git', icon: 'git-branch' },
]

export function DeveloperIDE() {
  const ide = useStore($ide)

  const activeLeftPanel = ide.panels.find(p => p.visible && p.position === 'left')
  const activeRightPanel = ide.panels.find(p => p.visible && p.position === 'right')

  return (
    <div className="flex flex-col h-full bg-surface text-foreground">
      <div className="flex items-center justify-between px-3 py-1 bg-surface-secondary border-b border-border">
        <div className="flex items-center gap-1">
          <button className="p-1 hover:bg-surface-hover rounded" onClick={() => toggleSidebar()} title="Toggle Sidebar">
            <span className="codicon codicon-menu" />
          </button>
          {modes.map(m => (
            <button
              className={`px-2 py-0.5 text-xs rounded flex items-center gap-1 ${ide.mode === m.id ? 'bg-accent text-white' : 'hover:bg-surface-hover'}`}
              key={m.id}
              onClick={() => setIDEMode(m.id)}
            >
              <span className={`codicon codicon-${m.icon}`} />
              {m.label}
            </button>
          ))}
        </div>
        <div className="text-xs text-foreground-secondary font-mono">
          {ide.activeProjectId ? `${ide.activeProjectId} — ${ide.activeFilePath || 'no file'}` : 'No project open'}
        </div>
        <div className="flex items-center gap-1">
          <button className="p-1 hover:bg-surface-hover rounded" onClick={() => toggleRightPanel()} title="Toggle AI Assistant">
            <span className="codicon codicon-comment-discussion" />
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {ide.sidebarVisible && (
          <div className="w-60 border-r border-border bg-surface-secondary flex flex-col">
            <div className="flex border-b border-border">
              {ide.panels.filter(p => p.position === 'left').map(p => (
                <button
                  className={`flex-1 px-2 py-1.5 text-xs text-center ${p.visible ? 'bg-surface text-foreground border-b-2 border-accent' : 'text-foreground-secondary hover:bg-surface-hover'}`}
                  key={p.id}
                  onClick={() => togglePanel(p.id)}
                >
                  {p.label}
                </button>
              ))}
            </div>
            <div className="flex-1 overflow-auto">
              {activeLeftPanel?.id === 'explorer' && <ProjectExplorer />}
              {activeLeftPanel?.id === 'search' && <CodeSearch />}
              {activeLeftPanel?.id === 'git' && <GitPanel />}
              {activeLeftPanel?.id === 'debug' && <DebugPanel />}
            </div>
          </div>
        )}

        <div className="flex-1 flex flex-col overflow-hidden">
          {ide.mode === 'diff' ? <ChangePreview /> : <CodeEditor />}

          {ide.bottomPanelVisible && (
            <div className="border-t border-border bg-surface-secondary" style={{ height: 200 }}>
              <div className="flex border-b border-border">
                {ide.panels.filter(p => p.position === 'bottom').map(p => (
                  <button
                    className={`px-3 py-1 text-xs ${p.visible ? 'bg-surface text-foreground border-b-2 border-accent' : 'text-foreground-secondary hover:bg-surface-hover'}`}
                    key={p.id}
                    onClick={() => togglePanel(p.id)}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              <div className="overflow-auto h-full">
                {ide.panels.find(p => p.id === 'problems' && p.visible) && <ProblemsPanel />}
                {ide.panels.find(p => p.id === 'output' && p.visible) && <OutputPanel />}
                {ide.panels.find(p => p.id === 'terminal' && p.visible) && <TerminalPanel />}
                {ide.panels.find(p => p.id === 'build' && p.visible) && <BuildPanel />}
                {ide.panels.find(p => p.id === 'test' && p.visible) && <TestPanel />}
              </div>
            </div>
          )}

          {!ide.bottomPanelVisible && (
            <div className="flex border-t border-border bg-surface-muted px-2 py-0.5 text-xs text-foreground-secondary">
              <span className="cursor-pointer hover:text-foreground" onClick={() => toggleBottomPanel()}>Problems</span>
              <span className="mx-1">|</span>
              <span className="cursor-pointer hover:text-foreground" onClick={() => toggleBottomPanel()}>Output</span>
              <span className="mx-1">|</span>
              <span className="cursor-pointer hover:text-foreground" onClick={() => toggleBottomPanel()}>Terminal</span>
              <div className="ml-auto flex gap-2">
                <span className="cursor-pointer hover:text-foreground">{ide.mode === 'code' ? 'Ln 1, Col 1' : ''}</span>
                <span className="cursor-pointer hover:text-foreground">UTF-8</span>
                <span className="cursor-pointer hover:text-foreground">{ide.editorTabSize ? `Spaces: ${ide.editorTabSize}` : ''}</span>
              </div>
            </div>
          )}
        </div>

        {ide.rightPanelVisible && activeRightPanel?.id === 'ai-assistant' && (
          <div className="w-80 border-l border-border bg-surface-secondary flex flex-col">
            <div className="px-3 py-2 border-b border-border font-medium text-xs flex items-center gap-2">
              <span className="codicon codicon-comment-discussion" />
              AI Assistant
              <button className="ml-auto p-0.5 hover:bg-surface-hover rounded" onClick={() => toggleRightPanel()}>
                <span className="codicon codicon-close" />
              </button>
            </div>
            <AIAssistant />
          </div>
        )}
      </div>
    </div>
  )
}

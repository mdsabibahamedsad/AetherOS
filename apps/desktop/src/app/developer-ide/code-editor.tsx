import { useStore } from '@nanostores/react'
import { useEffect, useState } from 'react'

import { $codeEditor, clearSearch, closeEditorTab, setActiveTab, toggleSplitView } from '../../store/code-editor'
import { closeFile } from '../../store/developer-ide'
import { $projectWorkspace } from '../../store/project-workspace'

const languageMap: Record<string, string> = {
  py: 'python', ts: 'typescript', tsx: 'typescriptreact', js: 'javascript', jsx: 'javascriptreact',
  rs: 'rust', go: 'go', java: 'java', c: 'c', cpp: 'cpp', h: 'c', hpp: 'cpp',
  html: 'html', css: 'css', json: 'json', yaml: 'yaml', yml: 'yaml', md: 'markdown',
  sh: 'shell', bash: 'shell', toml: 'ini', txt: 'plaintext',
}

export function CodeEditor() {
  const editor = useStore($codeEditor)
  const ws = useStore($projectWorkspace)

  if (editor.tabs.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center bg-surface text-foreground-secondary">
        <div className="text-center">
          <span className="codicon codicon-code text-4xl block mb-2" />
          <p className="text-sm">Select a file from the explorer to start editing</p>
          {ws.currentProject && (
            <p className="text-xs mt-1">{ws.currentProject.path}</p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col bg-surface overflow-hidden">
      <div className="flex border-b border-border bg-surface-secondary overflow-x-auto">
        {editor.tabs.map(tab => (
          <div
            className={`flex items-center gap-1 px-3 py-1.5 text-xs cursor-pointer border-r border-border min-w-0
              ${tab.filePath === editor.activeTabPath ? 'bg-surface text-foreground border-t-2 border-t-accent' : 'text-foreground-secondary hover:bg-surface-hover'}
              ${tab.isModified ? 'border-t-2 border-t-yellow-500' : ''}`}
            key={tab.filePath}
            onClick={() => { setActiveTab(tab.filePath); closeFile(tab.filePath); closeEditorTab(tab.filePath) }}
            style={{ borderTopWidth: tab.filePath === editor.activeTabPath ? 2 : 0 }}
          >
            <span className={`codicon codicon-${tab.filePath === editor.activeTabPath ? 'circle-filled' : 'circle-outline'} text-2xs ${tab.isModified ? 'text-yellow-500' : ''}`} />
            <span className="truncate max-w-32">{tab.fileName}</span>
            <button
              className="ml-1 p-0.5 hover:bg-surface-hover rounded opacity-60 hover:opacity-100"
              onClick={e => { e.stopPropagation(); closeFile(tab.filePath); closeEditorTab(tab.filePath) }}
            >
              <span className="codicon codicon-close text-2xs" />
            </button>
          </div>
        ))}
        <div className="flex-1" />
        <button className="px-2 hover:bg-surface-hover text-foreground-secondary" onClick={() => toggleSplitView()} title="Split View">
          <span className="codicon codicon-split-horizontal text-xs" />
        </button>
        <button className="px-2 hover:bg-surface-hover text-foreground-secondary" onClick={() => { clearSearch() }} title="Search">
          <span className="codicon codicon-search text-xs" />
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {editor.tabs.filter(t => t.filePath === editor.activeTabPath).map(tab => (
          <EditorContent key={tab.filePath} tab={tab} />
        ))}
        {editor.splitView && editor.tabs.filter(t => t.filePath !== editor.activeTabPath).slice(0, 1).map(tab => (
          <EditorContent key={tab.filePath + '-split'} tab={tab} />
        ))}
      </div>
    </div>
  )
}

function EditorContent({ tab }: { tab: any }) {
  const [content, setContent] = useState('')
  const ws = useStore($projectWorkspace)

  useEffect(() => {
    if (!ws.currentProject) {return}
    const fullPath = ws.currentProject.path + '/' + tab.filePath
    fetch('/api/read-file?path=' + encodeURIComponent(fullPath))
      .then(r => r.text())
      .then(setContent)
      .catch(() => setContent('// Unable to load file content'))
  }, [tab.filePath, ws.currentProject])

  const lines = content.split('\n')

  return (
    <div className="flex-1 overflow-auto font-mono text-xs">
      <table className="w-full border-collapse">
        <tbody>
          {lines.map((line, i) => (
            <tr className="hover:bg-surface-hover/30" key={i}>
              <td className="select-none text-right px-3 text-foreground-secondary w-12 border-r border-border align-top">
                {i + 1}
              </td>
              <td className="px-3 py-0 whitespace-pre-wrap break-all">
                {line || ' '}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

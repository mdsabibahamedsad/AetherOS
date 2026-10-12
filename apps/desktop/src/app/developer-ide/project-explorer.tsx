import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { openFile } from '../../store/developer-ide'
import { $projectWorkspace, setSelectedFile, toggleFolder } from '../../store/project-workspace'

const fileIconMap: Record<string, string> = {
  tsx: 'symbol-event', ts: 'symbol-class', js: 'symbol-variable', jsx: 'symbol-event',
  py: 'symbol-misc', rs: 'symbol-structure', go: 'symbol-namespace',
  json: 'symbol-key', md: 'symbol-text', css: 'symbol-color', html: 'symbol-numeric',
  yaml: 'symbol-string', yml: 'symbol-string', toml: 'symbol-parameter',
}

function getFileIcon(name: string, isDir: boolean): string {
  if (isDir) {return 'folder'}
  const ext = name.split('.').pop() || ''

  return fileIconMap[ext] || 'symbol-file'
}

export function ProjectExplorer() {
  const ws = useStore($projectWorkspace)
  const [search, setSearch] = useState('')

  return (
    <div className="flex flex-col h-full text-xs">
      <div className="p-2">
        <div className="relative">
          <span className="codicon codicon-search absolute left-2 top-1/2 -translate-y-1/2 text-foreground-secondary text-xs" />
          <input
            className="w-full pl-7 pr-2 py-1 text-xs bg-surface border border-border rounded placeholder-foreground-secondary outline-none focus:border-accent"
            onChange={e => setSearch(e.target.value)}
            placeholder="Search files..."
            value={search}
          />
        </div>
      </div>
      <div className="flex-1 overflow-auto px-1">
        {(ws.fileTree.length === 0 && !ws.fileTreeLoading) ? (
          <div className="p-4 text-center text-foreground-secondary">
            <p className="codicon codicon-folder-opened text-2xl mb-2" />
            <p>No project open</p>
            <p className="mt-1">Open or create a project to get started</p>
          </div>
        ) : ws.fileTreeLoading ? (
          <div className="p-4 text-center text-foreground-secondary">Loading...</div>
        ) : (
          ws.fileTree.map((file) => (
            <FileTreeItem
              depth={0}
              expandedFolders={ws.expandedFolders}
              item={file}
              key={file.path}
              onSelect={() => {
                setSelectedFile(file.path)

                if (!file.isDirectory) {
                  openFile(file.path)
                } else {
                  toggleFolder(file.path)
                }
              }}
              onToggle={() => toggleFolder(file.path)}
              search={search}
            />
          ))
        )}
      </div>
      {ws.currentProject && (
        <div className="p-2 border-t border-border text-foreground-secondary">
          <div className="flex items-center gap-1">
            <span className="codicon codicon-folder" />
            <span className="truncate flex-1">{ws.currentProject.name}</span>
            <span className="text-2xs">{ws.fileTree.length} files</span>
          </div>
        </div>
      )}
    </div>
  )
}

interface FileTreeItemProps {
  item: { path: string; name: string; isDirectory: boolean; children?: any[] }
  depth: number
  search: string
  expandedFolders: string[]
  onToggle: () => void
  onSelect: () => void
}

function FileTreeItem({ item, depth, search, expandedFolders, onToggle, onSelect }: FileTreeItemProps) {
  const isExpanded = expandedFolders.includes(item.path)
  const matchesSearch = !search || item.name.toLowerCase().includes(search.toLowerCase())

  if (search && !matchesSearch) {return null}

  return (
    <div>
      <div
        className="flex items-center gap-1 px-2 py-0.5 cursor-pointer hover:bg-surface-hover rounded-sm"
        onClick={onSelect}
        style={{ paddingLeft: `${8 + depth * 16}px` }}
      >
        {item.isDirectory && (
          <span className={`codicon codicon-chevron-${isExpanded ? 'down' : 'right'} text-foreground-secondary text-2xs`} />
        )}
        <span className={`codicon codicon-${getFileIcon(item.name, item.isDirectory)} text-foreground-secondary`} />
        <span className="truncate">{item.name}</span>
      </div>
      {item.isDirectory && isExpanded && item.children?.map((child: any) => (
        <FileTreeItem
          depth={depth + 1}
          expandedFolders={expandedFolders}
          item={child}
          key={child.path}
          onSelect={() => {
            if (!child.isDirectory) {openFile(child.path)}
            else {toggleFolder(child.path)}
          }}
          onToggle={() => {}}
          search={search}
        />
      ))}
    </div>
  )
}

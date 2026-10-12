/**
 * Jarvis files panel — REAL workspace listing via the read-only fs IPC.
 *
 * Directories expand through `aetheros:fs:readDir`; files preview the first
 * kilobytes through `readFileText`. There are no write/delete controls here
 * by design — mutations go through the Jarvis composer (gateway agent +
 * approvals) so every change is planned, approved and logged.
 */

import { useStore } from '@nanostores/react'
import { memo, useCallback, useEffect, useState } from 'react'

import { Codicon } from '@/components/ui/codicon'
import { readDesktopDir, readDesktopFileText } from '@/lib/desktop-fs'
import { $currentCwd } from '@/store/session'

interface Node {
  path: string
  name: string
  isDirectory: boolean
  children: Node[] | null
  error?: string
}

function FileTreeNode({ node, depth, onPreview }: { node: Node; depth: number; onPreview: (path: string) => void }) {
  const [expanded, setExpanded] = useState(depth < 1)
  const [children, setChildren] = useState<Node[] | null>(node.children)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(node.error ?? null)

  const toggle = useCallback(async () => {
    if (!node.isDirectory) {
      onPreview(node.path)

      return
    }

    const next = !expanded
    setExpanded(next)

    if (next && children === null && !loading) {
      setLoading(true)
      setError(null)

      try {
        const res = await readDesktopDir(node.path)

        if (res.error) {
          setError(res.error)
        } else {
          const nodes: Node[] = (res.entries ?? [])
            .slice()
            .sort((a, b) => Number(b.isDirectory) - Number(a.isDirectory) || a.name.localeCompare(b.name))
            .map(e => ({ path: e.path, name: e.name, isDirectory: e.isDirectory, children: null }))

          setChildren(nodes)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Could not list this folder.')
      } finally {
        setLoading(false)
      }
    }
  }, [node, expanded, children, loading, onPreview])

  return (
    <div>
      <button
        className="flex items-center gap-1.5 w-full px-2 py-1 rounded-md hover:bg-white/[0.04] transition-colors group"
        onClick={() => void toggle()}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {node.isDirectory ? (
          <Codicon className="size-3 text-white/20" name={expanded ? 'chevron-down' : 'chevron-right'} />
        ) : (
          <span className="w-3" />
        )}
        <Codicon
          className={`size-4 ${node.isDirectory ? 'text-[#00d4ff]' : 'text-white/30'}`}
          name={node.isDirectory ? 'folder' : 'file'}
        />
        <span className="text-[12px] text-white/60 truncate group-hover:text-white/80 transition-colors">
          {node.name}
        </span>
        {loading && <span className="codicon codicon-loading animate-spin text-[11px] text-white/20" />}
      </button>
      {node.isDirectory && expanded && (
        <div>
          {error && <div className="text-[11px] text-red-400/70 pl-8 py-0.5">{error}</div>}
          {children?.map(child => (
            <FileTreeNode depth={depth + 1} key={child.path} node={child} onPreview={onPreview} />
          ))}
          {children?.length === 0 && <div className="text-[11px] text-white/20 pl-8 py-0.5">Empty folder</div>}
        </div>
      )}
    </div>
  )
}

function FilesViewComponent() {
  const workspaceCwd = useStore($currentCwd)
  const [roots, setRoots] = useState<Node[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [preview, setPreview] = useState<{ path: string; text: string } | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      const start = workspaceCwd.trim()

      if (!start) {
        setError('Workspace root is unavailable. Open a project first.')

        return
      }

      try {
        const res = await readDesktopDir(start)

        if (cancelled) {return}

        if (res.error) {
          setError(res.error)

          return
        }

        setError(null)
        setRoots([{
          path: start,
          name: start.split(/[/\\]/).filter(Boolean).pop() ?? start,
          isDirectory: true,
          children: (res.entries ?? []).map(e => ({ path: e.path, name: e.name, isDirectory: e.isDirectory, children: null }))
        }])
      } catch (err) {
        if (!cancelled) {setError(err instanceof Error ? err.message : 'Could not list the workspace.')}
      }
    }

    void load()

    return () => { cancelled = true }
  }, [workspaceCwd])

  const onPreview = useCallback(async (path: string) => {
    setPreview(null)
    setPreviewError(null)

    try {
      const result = await readDesktopFileText(path)

      if (result.binary) {
        setPreviewError('Binary file — text preview is unavailable.')
      } else {
        setPreview({ path, text: result.text.slice(0, 4000) })
      }
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : 'Could not read this file.')
    }
  }, [])

  const visible = roots && query.trim()
    ? roots.map(filterTree(query.trim().toLowerCase())).filter((r): r is Node => r !== null)
    : roots

  return (
    <div className="h-full flex flex-col p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-white/90">Files</h2>
          <p className="text-[12px] text-white/30 mt-0.5">Live workspace — ask Jarvis in the composer to change anything</p>
        </div>
      </div>

      <div className="relative mb-3">
        <Codicon className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3 text-white/20" name="search" />
        <input
          className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] text-[12px] text-white/60 placeholder:text-white/20 outline-none focus:border-[#00d4ff]/40 transition-colors"
          onChange={e => setQuery(e.target.value)}
          placeholder="Filter by name..."
          value={query}
        />
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-dt space-y-0.5 min-h-0">
        {error && <div className="text-[12px] text-red-400/80 px-2 py-1">{error}</div>}
        {!error && !roots && <div className="text-[12px] text-white/30 px-2 py-1">Loading workspace...</div>}
        {visible?.map(entry => (
          <FileTreeNode depth={0} key={entry.path} node={entry} onPreview={onPreview} />
        ))}
      </div>

      {(preview || previewError) && (
        <div className="mt-3 max-h-48 overflow-auto rounded-lg bg-black/40 border border-white/[0.06] p-3">
          <div className="text-[10px] text-white/30 font-mono mb-1 truncate">{preview?.path}</div>
          {previewError
            ? <div className="text-[11px] text-red-400/80">{previewError}</div>
            : <pre className="text-[11px] text-white/60 whitespace-pre-wrap font-mono">{preview?.text}</pre>}
        </div>
      )}
    </div>
  )
}

function filterTree(query: string): (node: Node) => Node | null {
  const walk = (node: Node): Node | null => {
    const kids = node.children?.map(walk).filter((k): k is Node => k !== null) ?? null
    const self = node.name.toLowerCase().includes(query)

    if (self || (kids && kids.length > 0)) {return { ...node, children: kids }}

    return null
  }

  return walk
}

export const FilesView = memo(FilesViewComponent)

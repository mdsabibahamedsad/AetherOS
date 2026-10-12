import { useStore } from '@nanostores/react'

import { $gitBranch, $gitChanges, $gitIntegration, $gitUnstagedCount, setCommitMessage } from '../../store/git-integration'

export function GitPanel() {
  const git = useStore($gitIntegration)
  const branch = useStore($gitBranch)
  const changes = useStore($gitChanges)
  const unstaged = useStore($gitUnstagedCount)

  return (
    <div className="flex flex-col h-full text-xs">
      <div className="px-2 py-1.5 border-b border-border bg-surface-secondary">
        <div className="flex items-center gap-2">
          <span className="codicon codicon-git-branch text-foreground-secondary" />
          <span className="font-medium text-xs">{branch || '(no repo)'}</span>
          {git.ahead > 0 && <span className="text-2xs text-blue-500">{git.ahead}↑</span>}
          {git.behind > 0 && <span className="text-2xs text-yellow-500">{git.behind}↓</span>}
        </div>
      </div>

      {!git.isRepo ? (
        <div className="p-4 text-center text-foreground-secondary">
          <p>Not a git repository</p>
          <p className="text-2xs mt-1">Open a project with a .git folder</p>
        </div>
      ) : (
        <>
          <div className="px-2 py-1 border-b border-border text-2xs text-foreground-secondary flex items-center gap-1">
            <span className="codicon codicon-file" />
            Changes ({unstaged})
          </div>
          <div className="flex-1 overflow-auto">
            {changes.map((c, i) => (
              <div className="flex items-center gap-2 px-3 py-1 hover:bg-surface-hover cursor-pointer" key={i}>
                <span className={`codicon codicon-${c.status === 'M' ? 'edit' : c.status === '?' ? 'question' : c.status === 'D' ? 'trash' : 'file'} text-2xs`} />
                <span className="truncate flex-1">{c.file}</span>
                <span className={`text-2xs px-1 rounded ${
                  c.status === 'M' ? 'bg-yellow-500/20 text-yellow-500' :
                  c.status === '?' ? 'bg-blue-500/20 text-blue-500' :
                  c.status === 'D' ? 'bg-red-500/20 text-red-500' :
                  'bg-green-500/20 text-green-500'
                }`}>{c.status}</span>
              </div>
            ))}
            {changes.length === 0 && (
              <div className="p-3 text-center text-foreground-secondary text-2xs">No changes</div>
            )}
          </div>

          <div className="border-t border-border p-2">
            <input
              className="w-full px-2 py-1 text-xs bg-surface border border-border rounded outline-none focus:border-accent placeholder-foreground-secondary mb-1"
              onChange={e => setCommitMessage(e.target.value)}
              placeholder="Commit message..."
              value={git.commitMessage}
            />
            <div className="flex gap-1">
              <button className="flex-1 px-2 py-0.5 text-2xs bg-accent text-white rounded hover:bg-accent-hover disabled:opacity-50" disabled={!git.commitMessage.trim()}>
                Commit
              </button>
              <button className="px-2 py-0.5 text-2xs bg-surface-hover text-foreground rounded hover:bg-surface-muted">
                <span className="codicon codicon-cloud-upload" />
              </button>
              <button className="px-2 py-0.5 text-2xs bg-surface-hover text-foreground rounded hover:bg-surface-muted">
                <span className="codicon codicon-cloud-download" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

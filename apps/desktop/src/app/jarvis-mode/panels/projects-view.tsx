import { motion } from 'motion/react'
import { memo } from 'react'

import { Codicon } from '@/components/ui/codicon'

const QUICK_PROJECTS = [
  { name: 'AetherOS Desktop', path: '/aetheros/apps/desktop', branch: 'main', status: 'active' as const },
  { name: 'Web Dashboard', path: '/aetheros/web', branch: 'develop', status: 'active' as const },
  { name: 'Agent Core', path: '/aetheros', branch: 'main', status: 'active' as const },
]

function ProjectsViewComponent() {
  return (
    <div className="h-full flex flex-col p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-white/90">Projects</h2>
          <p className="text-[12px] text-white/30 mt-0.5">Manage your workspaces</p>
        </div>
        <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium bg-[#0066ff]/20 text-[#00d4ff] border border-[#0066ff]/30 hover:bg-[#0066ff]/30 transition-all">
          <Codicon className="size-3.5" name="new-file" />
          New Project
        </button>
      </div>

      <div className="space-y-2 flex-1 overflow-y-auto scrollbar-dt">
        {QUICK_PROJECTS.map((project, i) => (
          <motion.div
            animate={{ opacity: 1, y: 0 }}
            className="group p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] hover:border-white/[0.1] transition-all cursor-pointer"
            initial={{ opacity: 0, y: 10 }}
            key={project.name}
            transition={{ delay: i * 0.05 }}
          >
            <div className="flex items-start gap-3">
              <div className="flex items-center justify-center size-10 rounded-lg bg-gradient-to-br from-[#0066ff]/20 to-[#00d4ff]/20 border border-[#0066ff]/10 shrink-0">
                <Codicon className="size-5 text-[#00d4ff]" name="project" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[14px] font-medium text-white/80 truncate">{project.name}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${project.status === 'active' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-white/[0.06] text-white/30'}`}>
                    {project.status}
                  </span>
                </div>
                <div className="text-[11px] text-white/30 font-mono mt-0.5 truncate">{project.path}</div>
                <div className="flex items-center gap-3 mt-2">
                  <div className="flex items-center gap-1 text-[10px] text-white/25">
                    <Codicon className="size-3" name="git-branch" />
                    {project.branch}
                  </div>
                  <div className="flex items-center gap-1 text-[10px] text-white/25">
                    <Codicon className="size-3" name="repo" />
                    Private
                  </div>
                </div>
              </div>
              <button aria-label={`Open project ${project.name}`} className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-md hover:bg-white/[0.06] text-white/30 hover:text-white/60">
                <Codicon className="size-4" name="chevron-right" />
              </button>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="mt-4 p-3 rounded-xl bg-white/[0.02] border border-dashed border-white/[0.06]">
        <div className="flex items-center gap-2 text-[12px] text-white/25">
          <Codicon className="size-4" name="folder-opened" />
          Open an existing project from your filesystem
        </div>
      </div>
    </div>
  )
}

export const ProjectsView = memo(ProjectsViewComponent)

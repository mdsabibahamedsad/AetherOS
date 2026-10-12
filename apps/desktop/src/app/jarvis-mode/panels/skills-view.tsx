import { motion } from 'motion/react'
import { memo } from 'react'

import { Codicon } from '@/components/ui/codicon'

const SKILLS = [
  { name: 'Research', category: 'core', description: 'Web research and analysis', icon: 'search' },
  { name: 'Code Generation', category: 'core', description: 'Write and review code', icon: 'code' },
  { name: 'Browser Automation', category: 'core', description: 'Navigate and extract from web pages', icon: 'globe' },
  { name: 'File Operations', category: 'core', description: 'Read, write, and manage files', icon: 'files' },
  { name: 'Memory Management', category: 'core', description: 'Store and retrieve context', icon: 'database' },
  { name: 'Deployment', category: 'advanced', description: 'Build and deploy projects', icon: 'cloud' },
]

function SkillsViewComponent() {
  return (
    <div className="h-full flex flex-col p-6">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-white/90">Skills</h2>
        <p className="text-[12px] text-white/30 mt-0.5">Agent capabilities</p>
      </div>

      <div className="space-y-2 flex-1 overflow-y-auto scrollbar-dt">
        {SKILLS.map((skill, i) => (
          <motion.div
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] transition-all cursor-pointer"
            initial={{ opacity: 0, y: 8 }}
            key={skill.name}
            transition={{ delay: i * 0.04 }}
          >
            <div className="flex items-center justify-center size-8 rounded-lg bg-[#00d4ff]/10 shrink-0">
              <Codicon className="size-4 text-[#00d4ff]" name={skill.icon} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-medium text-white/70">{skill.name}</span>
                <span className="text-[9px] px-1 py-0.5 rounded-full bg-white/[0.05] text-white/25 uppercase">
                  {skill.category}
                </span>
              </div>
              <div className="text-[11px] text-white/30 mt-0.5">{skill.description}</div>
            </div>
            <Codicon className="size-3.5 text-emerald-400" name="check" />
          </motion.div>
        ))}
      </div>
    </div>
  )
}

export const SkillsView = memo(SkillsViewComponent)

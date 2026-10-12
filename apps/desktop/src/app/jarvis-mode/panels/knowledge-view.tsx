import { motion } from 'motion/react'
import { memo } from 'react'

import { Codicon } from '@/components/ui/codicon'

const CATEGORIES = [
  { name: 'Architecture', count: 12, icon: 'symbol-structure' },
  { name: 'API Reference', count: 28, icon: 'plug' },
  { name: 'Workflows', count: 8, icon: 'run-all' },
  { name: 'Troubleshooting', count: 15, icon: 'tools' },
  { name: 'Guides', count: 19, icon: 'book' },
  { name: 'FAQs', count: 6, icon: 'question' },
]

function KnowledgeViewComponent() {
  return (
    <div className="h-full flex flex-col p-6">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-white/90">Knowledge</h2>
        <p className="text-[12px] text-white/30 mt-0.5">Documentation & reference</p>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-4">
        {CATEGORIES.map((cat, i) => (
          <motion.button
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center gap-1.5 p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] hover:border-white/[0.1] transition-all"
            initial={{ opacity: 0, y: 8 }}
            key={cat.name}
            transition={{ delay: i * 0.04 }}
          >
            <Codicon className="size-5 text-[#00d4ff]" name={cat.icon} />
            <span className="text-[12px] font-medium text-white/60">{cat.name}</span>
            <span className="text-[10px] text-white/20">{cat.count} articles</span>
          </motion.button>
        ))}
      </div>

      <div className="flex-1">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-[10px] text-white/25 uppercase tracking-wider">Recently Accessed</span>
          <div className="flex-1 h-px bg-white/[0.06]" />
        </div>

        <div className="space-y-1">
          {['Multi-Agent Orchestration', 'Plugin Development Guide', 'Memory Provider API'].map((doc, i) => (
            <motion.div
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/[0.04] cursor-pointer transition-colors"
              initial={{ opacity: 0, x: -5 }}
              key={doc}
              transition={{ delay: i * 0.05 }}
            >
              <Codicon className="size-3.5 text-white/20" name="file-text" />
              <span className="text-[12px] text-white/50 truncate">{doc}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}

export const KnowledgeView = memo(KnowledgeViewComponent)

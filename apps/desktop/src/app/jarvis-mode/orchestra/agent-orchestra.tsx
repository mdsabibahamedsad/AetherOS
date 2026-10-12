import { useStore } from '@nanostores/react'
import { AnimatePresence, motion } from 'motion/react'
import { memo } from 'react'

import { $jarvisOrchestra, $jarvisOrchestraActive, clearOrchestra, type OrchestraModel } from '@/store/jarvis-mode'
import { $jarvisSystemStatus } from '@/store/jarvis-mode'

import { GlassPanel } from '../shared/glass-panel'

const PROVIDER_COLORS: Record<string, string> = {
  openai: '#10a37f',
  anthropic: '#d4a574',
  google: '#4285f4',
  deepseek: '#4f6ef7',
  groq: '#f97316',
  openrouter: '#8b5cf6',
  local: '#64748b'
}

function ModelCard({ model }: { model: OrchestraModel }) {
  const providerColor = PROVIDER_COLORS[model.provider] ?? '#00d4ff'

  return (
    <motion.div
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white/[0.02] border border-white/[0.06]"
      initial={{ opacity: 0, y: 10, scale: 0.95 }}
    >
      {/* Status indicator */}
      <div className="relative">
        <div className={`size-2.5 rounded-full ${
          model.status === 'working' ? 'bg-[#00d4ff]' :
          model.status === 'completed' ? 'bg-emerald-400' :
          model.status === 'error' ? 'bg-red-400' : 'bg-white/20'
        }`} />
        {model.status === 'working' && (
          <motion.div
            animate={{ scale: [1, 1.8, 1], opacity: [0.5, 0, 0.5] }}
            className="absolute inset-0 size-2.5 rounded-full bg-[#00d4ff]"
            transition={{ duration: 1.5, repeat: Infinity }}
          />
        )}
      </div>

      {/* Model info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-medium text-white/70 truncate">{model.name}</span>
          <span className="text-[8px] px-1 py-0.5 rounded-full" style={{ backgroundColor: `${providerColor}20`, color: providerColor }}>
            {model.provider}
          </span>
        </div>
        <div className="text-[9px] text-white/20 mt-0.5 truncate">{model.task}</div>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-2 text-[9px] text-white/20">
        <span>{(model.runtime / 1000).toFixed(1)}s</span>
        <span>{model.tokensUsed}t</span>
      </div>
    </motion.div>
  )
}

export function AgentOrchestraComponent() {
  const orchestra = useStore($jarvisOrchestra)
  const activeCount = useStore($jarvisOrchestraActive)
  const systemStatus = useStore($jarvisSystemStatus)

  if (orchestra.length === 0) {return null}

  return (
    <motion.div
      animate={{ opacity: 1, y: 0 }}
      className="fixed right-[calc(280px+24px)] bottom-24 z-50 w-[320px]"
      initial={{ opacity: 0, y: 20 }}
    >
      <GlassPanel className="p-4 rounded-2xl shadow-2xl" glow="blue" intensity="heavy">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="size-2 rounded-full bg-[#00d4ff] animate-pulse" style={{ boxShadow: '0 0 6px rgba(0,212,255,0.5)' }} />
            <span className="text-[9px] uppercase tracking-[0.2em] text-white/20 font-medium">AI Orchestra</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[9px] text-white/15">{activeCount} active</span>
            <button className="text-[9px] text-white/15 hover:text-white/30 transition-colors" onClick={clearOrchestra}>Clear</button>
          </div>
        </div>

        {/* Model cards */}
        <div className="space-y-1.5 max-h-[300px] overflow-y-auto scrollbar-dt">
          <AnimatePresence>
            {orchestra.map(m => <ModelCard key={m.id} model={m} />)}
          </AnimatePresence>
        </div>
      </GlassPanel>
    </motion.div>
  )
}

export const AgentOrchestra = memo(AgentOrchestraComponent)

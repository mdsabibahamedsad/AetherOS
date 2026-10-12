import { useStore } from '@nanostores/react'
import { AnimatePresence, motion } from 'motion/react'
import { memo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

import { Codicon } from '@/components/ui/codicon'
import { submitJarvisCommand } from '@/lib/jarvis/core/command-gateway'
import { AGENT_DEFINITIONS } from '@/lib/jarvis/orchestrator/agent-orchestrator'
import { createDesktopCommandDeps } from '@/lib/jarvis/os/local-executor'
import type { AgentType } from '@/lib/jarvis/types'
import {
  $jarvisAgents,
  addJarvisNotification,
  type JarvisAgent,
  removeJarvisAgent
} from '@/store/jarvis-mode'

import { GlassPanel } from '../shared/glass-panel'

const AGENT_TYPES: AgentType[] = ['research', 'coding', 'browser', 'planning', 'memory', 'automation']

const AGENT_COLORS: Record<string, string> = {
  research: '#a78bfa',
  coding: '#22c55e',
  browser: '#f59e0b',
  planning: '#00d4ff',
  memory: '#0066ff',
  automation: '#ef4444',
}

const AGENT_ICONS: Record<string, string> = {
  research: 'search',
  coding: 'code',
  browser: 'globe',
  planning: 'list-flat',
  memory: 'database',
  automation: 'run-all',
}

function AgentCard({ agent }: { agent: JarvisAgent }) {
  const color = AGENT_COLORS[agent.type] ?? '#64748b'
  const icon = AGENT_ICONS[agent.type] ?? 'hubot'
  const elapsed = agent.startedAt ? Math.floor((Date.now() - agent.startedAt) / 1000) : 0
  const elapsedStr = elapsed < 60 ? `${elapsed}s` : `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`

  return (
    <motion.div
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      initial={{ opacity: 0, y: 10 }}
      layout
    >
      <GlassPanel className="p-4 rounded-xl" glow="none" intensity="light">
      <div className="flex items-start gap-3">
        <div className="flex items-center justify-center size-10 rounded-lg shrink-0" style={{ backgroundColor: `${color}15`, borderColor: `${color}30` }}>
          <Codicon className="size-5" name={icon} style={{ color }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[14px] font-medium text-white/80">{agent.name}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full capitalize" style={{ backgroundColor: `${color}15`, color }}>
              {agent.type}
            </span>
          </div>
          <div className="flex items-center gap-3 mt-1.5 text-[11px] text-white/30">
            <span className="flex items-center gap-1">
              <span className={`size-1.5 rounded-full ${agent.status === 'running' ? 'animate-pulse' : ''}`} style={{ backgroundColor: color, boxShadow: agent.status === 'running' ? `0 0 6px ${color}` : undefined }} />
              {agent.status}
            </span>
            <span>{elapsedStr}</span>
          </div>
          {agent.currentTask && (
            <div className="text-[12px] text-white/50 mt-1.5 truncate">{agent.currentTask}</div>
          )}
          {agent.progress !== undefined && agent.status === 'running' && (
            <div className="mt-2 h-1 rounded-full bg-white/[0.06] overflow-hidden">
              <motion.div
                animate={{ width: `${agent.progress}%` }}
                className="h-full rounded-full"
                initial={{ width: 0 }}
                style={{ background: `linear-gradient(90deg, ${color}, ${color}88)` }}
                transition={{ duration: 0.5 }}
              />
            </div>
          )}
        </div>
        <button
          aria-label={`Remove ${agent.name ?? agent.id} from this list`}
          className="p-1 rounded-md hover:bg-white/[0.06] text-white/20 hover:text-red-400 transition-all opacity-0 group-hover:opacity-100"
          onClick={() => { removeJarvisAgent(agent.id) }}
          title="Remove from this list (the gateway session itself is untouched)"
        >
          <Codicon className="size-3.5" name="close" />
        </button>
      </div>
      </GlassPanel>
    </motion.div>
  )
}

function SpawnButton({ type }: { type: AgentType }) {
  const def = AGENT_DEFINITIONS[type]
  const color = AGENT_COLORS[type] ?? '#64748b'
  const icon = AGENT_ICONS[type] ?? 'hubot'
  const navigate = useNavigate()

  // Real delegation: the gateway agent spawns the specialist and streams
  // progress as genuine tool events. Nothing here is simulated.
  const handleSpawn = useCallback(() => {
    addJarvisNotification({ title: 'Delegating...', message: `Asking the agent to start ${def.label}`, type: 'info' })
    void submitJarvisCommand(`Delegate to a ${def.label}: report when it is running and stream its progress.`, {
      inputType: 'text',
      deps: createDesktopCommandDeps(navigate)
    }).catch(err => {
      addJarvisNotification({ title: 'Delegation failed', message: err instanceof Error ? err.message : String(err), type: 'error' })
    })
  }, [def.label, navigate])

  return (
    <GlassPanel className="rounded-xl overflow-hidden" glow="none" intensity="light">
      <motion.button
        className="flex items-center gap-2 p-3 w-full text-left cursor-pointer"
        onClick={handleSpawn}
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
      >
      <div className="flex items-center justify-center size-8 rounded-lg shrink-0" style={{ backgroundColor: `${color}15` }}>
        <Codicon className="size-4" name={icon} style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[12px] font-medium text-white/60">{def.label}</div>
        <div className="text-[10px] text-white/25 truncate">{def.description}</div>
      </div>
      <Codicon className="size-3.5 text-white/20" name="plus" />
      </motion.button>
    </GlassPanel>
  )
}

function AgentManagerPanelComponent() {
  const agents = useStore($jarvisAgents)

  return (
    <div className="h-full flex flex-col p-6">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-white/90">Agents</h2>
        <p className="text-[12px] text-white/30 mt-0.5">Spawn and monitor AI agents</p>
      </div>

      <div className="flex items-center gap-2 mb-4">
        <Codicon className="size-4 text-[#00d4ff]" name="hubot" />
        <span className="text-[12px] text-white/50">{agents.filter(a => a.status === 'running').length} active / {agents.length} total</span>
      </div>

      <div className="space-y-2 mb-4 flex-1 overflow-y-auto scrollbar-dt">
        <AnimatePresence>
          {agents.map(agent => (
            <AgentCard agent={agent} key={agent.id} />
          ))}
        </AnimatePresence>
        {agents.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Codicon className="size-10 text-white/[0.06] mb-3" name="hubot" />
            <span className="text-[13px] text-white/20">No agents running</span>
            <span className="text-[11px] text-white/15 mt-1">Spawn an agent below</span>
          </div>
        )}
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[10px] text-white/25 uppercase tracking-wider">Spawn Agent</span>
          <div className="flex-1 h-px bg-white/[0.06]" />
        </div>
        {AGENT_TYPES.map(type => (
          <SpawnButton key={type} type={type} />
        ))}
      </div>
    </div>
  )
}

export const AgentManagerPanel = memo(AgentManagerPanelComponent)

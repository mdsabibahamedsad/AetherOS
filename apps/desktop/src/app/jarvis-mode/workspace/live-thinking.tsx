import { useStore } from '@nanostores/react'
import { AnimatePresence, motion } from 'motion/react'
import { memo } from 'react'

import { $jarvisThinkingLabel, $jarvisThinkingStage, type ThinkingStage } from '@/store/jarvis-mode'

const STAGES: { stage: ThinkingStage; label: string; icon: string; color: string }[] = [
  { stage: 'understanding', label: 'Understanding', icon: 'search', color: '#00d4ff' },
  { stage: 'planning', label: 'Planning', icon: 'list-flat', color: '#0066ff' },
  { stage: 'searching', label: 'Searching', icon: 'database', color: '#a78bfa' },
  { stage: 'using-tools', label: 'Using Tools', icon: 'tools', color: '#f59e0b' },
  { stage: 'executing', label: 'Executing', icon: 'play', color: '#22c55e' },
  { stage: 'validating', label: 'Validating', icon: 'pass', color: '#00d4ff' },
  { stage: 'complete', label: 'Complete', icon: 'check', color: '#22c55e' },
]

function getStageIndex(current: ThinkingStage): number {
  return STAGES.findIndex(s => s.stage === current)
}

function LiveThinkingComponent() {
  const stage = useStore($jarvisThinkingStage)
  const label = useStore($jarvisThinkingLabel)
  const isActive = stage !== 'idle' && stage !== 'complete'
  const currentIdx = getStageIndex(stage)

  if (stage === 'idle') {return null}

  return (
    <AnimatePresence>
      <motion.div
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center gap-3 py-4"
        exit={{ opacity: 0, y: -10 }}
        initial={{ opacity: 0, y: -10 }}
      >
        {/* Pulsing core indicator */}
        {isActive && (
          <div className="relative">
            <motion.div
              animate={{
                scale: [1, 1.4, 1],
                opacity: [0.8, 0.4, 0.8],
                boxShadow: [
                  '0 0 12px #00d4ff60',
                  '0 0 24px #00d4ff40',
                  '0 0 12px #00d4ff60'
                ]
              }}
              className="size-3 rounded-full bg-[#00d4ff]"
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            />
          </div>
        )}

        {/* Stage pipeline */}
        <div className="flex items-center gap-1">
          {STAGES.map((s, i) => {
            const isPast = i < currentIdx
            const isCurrent = s.stage === stage
            const isFuture = i > currentIdx

            return (
              <div className="flex items-center gap-1" key={s.stage}>
                <motion.div
                  animate={isCurrent ? { scale: [1, 1.05, 1] } : undefined}
                  className={`flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium transition-all ${
                    isCurrent
                      ? 'bg-white/[0.1] border border-white/[0.15]'
                      : isPast
                        ? 'opacity-50'
                        : 'opacity-20'
                  }`}
                  transition={isCurrent ? { duration: 1.5, repeat: Infinity } : undefined}
                >
                  <span style={{ color: isPast || isCurrent ? s.color : undefined }}>{s.label}</span>
                </motion.div>
                {i < STAGES.length - 1 && (
                  <div className={`w-3 h-px ${isPast ? 'bg-white/30' : 'bg-white/10'}`} />
                )}
              </div>
            )
          })}
        </div>

        {/* Current label */}
        {label && stage !== 'complete' && (
          <motion.div
            animate={{ opacity: 1 }}
            className="text-[11px] text-white/40 font-mono"
            initial={{ opacity: 0 }}
            key={label}
          >
            {label}
          </motion.div>
        )}
      </motion.div>
    </AnimatePresence>
  )
}

export const LiveThinking = memo(LiveThinkingComponent)

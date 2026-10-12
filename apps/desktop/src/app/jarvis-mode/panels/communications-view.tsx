import { motion } from 'motion/react'
import { memo } from 'react'

import { Codicon } from '@/components/ui/codicon'

const PLATFORMS = [
  { name: 'Telegram', icon: 'comment', status: 'connected' as const, unread: 3 },
  { name: 'Discord', icon: 'comment-discussion', status: 'connected' as const, unread: 0 },
  { name: 'Slack', icon: 'comment', status: 'disconnected' as const, unread: 0 },
  { name: 'Email', icon: 'mail', status: 'connected' as const, unread: 12 },
  { name: 'WhatsApp', icon: 'comment', status: 'connecting' as const, unread: 0 },
]

function CommunicationsViewComponent() {
  return (
    <div className="h-full flex flex-col p-6">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-white/90">Communications</h2>
        <p className="text-[12px] text-white/30 mt-0.5">Unified inbox</p>
      </div>

      <div className="space-y-2 flex-1 overflow-y-auto scrollbar-dt">
        {PLATFORMS.map((platform, i) => {
          const statusColor = platform.status === 'connected' ? '#22c55e' : platform.status === 'connecting' ? '#f59e0b' : '#ef4444'

          return (
            <motion.div
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-3 p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] transition-all cursor-pointer"
              initial={{ opacity: 0, y: 8 }}
              key={platform.name}
              transition={{ delay: i * 0.05 }}
            >
              <div className="flex items-center justify-center size-10 rounded-lg bg-white/[0.05] shrink-0">
                <Codicon className="size-5 text-[#00d4ff]" name={platform.icon} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[14px] font-medium text-white/80">{platform.name}</span>
                  {platform.unread > 0 && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#ef4444]/20 text-[#ef4444] font-medium">
                      {platform.unread}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="size-1.5 rounded-full" style={{ backgroundColor: statusColor }} />
                  <span className="text-[11px] text-white/30 capitalize">{platform.status}</span>
                </div>
              </div>
              <Codicon className="size-4 text-white/20" name="chevron-right" />
            </motion.div>
          )
        })}
      </div>

      <div className="mt-4 p-3 rounded-xl bg-white/[0.02] border border-dashed border-white/[0.06]">
        <div className="flex items-center gap-2 text-[12px] text-white/25">
          <Codicon className="size-4" name="plug" />
          Connect additional platforms via the gateway
        </div>
      </div>
    </div>
  )
}

export const CommunicationsView = memo(CommunicationsViewComponent)

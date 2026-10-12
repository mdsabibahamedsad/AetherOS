import { motion } from 'motion/react'
import { memo } from 'react'

import { Codicon } from '@/components/ui/codicon'

const MCP_SERVERS = [
  { name: 'Filesystem', status: 'connected' as const, tools: 12, type: 'local' },
  { name: 'Browser', status: 'connected' as const, tools: 8, type: 'local' },
  { name: 'Database', status: 'disconnected' as const, tools: 0, type: 'remote' },
  { name: 'GitHub', status: 'connecting' as const, tools: 0, type: 'remote' },
]

function McpViewComponent() {
  return (
    <div className="h-full flex flex-col p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-white/90">MCP Servers</h2>
          <p className="text-[12px] text-white/30 mt-0.5">Model Context Protocol</p>
        </div>
        <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium bg-[#0066ff]/20 text-[#00d4ff] border border-[#0066ff]/30 hover:bg-[#0066ff]/30 transition-all">
          <Codicon className="size-3.5" name="plug" />
          Add Server
        </button>
      </div>

      <div className="space-y-2 flex-1 overflow-y-auto scrollbar-dt">
        {MCP_SERVERS.map((server, i) => {
          const statusColor = server.status === 'connected' ? '#22c55e' : server.status === 'connecting' ? '#f59e0b' : '#ef4444'

          return (
            <motion.div
              animate={{ opacity: 1, y: 0 }}
              className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] transition-all"
              initial={{ opacity: 0, y: 8 }}
              key={server.name}
              transition={{ delay: i * 0.05 }}
            >
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center size-10 rounded-lg bg-white/[0.05] shrink-0">
                  <Codicon className="size-5 text-[#00d4ff]" name="server" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[14px] font-medium text-white/80">{server.name}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full capitalize`} style={{ backgroundColor: `${statusColor}20`, color: statusColor }}>
                      {server.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-1.5">
                    <span className="text-[11px] text-white/30">
                      <Codicon className="size-3 inline mr-1" name="tools" />
                      {server.tools} tools
                    </span>
                    <span className="text-[11px] text-white/30 capitalize">{server.type}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-3">
                    {server.status === 'connected' && (
                      <>
                        <button className="px-2 py-0.5 rounded-md text-[10px] bg-white/[0.05] text-white/40 hover:text-white/70 transition-colors">Logs</button>
                        <button className="px-2 py-0.5 rounded-md text-[10px] bg-white/[0.05] text-white/40 hover:text-white/70 transition-colors">Permissions</button>
                      </>
                    )}
                    {server.status === 'disconnected' && (
                      <button className="px-2 py-0.5 rounded-md text-[10px] bg-[#22c55e]/10 text-[#22c55e] hover:bg-[#22c55e]/20 transition-colors">Connect</button>
                    )}
                  </div>
                </div>
                <div className="flex flex-col gap-1">
                  <motion.div animate={{ scale: server.status === 'connected' ? [1, 1.2, 1] : 1 }} className="size-2 rounded-full" style={{ backgroundColor: statusColor, boxShadow: server.status === 'connected' ? `0 0 8px ${statusColor}` : undefined }} />
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

export const McpView = memo(McpViewComponent)

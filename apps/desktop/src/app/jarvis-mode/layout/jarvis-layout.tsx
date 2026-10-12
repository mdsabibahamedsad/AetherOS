import { useStore } from '@nanostores/react'
import { motion } from 'motion/react'
import { memo, useCallback, useEffect } from 'react'

import { startJarvisGatewaySync } from '@/lib/jarvis/gateway-sync'
import { $jarvisLeftPanelSection, updateJarvisSystemStatus } from '@/store/jarvis-mode'

import { ParticleBackground } from '../animations/particle-background'
import { CommandPalette } from '../command-center/command-palette'
import { JarvisLeftPanel } from '../panels/left-panel'
import { JarvisRightPanel } from '../panels/right-panel'
import { SectionContent } from '../panels/section-content'
import { JarvisStatusBar } from '../status-bar/jarvis-status-bar'
import { ConversationalWorkspace } from '../workspace/conversational-workspace'

const CHAT_SECTION = 'chat'

function SystemStatusPoller() {
  const poll = useCallback(async () => {
    try {
      const stats = await window.aetherosDesktop?.getSystemStats?.()

      if (stats) {
        updateJarvisSystemStatus({ cpu: stats.cpu, memory: stats.memory, gpu: stats.gpu, uptime: stats.uptime })
      }
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    const stopSync = startJarvisGatewaySync()
    poll()
    const id = setInterval(poll, 15000)

    return () => {
      clearInterval(id)
      stopSync()
    }
  }, [poll])

  return null
}

function JarvisLayoutComponent() {
  const activeSection = useStore($jarvisLeftPanelSection)
  const showChat = activeSection === CHAT_SECTION

  return (
    <div className="fixed inset-0 z-[9999] flex flex-col bg-[#0a0a0f] overflow-hidden">
      <ParticleBackground />

      <div className="pointer-events-none fixed inset-0 z-0">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-[#0066ff]/[0.04] rounded-full blur-[120px]" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-[#9933ff]/[0.03] rounded-full blur-[100px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-[#00d4ff]/[0.02] rounded-full blur-[150px]" />
      </div>

      <div className="relative z-10">
        <JarvisStatusBar />
      </div>

      <div className="relative z-10 flex flex-1 min-h-0">
        <JarvisLeftPanel />
        <motion.div
          animate={{ opacity: 1 }}
          className="flex-1 min-w-0"
          initial={{ opacity: 0 }}
          key={activeSection}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          {showChat ? <ConversationalWorkspace /> : <SectionContent />}
        </motion.div>
        <JarvisRightPanel />
      </div>

      <CommandPalette />
      <SystemStatusPoller />
    </div>
  )
}

export const JarvisLayout = memo(JarvisLayoutComponent)

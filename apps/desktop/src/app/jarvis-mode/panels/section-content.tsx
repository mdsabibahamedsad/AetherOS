import { useStore } from '@nanostores/react'
import { AnimatePresence, motion } from 'motion/react'
import { memo } from 'react'

import { $jarvisLeftPanelSection } from '@/store/jarvis-mode'

import { AgentManagerPanel } from '../agents/agent-manager'
import { AutomationDashboard } from '../automation/automation-dashboard'

import { BrowserView } from './browser-view'
import { CommunicationsView } from './communications-view'
import { FilesView } from './files-view'
import { KnowledgeView } from './knowledge-view'
import { McpView } from './mcp-view'
import { MemoryView } from './memory-view'
import { ProjectsView } from './projects-view'
import { SettingsView } from './settings-view'
import { SkillsView } from './skills-view'
import { TerminalView } from './terminal-view'

const VIEW_REGISTRY: Record<string, React.ComponentType> = {
  projects: ProjectsView,
  memory: MemoryView,
  knowledge: KnowledgeView,
  files: FilesView,
  skills: SkillsView,
  mcp: McpView,
  terminal: TerminalView,
  browser: BrowserView,
  communications: CommunicationsView,
  settings: SettingsView,
  automation: AutomationDashboard,
  agents: AgentManagerPanel,
}

function SectionContentComponent() {
  const section = useStore($jarvisLeftPanelSection)
  const Component = VIEW_REGISTRY[section]

  if (!Component) {return null}

  return (
    <AnimatePresence mode="wait">
      <motion.div
        animate={{ opacity: 1, y: 0 }}
        className="h-full"
        exit={{ opacity: 0, y: -8 }}
        initial={{ opacity: 0, y: 8 }}
        key={section}
        transition={{ duration: 0.2 }}
      >
        <Component />
      </motion.div>
    </AnimatePresence>
  )
}

export const SectionContent = memo(SectionContentComponent)

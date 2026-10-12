import { useStore } from '@nanostores/react'
import { useCallback, useState } from 'react'

import type { StatusbarItem, StatusbarItemSide } from '@/app/shell/statusbar-controls'
import { $communications, selectConversation } from '@/store/communications'

import { ActivityLog } from './activity-log'
import { CommsAIAssistant } from './ai-assistant'
import { AutomationBuilder } from './automation-builder'
import { ContactsView } from './contacts'
import { ConversationWorkspace } from './conversation'
import { InboxView } from './inbox'
import { NotificationsView } from './notifications'
import { SchedulerView } from './scheduler'
import { CommsSettings } from './settings'

type CommsHubTab = 'inbox' | 'conversation' | 'contacts' | 'scheduler' | 'ai' | 'automation' | 'notifications' | 'activity' | 'settings'

const TABS: { id: CommsHubTab; label: string; icon: string }[] = [
  { id: 'inbox', label: 'Inbox', icon: 'inbox' },
  { id: 'conversation', label: 'Conversation', icon: 'comment-discussion' },
  { id: 'contacts', label: 'Contacts', icon: 'organization' },
  { id: 'scheduler', label: 'Scheduled', icon: 'clock' },
  { id: 'ai', label: 'AI Assistant', icon: 'robot' },
  { id: 'automation', label: 'Automation', icon: 'run-all' },
  { id: 'notifications', label: 'Notifications', icon: 'bell' },
  { id: 'activity', label: 'Activity', icon: 'history' },
  { id: 'settings', label: 'Settings', icon: 'gear' },
]

interface CommunicationsHubProps {
  setStatusbarItemGroup?: (id: string, items: readonly StatusbarItem[], side?: StatusbarItemSide) => void
}

export function CommunicationsHub({ setStatusbarItemGroup: _ }: CommunicationsHubProps = {}) {
  const comms = useStore($communications)
  const [activeTab, setActiveTab] = useState<CommsHubTab>('inbox')

  const handleSelectConversation = useCallback((id: string) => {
    selectConversation(id)
    setActiveTab('conversation')
  }, [])

  return (
    <div className="flex h-full flex-col">
      {/* Tab Bar */}
      <div className="flex shrink-0 items-center border-b border-(--ui-stroke-tertiary) bg-(--ui-sidebar-surface-background) px-4">
        <h1 className="mr-6 text-sm font-semibold tracking-tight">Communications</h1>
        <nav className="flex gap-1">
          {TABS.map(tab => (
            <button
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs transition-colors duration-200 ${
                activeTab === tab.id
                  ? 'bg-(--ui-row-active-background) text-foreground'
                  : 'text-(--ui-text-tertiary) hover:text-foreground'
              }`}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className={`codicon codicon-${tab.icon} text-sm`} />
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Content Area */}
      <div className="min-h-0 flex-1 overflow-hidden">
        {activeTab === 'inbox' && <InboxView onSelectConversation={handleSelectConversation} />}
        {activeTab === 'conversation' && <ConversationWorkspace />}
        {activeTab === 'contacts' && <ContactsView onSelectConversation={handleSelectConversation} />}
        {activeTab === 'scheduler' && <SchedulerView />}
        {activeTab === 'ai' && <CommsAIAssistant />}
        {activeTab === 'automation' && <AutomationBuilder />}
        {activeTab === 'notifications' && <NotificationsView />}
        {activeTab === 'activity' && <ActivityLog />}
        {activeTab === 'settings' && <CommsSettings />}
      </div>
    </div>
  )
}

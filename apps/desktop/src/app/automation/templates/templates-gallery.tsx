import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

interface TemplateDefinition {
  id: string
  name: string
  description: string
  category: string
  icon: string
  tags: string[]
  nodeCount: number
  popular: boolean
}

const TEMPLATES: TemplateDefinition[] = [
  { id: 'email-autoreply', name: 'Email Auto Reply', description: 'Automatically reply to incoming emails based on content', category: 'Communication', icon: 'mail', tags: ['email', 'automation', 'reply'], nodeCount: 5, popular: true },
  { id: 'github-pr-review', name: 'GitHub PR Review', description: 'Auto-review pull requests with AI analysis', category: 'Development', icon: 'git-pull-request', tags: ['github', 'pr', 'review', 'ai'], nodeCount: 7, popular: true },
  { id: 'telegram-ai-bot', name: 'Telegram AI Bot', description: 'AI-powered Telegram bot for automated responses', category: 'Messaging', icon: 'send', tags: ['telegram', 'bot', 'ai'], nodeCount: 4, popular: true },
  { id: 'discord-moderator', name: 'Discord Moderator', description: 'Automated Discord moderation with AI', category: 'Messaging', icon: 'message-circle', tags: ['discord', 'moderation', 'ai'], nodeCount: 6, popular: false },
  { id: 'website-monitor', name: 'Website Monitor', description: 'Monitor websites for changes and get alerts', category: 'Monitoring', icon: 'globe', tags: ['monitor', 'web', 'alert'], nodeCount: 4, popular: true },
  { id: 'research-pipeline', name: 'Research Pipeline', description: 'Automated research pipeline with web search and summarization', category: 'Research', icon: 'book', tags: ['research', 'search', 'summarize'], nodeCount: 8, popular: true },
  { id: 'meeting-summary', name: 'Meeting Summary', description: 'Summarize meetings from notes or transcripts', category: 'Productivity', icon: 'comment-discussion', tags: ['meeting', 'summary', 'notes'], nodeCount: 3, popular: false },
  { id: 'daily-report', name: 'Daily Report', description: 'Generate daily reports with key metrics', category: 'Reporting', icon: 'output', tags: ['report', 'daily', 'metrics'], nodeCount: 5, popular: false },
  { id: 'youtube-summarizer', name: 'YouTube Summarizer', description: 'Summarize YouTube videos automatically', category: 'Media', icon: 'play', tags: ['youtube', 'summary', 'video'], nodeCount: 3, popular: false },
  { id: 'social-media-poster', name: 'Social Media Poster', description: 'Schedule and post content to social media', category: 'Social', icon: 'broadcast', tags: ['social', 'post', 'schedule'], nodeCount: 5, popular: false },
  { id: 'lead-generator', name: 'Lead Generator', description: 'Generate leads from web research', category: 'Sales', icon: 'person-add', tags: ['leads', 'research', 'crm'], nodeCount: 6, popular: false },
  { id: 'customer-support', name: 'Customer Support', description: 'AI-powered customer support automation', category: 'Support', icon: 'comment-discussion', tags: ['support', 'customer', 'ai'], nodeCount: 7, popular: true },
  { id: 'bug-reporter', name: 'Bug Reporter', description: 'Auto-report bugs with context and logs', category: 'Development', icon: 'bug', tags: ['bug', 'report', 'debug'], nodeCount: 4, popular: false },
  { id: 'file-organizer', name: 'File Organizer', description: 'Automatically organize files by type and date', category: 'Productivity', icon: 'file-directory', tags: ['files', 'organize', 'cleanup'], nodeCount: 5, popular: false },
  { id: 'backup-workflow', name: 'Backup Workflow', description: 'Automated backup with scheduling and notifications', category: 'DevOps', icon: 'archive', tags: ['backup', 'schedule', 'notification'], nodeCount: 6, popular: false },
]

const CATEGORIES = ['All', ...new Set(TEMPLATES.map(t => t.category))]

export function TemplatesGallery() {
  const [category, setCategory] = useState('All')
  const [searchQuery, setSearchQuery] = useState('')

  const filtered = TEMPLATES.filter(t =>
    (category === 'All' || t.category === category) &&
    (t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
     t.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
     t.tags.some(tag => tag.includes(searchQuery.toLowerCase())))
  )

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-6 py-3">
        <div className="flex items-center gap-2">
          <Codicon className="text-purple-400" name="library" size="1rem" />
          <h2 className="text-base font-semibold">Workflow Templates</h2>
        </div>
        <input
          className="w-56 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-xs text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary"
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="Search templates..."
          type="text"
          value={searchQuery}
        />
      </div>

      <div className="flex items-center gap-1 border-b border-(--ui-stroke-tertiary) px-4 py-2">
        {CATEGORIES.map(cat => (
          <button
            className={cn(
              'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
              category === cat
                ? 'bg-(--ui-control-hover-background) text-foreground'
                : 'text-(--ui-text-tertiary) hover:text-foreground'
            )}
            key={cat}
            onClick={() => setCategory(cat)}
            type="button"
          >
            {cat}
          </button>
        ))}
      </div>

      <ScrollArea className="flex-1">
        <div className="grid grid-cols-3 gap-3 p-4">
          {filtered.map(tmpl => (
            <div
              className="group relative cursor-pointer rounded-xl border border-(--ui-stroke-tertiary) p-4 transition-all hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5"
              key={tmpl.id}
            >
              {tmpl.popular && (
                <span className="absolute right-2 top-2 rounded-full bg-primary/10 px-1.5 py-0.5 text-[9px] font-medium text-primary">Popular</span>
              )}

              <div className={cn(
                'mb-3 flex h-10 w-10 items-center justify-center rounded-lg',
                tmpl.category === 'Communication' ? 'bg-green-500/10' :
                tmpl.category === 'Development' ? 'bg-blue-500/10' :
                tmpl.category === 'Messaging' ? 'bg-cyan-500/10' :
                tmpl.category === 'Monitoring' ? 'bg-amber-500/10' :
                tmpl.category === 'Research' ? 'bg-purple-500/10' :
                tmpl.category === 'Productivity' ? 'bg-pink-500/10' :
                tmpl.category === 'Reporting' ? 'bg-orange-500/10' :
                'bg-(--ui-control-hover-background)'
              )}>
                <Codicon className={
                  tmpl.category === 'Communication' ? 'text-green-400' :
                  tmpl.category === 'Development' ? 'text-blue-400' :
                  tmpl.category === 'Messaging' ? 'text-cyan-400' :
                  tmpl.category === 'Monitoring' ? 'text-amber-400' :
                  tmpl.category === 'Research' ? 'text-purple-400' :
                  tmpl.category === 'Productivity' ? 'text-pink-400' :
                  tmpl.category === 'Reporting' ? 'text-orange-400' :
                  'text-(--ui-text-tertiary)'
                } name={tmpl.icon as any} size="1.25rem" />
              </div>

              <h3 className="mb-1 text-sm font-medium text-foreground">{tmpl.name}</h3>
              <p className="mb-3 text-xs text-(--ui-text-tertiary) line-clamp-2">{tmpl.description}</p>

              <div className="flex items-center justify-between">
                <div className="flex flex-wrap gap-1">
                  {tmpl.tags.slice(0, 3).map(tag => (
                    <span className="rounded bg-(--ui-stroke-tertiary) px-1.5 py-0.5 text-[9px] text-(--ui-text-tertiary)" key={tag}>{tag}</span>
                  ))}
                </div>
                <span className="text-[10px] text-(--ui-text-tertiary)">{tmpl.nodeCount} nodes</span>
              </div>

              <Button className="mt-3 w-full opacity-0 group-hover:opacity-100 transition-opacity" size="sm" variant="outline">
                Use Template
              </Button>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}

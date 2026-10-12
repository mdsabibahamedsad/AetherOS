import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

interface MarketplaceItem {
  id: string
  name: string
  description: string
  author: string
  icon: string
  category: string
  downloads: number
  rating: number
  tags: string[]
  type: 'workflow' | 'blueprint' | 'template' | 'plugin'
}

const MARKETPLACE_ITEMS: MarketplaceItem[] = [
  { id: 'mp-1', name: 'PR Auto Reviewer', description: 'Automatically reviews GitHub PRs with AI and posts comments', author: 'AetherOS Labs', icon: 'git-pull-request', category: 'Development', downloads: 1240, rating: 4.8, tags: ['github', 'pr', 'review'], type: 'blueprint' },
  { id: 'mp-2', name: 'Email Digest Generator', description: 'Generates daily email digests from multiple sources', author: 'AetherOS Labs', icon: 'mail', category: 'Productivity', downloads: 892, rating: 4.6, tags: ['email', 'digest'], type: 'blueprint' },
  { id: 'mp-3', name: 'Social Media Cross-poster', description: 'Cross-post content across Twitter, LinkedIn, and Mastodon', author: 'Community', icon: 'broadcast', category: 'Social', downloads: 654, rating: 4.3, tags: ['social', 'crosspost'], type: 'workflow' },
  { id: 'mp-4', name: 'Code Review Checklist', description: 'Generate code review checklists based on diff analysis', author: 'AetherOS Labs', icon: 'checklist', category: 'Development', downloads: 2103, rating: 4.9, tags: ['code', 'review', 'checklist'], type: 'template' },
  { id: 'mp-5', name: 'Incident Response Bot', description: 'Automated incident response with Slack notifications', author: 'Community', icon: 'alert', category: 'DevOps', downloads: 456, rating: 4.5, tags: ['incident', 'response', 'slack'], type: 'blueprint' },
  { id: 'mp-6', name: 'Research Paper Collector', description: 'Collects and summarizes research papers from arXiv', author: 'AetherOS Labs', icon: 'book', category: 'Research', downloads: 789, rating: 4.7, tags: ['research', 'papers', 'arxiv'], type: 'workflow' },
  { id: 'mp-7', name: 'Data Pipeline Builder', description: 'Build ETL pipelines with drag-and-drop simplicity', author: 'AetherOS Labs', icon: 'database', category: 'Data', downloads: 567, rating: 4.4, tags: ['etl', 'data', 'pipeline'], type: 'blueprint' },
  { id: 'mp-8', name: 'Customer Feedback Analyzer', description: 'Analyze customer feedback with sentiment analysis', author: 'Community', icon: 'comment-discussion', category: 'Analytics', downloads: 345, rating: 4.2, tags: ['feedback', 'sentiment', 'analysis'], type: 'template' },
  { id: 'mp-9', name: 'DevOps Monitoring Stack', description: 'Complete monitoring stack with alerts and dashboards', author: 'AetherOS Labs', icon: 'dashboard', category: 'DevOps', downloads: 1234, rating: 4.8, tags: ['monitoring', 'devops', 'alerts'], type: 'blueprint' },
  { id: 'mp-10', name: 'SEO Content Optimizer', description: 'Optimize content for search engines automatically', author: 'Community', icon: 'search', category: 'Marketing', downloads: 234, rating: 4.1, tags: ['seo', 'content', 'optimize'], type: 'workflow' },
  { id: 'mp-11', name: 'Invoice Processor', description: 'Extract and process invoice data automatically', author: 'AetherOS Labs', icon: 'file-text', category: 'Finance', downloads: 678, rating: 4.6, tags: ['invoice', 'processing', 'ocr'], type: 'blueprint' },
  { id: 'mp-12', name: 'Meeting Transcriber', description: 'Transcribe and summarize meetings from audio', author: 'Community', icon: 'mic', category: 'Productivity', downloads: 901, rating: 4.5, tags: ['meeting', 'transcribe', 'summary'], type: 'template' },
]

const CATEGORIES = ['All', 'Development', 'DevOps', 'Productivity', 'Data', 'Research', 'Social', 'Marketing', 'Finance', 'Analytics']

export function MarketplaceView() {
  const [category, setCategory] = useState('All')
  const [searchQuery, setSearchQuery] = useState('')

  const filtered = MARKETPLACE_ITEMS.filter(item =>
    (category === 'All' || item.category === category) &&
    (item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
     item.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
     item.tags.some(t => t.includes(searchQuery.toLowerCase())))
  )

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-6 py-3">
        <div className="flex items-center gap-2">
          <Codicon className="text-primary" name="package" size="1rem" />
          <h2 className="text-base font-semibold">Workflow Marketplace</h2>
        </div>
        <div className="flex items-center gap-2">
          <input
            className="w-56 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-xs text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary"
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search marketplace..."
            type="text"
            value={searchQuery}
          />
        </div>
      </div>

      <div className="flex items-center gap-1 border-b border-(--ui-stroke-tertiary) px-4 py-2 overflow-x-auto">
        {CATEGORIES.map(cat => (
          <button
            className={cn(
              'shrink-0 rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
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
        <div className="p-6">
          <div className="mb-6 grid grid-cols-4 gap-3">
            {[
              { label: 'Total Items', value: MARKETPLACE_ITEMS.length, icon: 'package' },
              { label: 'Blueprints', value: MARKETPLACE_ITEMS.filter(i => i.type === 'blueprint').length, icon: 'type-hierarchy' },
              { label: 'Templates', value: MARKETPLACE_ITEMS.filter(i => i.type === 'template').length, icon: 'library' },
              { label: 'Workflows', value: MARKETPLACE_ITEMS.filter(i => i.type === 'workflow').length, icon: 'run-all' },
            ].map(stat => (
              <div className="rounded-xl border border-(--ui-stroke-tertiary) p-3 text-center" key={stat.label}>
                <Codicon className="mx-auto mb-1 text-primary" name={stat.icon as any} size="1.25rem" />
                <div className="text-lg font-semibold tabular-nums text-foreground">{stat.value}</div>
                <div className="text-[10px] text-(--ui-text-tertiary)">{stat.label}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-3 gap-3">
            {filtered.map(item => (
              <div className="group relative rounded-xl border border-(--ui-stroke-tertiary) p-4 transition-all hover:border-primary/30 hover:shadow-lg" key={item.id}>
                <div className="flex items-start gap-3">
                  <div className={cn(
                    'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
                    item.type === 'blueprint' ? 'bg-primary/10' :
                    item.type === 'template' ? 'bg-purple-500/10' :
                    'bg-cyan-500/10'
                  )}>
                    <Codicon className={
                      item.type === 'blueprint' ? 'text-primary' :
                      item.type === 'template' ? 'text-purple-400' :
                      'text-cyan-400'
                    } name={item.icon as any} size="1.25rem" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="truncate text-sm font-medium text-foreground">{item.name}</h3>
                      <span className={cn(
                        'shrink-0 rounded px-1 py-0.5 text-[8px] font-medium uppercase',
                        item.type === 'blueprint' ? 'bg-primary/10 text-primary' :
                        item.type === 'template' ? 'bg-purple-500/10 text-purple-400' :
                        'bg-cyan-500/10 text-cyan-400'
                      )}>
                        {item.type}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-(--ui-text-tertiary) line-clamp-2">{item.description}</p>
                    <div className="mt-2 flex items-center gap-3 text-[10px] text-(--ui-text-tertiary)">
                      <span>by {item.author}</span>
                      <span className="flex items-center gap-0.5">
                        <Codicon className="text-amber-400" name="star-full" size="0.625rem" />
                        {item.rating}
                      </span>
                      <span className="flex items-center gap-0.5">
                        <Codicon name="cloud-download" size="0.625rem" />
                        {item.downloads}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap gap-1">
                  {item.tags.map(tag => (
                    <span className="rounded bg-(--ui-stroke-tertiary) px-1.5 py-0.5 text-[9px] text-(--ui-text-tertiary)" key={tag}>{tag}</span>
                  ))}
                </div>

                <Button className="mt-3 w-full opacity-0 group-hover:opacity-100 transition-opacity" size="sm">
                  <Codicon className="mr-1" name=" cloud-download" size="0.75rem" />
                  Install
                </Button>
              </div>
            ))}
          </div>

          <div className="mt-8 rounded-xl border border-dashed border-(--ui-stroke-tertiary) p-8 text-center">
            <Codicon className="mx-auto mb-2 text-(--ui-text-tertiary)" name="package" size="2rem" />
            <h3 className="text-sm font-medium text-foreground">Publish Your Own</h3>
            <p className="mt-1 text-xs text-(--ui-text-tertiary)">Package your workflow as a blueprint and share it with the community</p>
            <Button className="mt-3" size="sm" variant="outline">
              <Codicon className="mr-1" name="upload" size="0.875rem" />
              Publish to Marketplace
            </Button>
          </div>
        </div>
      </ScrollArea>
    </div>
  )
}

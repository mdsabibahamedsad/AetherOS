import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const AGENT_TEMPLATES = [
  { name: 'Code Reviewer Pro', category: 'coding', downloads: '45K', rating: 4.8, author: 'AetherOS Labs', description: 'Automated code review with inline suggestions and best practice checks.' },
  { name: 'Web Scraper', category: 'automation', downloads: '32K', rating: 4.6, author: 'DataWorks', description: 'Extract and structure data from any website.' },
  { name: 'GitHub PR Manager', category: 'devops', downloads: '28K', rating: 4.7, author: 'DevOps Inc', description: 'Automate PR review, merge, and release workflows.' },
  { name: 'Content Writer Pro', category: 'writing', downloads: '25K', rating: 4.5, author: 'ContentLab', description: 'Generate blog posts, articles, and social media content.' },
  { name: 'Database Analyst', category: 'data-analyst', downloads: '18K', rating: 4.4, author: 'DataViz', description: 'Query, analyze, and visualize database data.' },
  { name: 'Crypto Trader', category: 'automation', downloads: '15K', rating: 4.2, author: 'FinTech AI', description: 'Monitor markets and execute trades based on strategies.' },
  { name: 'Docker Manager', category: 'devops', downloads: '14K', rating: 4.6, author: 'InfraAI', description: 'Manage Docker containers, images, and compose files.' },
  { name: 'Research Assistant Pro', category: 'research', downloads: '12K', rating: 4.7, author: 'ScholarAI', description: 'Deep research with citation management and paper summaries.' }
]

const WORKFLOW_TEMPLATES = [
  { name: 'Code Review Pipeline', type: 'sequential', downloads: '22K', description: 'Write → Review → Refactor → Merge pipeline' },
  { name: 'Research & Write', type: 'coordinator', downloads: '18K', description: 'Researcher gathers data, Writer produces content' },
  { name: 'Data Pipeline', type: 'parallel', downloads: '14K', description: 'Parallel data collection from multiple sources' },
  { name: 'DevOps Deploy', type: 'sequential', downloads: '11K', description: 'Build → Test → Deploy → Monitor pipeline' }
]

const CATEGORIES = [
  { id: 'all', label: 'All' },
  { id: 'coding', label: 'Coding' },
  { id: 'automation', label: 'Automation' },
  { id: 'devops', label: 'DevOps' },
  { id: 'research', label: 'Research' },
  { id: 'writing', label: 'Writing' },
  { id: 'data-analyst', label: 'Data' }
]

export function Marketplace() {
  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="border-b px-6 py-4">
        <h2 className="text-lg font-semibold">Marketplace</h2>
        <p className="text-sm text-muted-foreground">Discover agent templates, workflows, and automation packs</p>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-5xl space-y-10">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Featured Agent Templates</h3>
              <div className="flex gap-1">
                {CATEGORIES.map(cat => (
                  <button className={cn('rounded-full px-3 py-1 text-xs font-medium transition-colors', cat.id === 'all' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent')} key={cat.id} type="button">
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-4 gap-4">
              {AGENT_TEMPLATES.map(tmpl => (
                <div className="group relative rounded-xl border p-4 transition-all hover:border-primary/30 hover:shadow-sm" key={tmpl.name}>
                  <div className="mb-3 flex items-start justify-between">
                    <Badge className="text-[10px] capitalize" variant="outline">{tmpl.category}</Badge>
                    <div className="flex items-center gap-1 text-xs text-yellow-500">
                      <svg className="h-3 w-3 fill-current" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>
                      {tmpl.rating}
                    </div>
                  </div>
                  <h4 className="font-medium text-sm">{tmpl.name}</h4>
                  <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{tmpl.description}</p>
                  <div className="mt-3 flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">{tmpl.downloads} downloads</span>
                    <Button size="sm" variant="outline">Install</Button>
                  </div>
                  <div className="mt-1 text-[10px] text-muted-foreground">by {tmpl.author}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Workflow Templates</h3>
            <div className="grid grid-cols-4 gap-4">
              {WORKFLOW_TEMPLATES.map(wf => (
                <div className="rounded-xl border p-4 transition-all hover:border-primary/30" key={wf.name}>
                  <div className="mb-3">
                    <Badge className="text-[10px] capitalize" variant="secondary">{wf.type}</Badge>
                  </div>
                  <h4 className="font-medium text-sm">{wf.name}</h4>
                  <p className="mt-1 text-xs text-muted-foreground">{wf.description}</p>
                  <div className="mt-3 flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">{wf.downloads} downloads</span>
                    <Button size="sm" variant="outline">Install</Button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border bg-gradient-to-br from-primary/5 to-primary/0 p-8 text-center">
            <h3 className="text-lg font-semibold">Publish Your Agent</h3>
            <p className="mt-2 text-sm text-muted-foreground max-w-md mx-auto">
              Created an amazing agent? Share it with the community on the AetherOS Marketplace.
            </p>
            <Button className="mt-4">Submit Agent</Button>
          </div>
        </div>
      </div>
    </div>
  )
}

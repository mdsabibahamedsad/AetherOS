import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Codicon } from '@/components/ui/codicon'

export function HelpView() {
  const links = [
    { icon: 'book', label: 'Documentation', desc: 'Read the AetherOS documentation', url: 'https://aetheros.ai/docs' },
    { icon: 'comment-discussion', label: 'Community', desc: 'Join the AetherOS community', url: 'https://discord.gg/aetheros' },
    { icon: 'github', label: 'GitHub', desc: 'View the source code', url: 'https://github.com/aetheros/aetheros' },
    { icon: 'question', label: 'FAQ', desc: 'Frequently asked questions', url: 'https://aetheros.ai/faq' },
    { icon: 'report', label: 'Report Issue', desc: 'File a bug report or feature request', url: 'https://github.com/aetheros/aetheros/issues' }
  ]

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>Help</PageTitle>
            <PageDescription>Documentation and support resources</PageDescription>
          </div>
        </PageHeader>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2">
        {links.map(link => (
          <a
            className="flex items-start gap-3 rounded-xl border border-(--ui-stroke-tertiary) p-4 transition-colors hover:bg-(--ui-control-hover-background)"
            href={link.url}
            key={link.label}
            rel="noreferrer"
            target="_blank"
          >
            <Codicon className="mt-0.5 shrink-0 text-(--ui-text-tertiary)" name={link.icon as any} size="1.25rem" />
            <div>
              <h3 className="text-sm font-medium">{link.label}</h3>
              <p className="mt-0.5 text-xs text-(--ui-text-tertiary)">{link.desc}</p>
            </div>
          </a>
        ))}
      </div>
    </PageShell>
  )
}

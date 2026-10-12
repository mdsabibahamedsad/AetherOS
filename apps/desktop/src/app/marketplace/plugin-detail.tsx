import { useCallback, useState } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { useI18n } from '@/i18n'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'

interface PluginAuthor {
  name: string
  avatar?: string
  url?: string
}

interface PluginVersion {
  version: string
  changelog?: string
  date: string
  requires?: string[]
}

interface PluginDependency {
  name: string
  version: string
  optional?: boolean
}

interface PluginPermission {
  name: string
  description: string
  required: boolean
}

interface PluginReview {
  id: string
  author: string
  rating: number
  comment: string
  date: string
}

export interface PluginDetailInfo {
  id: string
  name: string
  description: string
  longDescription?: string
  icon: string
  author: PluginAuthor
  version: string
  latestVersion?: string
  license: string
  homepage?: string
  repository?: string
  category: string
  rating: number
  downloads: number
  verified: boolean
  featured: boolean
  trending: boolean
  installed: boolean
  enabled: boolean
  installProgress?: number
  versions: PluginVersion[]
  dependencies: PluginDependency[]
  permissions: PluginPermission[]
  reviews: PluginReview[]
  screenshots: string[]
  readme?: string
  tags: string[]
}

interface PluginDetailViewProps {
  installing: boolean
  onBack: () => void
  onInstall: () => void
  onUpdate: () => void
  onRemove: () => void
  onEnableDisable: () => void
  onRollback?: (version: string) => void
  plugin: PluginDetailInfo
}

export function PluginDetailView({
  installing,
  onBack,
  onInstall,
  onUpdate,
  onRemove,
  onEnableDisable,
  onRollback,
  plugin
}: PluginDetailViewProps) {
  const { t } = useI18n()
  const [activeTab, setActiveTab] = useState<'readme' | 'versions' | 'deps' | 'permissions' | 'reviews'>('readme')
  const [currentScreenshot, setCurrentScreenshot] = useState(0)
  const [newReviewRating, setNewReviewRating] = useState(5)
  const [newReviewComment, setNewReviewComment] = useState('')
  const [submittingReview, setSubmittingReview] = useState(false)

  const hasUpdate = plugin.latestVersion && plugin.latestVersion !== plugin.version

  const handleSubmitReview = useCallback(async () => {
    if (!newReviewComment.trim()) {return}
    setSubmittingReview(true)
    await new Promise(r => setTimeout(r, 500))
    notify({ kind: 'success', title: 'Review Submitted', message: 'Your review has been posted' })
    setNewReviewComment('')
    setSubmittingReview(false)
  }, [newReviewComment])

  const iconName: Record<string, string> = {
    'AI': 'brain', 'Coding': 'code', 'Productivity': 'checklist',
    'Automation': 'zap', 'Research': 'book', 'DevTools': 'tools',
    'Security': 'shield', 'Vision': 'eye', 'Speech': 'mic',
    'Translation': 'globe', 'Database': 'database', 'Cloud': 'cloud',
    'Email': 'mail', 'Communication': 'comment', 'Filesystem': 'folder',
    'Utilities': 'wrench'
  }

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div className="flex items-center gap-3">
            <Button aria-label="Go back" className="text-muted-foreground hover:text-foreground" onClick={onBack} size="icon-xs" variant="ghost">
              <Codicon name="arrow-left" size="1rem" />
            </Button>
            <div>
              <PageTitle>{plugin.name}</PageTitle>
              <PageDescription>{plugin.description}</PageDescription>
            </div>
          </div>
        </PageHeader>
      }
    >
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="flex flex-wrap gap-6 rounded-xl border border-(--ui-stroke-tertiary) p-5">
          <span className="flex size-14 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Codicon name={iconName[plugin.category] || 'package'} size="1.75rem" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">{plugin.name}</h2>
                <p className="text-sm text-muted-foreground">by {plugin.author.name}</p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {hasUpdate && (
                  <Button disabled={installing} onClick={onUpdate} size="sm" variant="default">
                    <Codicon className="mr-1" name="cloud-download" size="0.75rem" />
                    Update to v{plugin.latestVersion}
                  </Button>
                )}
                {plugin.installed ? (
                  <>
                    <Button onClick={onEnableDisable} size="sm" variant={plugin.enabled ? 'outline' : 'default'}>
                      {plugin.enabled ? 'Disable' : 'Enable'}
                    </Button>
                    {onRollback && plugin.versions.length > 1 && (
                      <Button onClick={() => onRollback(plugin.versions[plugin.versions.length - 1].version)} size="sm" variant="outline">
                        Rollback
                      </Button>
                    )}
                    <Button className="text-muted-foreground hover:text-destructive" onClick={onRemove} size="sm" variant="ghost">
                      Remove
                    </Button>
                  </>
                ) : (
                  <Button disabled={installing} onClick={onInstall} size="sm">
                    {installing ? `Installing ${plugin.installProgress}%` : `Install v${plugin.version}`}
                  </Button>
                )}
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Codicon name="package" size="0.75rem" /> v{plugin.version}
              </span>
              <span className="flex items-center gap-1">
                <Codicon name="star" size="0.75rem" /> {plugin.rating}
              </span>
              <span className="flex items-center gap-1">
                <Codicon name="download" size="0.75rem" /> {plugin.downloads.toLocaleString()}
              </span>
              <span className="flex items-center gap-1">
                <Codicon name="file-text" size="0.75rem" /> {plugin.license}
              </span>
              {plugin.homepage && (
                <a className="flex items-center gap-1 text-primary hover:underline" href={plugin.homepage} rel="noreferrer" target="_blank">
                  Homepage <Codicon name="link-external" size="0.65rem" />
                </a>
              )}
              {plugin.repository && (
                <a className="flex items-center gap-1 text-primary hover:underline" href={plugin.repository} rel="noreferrer" target="_blank">
                  Repository <Codicon name="link-external" size="0.65rem" />
                </a>
              )}
              <Badge variant={plugin.verified ? 'default' : 'outline'}>
                {plugin.verified ? 'Verified' : 'Community'}
              </Badge>
            </div>
          </div>
        </div>

        {plugin.screenshots.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Screenshots</h3>
            <div className="overflow-hidden rounded-xl border border-(--ui-stroke-tertiary)">
              <div className="flex aspect-video items-center justify-center bg-(--ui-bg-quinary)">
                <Codicon className="text-muted-foreground/40" name="image" size="3rem" />
              </div>
              {plugin.screenshots.length > 1 && (
                <div className="flex items-center justify-center gap-2 border-t border-(--ui-stroke-tertiary) px-3 py-2">
                  <Button
                    className="text-muted-foreground hover:text-foreground"
                    disabled={currentScreenshot === 0}
                    onClick={() => setCurrentScreenshot(s => s - 1)}
                    size="icon-xs"
                    variant="ghost"
                  >
                    <Codicon name="chevron-left" size="0.75rem" />
                  </Button>
                  <span className="text-xs text-muted-foreground">
                    {currentScreenshot + 1} / {plugin.screenshots.length}
                  </span>
                  <Button
                    className="text-muted-foreground hover:text-foreground"
                    disabled={currentScreenshot === plugin.screenshots.length - 1}
                    onClick={() => setCurrentScreenshot(s => s + 1)}
                    size="icon-xs"
                    variant="ghost"
                  >
                    <Codicon name="chevron-right" size="0.75rem" />
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="flex gap-1 border-b border-(--ui-stroke-tertiary)">
          {(['readme', 'versions', 'deps', 'permissions', 'reviews'] as const).map(tab => (
            <button
              className={cn(
                'border-b-2 px-3 py-2 text-xs font-medium transition-colors',
                activeTab === tab ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
              key={tab}
              onClick={() => setActiveTab(tab)}
              type="button"
            >
              {tab === 'readme' && 'README'}
              {tab === 'versions' && `Versions (${plugin.versions.length})`}
              {tab === 'deps' && `Dependencies (${plugin.dependencies.length})`}
              {tab === 'permissions' && `Permissions (${plugin.permissions.length})`}
              {tab === 'reviews' && `Reviews (${plugin.reviews.length})`}
            </button>
          ))}
        </div>

        <div className="min-h-48">
          {activeTab === 'readme' && (
            <div className="space-y-4">
              <p className="text-sm leading-relaxed text-foreground/80">
                {plugin.longDescription || plugin.readme || plugin.description}
              </p>
              {plugin.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {plugin.tags.map(tag => (
                    <Badge key={tag} variant="outline">{tag}</Badge>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'versions' && (
            <div className="space-y-2">
              {plugin.versions.map(v => (
                <div className="rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5" key={v.version}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">v{v.version}</span>
                      {v.version === plugin.version && <Badge className="text-[0.55rem]" variant="default">Current</Badge>}
                      {v.version === plugin.latestVersion && <Badge className="text-[0.55rem]" variant="warn">Latest</Badge>}
                    </div>
                    <span className="text-xs text-muted-foreground">{v.date}</span>
                  </div>
                  {v.changelog && <p className="mt-1 text-xs text-muted-foreground">{v.changelog}</p>}
                  {v.requires && v.requires.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {v.requires.map(req => (
                        <Badge key={req} variant="muted">{req}</Badge>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {activeTab === 'deps' && (
            <div className="space-y-1">
              {plugin.dependencies.length === 0 ? (
                <p className="text-sm text-muted-foreground">No dependencies</p>
              ) : (
                plugin.dependencies.map(dep => (
                  <div className="flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2" key={dep.name}>
                    <Codicon name="package" size="1rem" />
                    <div className="min-w-0 flex-1">
                      <span className="text-sm font-medium">{dep.name}</span>
                      <span className="ml-2 text-xs text-muted-foreground">{dep.version}</span>
                    </div>
                    {dep.optional ? (
                      <Badge variant="outline">Optional</Badge>
                    ) : (
                      <Badge variant="default">Required</Badge>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'permissions' && (
            <div className="space-y-1">
              {plugin.permissions.map(perm => (
                <div className="flex items-start gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2" key={perm.name}>
                  <Codicon className="mt-0.5 shrink-0 text-muted-foreground" name={perm.required ? 'lock' : 'unlock'} size="1rem" />
                  <div className="min-w-0 flex-1">
                    <span className="text-sm font-medium">{perm.name}</span>
                    <p className="text-xs text-muted-foreground">{perm.description}</p>
                  </div>
                  {perm.required ? (
                    <Badge variant="default">Required</Badge>
                  ) : (
                    <Badge variant="outline">Optional</Badge>
                  )}
                </div>
              ))}
            </div>
          )}

          {activeTab === 'reviews' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5">
                <div className="flex items-center gap-0.5">
                  {[1, 2, 3, 4, 5].map(star => (
                    <button
                      className={cn(
                        'cursor-pointer transition-colors',
                        star <= newReviewRating ? 'text-amber-500' : 'text-muted-foreground/30'
                      )}
                      key={star}
                      onClick={() => setNewReviewRating(star)}
                      type="button"
                    >
                      <Codicon name="star" size="1rem" />
                    </button>
                  ))}
                </div>
                <input
                  className="min-w-0 flex-1 bg-transparent text-xs outline-none placeholder:text-muted-foreground"
                  onChange={e => setNewReviewComment(e.target.value)}
                  placeholder="Write a review..."
                  value={newReviewComment}
                />
                <Button
                  disabled={!newReviewComment.trim() || submittingReview}
                  onClick={() => void handleSubmitReview()}
                  size="sm"
                >
                  {submittingReview ? 'Submitting...' : 'Submit'}
                </Button>
              </div>

              {plugin.reviews.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">No reviews yet. Be the first!</p>
              ) : (
                plugin.reviews.map(review => (
                  <div className="rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5" key={review.id}>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{review.author}</span>
                      <div className="flex items-center gap-1 text-xs text-amber-500">
                        <Codicon name="star" size="0.75rem" />
                        {review.rating}
                        <span className="ml-1 text-muted-foreground">{review.date}</span>
                      </div>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{review.comment}</p>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </PageShell>
  )
}



import { useStore } from '@nanostores/react'

import { cn } from '@/lib/utils'
import { $multimodal } from '@/store/multimodal'

export function PrivacyIndicators() {
  const state = useStore($multimodal)
  const { privacy } = state

  const activeIndicators = [
    { active: privacy.micActive, label: 'Mic', icon: 'M5 4.5v5a3 3 0 006 0v-5a3 3 0 00-6 0zM2 9.5v0a6 6 0 0012 0v0', color: 'text-green-500' },
    { active: privacy.cameraActive, label: 'Camera', icon: 'M1 4.5A1.5 1.5 0 012.5 3h9A1.5 1.5 0 0113 4.5v6a1.5 1.5 0 01-1.5 1.5h-9A1.5 1.5 0 011 10.5v-6zM13 6l2.5-1.5v7L13 10', color: 'text-yellow-500' },
    { active: privacy.screenActive, label: 'Screen', icon: 'M0 2.5A1.5 1.5 0 011.5 1h13A1.5 1.5 0 0116 2.5v8a1.5 1.5 0 01-1.5 1.5H10l-.5 2H12v1H4v-1h2.5l-.5-2H1.5A1.5 1.5 0 010 10.5v-8z', color: 'text-orange-500' },
    { active: privacy.dataSentToCloud, label: 'Cloud', icon: 'M3.5 7a4 4 0 01.674-7.96A5 5 0 0113 3.5 3 3 0 0113 9.5H4.5A1.5 1.5 0 013.5 7z', color: 'text-blue-400' }
  ].filter(i => i.active)

  if (activeIndicators.length === 0) {return null}

  return (
    <div className="flex items-center gap-1.5 rounded-full bg-(--ui-background-tertiary) px-2 py-1">
      <div className="flex items-center gap-1">
        {activeIndicators.map(indicator => (
          <div
            className="flex items-center gap-1 rounded-full px-1.5 py-0.5"
            key={indicator.label}
            title={`${indicator.label} active`}
          >
            <span className="relative flex h-2 w-2">
              <span className={cn('absolute inline-flex h-full w-full animate-ping rounded-full opacity-75', indicator.color.replace('text-', 'bg-'))} />
              <span className={cn('relative inline-flex h-2 w-2 rounded-full', indicator.color.replace('text-', 'bg-'))} />
            </span>
            <span className="text-[10px] font-medium text-(--ui-text-tertiary)">{indicator.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function PrivacyBanner() {
  const state = useStore($multimodal)
  const { privacy } = state

  if (!privacy.micActive && !privacy.cameraActive && !privacy.screenActive) {return null}

  return (
    <div className="flex items-center justify-center gap-2 bg-(--ui-warning-background, #fef3c7) px-3 py-1 text-xs text-(--ui-warning, #d97706)">
      <svg fill="currentColor" height="12" viewBox="0 0 16 16" width="12">
        <path d="M8 1.5a6 6 0 100 12 6 6 0 000-12zM7.5 5v3.5h1V5h-1zm0 4.5v1h1v-1h-1z" />
      </svg>
      <span>
        {[
          privacy.micActive && 'microphone',
          privacy.cameraActive && 'camera',
          privacy.screenActive && 'screen'
        ]
          .filter(Boolean)
          .join(', ')}{' '}
        active — recording in progress
      </span>
    </div>
  )
}

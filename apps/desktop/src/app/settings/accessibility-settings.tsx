import { useStore } from '@nanostores/react'

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  $accessibility,
  setAnnouncementVolume,
  setCaptionsEnabled,
  setCaptionStyle,
  setContrastMode,
  setCustomFontSize,
  setFocusIndicatorEnabled,
  setFocusIndicatorWidth,
  setFontSize,
  setHighContrastEnabled,
  setKeyboardNavigationEnabled,
  setLargeFontsEnabled,
  setReduceMotion,
  setReduceTransparency,
  setScreenReaderEnabled,
  setVoiceNavigationEnabled
} from '@/store/accessibility-store'
import type { CaptionStyle, ContrastMode, FontSize } from '@/store/accessibility-store'

function RangeSlider({ value, min, max, step, onChange, label }: {
  value: number; min: number; max: number; step: number; onChange: (v: number) => void; label: string
}) {
  return (
    <div className="flex items-center gap-3">
      <input
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-(--ui-bg-tertiary) accent-[#00D4FF]"
        max={max}
        min={min}
        onChange={e => onChange(Number(e.target.value))}
        step={step}
        type="range"
        value={value}
      />
      <span className="min-w-8 text-right text-xs text-(--ui-text-secondary)">{value}{label}</span>
    </div>
  )
}

export function AccessibilitySettings() {
  const state = useStore($accessibility)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold">Accessibility</h2>
        <p className="text-sm text-(--ui-text-tertiary)">
          Configure accessibility features for screen readers, vision, hearing, and mobility
        </p>
      </div>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Vision</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Screen Reader</div>
            <div className="text-xs text-(--ui-text-tertiary)">Enable screen reader support</div>
          </div>
          <Switch checked={state.screenReaderEnabled} onCheckedChange={setScreenReaderEnabled} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">High Contrast</div>
            <div className="text-xs text-(--ui-text-tertiary)">Increase visual contrast</div>
          </div>
          <Switch checked={state.highContrastEnabled} onCheckedChange={setHighContrastEnabled} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Contrast Mode</div>
            <div className="text-xs text-(--ui-text-tertiary)">Color contrast preset</div>
          </div>
          <Select onValueChange={v => setContrastMode(v as ContrastMode)} value={state.contrastMode}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="normal">Normal</SelectItem>
              <SelectItem value="high">High Contrast</SelectItem>
              <SelectItem value="dark">Dark Mode</SelectItem>
              <SelectItem value="light">Light Mode</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Font Size</div>
            <div className="text-xs text-(--ui-text-tertiary)">UI text size</div>
          </div>
          <Select onValueChange={v => setFontSize(v as FontSize)} value={state.fontSize}>
            <SelectTrigger className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="small">Small</SelectItem>
              <SelectItem value="normal">Normal</SelectItem>
              <SelectItem value="large">Large</SelectItem>
              <SelectItem value="xlarge">X-Large</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Large Fonts</div>
            <div className="text-xs text-(--ui-text-tertiary)">Use larger text everywhere</div>
          </div>
          <Switch checked={state.largeFontsEnabled} onCheckedChange={setLargeFontsEnabled} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Custom Font Size</div>
            <div className="text-xs text-(--ui-text-tertiary)}">Base font size in pixels</div>
          </div>
          <div className="w-32">
            <RangeSlider
              label="px"
              max={24}
              min={12}
              onChange={setCustomFontSize}
              step={1}
              value={state.customFontSize}
            />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Reduce Motion</div>
            <div className="text-xs text-(--ui-text-tertiary)">Minimize animations</div>
          </div>
          <Switch checked={state.reduceMotion} onCheckedChange={setReduceMotion} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Reduce Transparency</div>
            <div className="text-xs text-(--ui-text-tertiary)">Reduce transparent elements</div>
          </div>
          <Switch checked={state.reduceTransparency} onCheckedChange={setReduceTransparency} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Focus Indicator</div>
            <div className="text-xs text-(--ui-text-tertiary)">Show keyboard focus ring</div>
          </div>
          <Switch checked={state.focusIndicatorEnabled} onCheckedChange={setFocusIndicatorEnabled} />
        </div>

        {state.focusIndicatorEnabled && (
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">Focus Width</div>
              <div className="text-xs text-(--ui-text-tertiary)}">Focus indicator thickness</div>
            </div>
            <div className="w-32">
              <RangeSlider
                label="px"
                max={6}
                min={1}
                onChange={setFocusIndicatorWidth}
                step={1}
                value={state.focusIndicatorWidth}
              />
            </div>
          </div>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Hearing</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Captions</div>
            <div className="text-xs text-(--ui-text-tertiary)">Show captions for audio content</div>
          </div>
          <Switch checked={state.captionsEnabled} onCheckedChange={setCaptionsEnabled} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Caption Style</div>
            <div className="text-xs text-(--ui-text-tertiary)">Caption appearance</div>
          </div>
          <Select onValueChange={v => setCaptionStyle(v as CaptionStyle)} value={state.captionStyle}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="default">Default</SelectItem>
              <SelectItem value="large">Large</SelectItem>
              <SelectItem value="high_contrast">High Contrast</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Announcement Volume</div>
            <div className="text-xs text-(--ui-text-tertiary)}">Volume for screen reader</div>
          </div>
          <div className="w-32">
            <RangeSlider
              label=""
              max={1}
              min={0}
              onChange={setAnnouncementVolume}
              step={0.1}
              value={state.announcementVolume}
            />
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Mobility & Navigation</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Keyboard Navigation</div>
            <div className="text-xs text-(--ui-text-tertiary)">Full keyboard navigation support</div>
          </div>
          <Switch checked={state.keyboardNavigationEnabled} onCheckedChange={setKeyboardNavigationEnabled} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Voice Navigation</div>
            <div className="text-xs text-(--ui-text-tertiary)">Navigate using voice commands</div>
          </div>
          <Switch checked={state.voiceNavigationEnabled} onCheckedChange={setVoiceNavigationEnabled} />
        </div>
      </section>
    </div>
  )
}

import { useStore } from '@nanostores/react'

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  $accessibility,
  setAnnouncementVolume,
  setBounceKeys,
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
  setSlowKeys,
  setStickyKeys,
  setToggleKeys,
  setVoiceNavigationEnabled
} from '@/store/accessibility-store'

function RangeSlider({ value, min, max, step, onChange, label }: {
  value: number
  min: number
  max: number
  step: number
  onChange: (v: number) => void
  label: string
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
      <span className="min-w-12 text-right text-xs text-(--ui-text-secondary)">{value}{label}</span>
    </div>
  )
}

export function AccessibilitySettings() {
  const state = useStore($accessibility)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold">Accessibility</h2>
        <p className="text-sm text-(--ui-text-tertiary)">Configure accessibility features for your device</p>
      </div>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">General</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Screen Reader</div>
            <div className="text-xs text-(--ui-text-tertiary)">Enable screen reader support (requires a screen reader installed)</div>
          </div>
          <Switch checked={state.screenReaderEnabled} onCheckedChange={setScreenReaderEnabled} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Keyboard Navigation</div>
            <div className="text-xs text-(--ui-text-tertiary)">Navigate using Tab, arrow keys, and keyboard shortcuts</div>
          </div>
          <Switch checked={state.keyboardNavigationEnabled} onCheckedChange={setKeyboardNavigationEnabled} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Voice Navigation</div>
            <div className="text-xs text-(--ui-text-tertiary)">Control the interface with voice commands</div>
          </div>
          <Switch checked={state.voiceNavigationEnabled} onCheckedChange={setVoiceNavigationEnabled} />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Vision & Display</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">High Contrast</div>
            <div className="text-xs text-(--ui-text-tertiary)">Increase visual contrast for better readability</div>
          </div>
          <Switch checked={state.highContrastEnabled} onCheckedChange={setHighContrastEnabled} />
        </div>

        {state.highContrastEnabled && (
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">Contrast Mode</div>
              <div className="text-xs text-(--ui-text-tertiary)">Select contrast preset</div>
            </div>
            <Select onValueChange={v => setContrastMode(v as typeof state.contrastMode)} value={state.contrastMode}>
              <SelectTrigger className="w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="normal">Normal</SelectItem>
                <SelectItem value="high">High Contrast</SelectItem>
                <SelectItem value="dark">Dark</SelectItem>
                <SelectItem value="light">Light</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Font Size</div>
            <div className="text-xs text-(--ui-text-tertiary)">Adjust text size</div>
          </div>
          <Select onValueChange={v => setFontSize(v as typeof state.fontSize)} value={state.fontSize}>
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
            <div className="text-sm font-medium">Custom Font Size</div>
            <div className="text-xs text-(--ui-text-tertiary)">Fine-tune font size: {state.customFontSize}px</div>
          </div>
          <div className="w-48">
            <RangeSlider
              label="px"
              max={32}
              min={10}
              onChange={setCustomFontSize}
              step={1}
              value={state.customFontSize}
            />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Large Fonts</div>
            <div className="text-xs text-(--ui-text-tertiary)">Use larger font sizes throughout the UI</div>
          </div>
          <Switch checked={state.largeFontsEnabled} onCheckedChange={setLargeFontsEnabled} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Reduce Motion</div>
            <div className="text-xs text-(--ui-text-tertiary)">Minimize animations and transitions</div>
          </div>
          <Switch checked={state.reduceMotion} onCheckedChange={setReduceMotion} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Reduce Transparency</div>
            <div className="text-xs text-(--ui-text-tertiary)">Reduce transparency and blur effects</div>
          </div>
          <Switch checked={state.reduceTransparency} onCheckedChange={setReduceTransparency} />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Captions & Audio</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Captions</div>
            <div className="text-xs text-(--ui-text-tertiary)">Show captions for audio and video content</div>
          </div>
          <Switch checked={state.captionsEnabled} onCheckedChange={setCaptionsEnabled} />
        </div>

        {state.captionsEnabled && (
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">Caption Style</div>
              <div className="text-xs text-(--ui-text-tertiary)">Choose caption appearance</div>
            </div>
            <Select onValueChange={v => setCaptionStyle(v as typeof state.captionStyle)} value={state.captionStyle}>
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
        )}

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Announcement Volume</div>
            <div className="text-xs text-(--ui-text-tertiary)">Volume for screen reader announcements</div>
          </div>
          <div className="w-48">
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
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Focus & Cursor</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Focus Indicator</div>
            <div className="text-xs text-(--ui-text-tertiary)">Show visible focus rings around focused elements</div>
          </div>
          <Switch checked={state.focusIndicatorEnabled} onCheckedChange={setFocusIndicatorEnabled} />
        </div>

        {state.focusIndicatorEnabled && (
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">Focus Indicator Width</div>
              <div className="text-xs text-(--ui-text-tertiary)">Thickness of the focus ring</div>
            </div>
            <div className="w-48">
              <RangeSlider
                label="px"
                max={8}
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
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Keyboard</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Sticky Keys</div>
            <div className="text-xs text-(--ui-text-tertiary)">Press modifier keys once to lock them</div>
          </div>
          <Switch
            checked={state.stickyKeys}
            onCheckedChange={setStickyKeys}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Slow Keys</div>
            <div className="text-xs text-(--ui-text-tertiary)">Delay before key press is accepted</div>
          </div>
          <Switch checked={state.slowKeys} onCheckedChange={setSlowKeys} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Bounce Keys</div>
            <div className="text-xs text-(--ui-text-tertiary)">Ignore accidental repeated key presses</div>
          </div>
          <Switch checked={state.bounceKeys} onCheckedChange={setBounceKeys} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Toggle Keys</div>
            <div className="text-xs text-(--ui-text-tertiary)">Play a sound when toggle keys are pressed</div>
          </div>
          <Switch checked={state.toggleKeys} onCheckedChange={setToggleKeys} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Typing Feedback</div>
            <div className="text-xs text-(--ui-text-tertiary)">Audio feedback when typing</div>
          </div>
          <Select
            onValueChange={v => $accessibility.set({ ...$accessibility.get(), typingFeedback: v as 'off' | 'sound' | 'voice' })}
            value={state.typingFeedback}
          >
            <SelectTrigger className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="off">Off</SelectItem>
              <SelectItem value="sound">Sound</SelectItem>
              <SelectItem value="voice">Voice</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </section>
    </div>
  )
}

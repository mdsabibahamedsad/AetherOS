import { atom } from 'nanostores'

export type FontSize = 'small' | 'normal' | 'large' | 'xlarge'
export type ContrastMode = 'normal' | 'high' | 'dark' | 'light'
export type CaptionStyle = 'default' | 'large' | 'high_contrast'

export interface AccessibilityState {
  screenReaderEnabled: boolean
  keyboardNavigationEnabled: boolean
  highContrastEnabled: boolean
  contrastMode: ContrastMode
  fontSize: FontSize
  customFontSize: number
  largeFontsEnabled: boolean
  captionsEnabled: boolean
  captionStyle: CaptionStyle
  voiceNavigationEnabled: boolean
  reduceMotion: boolean
  reduceTransparency: boolean
  focusIndicatorEnabled: boolean
  focusIndicatorWidth: number
  announcementVolume: number
  stickyKeys: boolean
  slowKeys: boolean
  bounceKeys: boolean
  toggleKeys: boolean
  typingFeedback: 'off' | 'sound' | 'voice'
}

export const $accessibility = atom<AccessibilityState>({
  screenReaderEnabled: false,
  keyboardNavigationEnabled: true,
  highContrastEnabled: false,
  contrastMode: 'normal',
  fontSize: 'normal',
  customFontSize: 16,
  largeFontsEnabled: false,
  captionsEnabled: false,
  captionStyle: 'default',
  voiceNavigationEnabled: false,
  reduceMotion: false,
  reduceTransparency: false,
  focusIndicatorEnabled: true,
  focusIndicatorWidth: 2,
  announcementVolume: 0.7,
  stickyKeys: false,
  slowKeys: false,
  bounceKeys: false,
  toggleKeys: false,
  typingFeedback: 'off'
})

const patch = (u: Partial<AccessibilityState>) =>
  $accessibility.set({ ...$accessibility.get(), ...u })

export function setScreenReaderEnabled(e: boolean) { patch({ screenReaderEnabled: e }) }

export function setKeyboardNavigationEnabled(e: boolean) { patch({ keyboardNavigationEnabled: e }) }

export function setHighContrastEnabled(e: boolean) { patch({ highContrastEnabled: e }) }

export function setContrastMode(m: ContrastMode) { patch({ contrastMode: m }) }

export function setFontSize(s: FontSize) { patch({ fontSize: s }) }

export function setCustomFontSize(s: number) { patch({ customFontSize: s }) }

export function setLargeFontsEnabled(e: boolean) { patch({ largeFontsEnabled: e }) }

export function setCaptionsEnabled(e: boolean) { patch({ captionsEnabled: e }) }

export function setCaptionStyle(s: CaptionStyle) { patch({ captionStyle: s }) }

export function setVoiceNavigationEnabled(e: boolean) { patch({ voiceNavigationEnabled: e }) }

export function setReduceMotion(r: boolean) { patch({ reduceMotion: r }) }

export function setReduceTransparency(r: boolean) { patch({ reduceTransparency: r }) }

export function setFocusIndicatorEnabled(e: boolean) { patch({ focusIndicatorEnabled: e }) }

export function setFocusIndicatorWidth(w: number) { patch({ focusIndicatorWidth: w }) }

export function setAnnouncementVolume(v: number) { patch({ announcementVolume: v }) }

export function setStickyKeys(e: boolean) { patch({ stickyKeys: e }) }

export function setSlowKeys(e: boolean) { patch({ slowKeys: e }) }

export function setBounceKeys(e: boolean) { patch({ bounceKeys: e }) }

export function setToggleKeys(e: boolean) { patch({ toggleKeys: e }) }

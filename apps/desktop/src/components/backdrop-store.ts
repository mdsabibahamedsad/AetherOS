import { atom } from 'nanostores'

export interface BackdropSettings {
  enabled: boolean
  opacity: number
  blendMode: string
  invert: boolean
  saturate: number
  brightness: number
  objectPosition: string
  scale: number
}

export const $backdropSettings = atom<BackdropSettings>({
  enabled: true,
  opacity: 0.025,
  blendMode: 'difference',
  invert: true,
  saturate: 1,
  brightness: 1,
  objectPosition: 'top left',
  scale: 160,
})

export const $radiusScalar = atom(0.2)

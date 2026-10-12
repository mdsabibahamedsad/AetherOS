/**
 * Marketplace store — plugin marketplace browsing state.
 */
import { atom } from 'nanostores'

export interface MarketplacePlugin {
  id: string
  name: string
  description: string
  icon: string
  author: string
  version: string
  latestVersion: string
  rating: number
  reviewCount: number
  downloadCount: number
  categories: string[]
  verified: boolean
  official: boolean
  installed: boolean
  enabled: boolean
  hasUpdate: boolean
  license: string
  homepage: string
  repository: string
  documentation: string
}

export interface MarketplaceCategory {
  id: string
  name: string
  slug: string
  icon: string
  count: number
}

export type MarketplaceSort = 'popularity' | 'downloads' | 'latest' | 'rating' | 'verified' | 'official'
export type MarketplaceViewMode = 'grid' | 'list'

export const $marketplacePlugins = atom<MarketplacePlugin[]>([])
export const $marketplaceCategories = atom<MarketplaceCategory[]>([])
export const $marketplaceLoading = atom<boolean>(false)
export const $marketplaceSearch = atom<string>('')
export const $marketplaceActiveCategory = atom<string | null>(null)
export const $marketplaceSort = atom<MarketplaceSort>('popularity')
export const $marketplaceViewMode = atom<MarketplaceViewMode>('grid')
export const $marketplaceFeatured = atom<MarketplacePlugin[]>([])
export const $marketplaceTotalCount = atom<number>(0)
export const $marketplaceCurrentPage = atom<number>(1)
export const $marketplaceInstalling = atom<string | null>(null)

export function setMarketplaceSearch(query: string) {
  $marketplaceSearch.set(query)
  $marketplaceCurrentPage.set(1)
}

export function setMarketplaceCategory(category: string | null) {
  $marketplaceActiveCategory.set(category)
  $marketplaceCurrentPage.set(1)
}

export function setMarketplaceSort(sort: MarketplaceSort) {
  $marketplaceSort.set(sort)
  $marketplaceCurrentPage.set(1)
}

export function setMarketplaceViewMode(mode: MarketplaceViewMode) {
  $marketplaceViewMode.set(mode)
}

export function setMarketplacePage(page: number) {
  $marketplaceCurrentPage.set(page)
}

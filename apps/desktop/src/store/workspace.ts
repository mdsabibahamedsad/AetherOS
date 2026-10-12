import { atom } from 'nanostores'

export interface Project {
  id: string
  name: string
  path: string
  lastOpened: number
  branch?: string
  provider?: string
  model?: string
}

export interface RecentChat {
  id: string
  title: string
  provider: string
  model: string
  lastMessage: string
  timestamp: number
  messageCount: number
}

export const $projects = atom<Project[]>([])
export const $recentChats = atom<RecentChat[]>([])
export const $currentWorkspace = atom<string | null>(null)

export function setProjects(projects: Project[]) {
  $projects.set(projects)
}

export function addProject(project: Project) {
  $projects.set([project, ...$projects.get().filter(p => p.id !== project.id)])
}

export function removeProject(id: string) {
  $projects.set($projects.get().filter(p => p.id !== id))
}

export function setRecentChats(chats: RecentChat[]) {
  $recentChats.set(chats)
}

export function addRecentChat(chat: RecentChat) {
  $recentChats.set([chat, ...$recentChats.get().filter(c => c.id !== chat.id)])
}

export function setCurrentWorkspace(path: string | null) {
  $currentWorkspace.set(path)
}

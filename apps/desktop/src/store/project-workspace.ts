import { atom, computed } from 'nanostores'

export interface ProjectFile {
  path: string
  name: string
  extension: string
  isDirectory: boolean
  size: number
  modifiedAt: number
  children?: ProjectFile[]
}

export interface ProjectMetadata {
  id: string
  name: string
  path: string
  language: string
  framework: string
  description: string
  version: string
  createdAt: number
  updatedAt: number
  lastOpenedAt: number
  isFavorite: boolean
  gitUrl: string
  buildSystem: string
  testFramework: string
  packageManager: string
}

export interface ProjectWorkspaceState {
  projects: ProjectMetadata[]
  recentProjects: ProjectMetadata[]
  favoriteProjects: ProjectMetadata[]
  currentProject: ProjectMetadata | null
  fileTree: ProjectFile[]
  fileTreeLoading: boolean
  expandedFolders: string[]
  selectedFilePath: string
  searchQuery: string
  searchResults: ProjectFile[]
  workspaceFolders: string[]
  multiRootWorkspaces: string[]
}

export const $projectWorkspace = atom<ProjectWorkspaceState>({
  projects: [],
  recentProjects: [],
  favoriteProjects: [],
  currentProject: null,
  fileTree: [],
  fileTreeLoading: false,
  expandedFolders: [],
  selectedFilePath: '',
  searchQuery: '',
  searchResults: [],
  workspaceFolders: [],
  multiRootWorkspaces: [],
})

export const $currentProject = computed($projectWorkspace, (s) => s.currentProject)
export const $currentProjectPath = computed($projectWorkspace, (s) => s.currentProject?.path ?? '')

export function setCurrentProject(project: ProjectMetadata | null) {
  const state = $projectWorkspace.get()
  $projectWorkspace.set({ ...state, currentProject: project })
}

export function updateCurrentProject(updates: Partial<ProjectMetadata>) {
  const state = $projectWorkspace.get()

  if (state.currentProject) {
    $projectWorkspace.set({ ...state, currentProject: { ...state.currentProject, ...updates } })
  }
}

export function setProjects(projects: ProjectMetadata[]) {
  const state = $projectWorkspace.get()
  $projectWorkspace.set({ ...state, projects })
}

export function setRecentProjects(projects: ProjectMetadata[]) {
  const state = $projectWorkspace.get()
  $projectWorkspace.set({ ...state, recentProjects: projects })
}

export function setFavoriteProjects(projects: ProjectMetadata[]) {
  const state = $projectWorkspace.get()
  $projectWorkspace.set({ ...state, favoriteProjects: projects })
}

export function setFileTree(tree: ProjectFile[]) {
  const state = $projectWorkspace.get()
  $projectWorkspace.set({ ...state, fileTree: tree, fileTreeLoading: false })
}

export function setFileTreeLoading(loading: boolean) {
  const state = $projectWorkspace.get()
  $projectWorkspace.set({ ...state, fileTreeLoading: loading })
}

export function toggleFolder(folderPath: string) {
  const state = $projectWorkspace.get()

  const expanded = state.expandedFolders.includes(folderPath)
    ? state.expandedFolders.filter(f => f !== folderPath)
    : [...state.expandedFolders, folderPath]

  $projectWorkspace.set({ ...state, expandedFolders: expanded })
}

export function setSelectedFile(filePath: string) {
  const state = $projectWorkspace.get()
  $projectWorkspace.set({ ...state, selectedFilePath: filePath })
}

export function addProject(project: ProjectMetadata) {
  const state = $projectWorkspace.get()
  $projectWorkspace.set({ ...state, projects: [project, ...state.projects.filter(p => p.id !== project.id)] })
}

export function removeProject(projectId: string) {
  const state = $projectWorkspace.get()
  $projectWorkspace.set({
    ...state,
    projects: state.projects.filter(p => p.id !== projectId),
    recentProjects: state.recentProjects.filter(p => p.id !== projectId),
    favoriteProjects: state.favoriteProjects.filter(p => p.id !== projectId),
    currentProject: state.currentProject?.id === projectId ? null : state.currentProject,
  })
}

export function toggleFavoriteProject(projectId: string) {
  const state = $projectWorkspace.get()
  const projects = state.projects.map(p => p.id === projectId ? { ...p, isFavorite: !p.isFavorite } : p)
  const currentProject = state.currentProject?.id === projectId ? { ...state.currentProject, isFavorite: !state.currentProject.isFavorite } : state.currentProject
  const favoriteProjects = projects.filter(p => p.isFavorite)
  $projectWorkspace.set({ ...state, projects, currentProject, favoriteProjects })
}

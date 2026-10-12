export interface Skill {
  name: string
  version: string
  description: string
  category: string
  enabled: boolean
  builtin: boolean
}

const registry: Map<string, Skill> = new Map()

function register(name: string, description: string, category: string, builtin = false, version = '1.0.0'): Skill {
  const skill: Skill = { name, version, description, category, enabled: true, builtin }
  registry.set(name, skill)

  return skill
}

export function loadBuiltinSkills(): void {
  register('code-review', 'Analyze and review code changes', 'development', true)
  register('project-analysis', 'Understand project structure and architecture', 'development', true)
  register('bug-detection', 'Find potential bugs and issues', 'quality', true)
  register('test-generation', 'Generate unit and integration tests', 'quality', true)
  register('documentation', 'Generate and update documentation', 'writing', true)
  register('research', 'Search, analyze, and summarize information', 'research', true)
  register('deployment', 'Build and deploy applications', 'devops', true)
  register('security-scan', 'Check for security vulnerabilities', 'security', true)
  register('performance-analysis', 'Analyze and optimize performance', 'optimization', true)
  register('refactoring', 'Suggest and apply code refactoring', 'development', true)
  register('dependency-check', 'Check and update dependencies', 'maintenance', true)
  register('commit-review', 'Review git commits and suggest improvements', 'development', true)
  register('browser-automation', 'Automate browser tasks', 'automation', true)
  register('terminal-assist', 'Help with terminal commands', 'automation', true)
}

export function getSkill(name: string): Skill | undefined {
  return registry.get(name)
}

export function getAllSkills(): Skill[] {
  return Array.from(registry.values())
}

export function getSkillsByCategory(category: string): Skill[] {
  return Array.from(registry.values()).filter(s => s.category === category)
}

export function enableSkill(name: string): void {
  const skill = registry.get(name)

  if (skill) {skill.enabled = true}
}

export function disableSkill(name: string): void {
  const skill = registry.get(name)

  if (skill) {skill.enabled = false}
}

export function getSkillStats(): { total: number; enabled: number; categories: number } {
  const all = Array.from(registry.values())

  return {
    total: all.length,
    enabled: all.filter(s => s.enabled).length,
    categories: new Set(all.map(s => s.category)).size
  }
}

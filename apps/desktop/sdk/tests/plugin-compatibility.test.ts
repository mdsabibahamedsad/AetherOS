import { describe, it, expect } from 'vitest'
import { createPluginContext } from '../plugin-api-v1'
import { checkPluginCompatibility } from '../deprecation-manager'
import { generateCompatReport, compareVersions } from '../sdk-compatibility-layer'

describe('SDK v1', () => {
  it('creates plugin context with correct version', () => {
    const ctx = createPluginContext({ id: 'test', name: 'Test Plugin', version: '1.0.0' })
    expect(ctx.sdkVersion).toBe('v1')
    expect(ctx.id).toBe('test')
    expect(ctx.name).toBe('Test Plugin')
  })

  it('provides all required API surfaces', () => {
    const ctx = createPluginContext({ id: 'test', name: 'Test', version: '1.0.0' })
    const required = ['system', 'files', 'dialogs', 'notifications', 'updater', 'telemetry', 'error', 'migration']
    for (const api of required) {
      expect(ctx.api).toHaveProperty(api)
    }
  })

  it('provides plugin hooks', () => {
    const ctx = createPluginContext({ id: 'test', name: 'Test', version: '1.0.0' })
    const hooks = ['onSessionStart', 'onSessionEnd', 'onToolCall', 'onToolResult', 'onAppStart', 'onAppQuit', 'onConfigChange', 'onError']
    for (const hook of hooks) {
      expect(ctx.hooks).toHaveProperty(hook)
      expect(typeof ctx.hooks[hook as keyof typeof ctx.hooks]).toBe('function')
    }
  })

  it('provides logger', () => {
    const ctx = createPluginContext({ id: 'test', name: 'Test', version: '1.0.0' })
    const levels = ['debug', 'info', 'warn', 'error']
    for (const level of levels) {
      expect(typeof ctx.log[level as keyof typeof ctx.log]).toBe('function')
    }
  })

  it('provides config store', () => {
    const ctx = createPluginContext({ id: 'test', name: 'Test', version: '1.0.0' })
    expect(typeof ctx.config.get).toBe('function')
    expect(typeof ctx.config.set).toBe('function')
    expect(typeof ctx.config.getAll).toBe('function')
    expect(typeof ctx.config.onChange).toBe('function')

    ctx.config.set('key1', 'value1')
    expect(ctx.config.get('key1')).toBe('value1')
    expect(ctx.config.get('nonexistent', 'default')).toBe('default')
  })
})

describe('Deprecation Manager', () => {
  it('detects compatible plugins', () => {
    const result = checkPluginCompatibility('1.0.0', '1.0.0')
    expect(result.compatible).toBe(true)
  })
})

describe('Compat Report', () => {
  it('generates full compatibility for matching versions', () => {
    const report = generateCompatReport('1.0.0', '1.0.0')
    expect(report.level).toBe('full')
  })
})

describe('Version Comparison', () => {
  it('correctly compares versions', () => {
    expect(compareVersions('1.0.0', '1.0.0')).toBe(0)
    expect(compareVersions('1.0.1', '1.0.0')).toBe(1)
    expect(compareVersions('1.0.0', '1.0.1')).toBe(-1)
    expect(compareVersions('2.0.0', '1.9.9')).toBe(1)
    expect(compareVersions('1.0.0', '0.9.9')).toBe(1)
  })
})

import { describe, expect, it } from 'vitest'

import { $resourceManager, addAlert, clearAlerts, updateMetric } from './resource-manager'

// The header Trash control must actually clear alerts (Master 58362: it only
// showed a toast while the store kept every alert).
describe('resource-manager alerts', () => {
  it('clearAlerts empties the alert history', () => {
    addAlert({ id: 't1', metric: 'cpu', message: 'high', timestamp: 1, severity: 'critical' })
    expect($resourceManager.get().alertHistory.length).toBeGreaterThan(0)
    clearAlerts()
    expect($resourceManager.get().alertHistory).toEqual([])
  })

  it('updateMetric appends real values to history', () => {
    updateMetric('cpu', 42)
    const cpu = $resourceManager.get().metrics.find(m => m.id === 'cpu')
    expect(cpu?.value).toBe(42)
    expect(cpu?.history[cpu.history.length - 1]).toBe(42)
  })
})

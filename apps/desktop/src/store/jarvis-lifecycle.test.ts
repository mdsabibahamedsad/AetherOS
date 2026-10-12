import { describe, expect, it } from 'vitest'

import { mapSocketToGatewayState, resetJarvisExecution, setJarvisExecution } from '@/store/jarvis-mode'
import { $jarvisExecution } from '@/store/jarvis-mode'

describe('mapSocketToGatewayState', () => {
  it('maps open to connected, degraded when health fails', () => {
    expect(mapSocketToGatewayState('open', { bootCompleted: true, reconnectAttempt: 0, healthOk: true })).toBe(
      'connected'
    )
    expect(mapSocketToGatewayState('open', { bootCompleted: true, reconnectAttempt: 0, healthOk: false })).toBe(
      'degraded'
    )
  })

  it('distinguishes connecting from reconnecting', () => {
    expect(mapSocketToGatewayState('connecting', { bootCompleted: false, reconnectAttempt: 0, healthOk: null })).toBe(
      'connecting'
    )
    expect(mapSocketToGatewayState('connecting', { bootCompleted: true, reconnectAttempt: 2, healthOk: null })).toBe(
      'reconnecting'
    )
  })

  it('never reports plain disconnected while retrying', () => {
    expect(mapSocketToGatewayState('closed', { bootCompleted: true, reconnectAttempt: 3, healthOk: null })).toBe(
      'reconnecting'
    )
    expect(mapSocketToGatewayState('closed', { bootCompleted: true, reconnectAttempt: 0, healthOk: null })).toBe(
      'disconnected'
    )
    expect(mapSocketToGatewayState('idle', { bootCompleted: false, reconnectAttempt: 0, healthOk: null })).toBe(
      'starting'
    )
  })

  it('maps error through', () => {
    expect(mapSocketToGatewayState('error', { bootCompleted: true, reconnectAttempt: 0, healthOk: null })).toBe(
      'error'
    )
  })
})

describe('$jarvisExecution', () => {
  it('transitions and resets without losing fields', () => {
    resetJarvisExecution()
    expect($jarvisExecution.get().state).toBe('IDLE')
    setJarvisExecution({ state: 'SUBMITTED', commandId: 'cmd-1', startedAt: 1 })
    expect($jarvisExecution.get().state).toBe('SUBMITTED')
    setJarvisExecution({ state: 'UNAVAILABLE', error: 'Gateway is not connected.' })
    expect($jarvisExecution.get().error).toBe('Gateway is not connected.')
    resetJarvisExecution()
    expect($jarvisExecution.get()).toEqual({
      state: 'IDLE',
      commandId: null,
      sessionId: null,
      startedAt: null,
      error: null
    })
  })
})

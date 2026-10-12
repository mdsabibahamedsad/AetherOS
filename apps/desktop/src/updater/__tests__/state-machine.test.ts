import { describe, expect, it } from 'vitest';

import { canTransition, UpdateStateMachine } from '../update-state-machine';

describe('update state machine', () => {
  it('walks the happy path', () => {
    const fsm = new UpdateStateMachine();

    for (const s of ['CHECKING', 'AVAILABLE', 'DOWNLOADING', 'VERIFYING', 'STAGING',
      'READY_TO_INSTALL', 'INSTALLING', 'RESTARTING', 'HEALTH_CHECK', 'COMPLETE'] as const) {
      fsm.transition(s);
    }

    expect(fsm.getState()).toBe('COMPLETE');
  });

  it('rejects illegal jumps (IDLE → INSTALLING skips verification)', () => {
    const fsm = new UpdateStateMachine();
    expect(() => fsm.transition('INSTALLING')).toThrow('Illegal update transition');
    expect(() => fsm.transition('COMPLETE')).toThrow();
  });

  it('routes post-activation failure to ROLLBACK, pre-activation to FAILED', () => {
    const a = new UpdateStateMachine();
    a.transition('CHECKING');
    a.fail();
    expect(a.getState()).toBe('FAILED');

    const b = new UpdateStateMachine();
    b.transition('CHECKING');
    b.transition('AVAILABLE');
    b.transition('DOWNLOADING');
    b.transition('VERIFYING');
    b.transition('STAGING');
    b.transition('READY_TO_INSTALL');
    b.transition('INSTALLING');
    b.fail();
    expect(b.getState()).toBe('ROLLBACK');
    b.transition('ROLLED_BACK');
    expect(b.getState()).toBe('ROLLED_BACK');
  });

  it('supports kill-switch BLOCKED flow', () => {
    expect(canTransition('CHECKING', 'BLOCKED')).toBe(true);
    expect(canTransition('BLOCKED', 'IDLE')).toBe(true);
    expect(canTransition('COMPLETE', 'INSTALLING')).toBe(false);
  });
});

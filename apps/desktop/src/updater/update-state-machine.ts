/**
 * Update State Machine — guarded transitions for the AetherOS update lifecycle.
 *
 * Spec (§13–§14): IDLE → CHECKING → AVAILABLE → DOWNLOADING → VERIFYING →
 * STAGING → READY_TO_INSTALL → INSTALLING → RESTARTING → HEALTH_CHECK →
 * COMPLETE, with FAILED / ROLLBACK / ROLLED_BACK / BLOCKED as side states.
 *
 * Any transition not present in TRANSITIONS is rejected so callers can
 * never silently skip VERIFYING or jump from IDLE to INSTALLING.
 */

import type { UpdateState } from './types';

type TransitionMap = Record<UpdateState, ReadonlySet<UpdateState>>;

const S = (states: UpdateState[]): ReadonlySet<UpdateState> => new Set(states);

export const UPDATE_TRANSITIONS: TransitionMap = {
  IDLE: S(['CHECKING', 'BLOCKED']),
  CHECKING: S(['AVAILABLE', 'IDLE', 'FAILED', 'BLOCKED']),
  AVAILABLE: S(['DOWNLOADING', 'IDLE', 'BLOCKED', 'FAILED']),
  DOWNLOADING: S(['VERIFYING', 'FAILED', 'IDLE', 'BLOCKED']),
  VERIFYING: S(['STAGING', 'FAILED', 'ROLLBACK', 'BLOCKED']),
  STAGING: S(['READY_TO_INSTALL', 'FAILED', 'ROLLBACK']),
  READY_TO_INSTALL: S(['INSTALLING', 'IDLE', 'FAILED', 'ROLLBACK']),
  INSTALLING: S(['RESTARTING', 'HEALTH_CHECK', 'FAILED', 'ROLLBACK']),
  RESTARTING: S(['HEALTH_CHECK', 'FAILED', 'ROLLBACK']),
  HEALTH_CHECK: S(['COMPLETE', 'FAILED', 'ROLLBACK']),
  COMPLETE: S(['IDLE', 'CHECKING']),
  FAILED: S(['IDLE', 'CHECKING', 'ROLLBACK', 'BLOCKED']),
  ROLLBACK: S(['ROLLED_BACK', 'FAILED']),
  ROLLED_BACK: S(['IDLE', 'CHECKING']),
  BLOCKED: S(['IDLE', 'CHECKING']),
};

export const TERMINAL_STATES: ReadonlySet<UpdateState> = new Set([
  'COMPLETE',
  'ROLLED_BACK',
  'BLOCKED',
  'IDLE',
]);

/** States from which it is safe to attempt recovery without rollback. */
export const RECOVERABLE_STATES: ReadonlySet<UpdateState> = new Set([
  'CHECKING',
  'AVAILABLE',
  'DOWNLOADING',
  'FAILED',
]);

/** States after which a failure MUST go through ROLLBACK, never silently IDLE. */
export const POST_ACTIVATION_STATES: ReadonlySet<UpdateState> = new Set([
  'INSTALLING',
  'RESTARTING',
  'HEALTH_CHECK',
]);

export function canTransition(from: UpdateState, to: UpdateState): boolean {
  return UPDATE_TRANSITIONS[from]?.has(to) ?? false;
}

export function assertTransition(from: UpdateState, to: UpdateState): void {
  if (!canTransition(from, to)) {
    throw new Error(`Illegal update transition: ${from} → ${to}`);
  }
}

export interface StateMachineListener {
  (from: UpdateState, to: UpdateState): void;
}

export class UpdateStateMachine {
  private state: UpdateState = 'IDLE';
  private history: Array<{ from: UpdateState; to: UpdateState; at: string }> = [];
  private listeners = new Set<StateMachineListener>();

  getState(): UpdateState {
    return this.state;
  }

  getHistory(): Array<{ from: UpdateState; to: UpdateState; at: string }> {
    return [...this.history];
  }

  onTransition(listener: StateMachineListener): () => void {
    this.listeners.add(listener);

    return () => this.listeners.delete(listener);
  }

  transition(to: UpdateState): UpdateState {
    assertTransition(this.state, to);
    const from = this.state;
    this.state = to;
    this.history.push({ from, to, at: new Date().toISOString() });

    for (const listener of this.listeners) {
      try {
        listener(from, to);
      } catch {
        // Listener errors must never break the state machine.
      }
    }

    return this.state;
  }

  /** Failure routing: post-activation failures go to ROLLBACK, else FAILED. */
  fail(): UpdateState {
    if (POST_ACTIVATION_STATES.has(this.state)) {
      return this.transition('ROLLBACK');
    }

    return this.transition('FAILED');
  }

  reset(): UpdateState {
    this.state = 'IDLE';
    this.history.push({ from: this.state, to: 'IDLE', at: new Date().toISOString() });

    return this.state;
  }
}

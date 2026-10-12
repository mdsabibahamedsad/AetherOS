import type { GatewayRequester } from './yolo-session'

export type StopSessionOutcome =
  | { stopped: true; sessionId: string }
  | { stopped: false; reason: 'no-active-session' }

/**
 * Interrupt the user's active agent session (the same `session.interrupt`
 * the overlay Stop buttons and STOP ALL use). Returns `stopped: false`
 * when there is nothing to stop instead of throwing — callers decide how
 * to surface that (palette notification, disabled button, …). Gateway
 * failures propagate so the caller can report the real error.
 */
export async function stopActiveSession(
  requestGateway: GatewayRequester,
  sessionId: string | null | undefined,
): Promise<StopSessionOutcome> {
  if (!sessionId) {
    return { stopped: false, reason: 'no-active-session' }
  }

  await requestGateway('session.interrupt', { session_id: sessionId })

  return { stopped: true, sessionId }
}

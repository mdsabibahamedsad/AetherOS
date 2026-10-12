import type { ActionStatusResponse } from '@/types/aetheros'

export interface BackupOutcome {
  /** Last log lines from the action (tail for failure display). */
  lines: string[]
  ok: boolean
}

export type ActionStatusFn = (name: string, lines?: number) => Promise<ActionStatusResponse>

const delay = (ms: number) => new Promise<void>(resolve => setTimeout(resolve, ms))

/**
 * Poll a spawned backend action (`backup`, `import`, …) until it stops
 * running, then report the real exit code. Timeouts surface as thrown
 * errors — never as fake success.
 */
export async function pollActionDone(
  getStatus: ActionStatusFn,
  name: string,
  opts: { intervalMs?: number; timeoutMs?: number } = {},
): Promise<BackupOutcome> {
  const intervalMs = opts.intervalMs ?? 1500
  const timeoutMs = opts.timeoutMs ?? 120_000
  const deadline = Date.now() + timeoutMs

  for (;;) {
    const status = await getStatus(name, 20)

    if (!status.running) {
      const ok = status.exit_code === 0

      return { lines: status.lines ?? [], ok }
    }

    if (Date.now() >= deadline) {
      throw new Error(`${name} timed out after ${Math.round(timeoutMs / 1000)}s`)
    }

    await delay(intervalMs)
  }
}

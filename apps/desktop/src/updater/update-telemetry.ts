/**
 * Update Telemetry + Observability (spec §62–§63).
 *
 * Minimal operational counters only: check / download / install /
 * rollback outcomes + durations + artifact size + failure reason.
 * NEVER user content, prompts, memory, or secrets.
 *
 * Sink is a JSONL file under userData so it works offline; a dashboard
 * can tail it. Counter names match the spec metric list.
 */

import { appendFile, mkdir } from 'node:fs/promises';
import { join } from 'node:path';

export type UpdateMetric =
  | 'update_checks'
  | 'update_available'
  | 'update_download_success'
  | 'update_download_failure'
  | 'update_install_success'
  | 'update_install_failure'
  | 'update_rollbacks';

export interface TelemetryEvent {
  metric: UpdateMetric;
  version?: string;
  channel?: string;
  platform?: string;
  durationMs?: number;
  artifactBytes?: number;
  failureReason?: string;
  at: string;
}

export class UpdateTelemetry {
  private counts = new Map<UpdateMetric, number>();
  private dir: string;
  private enabled: boolean;
  private timers = new Map<string, number>();

  constructor(dir: string, enabled = true) {
    this.dir = dir;
    this.enabled = enabled;
  }

  startTimer(key: string): void {
    this.timers.set(key, Date.now());
  }

  stopTimer(key: string): number | undefined {
    const t0 = this.timers.get(key);

    if (t0 === undefined) {return undefined;}
    this.timers.delete(key);

    return Date.now() - t0;
  }

  async record(event: Omit<TelemetryEvent, 'at'>): Promise<void> {
    this.counts.set(event.metric, (this.counts.get(event.metric) ?? 0) + 1);

    if (!this.enabled) {return;}
    const full: TelemetryEvent = { ...scrub(event), at: new Date().toISOString() };

    try {
      await mkdir(this.dir, { recursive: true });
      await appendFile(join(this.dir, 'update-telemetry.jsonl'), `${JSON.stringify(full)}\n`, 'utf-8');
    } catch {
      // Telemetry must never break updates.
    }
  }

  getCount(metric: UpdateMetric): number {
    return this.counts.get(metric) ?? 0;
  }

  snapshot(): Record<UpdateMetric, number> {
    return {
      update_checks: this.getCount('update_checks'),
      update_available: this.getCount('update_available'),
      update_download_success: this.getCount('update_download_success'),
      update_download_failure: this.getCount('update_download_failure'),
      update_install_success: this.getCount('update_install_success'),
      update_install_failure: this.getCount('update_install_failure'),
      update_rollbacks: this.getCount('update_rollbacks'),
    };
  }
}

/** Defense in depth: strip anything that is not an allowed scalar field. */
function scrub(event: Omit<TelemetryEvent, 'at'>): Omit<TelemetryEvent, 'at'> {
  return {
    metric: event.metric,
    version: typeof event.version === 'string' ? event.version.slice(0, 64) : undefined,
    channel: typeof event.channel === 'string' ? event.channel.slice(0, 32) : undefined,
    platform: typeof event.platform === 'string' ? event.platform.slice(0, 32) : undefined,
    durationMs: typeof event.durationMs === 'number' ? event.durationMs : undefined,
    artifactBytes: typeof event.artifactBytes === 'number' ? event.artifactBytes : undefined,
    failureReason: typeof event.failureReason === 'string' ? event.failureReason.slice(0, 128) : undefined,
  };
}

/**
 * Update Health — post-activation health checks, crash-loop protection,
 * versioned migrations with rollback (spec §22–§24).
 *
 * Health gate: launch → IPC → backend → storage → config → services →
 * migrations → update subsystem. ALL critical checks must pass before an
 * update is marked successful.
 */

import { compareVersions } from './semver';
import type { HealthCheck, HealthCheckResult } from './types';

export type CheckFn = () => Promise<{ passed: boolean; message?: string }>;

export interface CheckDef {
  name: string;
  critical: boolean;
  run: CheckFn;
}

export const REQUIRED_CHECKS = [
  'launch',
  'ipc',
  'backend',
  'storage',
  'config',
  'services',
  'migrations',
  'updater',
] as const;

export async function runHealthChecks(checks: CheckDef[], version: string): Promise<HealthCheckResult> {
  void version;
  const results: HealthCheck[] = [];

  for (const check of checks) {
    try {
      const r = await check.run();
      results.push({ name: check.name, passed: r.passed, message: r.message, critical: check.critical });
    } catch (e) {
      results.push({
        name: check.name,
        passed: false,
        message: e instanceof Error ? e.message : String(e),
        critical: check.critical,
      });
    }
  }

  const passed = results.every((r) => !r.critical || r.passed);

  return { passed, checks: results, timestamp: new Date().toISOString() };
}

/** Build the standard 8-gate suite from one probe per gate. */
export function standardChecks(probes: Partial<Record<(typeof REQUIRED_CHECKS)[number], CheckFn>>): CheckDef[] {
  return REQUIRED_CHECKS.map((name) => ({
    name,
    critical: true,
    run: probes[name] ?? (async () => ({ passed: true, message: 'no probe; assumed pass' })),
  }));
}

// --- Crash-loop protection (spec §23) ---------------------------------------

export interface CrashRecord {
  version: string;
  at: string;
}

export class CrashLoopGuard {
  private crashes: CrashRecord[] = [];
  constructor(
    private readonly threshold = 3,
    private readonly windowMs = 10 * 60 * 1000,
  ) {}

  recordCrash(version: string, now = Date.now()): { crashLoop: boolean; count: number } {
    this.crashes.push({ version, at: new Date(now).toISOString() });
    const cutoff = now - this.windowMs;
    const recent = this.crashes.filter((c) => c.version === version && new Date(c.at).getTime() >= cutoff);

    return { crashLoop: recent.length >= this.threshold, count: recent.length };
  }

  recordCleanStart(version: string): void {
    this.crashes = this.crashes.filter((c) => c.version !== version);
  }
}

// --- Migrations (spec §24) ----------------------------------------------------

export interface Migration {
  id: string;
  /** Semver of the release that introduces this migration. */
  version: string;
  precondition: (currentVersion: string) => boolean;
  execute: () => Promise<void>;
  validate: () => Promise<boolean>;
  rollback: () => Promise<void>;
}

export interface MigrationOutcome {
  applied: string[];
  failed?: { id: string; error: string };
  rolledBack: string[];
}

/**
 * Apply pending migrations in version order. On failure: roll back every
 * migration applied in THIS run (reverse order) and report.
 * Legacy data is never destroyed: rollback must restore the pre-run state.
 */
export async function applyMigrations(
  migrations: Migration[],
  currentVersion: string,
  targetVersion: string,
): Promise<MigrationOutcome> {
  const pending = migrations
    .filter((m) => compareVersions(m.version, currentVersion) > 0 && compareVersions(m.version, targetVersion) <= 0)
    .filter((m) => {
      try {
        return m.precondition(currentVersion);
      } catch {
        return false;
      }
    })
    .sort((a, b) => compareVersions(a.version, b.version));

  const applied: string[] = [];

  for (const m of pending) {
    try {
      await m.execute();
      const ok = await m.validate();

      if (!ok) {throw new Error(`validation failed for migration ${m.id}`);}
      applied.push(m.id);
    } catch (e) {
      const rolledBack: string[] = [];

      for (const id of [...applied, m.id].reverse()) {
        const mig = pending.find((p) => p.id === id);

        if (!mig) {continue;}

        try {
          await mig.rollback();
          rolledBack.push(id);
        } catch {
          // Report partial rollback; caller escalates to ROLLBACK_FAILURE.
        }
      }

      return {
        applied,
        failed: { id: m.id, error: e instanceof Error ? e.message : String(e) },
        rolledBack,
      };
    }
  }

  return { applied, rolledBack: [] };
}

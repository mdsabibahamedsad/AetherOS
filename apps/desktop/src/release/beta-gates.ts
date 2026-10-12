/**
 * Beta rollout gates + exit criteria (Master 74 §§3, 13–14, 52, 87–90).
 *
 * Pure functions — no I/O, no fabrication. Every evaluator takes either
 * measured inputs or null (telemetry unavailable) and returns an explicit
 * status. Missing telemetry yields UNVERIFIED, never a pass.
 */

export type BetaChannel = 'dev' | 'alpha' | 'beta' | 'rc' | 'stable' | 'enterprise';

export interface ChannelPolicy {
  channel: BetaChannel;
  versionPattern: string;
  signedArtifactsRequired: boolean;
  sbomRequired: boolean;
  provenanceRequired: boolean;
  maxRolloutStartPct: number;
  autoPromote: boolean;
  telemetryRequired: boolean;
  retainReleases: number;
  rollbackRequired: boolean;
}

export const CHANNEL_POLICIES: Record<BetaChannel, ChannelPolicy> = {
  dev: {
    channel: 'dev', versionPattern: '*-dev.*', signedArtifactsRequired: false,
    sbomRequired: false, provenanceRequired: false, maxRolloutStartPct: 100,
    autoPromote: false, telemetryRequired: false, retainReleases: 5, rollbackRequired: false,
  },
  alpha: {
    channel: 'alpha', versionPattern: '*-alpha.*', signedArtifactsRequired: true,
    sbomRequired: false, provenanceRequired: true, maxRolloutStartPct: 25,
    autoPromote: false, telemetryRequired: false, retainReleases: 5, rollbackRequired: true,
  },
  beta: {
    channel: 'beta', versionPattern: '*-beta.*', signedArtifactsRequired: true,
    sbomRequired: true, provenanceRequired: true, maxRolloutStartPct: 10,
    autoPromote: false, telemetryRequired: true, retainReleases: 3, rollbackRequired: true,
  },
  rc: {
    channel: 'rc', versionPattern: '*-rc.*', signedArtifactsRequired: true,
    sbomRequired: true, provenanceRequired: true, maxRolloutStartPct: 50,
    autoPromote: false, telemetryRequired: true, retainReleases: 3, rollbackRequired: true,
  },
  stable: {
    channel: 'stable', versionPattern: '^[0-9]+\\.[0-9]+\\.[0-9]+$', signedArtifactsRequired: true,
    sbomRequired: true, provenanceRequired: true, maxRolloutStartPct: 5,
    autoPromote: false, telemetryRequired: true, retainReleases: 3, rollbackRequired: true,
  },
  enterprise: {
    channel: 'enterprise', versionPattern: '^[0-9]+\\.[0-9]+\\.[0-9]+$', signedArtifactsRequired: true,
    sbomRequired: true, provenanceRequired: true, maxRolloutStartPct: 100,
    autoPromote: false, telemetryRequired: true, retainReleases: 5, rollbackRequired: true,
  },
};

export type GateStatus = 'PASS' | 'HOLD' | 'ROLLBACK' | 'UNVERIFIED';

export interface RolloutMetrics {
  crashRatePct: number | null;
  startupFailurePct: number | null;
  updateFailurePct: number | null;
  authFailurePct: number | null;
  securityAlerts: number | null;
  userReportedCritical: number | null;
}

export interface GateThresholds {
  maxCrashRatePct: number;
  maxStartupFailurePct: number;
  maxUpdateFailurePct: number;
  maxAuthFailurePct: number;
}

export const DEFAULT_THRESHOLDS: GateThresholds = {
  maxCrashRatePct: 2,
  maxStartupFailurePct: 1,
  maxUpdateFailurePct: 5,
  maxAuthFailurePct: 1,
};

export interface GateDecision {
  status: GateStatus;
  reasons: string[];
}

/**
 * Evaluate whether a rollout may advance. Any breached threshold → HOLD;
 * security alert or critical user report → ROLLBACK; any missing metric →
 * UNVERIFIED (never invent numbers).
 */
export function evaluateRolloutGate(metrics: RolloutMetrics, thresholds: GateThresholds = DEFAULT_THRESHOLDS): GateDecision {
  const reasons: string[] = [];
  let unverified = false;
  let hold = false;

  const check = (label: string, value: number | null, max: number): void => {
    if (value === null || !Number.isFinite(value)) {
      unverified = true;
      reasons.push(`${label}: UNVERIFIED (no telemetry)`);

      return;
    }

    if (value > max) {
      hold = true;
      reasons.push(`${label}: ${value}% exceeds threshold ${max}% → HOLD`);
    } else {
      reasons.push(`${label}: ${value}% within threshold ${max}%`);
    }
  };

  check('crashRate', metrics.crashRatePct, thresholds.maxCrashRatePct);
  check('startupFailure', metrics.startupFailurePct, thresholds.maxStartupFailurePct);
  check('updateFailure', metrics.updateFailurePct, thresholds.maxUpdateFailurePct);
  check('authFailure', metrics.authFailurePct, thresholds.maxAuthFailurePct);

  if (metrics.securityAlerts === null || metrics.userReportedCritical === null) {
    unverified = true;
    reasons.push('security/user signals: UNVERIFIED (no telemetry)');
  } else {
    if (metrics.securityAlerts > 0) {
      return { status: 'ROLLBACK', reasons: [...reasons, `securityAlerts: ${metrics.securityAlerts} → ROLLBACK`] };
    }

    if (metrics.userReportedCritical > 0) {
      return { status: 'ROLLBACK', reasons: [...reasons, `userReportedCritical: ${metrics.userReportedCritical} → ROLLBACK`] };
    }

    reasons.push('security/user signals: clear');
  }

  if (hold) {
    return { status: 'HOLD', reasons };
  }

  if (unverified) {
    return { status: 'UNVERIFIED', reasons };
  }

  return { status: 'PASS', reasons };
}

// --- Beta exit criteria (§52) -------------------------------------------------

export type ExitCategory =
  | 'p0' | 'security' | 'artifacts' | 'update' | 'rollback'
  | 'platforms' | 'knownIssues' | 'support' | 'monitoring' | 'incidentResponse';

export interface ExitCheck {
  category: ExitCategory;
  /** true = criterion met with evidence; false = failed; null = unverified */
  met: boolean | null;
  evidence: string;
}

export interface ExitScore {
  perCategory: Array<{ category: ExitCategory; status: 'PASS' | 'FAIL' | 'UNVERIFIED'; evidence: string }>;
  overall: 'READY' | 'NOT_READY';
  blockers: string[];
}

const REQUIRED_EXIT: ExitCategory[] = [
  'p0', 'security', 'artifacts', 'update', 'rollback',
  'platforms', 'knownIssues', 'support', 'monitoring', 'incidentResponse',
];

export function evaluateBetaExit(checks: ExitCheck[]): ExitScore {
  const byCategory = new Map<ExitCategory, ExitCheck>();

  for (const c of checks) {
    byCategory.set(c.category, c);
  }

  const perCategory: ExitScore['perCategory'] = [];
  const blockers: string[] = [];

  for (const cat of REQUIRED_EXIT) {
    const c = byCategory.get(cat);

    if (!c || c.met === null) {
      perCategory.push({ category: cat, status: 'UNVERIFIED', evidence: c?.evidence ?? 'no check recorded' });
      blockers.push(`${cat}: UNVERIFIED`);
    } else if (!c.met) {
      perCategory.push({ category: cat, status: 'FAIL', evidence: c.evidence });
      blockers.push(`${cat}: FAIL — ${c.evidence}`);
    } else {
      perCategory.push({ category: cat, status: 'PASS', evidence: c.evidence });
    }
  }

  return { perCategory, overall: blockers.length === 0 ? 'READY' : 'NOT_READY', blockers };
}

// --- Performance regression hook (Master 71, §69) -----------------------------

export interface PerfSample {
  startupMs: number | null;
  memoryMB: number | null;
  agentLatencyMs: number | null;
}

export interface PerfRegression {
  metric: string;
  baseline: number;
  beta: number;
  pctChange: number;
  regressed: boolean;
}

/** Compare beta against baseline. Nulls → UNVERIFIED entry, never a pass. */
export function comparePerf(baseline: PerfSample, beta: PerfSample, maxRegressionPct: number): { regressions: PerfRegression[]; unverified: string[] } {
  const regressions: PerfRegression[] = [];
  const unverified: string[] = [];

  const metrics: Array<[string, number | null, number | null]> = [
    ['startupMs', baseline.startupMs, beta.startupMs],
    ['memoryMB', baseline.memoryMB, beta.memoryMB],
    ['agentLatencyMs', baseline.agentLatencyMs, beta.agentLatencyMs],
  ];

  for (const [name, base, cur] of metrics) {
    if (base === null || cur === null) {
      unverified.push(name);

      continue;
    }

    const pct = base === 0 ? 0 : ((cur - base) / base) * 100;
    regressions.push({ metric: name, baseline: base, beta: cur, pctChange: pct, regressed: pct > maxRegressionPct });
  }

  return { regressions, unverified };
}

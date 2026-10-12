/**
 * AetherOS Platform Capability Registry — single source of truth.
 *
 * Values here MUST match actual implementations. Upgrade a cell only WITH
 * executable evidence (docs/AETHEROS_PLATFORM_RELEASE_MATRIX.md tracks the
 * evidence per cell):
 *
 * - Linux per-session values mirror electron/linux-session.cjs
 *   (`CAPABILITY_MATRIX`) exactly.
 * - iOS "backend-mediated" mirrors apps/ios MobileCapability (the device is a
 *   control plane; privileged execution happens server-side).
 * - Desktop reflects what apps/desktop actually ships today.
 *
 * Levels follow docs/AETHEROS_PLATFORM_ARCHITECTURE.md §6:
 *   native | backend-mediated | limited | unsupported
 */
export type CapabilityLevel = 'native' | 'backend-mediated' | 'limited' | 'unsupported';
export declare const CAPABILITY_KEYS: readonly ["browser", "terminal", "filesystem", "computerUse", "notifications", "tray", "agentControl", "taskSubmission", "planPreview", "confirmations"];
export type CapabilityKey = (typeof CAPABILITY_KEYS)[number];
export type PlatformId = 'windows-desktop' | 'macos-desktop' | 'linux-desktop-x11' | 'linux-desktop-wayland' | 'ios';
export type PlatformCapabilities = Record<CapabilityKey, CapabilityLevel>;
export declare const PLATFORM_CAPABILITIES: Record<PlatformId, PlatformCapabilities>;
/** Map a runtime platform + optional Linux session type to a registry entry. */
export declare function resolvePlatform(platform: 'win32' | 'darwin' | 'linux' | 'ios', linuxSession?: 'x11' | 'wayland' | 'x11-forwarded' | 'wslg' | 'headless'): PlatformId | null;
export declare function capabilityLevel(platform: PlatformId, key: CapabilityKey): CapabilityLevel;
/** Shared confirmation language across platforms. */
export declare const APPROVAL_CHOICES: readonly ["once", "session", "always", "deny"];
export type ApprovalChoiceValue = (typeof APPROVAL_CHOICES)[number];
/** Shared task/run state semantics across platforms. */
export declare const RUN_STATES: readonly ["queued", "running", "awaiting_approval", "completed", "failed", "stopped"];
export type RunStateValue = (typeof RUN_STATES)[number];
//# sourceMappingURL=platform-capabilities.d.ts.map
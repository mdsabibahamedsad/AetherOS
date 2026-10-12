import Foundation

/// Mirrors docs/AETHEROS_PLATFORM_ARCHITECTURE.md §6. Clients render/hide
/// features strictly by capability level; `unsupported` never renders a
/// control that would fake success.
public enum CapabilityLevel: String, Codable, Comparable {
    case native
    case limited
    case unsupported

    public static func < (lhs: CapabilityLevel, rhs: CapabilityLevel) -> Bool {
        let rank: [CapabilityLevel: Int] = [.native: 0, .limited: 1, .unsupported: 2]
        return rank[lhs]! < rank[rhs]!
    }
}

/// What an iOS client is allowed to do relative to desktop capabilities.
/// iOS is a control plane: privileged execution always happens server-side.
public enum MobileCapability: String, CaseIterable, Identifiable {
    case conversation
    case taskSubmission = "task_submission"
    case taskMonitoring = "task_monitoring"
    case planReview = "plan_review"
    case confirmationApprovals = "confirmation_approvals"
    case remoteTerminalRequest = "remote_terminal_request"
    case notifications

    public var id: String { rawValue }

    /// Backend-mediated by definition; a mobile device never executes tools.
    public var level: CapabilityLevel {
        switch self {
        case .conversation, .taskSubmission, .taskMonitoring, .planReview,
             .confirmationApprovals, .remoteTerminalRequest:
            return .limited // backend-mediated: requires a reachable, authorized backend
        case .notifications:
            return .native
        }
    }

    /// What this device genuinely does natively (control-plane actions).
    static let deviceCapabilities: [String] = [
        "task submission & monitoring",
        "plan review",
        "approval decisions",
        "activity history",
        "notifications"
    ]

    /// Desktop-only surfaces that MUST NOT appear as available on-device.
    static let neverAvailableOnDevice: [String] = [
        "shell execution",
        "host filesystem access",
        "desktop window management",
        "screen capture",
        "mouse/keyboard automation",
        "direct browser automation"
    ]
}

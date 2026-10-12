import Foundation

/// Wire models for the shared backend contract.
/// See docs/AETHEROS_CROSS_PLATFORM_API.md. Decoding is deliberately tolerant:
/// unknown/missing optional fields never break the client.

public struct APIErrorEnvelope: Codable, Error {
    public struct Body: Codable {
        public var message: String?
        public var type: String?
        public var param: String?
        public var code: String?
    }

    public var error: Body?
}

/// Liveness from GET /health (unauthenticated per the shared contract).
public struct HealthStatus: Codable, Equatable {
    public var status: String?
    public var version: String?
}

/// One streamed step of a run's execution plan/progress. Sourced ONLY from
/// real backend events on GET /v1/runs/{id}/events — the client never invents
/// steps or marks anything done without a server frame saying so.
public struct PlanStep: Identifiable, Equatable {
    public enum Kind: String {
        case tool, approval, completion, error, info
    }

    public var id: String
    public var kind: Kind
    public var title: String
    public var detail: String?
    public var at: Date

    public init(id: String, kind: Kind, title: String, detail: String? = nil, at: Date = Date()) {
        self.id = id
        self.kind = kind
        self.title = title
        self.detail = detail
        self.at = at
    }

    /// Decodes one SSE event frame into a step. Returns nil for frames that
    /// carry no displayable step (heartbeats etc.) — malformed input is
    /// skipped, never fatal.
    public static func parse(event: String, data: Data, now: Date = Date()) -> PlanStep? {
        struct Payload: Codable {
            var tool: String?
            var status: String?
            var summary: String?
            var message: String?
            var error: String?
            var seq: Int?
        }
        guard let payload = try? JSONDecoder().decode(Payload.self, from: data) else { return nil }
        switch event {
        case "tool.start", "tool_progress", "tool.complete":
            let name = payload.tool ?? payload.summary ?? "Tool"
            return PlanStep(id: "\(event)-\(payload.seq ?? Int(now.timeIntervalSince1970))",
                            kind: .tool,
                            title: name,
                            detail: payload.status ?? payload.message)
        case "approval.request":
            return PlanStep(id: "approval-\(payload.seq ?? 0)",
                            kind: .approval,
                            title: payload.summary ?? "Approval required",
                            detail: payload.message)
        case "run.complete", "completed":
            return PlanStep(id: "done-\(payload.seq ?? 0)", kind: .completion, title: "Completed")
        case "run.error", "error":
            return PlanStep(id: "error-\(payload.seq ?? 0)",
                            kind: .error,
                            title: "Failed",
                            detail: payload.error ?? payload.message)
        default:
            // Unknown event names stay visible as info rather than dropped.
            return PlanStep(id: "\(event)-\(payload.seq ?? Int(now.timeIntervalSince1970))",
                            kind: .info,
                            title: event,
                            detail: payload.summary ?? payload.message)
        }
    }
}

public struct CapabilitiesDoc: Codable, Equatable {
    public struct Endpoint: Codable, Equatable {
        public var method: String?
        public var path: String?
    }

    public var object: String?
    public var platform: String?
    public var features: [String: Bool]?
    public var endpoints: [String: Endpoint]?

    public func feature(_ name: String) -> Bool { features?[name] ?? false }
}

public struct SessionSummary: Codable, Identifiable, Equatable {
    public var session_id: String?
    public var title: String?
    public var created_at: String?
    public var updated_at: String?
    public var message_count: Int?

    public var id: String { session_id ?? UUID().uuidString }
}

public struct ChatCompletionResponse: Codable {
    public struct Choice: Codable {
        public struct Message: Codable {
            public var role: String?
            public var content: String?
        }

        public var index: Int?
        public var message: Message?
    }

    public var id: String?
    public var choices: [Choice]?
}

public enum RunState: String, Codable {
    case queued, running, awaitingApproval = "awaiting_approval"
    case completed, failed, stopped, unknown
}

public struct RunStatus: Codable, Identifiable, Equatable {
    public var run_id: String?
    public var status: String?
    public var created_at: String?
    public var error: String?

    public var id: String { run_id ?? UUID().uuidString }

    public var state: RunState {
        guard let raw = status?.lowercased() else { return .unknown }
        if raw.contains("await") || raw.contains("approval") { return .awaitingApproval }
        switch raw {
        case "queued", "pending": return .queued
        case "running", "active": return .running
        case "completed", "complete", "succeeded", "success": return .completed
        case "failed", "error": return .failed
        case "stopped", "cancelled", "canceled": return .stopped
        default: return .unknown
        }
    }
}

public enum ApprovalChoice: String, CaseIterable, Identifiable {
    case once, session, always, deny

    public var id: String { rawValue }
}

/// A pending approval as displayed by the mobile confirmation engine.
///
/// The client NEVER decides policy: it renders what the backend asked and
/// posts one of the four choices to POST /v1/runs/{id}/approval. Fields are
/// optional so a richer future payload still decodes.
public struct ApprovalRequest: Codable, Identifiable, Equatable {
    public var run_id: String?
    public var tool: String?
    public var summary: String?
    public var risk: String?
    public var target: String?
    public var scope: String?
    public var side_effects: [String]?

    public var id: String { run_id ?? UUID().uuidString }
}

public struct JobSummary: Codable, Identifiable, Equatable {
    public var job_id: String?
    public var name: String?
    public var schedule: String?
    public var paused: Bool?

    public var id: String { job_id ?? name ?? UUID().uuidString }
}

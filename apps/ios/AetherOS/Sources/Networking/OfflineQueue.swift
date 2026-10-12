import Foundation

/// Generates stable idempotency keys so an offline-queued submission retried
/// later cannot create duplicate tasks. Same (method, path, logical payload)
/// within a session reuses one key; keys are per-process on purpose — after
/// relaunch, a user retry is a NEW intent.
public struct IdempotencyKeyFactory {
    /// Boxed so `key(for:)` can memoize without mutating the struct —
    /// APIClient.request() is intentionally non-mutating (pure request
    /// building), and value copies share one session-wide key space.
    private final class Storage {
        var seen: [String: String] = [:]
    }

    private let storage = Storage()
    private let uuid: () -> String

    public init(uuid: @escaping () -> String = { UUID().uuidString }) {
        self.uuid = uuid
    }

    public func key(for method: String, path: String) -> String {
        let slot = "\(method) \(path)"
        if let existing = storage.seen[slot] { return existing }
        let fresh = uuid()
        storage.seen[slot] = fresh
        return fresh
    }
}

/// One queued submission that may outlive connectivity.
public struct QueuedRequest: Codable, Identifiable, Equatable {
    public enum State: String, Codable {
        case pending, retrying, failed, succeeded
    }

    public var id: String
    public var method: String
    public var path: String
    public var bodyJSON: Data?
    public var state: State
    public var attempts: Int
    public var lastError: String?
    public var createdAt: Date
    public var nextAttemptAt: Date?

    public init(
        id: String = UUID().uuidString,
        method: String,
        path: String,
        bodyJSON: Data? = nil,
        state: State = .pending,
        attempts: Int = 0,
        lastError: String? = nil,
        createdAt: Date = Date(),
        nextAttemptAt: Date? = nil
    ) {
        self.id = id
        self.method = method
        self.path = path
        self.bodyJSON = bodyJSON
        self.state = state
        self.attempts = attempts
        self.lastError = lastError
        self.createdAt = createdAt
        self.nextAttemptAt = nextAttemptAt
    }
}

public enum OfflinePolicy {
    /// Exponential backoff with cap and full jitter bounds. Pure for tests:
    /// attempt 0 → ~2s … capped at 5 min. Never negative.
    public static func backoff(attempt: Int, jitter: Double = Double.random(in: 0...1)) -> TimeInterval {
        let base = min(TimeInterval(2 << max(0, min(attempt, 7))), 300)
        return base * (0.5 + jitter / 2)
    }

    /// The ONLY states the UI may render; a request must never display as
    /// succeeded without a server acknowledgment.
    public static func uiState(for record: QueuedRequest, isReachable: Bool) -> String {
        if record.state == .succeeded { return "succeeded" }
        if !isReachable { return "offline" }
        switch record.state {
        case .pending: return "pending"
        case .retrying: return "retrying"
        case .failed: return "failed"
        case .succeeded: return "succeeded"
        }
    }

    /// Whether another attempt should be made now.
    public static func shouldRetry(_ record: QueuedRequest, now: Date = Date()) -> Bool {
        guard record.state == .retrying || record.state == .pending else { return false }
        guard record.attempts < 10 else { return false }
        guard let due = record.nextAttemptAt else { return true }
        return now >= due
    }

    /// Advance a record after a failure. Validation errors (4xx) are NOT
    /// retried — retrying them can never succeed.
    public static func recordFailure(_ record: QueuedRequest, status: Int?, message: String, now: Date = Date(), jitter: Double = .random(in: 0...1)) -> QueuedRequest {
        var r = record
        r.attempts += 1
        r.lastError = message
        let clientError = (400..<500).contains(status ?? 0)
        if clientError || r.attempts >= 10 {
            r.state = .failed
            r.nextAttemptAt = nil
        } else {
            r.state = .retrying
            r.nextAttemptAt = now.addingTimeInterval(backoff(attempt: r.attempts, jitter: jitter))
        }
        return r
    }

    public static func recordSuccess(_ record: QueuedRequest) -> QueuedRequest {
        var r = record
        r.state = .succeeded
        r.lastError = nil
        r.nextAttemptAt = nil
        return r
    }
}

import Foundation

/// Real connection state — the UI must never render success for a request
/// that has not reached the backend. Five states, no aliases.
public enum ConnectionStatus: Equatable {
    case connected
    case connecting
    case offline
    case reconnecting
    case failed(String)

    public var label: String {
        switch self {
        case .connected: return "Connected"
        case .connecting: return "Connecting…"
        case .offline: return "Offline"
        case .reconnecting: return "Reconnecting…"
        case .failed: return "Connection failed"
        }
    }

    public var isUsable: Bool { self == .connected }

    /// Pure state machine. Inputs: previous state, whether the latest probe
    /// succeeded, and whether a probe is currently in flight.
    public static func next(
        previous: ConnectionStatus,
        probeSucceeded: Bool?,
        probing: Bool
    ) -> ConnectionStatus {
        if probing {
            switch previous {
            case .connected, .reconnecting:
                return previous.isUsable ? .connected : .reconnecting
            case .failed, .offline, .connecting:
                return .connecting
            }
        }
        guard let ok = probeSucceeded else { return previous }
        if ok { return .connected }
        switch previous {
        case .connected:
            return .offline
        case .connecting:
            // A first connect that never succeeded is a failure with cause,
            // not a transient offline blip.
            return .failed("Server unreachable")
        default:
            return .offline
        }
    }
}

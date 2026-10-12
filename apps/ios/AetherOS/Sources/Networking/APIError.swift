import Foundation

/// Typed error surface for the AetherOS iOS client.
///
/// Every case renders a SAFE user-facing message: no stack traces, no raw
/// server bodies beyond a trimmed message field, never tokens or headers.
/// Server-side authorization stays authoritative — these errors only
/// classify what the backend already decided.
public enum AetherosError: Error, LocalizedError, Equatable {
    /// 401 — token missing/expired/invalid.
    case authenticationError
    /// 403 — token valid but not permitted for that resource.
    case authorizationError
    /// Transport-level failure (DNS, TLS, connection dropped).
    case networkError(String)
    /// Request exceeded its timeout interval.
    case timeoutError
    /// 5xx — backend failed; message is server-provided or generic.
    case serverError(status: Int, message: String)
    /// 4xx other than auth — malformed request/rejected payload.
    case validationError(String)
    /// The run cannot proceed without an explicit human decision.
    case confirmationRequiredError(runID: String?)
    /// The client tried a capability this device deliberately does not have
    /// (see MobileCapability.neverAvailableOnDevice) or the backend
    /// capabilities doc marked unavailable.
    case unsupportedCapabilityError(String)

    public var errorDescription: String? {
        switch self {
        case .authenticationError:
            return "Authentication failed. Check the API token in Settings."
        case .authorizationError:
            return "You are not authorized for this action on the server."
        case .networkError:
            return "Cannot reach your AetherOS server. Check your connection."
        case .timeoutError:
            return "The request timed out. Your server may be busy."
        case .serverError(let status, _):
            return "Server error (\(status)). Try again shortly."
        case .validationError:
            return "The request was rejected as invalid."
        case .confirmationRequiredError:
            return "This action needs your explicit approval first."
        case .unsupportedCapabilityError(let what):
            return "\(what) is not available on iOS. Use a desktop where the capability runs."
        }
    }

    // MARK: Mapping (pure, unit-tested)

    /// Maps HTTP status + optional server envelope message onto the taxonomy.
    public static func fromHTTP(status: Int, serverMessage: String?) -> AetherosError {
        switch status {
        case 401:
            return .authenticationError
        case 403:
            return .authorizationError
        case 409:
            return .confirmationRequiredError(runID: nil)
        case 400...499:
            return .validationError(serverMessage ?? "")
        default:
            return .serverError(status: status, message: serverMessage ?? "")
        }
    }

    /// Maps URLSession transport failures. Timeout is classified explicitly.
    public static func fromURLError(_ error: URLError) -> AetherosError {
        switch error.code {
        case .timedOut:
            return .timeoutError
        default:
            return .networkError(error.localizedDescription)
        }
    }
}

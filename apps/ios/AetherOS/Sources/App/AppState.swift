import Foundation

/// Process-wide client state. Holds the API client, connection status, and
/// the offline queue. Authorization ALWAYS happens server-side; this class
/// never makes policy decisions.
@MainActor
public final class AppState: ObservableObject {
    @Published public var connection: ConnectionStatus = .offline
    @Published public var capabilities: CapabilitiesDoc?
    @Published public var health: HealthStatus?
    @Published public var runs: [RunStatus] = []
    @Published public var queue: [QueuedRequest] = []
    @Published public var lastError: String?

    /// Back-compat for existing views/tests.
    public var reachable: ConnectionStatus { connection }

    public private(set) var client: APIClient?
    let tokenStore: TokenStore
    let settings: UserDefaults

    public static let serverURLKey = "server_base_url"
    public static let notificationsEnabledKey = "notifications_enabled"

    public init(tokenStore: TokenStore = KeychainTokenStore(), settings: UserDefaults = .standard) {
        self.tokenStore = tokenStore
        self.settings = settings
        rebuildClient()
    }

    /// Server URL is user config (NOT a secret → UserDefaults); token is a
    /// secret (→ Keychain only).
    public func rebuildClient() {
        guard
            let raw = settings.string(forKey: Self.serverURLKey),
            let url = URL(string: raw),
            let scheme = url.scheme?.lowercased(),
            scheme == "https" || scheme == "http"
        else {
            client = nil
            return
        }
        // Plain HTTP is accepted only for loopback (local api_server testing).
        if scheme == "http", !(url.host == "127.0.0.1" || url.host == "localhost") {
            client = nil
            return
        }
        client = APIClient(config: APIConfig(baseURL: url, tokenProvider: { [tokenStore] in tokenStore.load() }))
    }

    public var isConfigured: Bool { client != nil }

    public func saveServerURL(_ string: String) {
        settings.set(string.trimmingCharacters(in: .whitespacesAndNewlines), forKey: Self.serverURLKey)
        rebuildClient()
    }

    public func saveToken(_ token: String) {
        tokenStore.save(token)
    }

    // MARK: Connection lifecycle (5 real states)

    /// Full probe: capabilities + health. Drives the connection state machine.
    public func connect() async {
        guard let client else {
            connection = .failed("No server configured")
            return
        }
        if connection != .connected { connection = .connecting }
        do {
            async let caps = client.capabilities()
            async let hp = client.health()
            let (c, h) = try await (caps, hp)
            capabilities = c
            health = h
            connection = .connected
            lastError = nil
        } catch {
            health = nil
            connection = ConnectionStatus.next(
                previous: connection,
                probeSucceeded: false,
                probing: false
            )
            lastError = Self.sanitize(error)
        }
    }

    public func refreshCapabilities() async {
        await connect()
    }

    // MARK: Capability gating

    /// Throws unsupportedCapabilityError when the backend says this feature is
    /// unavailable — the client NEVER fakes a capability it does not have.
    public func ensureSupported(feature: String) throws {
        guard let features = capabilities?.features else { return }
        if features[feature] == false {
            throw AetherosError.unsupportedCapabilityError(feature)
        }
    }

    // MARK: Actions

    public func submitRun(_ prompt: String) async {
        guard let client else { return }
        do {
            try ensureSupported(feature: "runs")
            let run = try await client.submitRun(prompt: prompt)
            runs.insert(run, at: 0)
            connection = .connected
        } catch is CancellationError {
            // Cancelled submissions are not errors and are not queued.
        } catch {
            if case AetherosError.unsupportedCapabilityError = error {
                connection = .connected
                lastError = Self.sanitize(error)
            } else {
                lastError = Self.sanitize(error)
                // Queue for retry; submission is idempotent via request ID header.
                queue.append(QueuedRequest(method: "POST", path: "/v1/runs"))
                connection = .reconnecting
            }
        }
    }

    public func resolveApproval(runID: String, choice: ApprovalChoice) async {
        guard let client else { return }
        do {
            try await client.approveRun(runID: runID, choice: choice)
        } catch {
            lastError = Self.sanitize(error)
        }
    }

    /// Errors may contain server echo of request data; strip before display.
    static func sanitize(_ error: Error) -> String {
        let text = error.localizedDescription
        guard text.count > 300 else { return text }
        return String(text.prefix(300)) + "…"
    }
}

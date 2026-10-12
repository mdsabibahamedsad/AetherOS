import Foundation

public struct APIConfig {
    /// Base URL of the gateway api_server, e.g. https://host.example:8443
    public var baseURL: URL
    public var tokenProvider: () -> String?

    public init(baseURL: URL, tokenProvider: @escaping () -> String?) {
        self.baseURL = baseURL
        self.tokenProvider = tokenProvider
    }
}

/// Thin async client over the shared backend contract.
/// Every request carries the bearer token; nothing is ever logged.
public struct APIClient {
    public var config: APIConfig
    public var session: URLSession
    private var idempotency: IdempotencyKeyFactory

    public init(config: APIConfig, session: URLSession = .shared) {
        self.config = config
        self.session = session
        self.idempotency = IdempotencyKeyFactory()
    }

    // MARK: Request building (pure, unit-tested)

    public func request(
        method: String,
        path: String,
        query: [URLQueryItem] = [],
        body: Data? = nil,
        idempotent: Bool = false
    ) throws -> URLRequest {
        guard var components = URLComponents(url: config.baseURL, resolvingAgainstBaseURL: false) else {
            throw AetherosError.validationError("bad base URL")
        }
        components.path = (components.path.isEmpty ? "" : components.path) + path
        if !query.isEmpty { components.queryItems = query }

        guard let url = components.url else {
            throw AetherosError.validationError("cannot build URL for \(path)")
        }

        var req = URLRequest(url: url)
        req.httpMethod = method
        req.timeoutInterval = 30
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = config.tokenProvider(), !token.isEmpty {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        // Replay protection for retryable submissions: same logical request
        // reuses one ID across offline-queue retries.
        if idempotent {
            let key = idempotency.key(for: method, path: path)
            req.setValue(key, forHTTPHeaderField: "X-Aetheros-Request-Id")
        }
        req.httpBody = body
        return req
    }

    // MARK: Core call

    @discardableResult
    private func send<T: Decodable>(_ req: URLRequest, as type: T.Type) async throws -> T {
        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: req)
        } catch let error as URLError {
            throw AetherosError.fromURLError(error)
        } catch {
            throw AetherosError.networkError(error.localizedDescription)
        }
        try Self.validate(response, data: data)
        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw AetherosError.validationError("decoding \(String(describing: T.self)) failed")
        }
    }

    static func validate(_ response: URLResponse, data: Data) throws {
        guard let http = response as? HTTPURLResponse else {
            throw AetherosError.networkError("not an HTTP response")
        }
        guard !(200...299).contains(http.statusCode) else { return }
        let envelope = try? JSONDecoder().decode(APIErrorEnvelope.self, from: data)
        let message = envelope?.error?.message
            ?? String(data: data.prefix(200), encoding: .utf8)
            ?? ""
        if http.statusCode == 409 {
            throw AetherosError.confirmationRequiredError(runID: nil)
        }
        throw AetherosError.fromHTTP(status: http.statusCode, serverMessage: message)
    }

    // MARK: Endpoints

    /// Liveness probe (unauthenticated per the shared contract §5 Health).
    public func health() async throws -> HealthStatus {
        try await send(try request(method: "GET", path: "/health"), as: HealthStatus.self)
    }

    public func capabilities() async throws -> CapabilitiesDoc {
        try await send(try request(method: "GET", path: "/v1/capabilities"), as: CapabilitiesDoc.self)
    }

    public func sessions() async throws -> [SessionSummary] {
        // The server may return a bare array or an envelope; decode permissively.
        let req = try request(method: "GET", path: "/api/sessions", query: [URLQueryItem(name: "limit", value: "50")])
        let (data, response) = try await session.data(for: req)
        try Self.validate(response, data: data)
        if let list = try? JSONDecoder().decode([SessionSummary].self, from: data) { return list }
        struct Envelope: Codable { var sessions: [SessionSummary]? }
        return (try JSONDecoder().decode(Envelope.self, from: data)).sessions ?? []
    }

    public struct TranscriptMessage: Codable, Identifiable, Equatable {
        public var role: String?
        public var content: String?

        public var id: String { "\(role ?? "msg")-\(content?.hashValue ?? 0)" }
    }

    /// Transcript for the Activity/History screen. Accepts a bare array or an
    /// envelope; both shapes exist across api_server versions.
    public func transcript(sessionID: String) async throws -> [TranscriptMessage] {
        let req = try request(method: "GET", path: "/api/sessions/\(sessionID)/messages")
        let (data, response) = try await session.data(for: req)
        try Self.validate(response, data: data)
        if let list = try? JSONDecoder().decode([TranscriptMessage].self, from: data) { return list }
        struct Envelope: Codable { var messages: [TranscriptMessage]? }
        return (try JSONDecoder().decode(Envelope.self, from: data)).messages ?? []
    }

    public func chat(sessionID: String, message: String) async throws -> String {
        struct Body: Encodable { var message: String }
        let body = try JSONEncoder().encode(Body(message: message))
        let req = try request(
            method: "POST",
            path: "/api/sessions/\(sessionID)/chat",
            body: body,
            idempotent: true
        )
        let completion = try await send(req, as: ChatCompletionResponse.self)
        return completion.choices?.first?.message?.content ?? ""
    }

    public func submitRun(prompt: String) async throws -> RunStatus {
        struct Body: Encodable { var input: String }
        let body = try JSONEncoder().encode(Body(input: prompt))
        return try await send(
            try request(method: "POST", path: "/v1/runs", body: body, idempotent: true),
            as: RunStatus.self
        )
    }

    public func runStatus(runID: String) async throws -> RunStatus {
        try await send(try request(method: "GET", path: "/v1/runs/\(runID)"), as: RunStatus.self)
    }

    public func stopRun(runID: String) async throws {
        _ = try await send(try request(method: "POST", path: "/v1/runs/\(runID)/stop"), as: RunStatus.self)
    }

    public func approveRun(runID: String, choice: ApprovalChoice) async throws {
        struct Body: Encodable { var choice: String }
        let body = try JSONEncoder().encode(Body(choice: choice.rawValue))
        _ = try await send(
            try request(method: "POST", path: "/v1/runs/\(runID)/approval", body: body),
            as: RunStatus.self
        )
    }

    public func jobs() async throws -> [JobSummary] {
        struct Envelope: Codable { var jobs: [JobSummary]? }
        let req = try request(method: "GET", path: "/api/jobs")
        let (data, response) = try await session.data(for: req)
        try Self.validate(response, data: data)
        if let list = try? JSONDecoder().decode([JobSummary].self, from: data) { return list }
        return (try? JSONDecoder().decode(Envelope.self, from: data))?.jobs ?? []
    }

    // MARK: SSE run events

    /// Consumes `event:`/`data:` SSE frames from GET /v1/runs/{id}/events.
    /// Yields decoded JSON payloads; malformed frames are skipped, never fatal.
    public func runEvents(runID: String) -> AsyncThrowingStream<(event: String, data: Data), Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    let req = try request(method: "GET", path: "/v1/runs/\(runID)/events")
                    let (bytes, response) = try await session.bytes(for: req)
                    try Self.validate(response, data: Data())
                    var eventName = "message"
                    for try await line in bytes.lines {
                        if line.hasPrefix("event:") {
                            eventName = String(line.dropFirst("event:".count)).trimmingCharacters(in: .whitespaces)
                        } else if line.hasPrefix("data:") {
                            let payload = String(line.dropFirst("data:".count)).trimmingCharacters(in: .whitespaces)
                            if let data = payload.data(using: .utf8) {
                                continuation.yield((eventName, data))
                            }
                        } else if line.isEmpty {
                            eventName = "message"
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }
}

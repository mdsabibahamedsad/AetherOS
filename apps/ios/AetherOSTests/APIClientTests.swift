import XCTest
@testable import AetherOS

/// Request-building tests use URLProtocol to avoid any real network.
final class APIClientTests: XCTestCase {
    private func makeClient(token: String? = "secret-token") -> APIClient {
        APIClient(
            config: APIConfig(baseURL: URL(string: "https://backend.example")!, tokenProvider: { token })
        )
    }

    func testRequestCarriesBearerTokenAndJSONHeaders() throws {
        let req = try makeClient().request(method: "GET", path: "/v1/capabilities")
        XCTAssertEqual(req.url?.absoluteString, "https://backend.example/v1/capabilities")
        XCTAssertEqual(req.value(forHTTPHeaderField: "Authorization"), "Bearer secret-token")
        XCTAssertEqual(req.value(forHTTPHeaderField: "Content-Type"), "application/json")
    }

    func testRequestOmitsAuthorizationWhenNoToken() throws {
        let req = try makeClient(token: nil).request(method: "GET", path: "/v1/models")
        XCTAssertNil(req.value(forHTTPHeaderField: "Authorization"))
    }

    func testIdempotentRequestsReuseOneKey() throws {
        let client = makeClient()
        let first = try client.request(method: "POST", path: "/v1/runs", idempotent: true)
        let second = try client.request(method: "POST", path: "/v1/runs", idempotent: true)
        XCTAssertEqual(
            first.value(forHTTPHeaderField: "X-Aetheros-Request-Id"),
            second.value(forHTTPHeaderField: "X-Aetheros-Request-Id"),
            "offline retries must be replay-safe"
        )
        let other = try client.request(method: "POST", path: "/api/sessions/1/chat", idempotent: true)
        XCTAssertNotEqual(first.value(forHTTPHeaderField: "X-Aetheros-Request-Id"), other.value(forHTTPHeaderField: "X-Aetheros-Request-Id"))
    }

    func testApprovalChoiceBodyMatchesBackendContract() throws {
        // Backend expects {"choice": "once"|"session"|"always"|"deny"}.
        struct Body: Encodable { var choice: String }
        for choice in ApprovalChoice.allCases {
            let data = try JSONEncoder().encode(Body(choice: choice.rawValue))
            let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: String])
            XCTAssertEqual(object["choice"], choice.rawValue)
            XCTAssertNoThrow(try approvalRequest(body: data))
        }
    }

    private func approvalRequest(body: Data) throws -> URLRequest {
        try makeClient().request(method: "POST", path: "/v1/runs/r1/approval", body: body)
    }

    func testValidateThrowsTypedErrors() {
        let ok = HTTPURLResponse(url: URL(string: "https://x")!, statusCode: 200, httpVersion: nil, headerFields: nil)!
        XCTAssertNoThrow(try APIClient.validate(ok, data: Data()))

        let unauth = HTTPURLResponse(url: URL(string: "https://x")!, statusCode: 401, httpVersion: nil, headerFields: nil)!
        XCTAssertThrowsError(try APIClient.validate(unauth, data: Data())) { error in
            XCTAssertTrue(error is AetherosError)
            XCTAssertEqual(error as? AetherosError, .authenticationError)
        }
    }

    func testCapabilitiesDecoding() throws {
        let json = """
        {
          "object": "aetheros.api_server.capabilities",
          "platform": "aetheros",
          "auth": {"type": "bearer", "required": true},
          "features": {"run_approval_response": true, "audio_api": false},
          "endpoints": {"models": {"method": "GET", "path": "/v1/models"}}
        }
        """
        let doc = try JSONDecoder().decode(CapabilitiesDoc.self, from: Data(json.utf8))
        XCTAssertEqual(doc.object, "aetheros.api_server.capabilities")
        XCTAssertTrue(doc.feature("run_approval_response"))
        XCTAssertFalse(doc.feature("audio_api"))
        XCTAssertEqual(doc.endpoints?["models"]?.path, "/v1/models")
    }

    func testRunStatusStateMapping() throws {
        func decode(_ status: String) throws -> RunStatus {
            let json = #"{"run_id": "r1", "status": "\#(status)"}"#
            return try JSONDecoder().decode(RunStatus.self, from: Data(json.utf8))
        }
        XCTAssertEqual(try decode("running").state, .running)
        XCTAssertEqual(try decode("awaiting_approval").state, .awaitingApproval)
        XCTAssertEqual(try decode("completed").state, .completed)
        XCTAssertEqual(try decode("failed").state, .failed)
        XCTAssertEqual(try decode("mystery-status").state, .unknown)
    }
}

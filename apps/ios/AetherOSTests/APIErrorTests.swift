import XCTest
@testable import AetherOS

/// Typed error taxonomy: mapping + safe user-facing messages.
final class APIErrorTests: XCTestCase {
    func testHTTPStatusMapping() {
        XCTAssertEqual(AetherosError.fromHTTP(status: 401, serverMessage: nil), .authenticationError)
        XCTAssertEqual(AetherosError.fromHTTP(status: 403, serverMessage: nil), .authorizationError)
        if case .confirmationRequiredError = AetherosError.fromHTTP(status: 409, serverMessage: nil) {} else {
            XCTFail("409 must classify as confirmationRequiredError")
        }
        if case .validationError = AetherosError.fromHTTP(status: 422, serverMessage: "bad input") {} else {
            XCTFail("4xx must classify as validationError")
        }
        if case .serverError(let status, _) = AetherosError.fromHTTP(status: 503, serverMessage: nil) {
            XCTAssertEqual(status, 503)
        } else {
            XCTFail("5xx must classify as serverError")
        }
    }

    func testTimeoutMapping() {
        let timeout = URLError(.timedOut)
        XCTAssertEqual(AetherosError.fromURLError(timeout), .timeoutError)
        let dns = URLError(.cannotFindHost)
        if case .networkError = AetherosError.fromURLError(dns) {} else {
            XCTFail("non-timeout transport failures are networkError")
        }
    }

    func testUserFacingMessagesNeverLeakServerBodies() {
        // Even a hostile server message cannot leak into the rendered text.
        let secret = "Authorization: Bearer sk-live-SECRET"
        let error = AetherosError.serverError(status: 500, message: secret)
        XCTAssertFalse(error.errorDescription?.contains(secret) ?? true)
        XCTAssertTrue(error.errorDescription?.contains("500") ?? false)

        for e in sampleErrors() {
            let text = e.errorDescription ?? ""
            XCTAssertFalse(text.lowercased().contains("bearer"))
            XCTAssertFalse(text.lowercased().contains("stack"))
            XCTAssertFalse(text.isEmpty)
        }
    }

    func testUnsupportedCapabilityMessageNamesCapability() {
        let e = AetherosError.unsupportedCapabilityError("Terminal access")
        XCTAssertEqual(e.errorDescription, "Terminal access is not available on iOS. Use a desktop where the capability runs.")
    }

    private func sampleErrors() -> [AetherosError] {
        [
            .authenticationError,
            .authorizationError,
            .networkError("dropped"),
            .timeoutError,
            .serverError(status: 500, message: "boom"),
            .validationError("nope"),
            .confirmationRequiredError(runID: "r1"),
            .unsupportedCapabilityError("Shell execution")
        ]
    }
}

/// Connection state machine: exactly five real states; success never renders
/// without a probe that reached the backend.
final class ConnectionTests: XCTestCase {
    func testFiveStatesExist() {
        let all: [ConnectionStatus] = [.connected, .connecting, .offline, .reconnecting, .failed("x")]
        XCTAssertEqual(Set(all.map(\.label)).count, 5)
        XCTAssertEqual(all.filter(\.isUsable), [.connected], "only connected may render success")
    }

    func testFirstConnectFailureIsFailedNotOffline() {
        let next = ConnectionStatus.next(previous: .connecting, probeSucceeded: false, probing: false)
        guard case .failed = next else { return XCTFail("expected failed, got \(next)") }
    }

    func testEstablishedConnectionDropsToOfflineThenReconnects() {
        let dropped = ConnectionStatus.next(previous: .connected, probeSucceeded: false, probing: false)
        XCTAssertEqual(dropped, .offline)
        let retrying = ConnectionStatus.next(previous: .offline, probeSucceeded: nil, probing: true)
        XCTAssertEqual(retrying, .connecting)
        let restored = ConnectionStatus.next(previous: .connecting, probeSucceeded: true, probing: false)
        XCTAssertEqual(restored, .connected)
    }

    func testNoStateChangeWithoutEvidence() {
        XCTAssertEqual(
            ConnectionStatus.next(previous: .offline, probeSucceeded: nil, probing: false),
            .offline
        )
    }
}

/// Plan steps come only from real SSE frames.
final class PlanStepTests: XCTestCase {
    func testParsesToolFrame() throws {
        let data = Data(#"{"tool":"terminal","status":"running","seq":1}"#.utf8)
        let step = try XCTUnwrap(PlanStep.parse(event: "tool.start", data: data))
        XCTAssertEqual(step.kind, .tool)
        XCTAssertEqual(step.title, "terminal")
    }

    func testMalformedFrameIsSkippedNotFatal() {
        XCTAssertNil(PlanStep.parse(event: "tool.start", data: Data("not json".utf8)))
    }

    func testUnknownEventStaysVisibleAsInfo() throws {
        let step = try XCTUnwrap(PlanStep.parse(event: "mystery.event", data: Data("{}".utf8)))
        XCTAssertEqual(step.kind, .info)
        XCTAssertEqual(step.title, "mystery.event")
    }

    func testCompletionAndErrorFramesClassify() throws {
        let done = try XCTUnwrap(PlanStep.parse(event: "run.complete", data: Data("{}".utf8)))
        XCTAssertEqual(done.kind, .completion)
        let err = try XCTUnwrap(PlanStep.parse(event: "run.error", data: Data(#"{"error":"boom"}"#.utf8)))
        XCTAssertEqual(err.kind, .error)
        XCTAssertEqual(err.detail, "boom")
    }
}

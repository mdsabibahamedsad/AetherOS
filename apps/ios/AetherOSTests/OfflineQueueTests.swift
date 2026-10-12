import XCTest
@testable import AetherOS

final class OfflineQueueTests: XCTestCase {
    func testBackoffGrowsAndCaps() {
        let noJitter: (Int) -> TimeInterval = { OfflinePolicy.backoff(attempt: $0, jitter: 0.5) }
        XCTAssertEqual(noJitter(0), 2, accuracy: 1.01) // ~2s ±jitter
        XCTAssertGreaterThan(noJitter(3), noJitter(0))
        let capped = OfflinePolicy.backoff(attempt: 50, jitter: 1)
        XCTAssertLessThanOrEqual(capped, 300 * 1.0)
    }

    func testFailureAdvancesToRetryingWithDueDate() {
        let record = QueuedRequest(method: "POST", path: "/v1/runs")
        let now = Date()
        let after = OfflinePolicy.recordFailure(record, status: 503, message: "unavailable", now: now, jitter: 0.5)
        XCTAssertEqual(after.state, .retrying)
        XCTAssertEqual(after.attempts, 1)
        XCTAssertNotNil(after.nextAttemptAt)
        XCTAssertFalse(OfflinePolicy.shouldRetry(after, now: now))
        XCTAssertTrue(OfflinePolicy.shouldRetry(after, now: now.addingTimeInterval(301)))
    }

    func testClientErrorsAreNeverRetried() {
        let record = QueuedRequest(method: "POST", path: "/v1/runs")
        for status in [400, 401, 404, 422] {
            let after = OfflinePolicy.recordFailure(record, status: status, message: "bad request")
            XCTAssertEqual(after.state, .failed, "status \(status) must not be retried")
            XCTAssertFalse(OfflinePolicy.shouldRetry(after))
        }
    }

    func testGivesUpAfterTenAttempts() {
        var record = QueuedRequest(method: "POST", path: "/v1/runs")
        for _ in 0..<10 {
            record = OfflinePolicy.recordFailure(record, status: 500, message: "server error", jitter: 0.5)
        }
        XCTAssertEqual(record.state, .failed)
    }

    func testUIStateMappingIsHonest() {
        let pending = QueuedRequest(method: "POST", path: "/v1/runs")
        XCTAssertEqual(OfflinePolicy.uiState(for: pending, isReachable: false), "offline")
        XCTAssertEqual(OfflinePolicy.uiState(for: pending, isReachable: true), "pending")

        let retrying = OfflinePolicy.recordFailure(pending, status: 502, message: "x")
        XCTAssertEqual(OfflinePolicy.uiState(for: retrying, isReachable: true), "retrying")

        let failed = OfflinePolicy.recordFailure(QueuedRequest(method: "POST", path: "/v1/runs"), status: 400, message: "nope")
        XCTAssertEqual(OfflinePolicy.uiState(for: failed, isReachable: true), "failed")

        let succeeded = OfflinePolicy.recordSuccess(failed)
        XCTAssertEqual(OfflinePolicy.uiState(for: succeeded, isReachable: false), "succeeded")
    }

    func testIdempotencyKeyIsStablePerLogicalRequest() {
        var factory = IdempotencyKeyFactory(uuid: { "key-\(UUID().uuidString.count)" })
        let a1 = factory.key(for: "POST", path: "/v1/runs")
        let a2 = factory.key(for: "POST", path: "/v1/runs")
        XCTAssertEqual(a1, a2, "retries of the same logical request must reuse one key")
        let b = factory.key(for: "POST", path: "/api/sessions")
        XCTAssertNotEqual(a1, b)
    }
}

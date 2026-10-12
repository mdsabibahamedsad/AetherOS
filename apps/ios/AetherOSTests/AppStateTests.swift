import XCTest
@testable import AetherOS

final class AppStateTests: XCTestCase {
    @MainActor
    func testClientRequiresHTTPSExceptLoopback() {
        let state = AppState(tokenStore: InMemoryTokenStore(), settings: UserDefaults(suiteName: "test-appstate")!)

        state.saveServerURL("https://backend.example")
        XCTAssertNotNil(state.client)

        state.saveServerURL("http://127.0.0.1:8443")
        XCTAssertNotNil(state.client, "loopback HTTP is allowed for local api_server testing")

        state.saveServerURL("http://insecure.example")
        XCTAssertNil(state.client, "plain HTTP to non-loopback hosts must be refused")

        state.saveServerURL("ftp://weird.example")
        XCTAssertNil(state.client)
    }

    @MainActor
    func testSanitizeTruncatesLongErrors() {
        let long = String(repeating: "x", count: 1000)
        let sanitized = AppState.sanitize(TestError(long))
        XCTAssertEqual(sanitized.count, 301)
    }

    private struct TestError: Error, LocalizedError {
        var errorDescription: String? { message }
        let message: String
    }
}

final class InMemoryTokenStore: TokenStore {
    private var token: String?

    func load() -> String? { token }
    func save(_ newToken: String) { token = newToken }
    func clear() { token = nil }
}

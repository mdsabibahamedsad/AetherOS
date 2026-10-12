import XCTest
@testable import AetherOS

final class DeepLinkTests: XCTestCase {
    func testParsesKnownHosts() {
        XCTAssertEqual(DeepLink.parse(URL(string: "aetheros://task/run-123")!), DeepLink(kind: .task, id: "run-123"))
        XCTAssertEqual(DeepLink.parse(URL(string: "aetheros://approval/abc-1")!), DeepLink(kind: .approval, id: "abc-1"))
        XCTAssertEqual(DeepLink.parse(URL(string: "aetheros://session/s42")!), DeepLink(kind: .session, id: "s42"))
        XCTAssertEqual(DeepLink.parse(URL(string: "aetheros://notification/n9")!), DeepLink(kind: .notification, id: "n9"))
    }

    func testAcceptsIDViaQueryParameter() {
        let link = DeepLink.parse(URL(string: "aetheros://task?id=abc_123")!)
        XCTAssertEqual(link, DeepLink(kind: .task, id: "abc_123"))
    }

    func testRejectsUnknownHostsAndSchemes() {
        XCTAssertNil(DeepLink.parse(URL(string: "aetheros://shell/rm -rf")!))
        XCTAssertNil(DeepLink.parse(URL(string: "https://example.com/task/1")!))
        XCTAssertNil(DeepLink.parse(URL(string: "evil://task/1")!))
    }

    func testRejectsEmptyOversizedOrIllegalIDs() {
        XCTAssertNil(DeepLink.parse(URL(string: "aetheros://task/")!))
        XCTAssertNil(DeepLink.parse(URL(string: "aetheros://task?id=")!))
        let oversized = String(repeating: "a", count: 129)
        XCTAssertNil(DeepLink.parse(URL(string: "aetheros://task/\(oversized)")!))
        XCTAssertNil(DeepLink.parse(URL(string: "aetheros://task/id%20with%20slash%2F..%2Fetc")!))
        XCTAssertNil(DeepLink.parse(URL(string: "aetheros://task/a;b")!))
    }
}

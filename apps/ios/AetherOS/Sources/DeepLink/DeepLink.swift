import Foundation

/// Validated `aetheros://` deep link.
///
/// Security rules (docs/AETHEROS_CROSS_PLATFORM_API.md §8):
/// - Only known hosts are accepted; unknown hosts are dropped.
/// - Parameters are length-capped and value-checked.
/// - A deep link may NAVIGATE to an approval screen but can NEVER approve
///   anything by itself, and never carries tokens or secrets.
public struct DeepLink: Equatable {
    public enum Kind: String, CaseIterable {
        case task
        case approval
        case session
        case notification
    }

    public var kind: Kind
    public var id: String

    public static func parse(_ url: URL) -> DeepLink? {
        guard url.scheme?.lowercased() == "aetheros" else { return nil }
        guard let host = url.host?.lowercased(), let kind = Kind(rawValue: host) else { return nil }

        // Path form: aetheros://task/<id> — reject empty or oversized ids.
        var rawID = url.pathComponents.filter { $0 != "/" }.first ?? ""
        if rawID.isEmpty {
            rawID = URLComponents(url: url, resolvingAgainstBaseURL: false)?
                .queryItems?
                .first(where: { $0.name == "id" })?
                .value ?? ""
        }
        let id = rawID.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !id.isEmpty, id.count <= 128 else { return nil }
        guard id.allSatisfy({ $0.isLetter || $0.isNumber || "-_.".contains($0) }) else { return nil }

        return DeepLink(kind: kind, id: id)
    }
}

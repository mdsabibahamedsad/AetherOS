import Foundation
import Security

/// Abstraction so tests can inject token behavior without touching Keychain.
public protocol TokenStore: AnyObject {
    func load() -> String?
    func save(_ token: String)
    func clear()
}

/// Tokens live ONLY in the iOS Keychain — never UserDefaults, never files,
/// never logs. Service/account names are stable for migration safety.
public final class KeychainTokenStore: TokenStore {
    private let service: String
    private let account: String

    public init(service: String = "com.aetheros.mobile", account: String = "api_token") {
        self.service = service
        self.account = account
    }

    private var baseQuery: [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
    }

    public func load() -> String? {
        var query = baseQuery
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess, let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    public func save(_ token: String) {
        guard let data = token.data(using: .utf8) else { return }

        var query = baseQuery
        // AccessibleWhenUnlocked: enough for foreground use; avoids keeping
        // the secret readable while the device is locked.
        query[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlocked
        query[kSecValueData as String] = data

        if SecItemUpdate(baseQuery as CFDictionary, [kSecValueData as String: data] as CFDictionary) == errSecItemNotFound {
            SecItemAdd(query as CFDictionary, nil)
        }
    }

    public func clear() {
        SecItemDelete(baseQuery as CFDictionary)
    }
}

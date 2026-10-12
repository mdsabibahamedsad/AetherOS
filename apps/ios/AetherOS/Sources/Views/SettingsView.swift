import SwiftUI
import UserNotifications

struct SettingsView: View {
    @EnvironmentObject var state: AppState
    @AppStorage(AetherosSettings.serverURLKey) private var serverURL = ""
    @State private var token = ""
    @State private var notificationsEnabled = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Backend") {
                    TextField("https://your-host:8443", text: $serverURL, prompt: Text("Server URL"))
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .onSubmit { state.saveServerURL(serverURL) }
                    SecureField("API token (stored in Keychain)", text: $token)
                        .onSubmit { state.saveToken(token); token = "" }
                    if let caps = state.capabilities, let object = caps.object {
                        Label(object, systemImage: "checkmark.seal")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                Section {
                    Toggle("Alerts on my devices", isOn: $notificationsEnabled)
                        .onChange(of: notificationsEnabled) { enabled in
                            // Permission is requested ONLY when the user opts
                            // in. Payloads never contain secrets.
                            AetherosSettings.setNotifications(enabled)
                        }
                } header: {
                    Text("Notifications")
                } footer: {
                    Text("Approval requests and task outcomes only. Message content is fetched after you unlock the app.")
                }

                Section("About") {
                    LabeledContent("Version", value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0.0")
                    ForEach(MobileCapability.neverAvailableOnDevice, id: \.self) { cap in
                        Label(cap, systemImage: "xmark.shield")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Settings")
        }
    }
}

enum AetherosSettings {
    static let serverURLKey = AppState.serverURLKey

    static func setNotifications(_ enabled: Bool) {
        UserDefaults.standard.set(enabled, forKey: AppState.notificationsEnabledKey)
        guard enabled else { return }
        let center = UNUserNotificationCenter.current()
        center.requestAuthorization(options: [.alert, .badge, .sound]) { _, _ in }
    }
}

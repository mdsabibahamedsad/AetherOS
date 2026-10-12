import SwiftUI

/// First-run authentication gate. The app is a secure CLIENT: it stores only
/// a user-provided server URL (UserDefaults) and API token (Keychain). There
/// are no embedded secrets and no way to bypass server-side authorization.
struct AuthGateView: View {
    @EnvironmentObject var state: AppState
    @AppStorage(AetherosSettings.serverURLKey) private var serverURL = ""
    @State private var token = ""
    @State private var busy = false
    @State private var failure: String?

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Image(systemName: "circle.hexagongrid.fill")
                    .font(.system(size: 56))
                    .foregroundStyle(.tint)
                    .accessibilityHidden(true)
                Text("AetherOS")
                    .font(.largeTitle.weight(.bold))
                Text("Connect to your AetherOS backend to run tasks, review activity, and approve agent actions.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)

                Form {
                    Section("Server") {
                        TextField("https://your-host:8443", text: $serverURL, prompt: Text("Server URL"))
                            .keyboardType(.URL)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                        SecureField("API token", text: $token)
                    }
                    Section {
                        Button {
                            Task { await signIn() }
                        } label: {
                            if busy {
                                ProgressView().frame(maxWidth: .infinity)
                            } else {
                                Text("Connect").frame(maxWidth: .infinity)
                            }
                        }
                        .disabled(serverURL.trimmingCharacters(in: .whitespaces).isEmpty || token.isEmpty || busy)
                        if let failure {
                            Text(failure)
                                .font(.footnote)
                                .foregroundStyle(.red)
                        }
                    } footer: {
                        Text("The token is stored in the iOS Keychain. Authorization is enforced by your server; this app cannot grant itself access.")
                    }
                }
                .scrollBounceBehavior(.basedOnSize)
            }
            .padding(.top, 32)
            .navigationTitle("Welcome")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private func signIn() async {
        busy = true
        failure = nil
        state.saveServerURL(serverURL)
        state.saveToken(token)
        token = ""
        await state.connect()
        busy = false
        switch state.connection {
        case .connected:
            break
        case .failed(let why):
            failure = why
        default:
            failure = "Could not verify the connection. Check the URL and token."
        }
    }
}

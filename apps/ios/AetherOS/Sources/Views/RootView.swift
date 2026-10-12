import SwiftUI

struct RootView: View {
    @EnvironmentObject var state: AppState
    @ObservedObject var router = DeepLinkRouter.shared

    var body: some View {
        if state.isConfigured {
            mainTabs
        } else {
            AuthGateView()
        }
    }

    private var mainTabs: some View {
        TabView {
            HomeView()
                .tabItem { Label("Home", systemImage: "house") }
            RunsView()
                .tabItem { Label("Tasks", systemImage: "square.and.pencil") }
            ApprovalsView()
                .tabItem { Label("Approvals", systemImage: "checkmark.shield") }
            ActivityView()
                .tabItem { Label("Activity", systemImage: "clock.arrow.circlepath") }
            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
        }
        .safeAreaInset(edge: .top) { ConnectionBanner() }
    }
}

/// Honest connectivity surface driven by the five-state machine. The app
/// never renders success for a request that has not reached the backend.
struct ConnectionBanner: View {
    @EnvironmentObject var state: AppState

    var body: some View {
        if !state.connection.isUsable {
            HStack(spacing: 6) {
                Image(systemName: bannerIcon)
                Text(bannerText)
            }
            .font(.footnote)
            .frame(maxWidth: .infinity)
            .padding(6)
            .background(Color.orange.opacity(0.15))
            .accessibilityIdentifier("connection_banner")
        }
    }

    private var bannerText: String {
        switch state.connection {
        case .connected:
            return ""
        case .connecting:
            return "Connecting to your AetherOS server…"
        case .reconnecting:
            return "Reconnecting — queued actions will retry automatically"
        case .offline:
            return "Offline — actions will queue and retry"
        case .failed(let why):
            return "Connection failed: \(why)"
        }
    }

    private var bannerIcon: String {
        switch state.connection {
        case .connected, .connecting, .reconnecting, .offline:
            return "icloud"
        case .failed:
            return "exclamationmark.icloud"
        }
    }
}

/// Activity / history screen backed by GET /api/sessions (real transcript
/// sync from the user's backend). Tapping a session loads its transcript.
struct ActivityView: View {
    @EnvironmentObject var state: AppState
    @State private var sessions: [SessionSummary] = []
    @State private var loadError: String?
    @State private var loaded = false

    var body: some View {
        NavigationStack {
            List {
                if let loadError {
                    Text(loadError).font(.footnote).foregroundStyle(.secondary)
                } else if loaded && sessions.isEmpty {
                    Text("No sessions yet.")
                        .foregroundStyle(.secondary)
                }
                ForEach(sessions) { session in
                    NavigationLink(value: session.id) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(session.title ?? session.id)
                                .font(.subheadline.weight(.medium))
                                .lineLimit(1)
                            if let updated = session.updated_at {
                                Text(updated)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Activity")
            .navigationDestination(for: String.self) { sessionID in
                TranscriptView(sessionID: sessionID)
            }
            .refreshable { await load() }
            .task {
                guard !loaded else { return }
                await load()
            }
        }
    }

    private func load() async {
        guard let client = state.client else {
            loadError = "Connect to your server first."
            loaded = true
            return
        }
        do {
            sessions = try await client.sessions()
            loadError = nil
            loaded = true
        } catch {
            loadError = AppState.sanitize(error)
            loaded = true
        }
    }
}

/// Read-only transcript of one past conversation.
struct TranscriptView: View {
    @EnvironmentObject var state: AppState
    let sessionID: String
    @State private var messages: [APIClient.TranscriptMessage] = []
    @State private var errorText: String?

    var body: some View {
        List(messages) { message in
            VStack(alignment: .leading, spacing: 4) {
                Text(message.role ?? "message")
                    .font(.caption.bold())
                    .foregroundStyle(.secondary)
                Text(message.content ?? "")
                    .font(.subheadline)
            }
            .accessibilityElement(children: .combine)
        }
        .navigationTitle("Transcript")
        .overlay {
            if let errorText {
                ContentUnavailableCompat(title: "Unavailable", detail: errorText)
            } else if messages.isEmpty {
                ProgressView()
            }
        }
        .task {
            guard let client = state.client else { return }
            do { messages = try await client.transcript(sessionID: sessionID) }
            catch { errorText = AppState.sanitize(error) }
        }
    }
}

/// iOS 17 has ContentUnavailableView; small shim keeps the tree simple.
struct ContentUnavailableCompat: View {
    var title: String
    var detail: String

    var body: some View {
        VStack(spacing: 12) {
            Text(title).font(.title2.weight(.semibold))
            Text(detail)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .accessibilityElement(children: .combine)
    }
}

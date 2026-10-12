import SwiftUI

/// Home screen: real connection status, agent status from the backend
/// capabilities/health endpoints, and navigation into the platform's
/// capability model. Nothing here is simulated — every value comes from a
/// server response or is honestly "unknown until connected".
struct HomeView: View {
    @EnvironmentObject var state: AppState

    var body: some View {
        NavigationStack {
            List {
                Section("Connection") {
                    ConnectionStatusRow(status: state.connection)
                    if let health = state.health, let status = health.status {
                        LabeledContent("Backend health", value: status)
                    }
                    if let error = state.lastError {
                        Text(error).font(.footnote).foregroundStyle(.secondary)
                    }
                }

                Section("Agent") {
                    if let caps = state.capabilities {
                        LabeledContent("Platform", value: caps.platform ?? "aetheros")
                        let enabled = (caps.features ?? [:]).filter { $0.value }.keys.sorted()
                        if enabled.isEmpty {
                            Text("No features reported by the server.")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        } else {
                            ForEach(enabled, id: \.self) { feature in
                                Label(feature, systemImage: "checkmark.circle")
                                    .font(.footnote)
                            }
                        }
                    } else {
                        Text("Agent status is unknown until connected.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }

                Section("This device") {
                    ForEach(MobileCapability.deviceCapabilities, id: \.self) { cap in
                        Label(cap, systemImage: "iphone")
                            .font(.footnote)
                    }
                    ForEach(MobileCapability.neverAvailableOnDevice, id: \.self) { cap in
                        Label("\(cap) — mediated by your backend", systemImage: "arrow.traverse")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Home")
            .refreshable { await state.connect() }
        }
    }
}

/// The five-state connection surface used everywhere in the app.
struct ConnectionStatusRow: View {
    let status: ConnectionStatus

    private var color: Color {
        switch status {
        case .connected: return .green
        case .connecting, .reconnecting: return .orange
        case .offline: return .gray
        case .failed: return .red
        }
    }

    private var icon: String {
        switch status {
        case .connected: return "checkmark.icloud.fill"
        case .connecting, .reconnecting: return "arrow.triangle.2.circlepath.icloud"
        case .offline: return "icloud.slash"
        case .failed: return "exclamationmark.icloud"
        }
    }

    var body: some View {
        Label {
            Text(status.label)
        } icon: {
            Image(systemName: icon).foregroundStyle(color)
        }
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("connection_status_row")
    }
}

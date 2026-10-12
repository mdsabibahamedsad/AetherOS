import SwiftUI

struct RunsView: View {
    @EnvironmentObject var state: AppState
    @State private var prompt = ""

    var body: some View {
        NavigationStack {
            List {
                Section("New task (runs on your AetherOS backend)") {
                    TextField("Describe the task…", text: $prompt, axis: .vertical)
                        .lineLimit(2...5)
                    Button("Submit") {
                        let text = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
                        guard !text.isEmpty else { return }
                        prompt = ""
                        Task { await state.submitRun(text) }
                    }
                    .disabled(prompt.trimmingCharacters(in: .whitespaces).isEmpty || state.client == nil)
                    .accessibilityHint("Submits the task to your backend for execution")
                }

                Section("Recent runs") {
                    if state.runs.isEmpty {
                        Text("No runs yet.")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(state.runs) { run in
                            NavigationLink(value: run.id) {
                                VStack(alignment: .leading) {
                                    Text(run.id).font(.footnote.monospaced())
                                    Text(run.state.rawValue)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("Tasks")
            .navigationDestination(for: String.self) { runID in
                RunDetailView(runID: runID)
            }
            .refreshable { await state.refreshCapabilities() }
        }
    }
}

struct RunDetailView: View {
    @EnvironmentObject var state: AppState
    let runID: String
    @State private var status: RunStatus?
    @State private var loadError: String?

    var body: some View {
        List {
            Section("Status") {
                Text(status?.state.rawValue ?? "unknown")
                    .font(.title3.weight(.semibold))
                if let error = status?.error {
                    Text(error).font(.footnote).foregroundStyle(.secondary)
                }
            }

            if status?.state == .awaitingApproval {
                Section("Approval required") {
                    ConfirmationCard(
                        request: ApprovalRequest(
                            run_id: runID,
                            tool: nil,
                            summary: "The agent is waiting for your decision to continue.",
                            risk: nil,
                            target: nil,
                            scope: nil,
                            side_effects: nil
                        )
                    ) { choice in
                        Task { await state.resolveApproval(runID: runID, choice: choice) }
                        Task { await reload() }
                    }
                }
            }

            PlanPreviewView(runID: runID)

            if status?.state == .running || status?.state == .queued || status?.state == .awaitingApproval {
                Section {
                    Button(role: .destructive) {
                        Task {
                            try? await state.client?.stopRun(runID: runID)
                            await reload()
                        }
                    } label: {
                        Label("Stop run", systemImage: "stop.circle").frame(maxWidth: .infinity)
                    }
                }
            }
        }
        .navigationTitle("Run")
        .task { await reload() }
    }

    private func reload() async {
        guard let client = state.client else { return }
        do { status = try await client.runStatus(runID: runID) }
        catch { loadError = AppState.sanitize(error) }
    }
}

/// The mobile confirmation engine. Renders what the backend asked — task,
/// action, risk, target, scope, side effects — and posts one of the four
/// policy choices. It can NEVER widen or pre-authorize permissions.
struct ConfirmationCard: View {
    let request: ApprovalRequest
    let onResolve: (ApprovalChoice) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(request.tool ?? "Action", systemImage: "wrench.and.screwdriver")
                .font(.headline)

            if let summary = request.summary {
                Text(summary).font(.subheadline)
            }
            Grid(alignment: .leading, horizontalSpacing: 8, verticalSpacing: 4) {
                if let risk = request.risk {
                    GridRow {
                        Text("Risk").font(.caption.bold()).gridColumnAlignment(.leading)
                        Text(risk).font(.caption)
                    }
                }
                if let target = request.target {
                    GridRow {
                        Text("Target").font(.caption.bold())
                        Text(target).font(.caption)
                    }
                }
                if let scope = request.scope {
                    GridRow {
                        Text("Scope").font(.caption.bold())
                        Text(scope).font(.caption)
                    }
                }
            }
            if let effects = request.side_effects, !effects.isEmpty {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Possible side effects").font(.caption.bold())
                    ForEach(effects, id: \.self) { Text("• " + $0).font(.caption) }
                }
                .accessibilityElement(children: .combine)
            }

            HStack(spacing: 12) {
                Button(role: .destructive) {
                    onResolve(.deny)
                } label: {
                    Text("Deny").frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)

                Menu {
                    ForEach([ApprovalChoice.once, .session, .always]) { choice in
                        Button(choiceLabel(choice)) { onResolve(choice) }
                    }
                } label: {
                    Text("Approve").frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .accessibilityLabel("Approve with scope")
            }
        }
        .padding()
        .background(Color.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("confirmation_card")
    }

    private func choiceLabel(_ choice: ApprovalChoice) -> String {
        switch choice {
        case .once: return "Approve once"
        case .session: return "Approve for this session"
        case .always: return "Always allow this action"
        case .deny: return "Deny"
        }
    }
}

struct ApprovalsView: View {
    @EnvironmentObject var state: AppState

    var body: some View {
        NavigationStack {
            ContentUnavailableCompat(
                title: "No pending approvals",
                detail: "Approval requests appear here when your agent needs a decision."
            )
            .navigationTitle("Approvals")
        }
    }
}

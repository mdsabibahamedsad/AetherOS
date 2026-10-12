import SwiftUI

/// Plan preview / execution progress for a run.
///
/// Steps come ONLY from the backend's SSE stream (GET /v1/runs/{id}/events).
/// The client never invents steps and never shows completion without a
/// server frame. Desktop-only capabilities referenced by a step are labeled
/// as remote — iOS mediates them through the authenticated backend.
struct PlanPreviewView: View {
    @EnvironmentObject var state: AppState
    let runID: String

    @State private var steps: [PlanStep] = []
    @State private var streaming = false

    var body: some View {
        Section("Plan & progress") {
            if steps.isEmpty {
                Text(streaming ? "Waiting for events from your server…" : "No events received yet.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(steps) { step in
                    HStack(alignment: .top, spacing: 10) {
                        Image(systemName: icon(for: step.kind))
                            .foregroundStyle(color(for: step.kind))
                            .frame(width: 22)
                            .accessibilityHidden(true)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(step.title).font(.subheadline.weight(.medium))
                            if let detail = step.detail, !detail.isEmpty {
                                Text(detail)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                    .accessibilityElement(children: .combine)
                }
            }
            if streaming {
                ProgressView().controlSize(.small)
            }
        }
        .task { await stream() }
    }

    private func stream() async {
        guard let client = state.client else { return }
        streaming = true
        defer { streaming = false }
        do {
            for try await frame in client.runEvents(runID: runID) {
                if let step = PlanStep.parse(event: frame.event, data: frame.data) {
                    steps.append(step)
                }
                if frame.event == "run.complete" || frame.event == "completed"
                    || frame.event == "run.error" || frame.event == "error" {
                    return
                }
            }
        } catch is CancellationError {
            // View disappeared; stop quietly.
        } catch {
            state.lastError = AppState.sanitize(error)
        }
    }

    private func icon(for kind: PlanStep.Kind) -> String {
        switch kind {
        case .tool: return "wrench.and.screwdriver"
        case .approval: return "checkmark.shield"
        case .completion: return "checkmark.circle.fill"
        case .error: return "xmark.octagon.fill"
        case .info: return "info.circle"
        }
    }

    private func color(for kind: PlanStep.Kind) -> Color {
        switch kind {
        case .tool: return .blue
        case .approval: return .orange
        case .completion: return .green
        case .error: return .red
        case .info: return .secondary
        }
    }
}

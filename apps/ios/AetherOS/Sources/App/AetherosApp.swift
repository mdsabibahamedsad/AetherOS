import SwiftUI

@main
struct AetherosApp: App {
    @StateObject private var state = AppState()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(state)
                .task { await state.refreshCapabilities() }
                .onOpenURL { url in
                    // Deep links navigate only; they never carry credentials
                    // and can never approve anything on their own.
                    guard let link = DeepLink.parse(url) else { return }
                    DeepLinkRouter.shared.pendingLink = link
                }
        }
    }
}

/// Holds the last validated deep link for RootView to route to.
@MainActor
final class DeepLinkRouter: ObservableObject {
    static let shared = DeepLinkRouter()
    @Published var pendingLink: DeepLink?
}

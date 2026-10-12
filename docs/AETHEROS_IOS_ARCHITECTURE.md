# AetherOS iOS Architecture

SwiftUI client > ViewModel state machines > APIClient (bearer+idempotency) > gateway api_server > Agent Kernel/Runtime. Mobile owns observe/command/approve, never local execution.

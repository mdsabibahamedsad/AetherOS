# AetherOS macOS Sandbox Decision

Decision: **direct Developer ID distribution WITHOUT App Sandbox.
Mac App Store is NOT a target.**

Evidence: agent execution (arbitrary approved tools), computer-use
(Accessibility/Screen Recording), MCP/A2A servers, bundled Python
backend, cross-app automation are architecturally incompatible with
App Sandbox entitlements. Enabling the sandbox would silently break
the product's core. Sandbox-tested features: none (correctly — the
decision is architectural, validated by entitlement + capability
review, not by a fake sandbox run). Revisit only if a sandboxed
companion (e.g. viewer-only) app is productized.

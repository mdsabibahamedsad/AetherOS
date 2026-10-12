# AetherOS Web + Server Architecture (Master 69)

Modular monolith (no service split without cause): Vite SPA →
FastAPI dashboard server (loopback) + aiohttp gateway api_server →
control plane (auth/tenancy/policy/approvals) → runtimes
(agents/workers/schedulers/browser/computer) → durable storage
(SessionDB/SQLite, artifacts, memory). Realtime: SSE primary,
WebSocket only where bidirectional. Events: single canonical schema
(event_id/type/tenant/subject/sequence/timestamps/producer/
correlation/causation/version). Tenancy: every resource tenant-bound;
UI filtering never substitutes for authorization. Execution never
flows Web → shell; always identity → authority → policy → capsule →
audit.

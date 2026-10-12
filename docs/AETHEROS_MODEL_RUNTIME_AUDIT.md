# AetherOS Model Runtime — Repository Audit (Master 45, Phase 1)

## Existing architecture (verified)

- `providers/base.py` — `ProviderProfile` declarative (auth, endpoints,
  quirks, vision flags, streaming flags, models fetch with WAF-safe UA,
  health-check support flags). Transport stays on AIAgent.
- `aetheros_providers/` — api_key_manager (encrypted storage via
  SecurityFoundation, validation, rate-limit tracking), local_model_manager
  (Ollama/LM Studio/llama.cpp/vLLM/LocalAI detection, health, model list,
  download progress, GPU status), model_database (cache/search/favorites/
  pins/recent), model_registry (per-task assignments: chat/vision/coding/
  planning/research/compression/browser/voice/mcp/automation/embeddings/
  reranking/...), failover (retry/fallback/circuit strategies),
  multi_provider orchestrator, model_selector (filter/compare),
  model_validator, provider_manager/settings.
- `aetheros_automation/routing/model_router.py` — capability table with
  pricing + privacy labels (hardcoded current models; treated as fallback
  hints, not discovery).
- `aetheros_swarm/integrations.py` — ROLE_MODEL_CHAIN role preference
  lists (policy hook, reused).
- `aetheros_observability/` — cost tracker (ESTIMATED marking),
  redaction engine (canonical text redactor reuse), tracing, metrics.
- Desktop: `app/models`, `app/provider-manager`, model pickers,
  `app/ai-actions`. IPC `@method` pattern; `tools/*_tool.py` + toolset
  pattern; `aetheros_cli/*_cmd.py` + parser pattern (proven in M44).

## Reusable (not duplicated)

ProviderProfile, local_model_manager detection/health, api_key_manager
storage, model_database cache, model_registry assignments, failover
strategies, observability cost/redaction/tracing, swarm role chains.

## Missing (built in `aetheros_ai_runtime/`)

Canonical ModelRecord/ProviderRecord with provenance (anti-spoofing),
unified registry with trust/allow/block/pinning/deprecation, adapter
ABC (OpenAI/Anthropic/local/custom) over real HTTP, hardware-aware local
fit analysis, download manager with verify, policy-aware router with
trace, privacy classifier + redaction + escalation approval, health +
circuit breakers, normalized streaming/cancel/retry/tokens/context,
fallback respecting privacy, cascade/escalation pipelines, embedding/
rerank/vision/audio registries, compute-mesh pairing/scheduler,
benchmark engine with reproducibility, usage/privacy dashboards data,
e-stop/safe mode, org policy DSL, CLI/IPC/UI.

## Risks

Hardcoded model names in old router tables (quarantined as fallback
hints; router prefers live discovery). Credential handling stays in
existing managers; runtime only receives scoped auth handles.

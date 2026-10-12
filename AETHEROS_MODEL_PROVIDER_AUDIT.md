# AETHEROS MODEL PROVIDER AUDIT

**Master Prompt 6 — Phase 0 deliverable.**
Scope: full read-only audit of the provider / model / routing / credential
surface of the aetheros repo. No code was modified to produce this document.

Bottom line up front: **the codebase already implements ~80% of Master
Prompt 6's surface**, but in an architecture that is deliberately different
from the one the prompt sketches (declarative `ProviderProfile` + transport
registry + credential pool instead of a single `Provider` class). The three
genuine, high-value gaps are:

1. **Auto model routing / task classification in the live loop does not
   exist.** `smart_model_routing` is documented in `AGENTS.md` but has **zero
   Python references**. There are *four* disjoint router implementations, none
   wired into the runtime loop (`agent/conversation_loop.py`).
2. **Role-based model aliases** (`default` / `fast` / `smart` / `reasoning` /
   `coding` / `vision` / `research`) do not exist. Only provider/family short
   aliases (`sonnet`, `gpt5`, `gemini`, …) exist today.
3. **No per-request route receipt** ("which model answered this turn") and no
   cost/latency/quality feedback loop feeding routing decisions.

Everything else in the 88-phase list maps onto existing, working, tested
infrastructure. Per the Non-Negotiable Preservation Rule, those must be
extended, not rebuilt.

---

## 1. Providers currently supported

### Bundled provider profiles (`plugins/model-providers/`, 37 dirs)

Profiles are declarative `ProviderProfile` objects registered at import time:
`aetheros`, `alibaba`, `alibaba-coding-plan`, `anthropic`, `arcee`,
`azure-foundry`, `bedrock`, `cloudflare`, `cohere`, `copilot`,
`copilot-acp`, `custom`, `deepseek`, `fireworks`, `gemini`, `gmi`,
`google-vertex-ai`, `groq`, `huggingface`, `kilocode`, `kimi-coding`,
`minimax`, `mistral`, `nous`, `novita`, `nvidia`, `ollama-cloud`,
`openai-codex`, `opencode-zen`, `openrouter`, `perplexity`, `qwen-oauth`,
`stepfun`, `together`, `xai`, `xiaomi`, `zai`.

### Additional catalog-only / legacy providers (`aetheros_cli/models.py::_PROVIDER_MODELS`, lines 156–498)

`openai`, `openai-api`, `moonshot`, `xai-oauth`, `google-gemini-cli`,
`vertex-ai`, `opencode-go`, and the legacy `aetheros` → `nous` alias
(line 503).

### Provider discovery (`providers/__init__.py`)

- Lazy scan on first `get_provider_profile()` / `list_providers()`
  (`providers/__init__.py:140`).
- Order: bundled plugins → `$AETHEROS_HOME/plugins/model-providers/`
  (user overrides win, last-writer-wins, `:53`) → legacy `providers/<name>.py`
  single-file modules (`:176-190`).
- Extensible by design: dropping a plugin dir (or a single file) adds a
  provider with no core edits. **This satisfies Master Prompt 6 Phase 2
  (provider registry, extensible).**

### The `ProviderProfile` shape (`providers/base.py:38`)

| Master Prompt 6 field | Existing equivalent |
|---|---|
| provider_id | `name` (+ `aliases`) |
| display_name | `display_name`, `description`, `logo` |
| api_type / protocol family | `api_mode` (`chat_completions`, `anthropic_messages`, `codex_responses`, `bedrock_converse`) + transport registry |
| base_url | `base_url`, `models_url` |
| authentication_type | `auth_type` (`api_key`, `oauth_device_code`, `oauth_external`, `copilot`, `aws_sdk`) |
| supported capabilities | `supports_vision`, `supports_streaming`, `supports_health_check`, `supports_vision_tool_messages` (per-provider flags) |
| model_discovery_method | `fetch_models()` (live `/models`) + models.dev + static catalog |
| health_check_method | `check_health()` (`providers/base.py:166`) |
| status | derived: doctor / `provider_health.py` probes |
| documentation_url | `signup_url` |
| configuration_schema | `env_vars` tuple + `OPTIONAL_ENV_VARS` metadata (`aetheros_cli/config.py:2743`) |
| provider-specific request quirks | `prepare_messages`, `build_extra_body`, `build_api_kwargs_extras`, `get_max_tokens`, `default_aux_model` |

**Gap:** there is no explicit `capabilities()` method and no per-provider
`status` persistence; both are computed on demand. This is a shape difference,
not a missing feature.

## 2. Models currently supported

- **Canonical static catalog:** `aetheros_cli/models.py::_PROVIDER_MODELS`
  (lines 156–498), ~35 provider keyed lists, plus curated generators for
  codex / xAI and a models.dev-backed live layer.
- **models.dev registry:** `agent/models_dev.py` — bundled snapshot → disk
  cache (`~/.aetheros/models_dev_cache.json`, `:187`) → network → stale-cache
  fallback (`:240-318`). Aetheros→models.dev ID map `:142-180`.
- **Setup fallback catalog:** `aetheros_cli/setup.py::_DEFAULT_PROVIDER_MODELS`
  (`:73-111`), used when live `/v1/models` is unreachable.
- **Context lengths:** `agent/model_metadata.py::DEFAULT_CONTEXT_LENGTHS`
  (`:139-257`, longest-key-first substring match), resolved via
  `get_model_context_length()` (`:1529-1894`) which runs a 10-step
  provider-aware chain (config override → cache → custom-provider probe →
  Bedrock static → Ollama `/api/show` → Anthropic `/v1/models` → Copilot →
  Nous portal → Codex OAuth → GMI → OpenRouter → models.dev → static table →
  local query → 256K default). Local-endpoint detection `:422-450`.
- **Capability metadata:** three parallel models —
  1. `agent/models_dev.py::ModelInfo` / `ModelCapabilities` (`:46-122`,
     `:401-410`): reasoning, tool_call, attachment, structured_output,
     modalities, context_window, max_output, pricing.
  2. `aetheros_providers/model_database.py::ModelCapability` flag enum
     (`:22-35`: CHAT/VISION/TOOL_CALLING/STREAMING/REASONING/CODE/
     FUNCTION_CALLING/JSON_MODE/EMBEDDINGS/IMAGE_GENERATION/SPEECH/
     TRANSCRIPTION) + `ModelInfo` (`:38-56`).
  3. `aetheros_cli/model_selector.py::ModelFilter` (`:16-31`:
     reasoning/vision/code/fast/cheap/large_context/streaming/local/cloud).

**Gap (duplication):** three separate capability/model-metadata schemas exist
in `agent/`, `aetheros_cli/`, and `aetheros_providers/`, plus the models.dev
dataclasses. They do not share a base type and are not cross-synced. This is
the single biggest normalization opportunity — and the riskiest to touch
(see §24).

## 3. Provider APIs (protocol families)

- **`chat_completions`** (OpenAI-compatible) — default; `agent/transports/chat_completions.py`.
- **`anthropic_messages`** — `agent/transports/anthropic.py` + `agent/anthropic_adapter.py`.
- **`codex_responses`** — `agent/codex_responses_adapter.py`, `agent/codex_runtime.py`,
  `agent/transports/codex.py`.
- **`bedrock_converse`** — `agent/transports/bedrock.py` + `agent/bedrock_adapter.py`
  (boto3 `converse`).
- Native special cases: `agent/gemini_native_adapter.py`, `agent/gemini_cloudcode_adapter.py`,
  `agent/azure_identity_adapter.py`, `agent/copilot_acp_client.py`, `agent/google_oauth.py`.

**Transport abstraction** (`agent/transports/`):
`ProviderTransport` ABC (`base.py:16`) with `convert_messages` /
`convert_tools` / `build_kwargs` / `normalize_response` /
`map_finish_reason`. Registered via `register_transport` / `get_transport`
(`transports/__init__.py:21`). **Normalized output type:**
`agent/transports/types.py` — `NormalizedResponse`, `ToolCall`
(id/name/arguments + `provider_data`), `Usage`, `build_tool_call`,
`map_finish_reason`.

> This **is** the "universal provider interface" (Phase 1) and the
> "normalized internal request/response" (Phases 15–16), already realized —
> as a transport layer, not a `Provider` class. `api_mode` is determined at
> setup (`aetheros_cli/providers.py::determine_api_mode`) and re-derived on
> model switch.

## 4. Authentication methods

- **API key** (`.env`, optional OS keychain, `auth.json`, Bitwarden, credential pool).
- **OAuth device code / external** — openai-codex, xai-oauth, qwen-oauth,
  minimax-oauth, google-gemini-cli (`aetheros_cli/runtime_provider.py:1338-1408`).
- **Copilot / ACP** — copilot, copilot-acp.
- **AWS SDK** — bedrock (`auth_type="aws_sdk"`).

Credential **sources** (`agent/credential_sources.py:1-37`):
`env:<VAR>`, `claude_code`, `aetheros_pkce`, `device_code`, `qwen-cli`,
`gh_cli`, `config:<name>`, `model_config`, `manual`. Persistence boundary in
`agent/credential_persistence.py:20-26`.

## 5. Model discovery

- Live: `ProviderProfile.fetch_models()` (`providers/base.py:262`) — GET
  `models_url` or `{base_url}/models`, Bearer or custom headers, UA override.
  Returns `None` for no-catalog providers (bedrock, copilot-acp, …).
- models.dev: `agent/models_dev.py::list_agentic_models` (`:575`) + context
  lookup (`:321-377`).
- Static fallback: `_PROVIDER_MODELS` + setup `_DEFAULT_PROVIDER_MODELS`.
- Cache: `aetheros_cli/model_catalog.py` — TTL 1h (`:76`), in-process + disk
  (`~/.aetheros/cache/model_catalog.json`, `:117`), **never raises, keeps
  stale cache on fetch failure** (`:14`, `:285-286`). Also
  `_provider_models_cache_path` → `$AETHEROS_HOME/provider_models_cache.json`
  (`aetheros_cli/models.py:2381`, TTL 1h `:2378`).

**Refresh:** `aetheros model --refresh` clears the caches
(`aetheros_cli/main.py:2550-2555`); `--refresh` on `/model`.

**Discovery provenance is implicit (dynamic/static/unknown), not labeled.**
Phase 8's "clearly mark DYNAMIC / STATIC / UNKNOWN" is partially covered by
`ModelInfo.source` (`api|fallback|local|manual`,
`aetheros_providers/model_database.py:55`) but that package is unwired.

## 6. Model selection (UI surfaces — all functional)

| Surface | Location |
|---|---|
| Interactive CLI picker (`/model`) | `cli.py:6523` `_open_model_picker`, two-stage provider→model, `_confirm_expensive_model_switch` `:6538`, persist via `save_config_value` `:6949-6951` |
| Standalone `aetheros model` | `aetheros_cli/main.py:2550` → `select_provider_and_model` `:2578`, parser `subcommands/model.py:12-72` |
| Gateway `/model` | `gateway/slash_commands.py:957` (inline pickers `:1029-1182`, typed switch `:1216+`), per-session overrides `gateway/run.py:12276-12295` |
| TUI | `tui_gateway/server.py` `model.options` `:8971`, `model.save_key` `:9011`, `model.disconnect` `:9093` |
| Dashboard | `aetheros_cli/web_server.py` `GET /api/model/options` `:2996`, `POST /api/model/set` `:3111`, aux slots `:2981-2993` |
| Desktop | `apps/desktop/src/app/provider-manager/` (7 tabs) |
| Provider CLI | `aetheros providers` (`aetheros_cli/providers_cmd.py:49-301`) + `aetheros models {search,flag,flags,list,route}` `:366-541` |

Shared picker substrate: `aetheros_cli/inventory.py::load_picker_context`
(`:78`) / `build_models_payload` (`:110`) — single source for CLI, TUI,
dashboard.

## 7. Chat execution / model binding (Phases 13, 23)

- Model + provider are fixed at agent init (`agent/agent_init.py:281,316`)
  and read at request time in `build_api_kwargs`
  (`agent/chat_completion_helpers.py:555`). No hidden substitution —
  **manual binding is exact and enforced.**
- CLI resolution priority (`aetheros_cli/cli_agent_setup_mixin.py:174-216`):
  explicit `--model`/session model → custom-provider model → catalog default
  → normalize-for-provider.
- Mid-session switch: `/model` → `agent_runtime_helpers.py:1365`
  `switch_model()` — in-place swap, persists across turns (cache-safe note at
  `cli.py:6902-6906`).
- Provider/credential resolution: `aetheros_cli/runtime_provider.py:1217`
  `resolve_runtime_provider` (17-step chain incl. Azure-Anthropic shortcut,
  named custom, env runtime, credential pool, OAuth, native Anthropic).

## 8. Streaming (Phase 17)

`interruptible_streaming_api_call` (`agent/chat_completion_helpers.py:1561-2662`):
worker thread, stale detector, per-api_mode dispatch (`:1571-1594`). Key
safety properties already present:

- Stream retries: `HERMES_STREAM_RETRIES` default 2 (`:2216`).
- **Partial-delivery rule** (`:2271-2361`): no retry once tokens delivered —
  except an in-flight tool call with a transient error (silent reconnect).
- Stream-not-supported / Bedrock IAM denied → `_disable_streaming=True`,
  non-streaming fallback (`:2440-2478`).
- Failed-after-delivery returns a stub (`PARTIAL_STREAM_STUB_ID`, `:2603-2662`)
  so the loop resumes without duplicating.
- Interrupt: force-close + `InterruptedError`, no retry (`:2584-2602`).

## 9. Tool calling (Phases 18, 36, 38)

- Toolset assembly: `model_tools.py::get_tool_definitions` (`:283-358`),
  memoized, filtered by enabled toolsets, `check_fn` gating
  (`tools/registry.py:419-478`).
- Dispatch: `handle_function_call` (`model_tools.py:887-1286`) — arg
  coercion, security PEP wrapper, plugin hooks, registry dispatch.
- **Duplicate protection already exists:** `_deduplicate_tool_calls`
  (`run_agent.py:3306-3321`, dedups `(name, arguments)` within a turn) +
  deterministic call IDs `_deterministic_call_id` (`run_agent.py:3334-3341`,
  prompt-cache-safe) + `sanitize_api_messages` orphan-stripping
  (`agent_runtime_helpers.py:1961-2022`).
- Provider-agnostic tool-call normalization via transport `convert_tools` +
  `ToolCall` type.

## 10. Structured output (Phase 19)

**Only in the plugin layer:** `agent/plugin_llm.py::complete_structured`
(`:898-916`, builds `response_format.json_schema`/`json_object`, optional
`jsonschema.validate` `:472-475`). **Not in the core loop.** Catalog metadata
flags exist (`models_dev.py:60`) but aren't wired to requests. Phase 19 is a
legitimate partial gap — but adding structured output to the core loop is a
core-tool-schema change that must be deliberate (see plan §B).

## 11. Multimodal (Phases 20, 21, 66)

- **Vision routing exists and is capability-aware:** `agent/image_routing.py:316`
  `decide_image_input_mode` (`auto`|`native`|`text`); native fast path when
  the main model supports vision, else auxiliary text pipeline
  (`resolve_vision_provider_client`, `auxiliary_client.py:4130-4294`).
  Vision-incapable main providers are skipped (`_PROVIDERS_WITHOUT_VISION`
  `:342-345`). Image-size shrink-on-reject (`run_agent._try_shrink_image_parts_in_messages`).
- **Image gen:** `agent/image_gen_registry.py` + `ImageGenProvider` ABC +
  `plugins/image_gen/` (fal, krea, openai, openai-codex, xai) + legacy FAL
  fallback in `tools/image_generation_tool.py:392`.
- **Audio:** transcription (`tools/transcription_tools.py` + registry,
  built-ins local/groq/openai/mistral/xai/elevenlabs) and TTS
  (`tools/tts_tool.py` + registry, 10 built-ins).
- **Video gen:** `tools/video_generation_tool.py` + `video_gen_registry.py`.
- **Embeddings:** `aetheros_memory/embedding_engine.py` (openai/gemini/
  cohere/jina/voyage/local) + vector DB + RAG — **but this package is NOT
  wired into the agent runtime** (only `aetheros_cli/memory_intelligence_cli.py`
  uses it). Agent memory (`agent/memory_manager.py`) is keyword-based.
  Phase 20/21 embedding support is a real gap in the *agent core*.

## 12. Reasoning (Phases 67)

- `reasoning_config` plumbing: `ProviderProfile.build_api_kwargs_extras`
  (`providers/base.py:132`), OpenRouter `extra_body.reasoning`, Kimi
  `reasoning_effort`.
- `agent.reasoning_effort` config (`aetheros_cli/setup.py:114-126`);
  `/reasoning` slash command (`aetheros_cli/commands.py:174-179`).
- Hidden-reasoning scrubbing: `agent/think_scrubber.py` (stateful stream
  scrubber for think tags, handles split deltas); reasoning stored in
  `assistant_msg["reasoning"]`, replayed via
  `reapply_reasoning_echo_for_provider` (`agent_runtime_helpers.py:2178`).

## 13. Context limits / overflow (Phases 64, 65, 79)

- Full chain in §2 (10-step resolver).
- Token estimation: `agent/model_metadata.py:1897-2006`.
- **Overflow recovery:** `conversation_loop.py` — 413 → compress + retry
  (`:2429-2432`), Anthropic long-context tier → drop to 200K + compress
  (`:2496-2545`), `compression.enabled:false` → terminal error
  (`:2450-2487`), `compression_attempts` cap (`:2525`). Proactive preflight +
  real-token post gate (`:3790-3810`).
- Compression: `agent/context_compressor.py` (prune tool results → protect
  head/tail → LLM summarize middle), threshold = 50% of context length
  (`:674-677`), anti-thrash, model-switch budget recalibration
  (`update_model :605-631`).

## 14. Fallback (Phases 34, 35, 36)

- Config: `fallback_model` (`aetheros_cli/config.py:811,4345`),
  `fallback_providers`.
- Chain built at init: `agent/agent_init.py:929-952`
  (`_fallback_chain`, `_fallback_index`).
- Activation: `try_activate_fallback` (`chat_completion_helpers.py:1044-1257`)
  — validates/skips entries, rebuilds client, re-evaluates prompt-cache
  eligibility, sets `_rate_limited_until` cooldown.
- Eager fallback on 429/billing instead of burning retries:
  `conversation_loop.py:2547-2576`, guarded by pool-recovery check.
- Turn-scoped: `restore_primary_runtime` (`agent_runtime_helpers.py:906-990`).
- One-extra-recovery `try_recover_primary_transport` (`:738-814`).
- CLI auth-failure fallback: `cli_agent_setup_mixin.py:50-72`.

## 15. Retry / rate limit / health (Phases 31–33)

- Retry: `agent._api_max_retries` default 3 (`agent_init.py:1316-1323`);
  loop `conversation_loop.py:800-811`; jittered backoff
  (`agent/retry_utils.py:19`, 5s base / 120s max / 0.5 jitter); per-call caps
  (invalid tool name 3, invalid JSON args 3, codex continuation 3, truncated
  tool call 3, stream 2). `TurnRetryState` (`agent/turn_retry_state.py`)
  one-shot guards.
- Rate limit: `agent/aetheros_rate_guard.py` (file-backed breaker,
  `x-ratelimit-*` parsing, genuine-429 detection); credential-pool cooldowns
  (401→5m, 429→1h, default→1h; `credential_pool.py:111-113`); per-agent
  `_rate_limited_until` 60s; `rate_limit_tracker.py` bucket display.
- Health: `aetheros_cli/doctor.py` (16 sections, `/models` probes,
  dedicated OpenRouter/Anthropic/Bedrock/Azure probes), `aetheros_cli/
  provider_health.py::probe_provider_health` (`:85`), `ProviderProfile.
  check_health` (`providers/base.py:166`).
- **No explicit circuit-breaker class** — protection is layered cooldowns
  (timed breaker, turn-scoped fallback reset, cross-session file breaker,
  compressor cooldowns). Functionally present; structurally different from
  "circuit breaker" (Phase 32).

## 16. Error mapping (Phases 50, 51)

- `FailoverReason` enum (`agent/error_classifier.py:24-64`) — 20 categories:
  auth, auth_permanent, billing, rate_limit, overloaded, server_error,
  timeout, context_overflow, payload_too_large, image_too_large,
  model_not_found, provider_policy_blocked, content_policy_blocked,
  format_error, invalid_encrypted_content, multimodal_tool_content_unsupported,
  thinking_signature, long_context_tier, oauth_long_context_beta_forbidden,
  llama_cpp_grammar_pattern, unknown.
- Classifier pipeline `classify_api_error` (`:441`) with status / code /
  message tables; result `ClassifiedError` (`:69-89`) carries `retryable`,
  `should_compress`, `should_rotate_credential`, `should_fallback`.
- User-facing: non-retryable abort prints provider/model/endpoint + provider-
  specific 401 hints (`conversation_loop.py:2991-3015`).

## 17. Credential pool / rotation (Phases 6, 52, 53)

- `agent/credential_pool.py` — failover pool, statuses OK/EXHAUSTED/DEAD
  (`:55-61`), strategies fill_first/round_robin/random/least_used
  (`:96-105`), cooldowns + provider `reset_at`, DEAD permanent removal
  (`:1410-1415`), soft leases with `max_concurrent` (`:1428-1466`), env
  seeding (`:2018-2060`).
- Key storage: `.env` (default) + optional OS keychain
  (`aetheros_cli/api_key_store.py`, `security.api_key_storage` = env/keychain/
  auto) + `auth.json` (0o600 atomic writes + cross-process flock,
  `auth.py:852-1301`) + Bitwarden (`agent/secret_sources/bitwarden.py`).
- **Full keys never displayed:** key CLI verbs show/remove/rotate/list
  (`providers_cmd.py:164-284`).

**Gap (Phase 7):** no live validation at key-entry time
(`_prompt_api_key`, `main.py:3819-3900`, just saves). Validation is indirect:
doctor `/models` probe, setup model fetch, OAuth token checks. "Save →
validate immediately" is not wired into the wizard.

## 18. Cost / usage / latency (Phases 28, 29, 54–56)

- **Cost pipeline (end-to-end, working):** `conversation_loop.py:1624`
  `estimate_usage_cost()` → `agent.session_estimated_cost_usd` → per-turn
  dict with `billing_provider` / `billing_model` / `cost_source`
  (`:1660-1667`) → `turn_finalizer.py:350` persists to SQLite `sessions`
  (`aetheros_state.py:460-464`) → `aetheros_cli/usage_cmd.py` aggregation +
  `gateway /usage`.
- Pricing sources (3, overlapping): hardcoded `_OFFICIAL_DOCS_PRICING`
  snapshot (`agent/usage_pricing.py:86`), models.dev catalog, live
  OpenRouter/Novita pricing (`aetheros_cli/models.py:1325,1529,1556`).
- Cost guard: `aetheros_cli/model_cost_guard.py` (threshold warning wired
  into picker `cli.py:6543` and dashboard `web_server.py:3134`).
- **No feedback loop:** latency is manual-probe-only
  (`provider_health.py:85`), no per-model error-rate persistence, no
  cost/latency/quality data feeding any routing decision. Phase 29/30
  (latency/quality-aware routing) is a genuine gap.

## 19. Model router — the fragmented picture (Phases 22–26, 58, 59)

Four disjoint implementations, **none wired into the live loop**:

| Router | Location | Wired? |
|---|---|---|
| Phase-16 orchestrator router | `aetheros_automation/routing/model_router.py:149` (capability table `:9-106`, role prefs `:108-125`, fallback chains `:127-146`) | No — only orchestrator/jarvis/secops/coordination |
| CLI advisory router | `aetheros_cli/model_router.py:35` (`manual/fastest/cheapest/quality/offline/enterprise`), `resolve_route` `:146`, `persist_route` `:269` | Advisory only (`aetheros models route`); explicitly never rewrites loop resolution |
| Standalone package | `aetheros_providers/` (TaskType, DEFAULT_TASK_PROVIDERS, model_selector, model_database) | No — imported only by itself + tests |
| Desktop router | `apps/desktop/src/lib/model-router.ts:135` + `store/provider-manager.ts` | No — in-memory only, never persisted |

**Task classification:** `apps/desktop/src/lib/model-router.ts::detectInputTypes`
(`:67-133`) is the only prompt→task-type classifier and it never reaches the
agent. **`smart_model_routing` has zero Python references** (verified by
repo-wide grep) despite being listed in `AGENTS.md` and `docs/ARCHITECTURE.md`.

This is the #1 genuine missing feature of Master Prompt 6 and the #1
duplication problem (four routers that should be one).

## 20. Model aliases, favorites, recent (Phases 39–41)

- **Family aliases exist:** `aetheros_cli/model_switch.py::MODEL_ALIASES`
  (`:105-154`) — sonnet/opus/haiku/claude, gpt5/gpt/codex/o3/o4, gemini,
  deepseek, grok, llama, qwen, minimax, nemotron, kimi, glm, step, mimo,
  trinity. `resolve_alias` (`:444-518`) resolves against the live catalog
  with highest-version sort. `DIRECT_ALIASES` (`:165-`) config-loadable.
- **Role-based aliases (`default`/`fast`/`smart`/`reasoning`/`coding`/
  `vision`/`research`) DO NOT exist.** `fast` is a request-mode toggle
  (`service_tier=priority`, `/fast` command), not a model alias.
- **Favorites/pins/hidden/deprecated flags:** `aetheros_cli/model_registry.py`
  (`$AETHEROS_HOME/state/model_registry.json`), exposed via
  `aetheros models {flag,flags,search,list}`. **But the interactive CLI picker
  does not sort by favorites/recently used**, and `aetheros_providers/
  model_database.py` (favorites/pins/recent, LRU cap 20) is unwired.

## 21. Local models (Phases 45, 46, 63)

- `plugins/model-providers/custom/__init__.py` (Ollama `num_ctx`, think,
  fetch_models), `agent/lmstudio_reasoning.py`, local-endpoint detection
  `agent/model_metadata.py:422`, `_auto_detect_local_model`
  (`aetheros_cli/runtime_provider.py:159`), `aetheros_providers/
  local_model_manager.py` (GPU info), `aetheros models route --offline`.
- **Gap:** `ProviderProfile.category` supports `"local"` (`providers/base.py:53`)
  but **no profile sets it** — local detection is URL-heuristic
  (`model_router.py:64`). No explicit local-first routing policy.

## 22. Privacy / policy (Phases 44, 47, 81, 82)

- Partial: credential-pool strategies, `security` config section,
  authorization engine (`agent/authorization_engine.py`), tool security.
- **No model policy** (ALLOWED/BLOCKED_PROVIDERS, ALLOWED/BLOCKED_MODELS,
  MAX_COST, MAX_LATENCY, REQUIRED_CAPABILITIES, PRIVACY_LEVEL) exists.
- **No privacy-first routing** (LOCAL_ONLY / APPROVED_PROVIDERS_ONLY /
  NO_TRAINING_ONLY). `aetheros models route` policies are about
  cost/latency/offline, not privacy.
- Cost safety is threshold-warning only (no hard per-request budget
  enforcement). Phase 82 (router cannot exceed configured budget through
  retries/fallback) is a genuine gap.

## 23. Observability / receipts (Phases 57, 58, 84)

- `aetheros_observability/` package (MetricsRegistry, `record_model_call`
  in `cost.py:111`, tracing) — **NOT imported by the agent loop**.
- Status bar shows current model (`cli.py:3777-3793`); `/model` switch prints
  a full receipt (`cli.py:6913-6941`). **No per-turn "which model answered"
  route receipt** — Phase 57 gap.
- No routing-transparency output (Phase 58) since auto-routing doesn't exist.
- No model-selection debugger (Phase 59).

## 24. Duplicate implementations (Phase 87 input)

1. **Three model-metadata schemas** — `agent/models_dev.py` vs
   `aetheros_providers/model_database.py` vs `aetheros_cli/model_selector.py`
   vs the static `_PROVIDER_MODELS`. Related but not unified.
2. **Four model routers** — §19. Should converge to one live router.
3. **Three model caches** — `aetheros_cli/model_catalog.py`,
   `provider_models_cache.json` (`models.py:2381`), models.dev disk cache,
   plus `aetheros_providers/model_database.py` cache file.
4. **Three pricing sources** — `usage_pricing.py` snapshot, models.dev,
   live OpenRouter/Novita (`models.py`).
5. **`_AETHEROS_CORE_TOOLS` vs `_HERMES_CORE_TOOLS`** — legacy alias
   (`toolsets.py:79`).
6. **Per-surface multimodal registries** (image_gen/transcription/tts/video/
   web_search/memory) all repeat the same dict+lock+register_provider+
   get_active_provider pattern — a shared ABC + orchestrator opportunity, per
   AGENTS.md's "extend, don't duplicate."

## 25. Known bugs / risks found

- `smart_model_routing` config key is documented but absent — code/`doctor`
  would reject it as unknown root key (`config.py:4254-4260`).
- No live credential validation at key entry (Phase 7 gap) → users can save a
  bad key and only discover via doctor/setup fetch.
- Interactive CLI picker ignores favorites/pins/recently-used despite a
  working registry.
- `aetheros_providers/` and `aetheros_memory/` (embeddings) are shipped but
  dead in the live loop — classic "wired-in-without-E2E" risk per AGENTS.md.
- `ContextProfile.model_hint` (`agent/coding_context.py:224-225`) is a dead
  routing seam ("not yet consumed by the router").
- `agent/moonshot_schema.py` is unrelated to model metadata (name collision
  trap for future work).
- AGENTS.md §Known Pitfalls: `_last_resolved_tool_names` process-global can be
  stale during subagent runs.

## 26. Phase-by-phase gap map (Master Prompt 6)

Legend: **[EXISTS]** working infrastructure → extend/reuse, do not rebuild.
**[PARTIAL]** exists but incomplete vs the phase. **[GAP]** missing.

| Phase | Status | Where / What |
|---|---|---|
| 0 audit | ✅ this doc | — |
| 1 universal provider interface | [EXISTS] | transports (agent/transports/) + ProviderProfile + NormalizedResponse |
| 2 provider registry | [EXISTS] | providers/__init__.py + plugins/model-providers/ (extensible) |
| 3 model registry | [PARTIAL] | fragmented across §24.1; normalize the schema |
| 4 provider→api→model flow | [PARTIAL] | flow works; no explicit step states; no inline key validation |
| 5 provider selector | [EXISTS] | setup wizard, aetheros providers, pickers (§6) |
| 6 API key mgmt | [EXISTS] | .env + keychain + auth.json + Bitwarden + pool |
| 7 credential validation | [PARTIAL] | indirect only (doctor/setup/oauth); no save-time validation |
| 8 model discovery | [EXISTS] | fetch_models + models.dev + static + cache |
| 9 model list refresh | [EXISTS] | `aetheros model --refresh`, `/model --refresh` |
| 10 model selector | [EXISTS] | pickers (§6); favorites/recent not in picker |
| 11 model details | [PARTIAL] | switch receipt shows context/cost/capabilities; no central details panel |
| 12 model test | [PARTIAL] | desktop ModelTester only; no CLI model-test |
| 13 chat model binding | [EXISTS] | exact, no hidden substitution |
| 14 selection priority | [EXISTS] | explicit > session > config default > fallback chain |
| 15 unified chat request | [EXISTS] | build_api_kwargs + transport convert; no formal request_id |
| 16 response normalization | [EXISTS] | NormalizedResponse/Usage/ToolCall + finish-reason mapping |
| 17 streaming | [EXISTS] | §8 (retries, partial-delivery, stub, non-stream fallback) |
| 18 tool calling | [EXISTS] | §9 (+ dedup, deterministic IDs) |
| 19 structured output | [PARTIAL] | plugin_llm only; not in core loop |
| 20 multimodal | [PARTIAL] | vision/image/audio/video exist; embeddings not in core |
| 21 capability matching | [PARTIAL] | vision routing; no general capability router |
| 22 model router | [GAP] | 4 disjoint routers, none live — consolidate + wire |
| 23 manual routing | [EXISTS] | exact binding + /model + /provider |
| 24 auto routing | [GAP] | `smart_model_routing` is a doc-ghost |
| 25 routing strategies | [PARTIAL] | aetheros_cli/model_router.py policies exist but advisory |
| 26 task classification | [GAP] | desktop detectInputTypes only; not live |
| 27 capability-aware routing | [PARTIAL] | vision only |
| 28 cost-aware routing | [GAP] | cost guard warning only; no budget-aware routing |
| 29 latency-aware routing | [GAP] | manual probes only; no rolling metrics |
| 30 quality-aware routing | [GAP] | none |
| 31 provider health | [EXISTS] | doctor + provider_health + check_health |
| 32 circuit breaker | [PARTIAL] | layered cooldowns; no explicit breaker class |
| 33 retry policy | [EXISTS] | §15 (bounded, error-class-gated) |
| 34 provider failover | [EXISTS] | fallback chain + credential pool + restore_primary |
| 35 model fallback | [EXISTS] | fallback_model chain |
| 36 fallback safety | [EXISTS] | stream partial-delivery, tool dedup, deterministic IDs |
| 37 streaming fallback | [EXISTS] | stub/resume/reconnect logic (§8) |
| 38 tool-call fallback | [EXISTS] | dedup + deterministic call IDs |
| 39 model aliases | [PARTIAL] | family aliases exist; role aliases missing |
| 40 favorites | [PARTIAL] | registry exists; picker ignores it |
| 41 recent models | [PARTIAL] | DB tracks; unwired |
| 42 project model | [GAP] | model_hint dead seam; no per-project pinning |
| 43 agent model | [PARTIAL] | agents map personality→reasoning_effort; no per-agent model id |
| 44 model policy | [GAP] | none |
| 45 local models | [EXISTS] | custom profile + ollama/lmstudio detection |
| 46 local-first | [GAP] | no category="local" profile, no local-first policy |
| 47 privacy routing | [GAP] | none |
| 48 api compatibility | [EXISTS] | 4 api_modes + transport registry |
| 49 adapter testing | [PARTIAL] | tests/agent + tests/providers exist; no per-adapter matrix test |
| 50 error normalization | [EXISTS] | FailoverReason + ClassifiedError |
| 51 user-facing errors | [EXISTS] | actionable hints on abort |
| 52 key rotation | [EXISTS] | credential pool + `aetheros providers key rotate` |
| 53 multiple keys | [EXISTS] | credential pool strategies |
| 54 usage tracking | [EXISTS] | §18 pipeline |
| 55 cost dashboard | [EXISTS] | usage_cmd + gateway /usage |
| 56 model usage dashboard | [PARTIAL] | usage by model exists; no latency/error-rate aggregation |
| 57 route receipt | [GAP] | no per-turn receipt |
| 58 routing transparency | [GAP] | n/a until auto-routing exists |
| 59 model selection debugger | [GAP] | none |
| 60 catalog health | [PARTIAL] | hidden/deprecated flags exist; no auto-stale detection |
| 61 model sync | [EXISTS] | `--refresh` + cache staleness; selection preserved |
| 62 model cache | [EXISTS] | model_catalog.py TTL + stale-keep; not labeled CACHED |
| 63 offline mode | [PARTIAL] | offline route policy + local detection; no explicit offline UI label |
| 64 context validation | [EXISTS] | §13 (preflight + compress + error) |
| 65 long-context routing | [PARTIAL] | context-aware compress threshold; no routing-by-context |
| 66 multimodal routing | [EXISTS] | vision; image/audio via capability flags |
| 67 reasoning routing | [PARTIAL] | reasoning_config/effort; no routing by reasoning need |
| 68 coding routing | [GAP] | no per-task coding model selection |
| 69 research routing | [GAP] | none |
| 70 memory routing | [PARTIAL] | compressor context-aware; no memory-model routing |
| 71 router test suite | [GAP] | tests for aetheros_cli/model_router.py exist; no live-router suite |
| 72 critical UI regression | [GAP] | no E2E covering the full setup→chat→restart flow |
| 73 multi-provider UI test | [PARTIAL] | tests/providers + test_setup_*; no combined multi-provider UI test |
| 74 model switching test | [PARTIAL] | switch tests exist; verify history preservation |
| 75 failure test | [EXISTS] | tests/run_agent/test_provider_fallback.py |
| 76 rate limit test | [EXISTS] | test_credential_pool + rate guard tests |
| 77 invalid key test | [EXISTS] | doctor tests |
| 78 model not found test | [PARTIAL] | error classifier tests; no UI unavailability path test |
| 79 context limit test | [EXISTS] | compression/overflow tests |
| 80 security test | [EXISTS] | key-handling tests + redaction |
| 81 routing security | [GAP] | no routing to bypass (yet); policy layer missing |
| 82 cost safety | [GAP] | threshold warning only; no hard budget |
| 83 retry safety | [EXISTS] | bounded retries + guards (§15) |
| 84 observability | [PARTIAL] | aetheros_observability exists but unwired |
| 85 performance | [PARTIAL] | no router overhead measurement (no router) |
| 86 final regression | [PARTIAL] | suite exists; run after changes |
| 87 final scan | ✅ partial | this audit (§24); rerun after changes |
| 88 final report | pending | after implementation |

## 27. Files to modify (when implementing the gaps)

Highest-leverage, aligned with AGENTS.md (extend, don't duplicate):

1. **Live auto router + task classification** (Phases 22–30, 58, 59):
   new `agent/model_routing.py` (or extend `agent/auxiliary_client.py`
   pattern) consulted at turn start; build on `agent/models_dev.py`
   capabilities + `aetheros_cli/model_router.py` policies. Explicit-opt-in
   config `agent.auto_routing` (default off, per Phase 12/14 rules). Reuse
   `_deduplicate_tool_calls` + fallback machinery for safety.
2. **Role-based aliases** (Phase 39): extend `aetheros_cli/model_switch.py:105`
   `MODEL_ALIASES` with `default/fast/smart/reasoning/coding/vision/research`
   resolving via `aetheros_cli/model_selector.py::suggest_for_task`.
3. **Per-turn route receipt** (Phase 57): surface `agent.provider/model`
   (already known post-turn) in the CLI response footer / `turn_finalizer`.
4. **Credential save-time validation** (Phase 7): call
   `ProviderProfile.check_health` / `fetch_models` after `save_env_value`
   in `main.py::_prompt_api_key`.
5. **Picker favorites/recent** (Phases 40–41): consult
   `aetheros_cli/model_registry.py` in `cli.py::_open_model_picker`.
6. **Model policy** (Phases 44, 47, 81, 82): new `agent/model_policy.py`
   enforcing allow/block/budget/privacy before routing; wire into the router.
7. **Route metadata labeling** (Phases 8, 62): tag model sources
   DYNAMIC/STATIC/CACHED.
8. **Structured output in core loop** (Phase 19) — only if warranted by a
   concrete consumer; otherwise leave in plugin layer.

## 28. Files that must remain untouched

- `agent/conversation_loop.py` — the prompt-caching + retry + fallback heart;
  only additive hooks.
- `agent/chat_completion_helpers.py`, `agent/agent_init.py`,
  `agent/agent_runtime_helpers.py` — runtime resolution; any new routing must
  plug in before/around, not rewrite.
- `agent/transports/*`, `providers/*`, `plugins/model-providers/*` — working
  provider/transport layer; treat as a stable API.
- `toolsets.py`, `model_tools.py`, `tools/registry.py` — tool schema surface
  (every addition is paid per call).
- `gateway/run.py`, `run_agent.py` core loops.
- `cli.py` session/prompt-caching paths; `aetheros_state.py`.
- Existing 17k-test suite + all provider plugins.

## 29. Recommended sequence (if implementing)

1. **Auto-routing + task classification** (the doc-ghost): new opt-in
   `agent.auto_routing`, capability-aware candidate selection from
   models.dev + provider health, bounded fallback reusing existing machinery,
   full transparency (Phase 58) and receipts (Phase 57). This is the only
   genuinely-new runtime surface.
2. **Role aliases + picker favorites/recent** — small, high-visibility UI.
3. **Credential save-time validation** — closes the Phase 4/7 flow gap.
4. **Model policy + privacy/cost enforcement** — gate the router.
5. **Tests (Phases 71–79)** — including the critical E2E regression flow
   (Phase 72).
6. **Final scan + report (Phases 87–88)**.
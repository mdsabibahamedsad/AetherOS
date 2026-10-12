# Refactoring Analysis Report

**Generated:** July 11, 2026
**Analyzed Files:** `run_agent.py` (5,368 lines), `cli.py` (13,810 lines)

---

## Executive Summary

Both `run_agent.py` and `cli.py` are documented "god files" that the project's own `AGENTS.md` identifies as refactoring targets. However, `run_agent.py` already has a **forwarder/delegation pattern** in place — most of its heavy logic lives in extracted modules under `agent/` and `tools/`. `cli.py` has also begun extraction with `CLIAgentSetupMixin` and `CLICommandsMixin`.

This report provides a safe, incremental extraction plan rather than a wholesale rewrite.

---

## File: run_agent.py (5,368 lines)

### Current Architecture

```
run_agent.py
├── Imports (proxy patterns)     ~150 lines
├── Module-level helpers           ~50 lines
│   ├── _launch_cwd_for_session
│   ├── _routermint_headers
│   ├── _pool_may_recover_from_rate_limit
│   └── _qwen_portal_headers
├── _StreamErrorEvent class        ~50 lines
└── AIAgent class                 ~5,100 lines
    ├── __init__ (forwarder to agent/agent_init.py)   ~120 lines
    ├── Property/Session helpers                       ~300 lines
    │   ├── _get_session_db_for_recall
    │   ├── _ensure_db_session
    │   └── _transition_context_engine_session
    ├── reset_session_state                            ~70 lines
    ├── LM Studio runtime loading                      ~40 lines
    ├── switch_model (forwarder)                       ~5 lines
    ├── Print/Display helpers                          ~250 lines
    │   ├── _safe_print, _vprint, _should_start_quiet_spinner
    │   ├── _emit_status, _emit_warning, _emit_notice
    │   └── Buffered retry/fallback status
    ├── Codex/Stream helpers                           ~200 lines
    │   ├── _disable_codex_reasoning_replay
    │   ├── _is_provider_stream_parse_error
    │   ├── _log_stream_retry, _emit_stream_drop
    │   └── _emit_auxiliary_failure
    ├── URL/Mode detection helpers                     ~200 lines
    │   ├── _is_direct_openai_url, _is_azure_openai_url
    │   ├── _is_github_copilot_url, _is_openrouter_url
    │   ├── _is_ollama_glm_backend
    │   └── _model_requires_responses_api
    ├── Timeout helpers                                ~150 lines
    │   ├── _resolved_api_call_timeout
    │   ├── _resolved_api_call_stale_timeout_base
    │   └── _compute_non_stream_stale_timeout
    ├── max_tokens/Output helpers                      ~80 lines
    ├── Think-block/Content helpers                    ~100 lines
    │   ├── _has_content_after_think_block
    │   ├── _strip_think_blocks
    │   └── _has_natural_response_ending
    ├── Backward compat imports                        ~20 lines
    ├── Background review                              ~60 lines
    ├── Session persistence helpers                    ~200 lines
    │   ├── _persist_session, _drop_trailing_empty_response_scaffolding
    │   ├── _repair_message_sequence
    │   ├── _flush_messages_to_session_db
    │   └── _save_session_log
    ├── Trajectory helpers                             ~40 lines
    ├── Error/Entitlement helpers                      ~200 lines
    │   ├── _is_entitlement_failure
    │   ├── _decorate_xai_entitlement_error
    │   ├── _summarize_api_error
    │   └── _extract_api_error_context (forwarder)
    ├── Usage/Plugin hooks                             ~300 lines
    │   ├── _usage_summary_for_api_request_hook
    │   ├── _hook_payload_max_chars, _is_sensitive_hook_key
    │   ├── _hook_jsonable, _sanitize_hook_payload
    │   ├── _api_request_payload_for_hook
    │   └── _invoke_api_request_error_hook
    ├── Debug helpers                                  ~50 lines
    ├── Content redaction                              ~80 lines
    └── (rest of class continues with conversation loop, 
         tool execution, streaming, retry logic)       ~2,500 lines
```

### Already-Done Extraction

The following modules already exist and are used as forwarder targets:

| Module | Function | run_agent.py Lines Saved |
|--------|----------|-------------------------|
| `agent/agent_init.py` (1,743 lines) | `init_agent()` | ~120 |
| `agent/agent_runtime_helpers.py` (2,527 lines) | `switch_model`, `strip_think_blocks`, etc. | ~200 |
| `agent/conversation_loop.py` (4,245 lines) | Core loop logic | ~2,500 |
| `agent/prompt_builder.py` | System prompt assembly | ~400 |
| `agent/context_compressor.py` | Context compression | ~300 |
| `agent/background_review.py` | Background memory/skill review | ~60 |
| `agent/stream_diag.py` | Stream diagnostics | ~100 |
| `agent/conversation_compression.py` | Compression checks | ~50 |
| `agent/chat_completion_helpers.py` | API call helpers | ~200 |
| `agent/tool_guardrails.py` | Tool guardrails | ~100 |
| `agent/tool_dispatch_helpers.py` | Tool dispatch utilities | ~150 |
| `agent/trajectory.py` | Trajectory saving | ~40 |
| `agent/message_sanitization.py` | Message sanitization | ~80 |
| `agent/system_prompt.py` | System prompt formatting | ~50 |
| `agent/tool_result_classification.py` | Tool result classification | ~30 |
| `agent/retry_utils.py` | Retry/backoff utilities | ~20 |

### Recommended Next Extractions (Low Risk)

| Module Name | Lines to Extract | Content | Risk |
|-------------|-----------------|---------|------|
| `agent/session_helpers.py` | ~150 | `_get_session_db_for_recall`, `_ensure_db_session`, `_transition_context_engine_session`, `reset_session_state`, `_persist_session`, `_flush_messages_to_session_db`, `_save_session_log` | Low — purely internal helpers |
| `agent/stream_helpers.py` | ~200 | `_is_provider_stream_parse_error`, `_log_stream_retry`, `_emit_stream_drop`, `_emit_auxiliary_failure`, `_disable_codex_reasoning_replay` | Low — stream-specific |
| `agent/url_detect.py` | ~100 | `_is_direct_openai_url`, `_is_azure_openai_url`, `_is_github_copilot_url`, `_is_ollama_glm_backend`, `_is_openrouter_url` | Low — pure detection functions |
| `agent/entitlement.py` | ~100 | `_is_entitlement_failure`, `_decorate_xai_entitlement_error` | Low — isolated utility |
| `agent/timeout_helpers.py` | ~100 | `_resolved_api_call_timeout`, `_resolved_api_call_stale_timeout_base`, `_compute_non_stream_stale_timeout` | Low — isolated |

**Total extractable**: ~650 lines (12% of the file). The remaining ~4,700 lines are the core agent loop and tool orchestration that is harder to separate without breaking the class design.

---

## File: cli.py (13,810 lines)

### Current Architecture

```
cli.py
├── Imports (~100)                                      ~100 lines
├── CanonicalUsage, formatting helpers                   ~100 lines
├── _strip_reasoning_tags                                ~50 lines
├── _assistant_content_as_text                           ~30 lines
├── Configuration Loading                                ~400 lines
│   ├── load_cli_config()
│   ├── _load_prefill_messages
│   ├── _resolve_prefill_messages_file
│   └── _parse_reasoning_config
├── Module-level initialization (~500 lines)             ~500 lines
│   ├── CLI_CONFIG = load_cli_config()
│   ├── logging setup, skin init, tool preview init
│   ├── AsyncHttpxDelNeuter (import patching)
│   └── Import proxy functions
├── Signals/Worktree setup                               ~400 lines
│   ├── _git_repo_root, _setup_worktree
│   ├── _worktree_has_unpushed_commits
│   ├── _cleanup_worktree, _prune_stale_worktrees
│   └── _prune_orphaned_branches
├── ASCII Art & Branding                                 ~200 lines
│   ├── _hex_to_ansi, _LIGHT_MODE_REMAP
│   ├── _SkinAwareAnsi, _ACCENT, _DIM
│   └── _detect_light_mode, _query_osc11_background
├── Output/Display helpers                               ~500 lines
│   ├── _render_final_assistant_content
│   ├── _OUTPUT_HISTORY system
│   ├── _cprint, _replay_output_history
│   └── _rich_text_from_ansi, _strip_markdown_syntax
├── File-drop/Attachment helpers                         ~200 lines
│   ├── _split_path_input, _resolve_attachment_path
│   ├── _detect_file_drop, _file_drop_help
│   └── _IMAGE_EXTENSIONS
├── TERMINAL_INPUT_MODE_RESET_SEQ                        ~10 lines
└── AetherosCLI class (~12,000 lines) - everything else
    ├── __init__ + setup
    ├── Prompt toolkik TUI (key bindings, layout)
    ├── Interactive loop
    ├── Conversation management
    ├── Tool activity display
    ├── Slash command handlers (~40+ commands)
    ├── Session management
    ├── Provider/model management
    └── Cleanup/exit
```

### Already-Done Extraction

| Module | Function | cli.py Lines Saved |
|--------|----------|-------------------|
| `aetheros_cli/cli_agent_setup_mixin.py` | Agent setup mixin | ~200 |
| `aetheros_cli/cli_commands_mixin.py` | Command handlers mixin | ~500 |
| `aetheros_cli/banner.py` | Welcome banner, branding | ~200 |
| `aetheros_cli/commands.py` | Command registry, autocomplete | ~300 |
| `aetheros_cli/callbacks.py` | Interactive callbacks | ~200 |

### Recommended Extractions (Moderate Risk)

| Module Name | Lines to Extract | Content | Risk |
|-------------|-----------------|---------|------|
| `aetheros_cli/cli_output.py` | ~300 | Display helpers: `_cprint`, `_OUTPUT_HISTORY`, `_render_final_assistant_content`, output formatting | Medium — widely referenced |
| `aetheros_cli/cli_worktree.py` | ~400 | Worktree management: `_setup_worktree`, `_cleanup_worktree`, `_prune_stale_worktrees`, `_git_repo_root` | Low — isolated |
| `aetheros_cli/cli_light_mode.py` | ~300 | Light/dark detection: `_detect_light_mode`, `_query_osc11_background`, `_LIGHT_MODE_REMAP`, `_SkinAwareAnsi` | Low — mostly pure functions |
| `aetheros_cli/cli_config.py` | ~400 | Config loading: `load_cli_config`, `_resolve_prefill_messages_file`, `_parse_reasoning_config` | Medium — many dependents |
| `aetheros_cli/cli_attachment.py` | ~200 | File drop helpers: `_split_path_input`, `_resolve_attachment_path`, `_detect_file_drop` | Low — isolated |

**Total extractable**: ~1,600 lines (12% of the file). The remaining ~12,000 lines are the core AetherosCLI class (interactive loop, prompt UI, key bindings, conversation management) which are tightly coupled.

---

## Dependency Graph (Before)

```
run_agent.py
   ├── agent/agent_init.py
   ├── agent/agent_runtime_helpers.py
   ├── agent/conversation_loop.py
   ├── agent/prompt_builder.py
   ├── agent/context_compressor.py
   ├── agent/background_review.py
   ├── agent/stream_diag.py
   ├── agent/chat_completion_helpers.py
   ├── agent/tool_guardrails.py
   ├── agent/tool_dispatch_helpers.py
   ├── agent/trajectory.py
   ├── agent/message_sanitization.py
   ├── agent/system_prompt.py
   ├── agent/tool_result_classification.py
   ├── agent/retry_utils.py
   ├── agent/model_metadata.py
   ├── agent/display.py
   ├── agent/memory_manager.py
   ├── agent/error_classifier.py
   ├── agent/redact.py
   ├── agent/usage_pricing.py
   ├── tools/terminal_tool.py
   ├── tools/interrupt.py
   ├── tools/browser_tool.py
   ├── tools/checkpoint_manager.py
   ├── model_tools.py
   ├── aetheros_state.py
   └── aetheros_cli/* (env_loader, timeouts, __version__)

cli.py
   ├── aetheros_cli/cli_agent_setup_mixin.py
   ├── aetheros_cli/cli_commands_mixin.py
   ├── aetheros_cli/banner.py
   ├── aetheros_cli/commands.py
   ├── aetheros_cli/callbacks.py
   ├── aetheros_cli/skin_engine.py
   ├── aetheros_cli/browser_connect.py
   ├── aetheros_cli/env_loader.py
   ├── aetheros_cli/config.py
   ├── aetheros_cli/fallback_config.py
   ├── aetheros_cli/models.py
   ├── aetheros_cli/pt_input_extras.py
   ├── agent/* (display, markdown_tables, usage_pricing, account_usage)
   ├── model_tools.py
   ├── toolsets.py
   ├── tools/* (terminal_tool, browser_tool, skills_tool, mcp_tool)
   └── cron/*, gateway/*
```

## Decision: Do Not Refactor Now

**Recommendation**: The existing forwarder pattern in `run_agent.py` and the mixin pattern in `cli.py` already represent significant refactoring progress. The remaining `AIAgent` class body and `AetherosCLI` class body are:

1. **Already well-structured** with clear method grouping
2. **Heavily referenced** by ~1,500 test files via `from run_agent import ...` and `mock.patch("run_agent.XXX")` patterns
3. **Partially migrated** — much logic lives in `agent/conversation_loop.py` (4,245 lines) and `agent/agent_init.py` (1,743 lines)

A full extraction would:
- Break ~1,500 test file imports
- Require import bridge/alias patterns
- Create circular dependency risks
- Provide minimal runtime benefit (Python class structure overhead is negligible)

**Better approach**: Extract small, isolated utility groups (session helpers, URL detection, entitlement detection, light mode detection) as separate modules, then re-import with forwarder patterns — the same strategy already used for the major modules.

# AetherOS Tool Runtime

Source: `tools/registry.py`, `kernel/core/tool_manager.py`,
`kernel/core/syscalls.py`, `kernel/core/capability_invoker.py`.

## Tool Registry

`tools.registry.ToolRegistry` — auto-discovered via `tools/*.py`
calling `registry.register()` at import. 114 tools (72 after
`get_tool_definitions(None, None, True)` — `None` = all toolsets).

```python
ToolEntry {
    name, description, handler, schema, toolset, provider,
    requires_env, check_fn, risk_level, permissions, platform,
    circuit_breaker, retry_config, timeout_config, sandbox_config,
    supports_background, cancellation, streaming, dynamic_schema,
    output_schema, max_result_size_chars, confirmation_required,
    emoji, is_async
}
```

## ToolManager Bridge

`kernel/core/tool_manager.py` → discovers tools, registers each as
`tool.<name>` capability via `CapabilityManager`.

```python
tool_manager.discover_tools()  # returns count
tool_manager.list_tools()      # tool names
tool_manager.get_capability_id("read_file")  # "tool.read_file"
```

## Capability Invocation

`CapabilityInvoker.invoke(invocation)` — every tool call passes through
the full syscall pipeline:

```
1. descriptor lookup (CapabilityManager)
2. AuthorityManager grant validity + capability subset
3. PolicyEngine check_capability
4. SecurityBoundary (injection, IFC, emergency, quarantine)
5. ResourceManager (remaining budget)
6. Provider.invoke (ToolCapabilityProvider → handler(args))
7. Verification (observe/verify/attest)
8. Receipt + egress log + audit
```

## Tool→Capability Mapping

`syscalls.py` canonical syscall catalog maps syscalls → tool capabilities:

| Syscall | Backing Tool(s) |
|---|---|
| `fs.read` | `read_file` |
| `fs.write` | `write_file` |
| `fs.delete` | `write_file` |
| `fs.list` | `search_files` |
| `fs.search` | `search_files` |
| `fs.patch` | `patch` |
| `process.execute` | `process`, `execute_code` |
| `terminal.execute` | `terminal` |
| `network.request` | `web_extract`, `web_search` |
| `research.search` | `web_search`, `session_search` |
| `research.fetch` | `web_extract`, `document_extract` |
| `browser.navigate` | `browser_navigate` |
| `browser.click` | `browser_click` |
| `browser.type` | `browser_type` |
| `browser.screenshot` | `browser_snapshot`, `screen_capture` |
| `browser.extract` | `browser_snapshot`, `web_extract` |
| `computer.observe` | `screen_capture`, `screen_understand`, `computer_use` |
| `computer.screenshot` | `screen_capture`, `computer_use` |
| `computer.click` | `computer_use` |
| `computer.type` | `computer_use` |
| `memory.read` | `memory`, `memory2_get`, `memory2_search` |
| `memory.write` | `memory`, `memory2_create` |
| `memory.search` | `memory2_search`, `memory` |
| `automation.create` | `automation_create`, `automation_build` |
| `automation.execute` | `automation_run` |
| `agent.delegate` | `delegate_task` |
| `message.send` | `discord`, `integration_webhook` |
| `vision.analyze` | `vision_analyze`, `screen_understand` |
| `audio.transcribe` | `text_to_speech` |

## Tool Capability Metadata

`ToolManager._infer_risk_level()` from name + schema:
- `write/delete/remove/patch/edit` → `IRREVERSIBLE`
- `web/network/http/fetch/browser` → `EXTERNAL_SIDE_EFFECT`
- `exec/terminal/shell/process/run` → `EXTERNAL_SIDE_EFFECT`, `SECURITY_CRITICAL`
- `computer/click/type/keyboard/mouse` → `PHYSICAL`, `EXTERNAL_SIDE_EFFECT`
- `device/robot` → `PHYSICAL`
- `pay/transfer/buy/sell/trade` → `FINANCIAL`

Credentials inferred: `github`→`GITHUB_TOKEN`, `gitlab`→`GITLAB_TOKEN`,
`aws`→`AWS_CREDENTIALS`, etc. Network/filesystem/device access inferred
from name patterns.

## Execution

`CapabilityInvoker` → `provider.invoke(invocation)` →
`ToolCapabilityProvider.invoke(invocation)` → `handler(inputs)`.
`handler` receives `inputs` + `task_id` (from `invocation.intent_id`).

Results must be JSON-serializable. `verify(invocation, result)` →
`result is not None` by default.

## Security

- No tool bypasses `CapabilityInvoker` pipeline
- `SecurityBoundary` screens inputs for prompt injection
- `NetworkManager` screens egress URLs
- `ResourceManager` enforces budgets
- `PolicyEngine` gates by capability + risk
- Sandbox where `SandboxConfig` present
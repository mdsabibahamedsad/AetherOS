# AetherOS Model Runtime

Source: `kernel/core/model_manager.py`, `kernel/core/syscalls.py` (no
dedicated model syscall — model calls go through `ModelManager.select_model`
+ provider `complete()`).

## ModelManager

```python
class ModelManager:
    def register_provider(name, provider, availability=1.0)
    def register_model(ModelProfile)
    def select_model(ModelSelection) -> ModelProfile | None
    def list_models(provider, capability, local_only)
    def estimate_cost(model_id, messages) -> float
    def record_usage(model_id, input_tokens, output_tokens, latency_ms, success)
    def check_health(model_id) -> Dict
```

## ModelProfile

```text
ModelProfile {
    model_id, name, provider
    capabilities: List[ModelCapability]
    context_window, max_output_tokens
    supports_vision, audio, video, tools, structured_output, streaming
    reasoning_level: standard|high|deep
    latency_class: fast|normal|slow
    cost_per_1k_input, cost_per_1k_output
    privacy_level: DataClassification
    local: bool
    gpu_memory_mb, availability: float (0.0-1.0), health
}
```

`ModelCapability`: TEXT, REASONING, VISION, AUDIO, VIDEO, TOOL_USE,
STRUCTURED_OUTPUT, STREAMING.

`ModelProvider`: LOCAL, OPENAI, ANTHROPIC, GOOGLE, AZURE, BEDROCK,
VERTEX, TOGETHER, FIREWORKS, OPENROUTER, CUSTOM.

## Selection

`select_model(selection: ModelSelection)` filters by:
1. Health = healthy
2. Excluded providers/models
3. Required capabilities (all must match)
4. Min context window
5. Max cost per 1k
5. Latency class ≤ requested
6. Privacy level ≥ requirement (≥ not ≤ — SECRET-cleared needed for
   SECRET work)
7. Reasoning level ≥ required
8. Selection policies (default: prefer local → preferred caps → lowest
   cost)
9. First candidate

Unconfigured providers register `availability=0.0` → excluded.

## Local-first (§16, §69)

`model_policy.local_only = True` denies cloud fallback. `cloud_allowed:
false` denies cloud models. Provider policy `allow/deny` per provider.

## Cost + Latency

`estimate_cost(model_id, messages)` → provider.estimate_cost or
rough `(input_tokens/1000) * cost_per_1k_input`.

`LatencyManager` records: queue, planning, model, tool, network, render,
approval, execution, verification, end-to-end → p50/p95/p99.

## Provider Interface

```python
class IModelProvider:
    def get_capabilities() -> Dict
    def complete(messages, tools, **kwargs) -> Any
    def estimate_cost(messages, tools) -> float
```

Provider must register with `register_provider(name, provider,
availability)` — unconfigured providers get `availability=0.0` and are
excluded from selection.

## Syscall Integration

No direct model syscall — agent runtime calls `ModelManager.select_model`
→ `provider.complete()` → result. Cost recorded in `CostManager`.
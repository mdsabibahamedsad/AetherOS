"""Tests for AetherOS AI Runtime - Model Hub + Provider Fabric + Intelligent Router."""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from aetheros_runtime.models import (
    DataClass, ProviderKind, HealthState, CircuitState,
    Provenance, Pricing, ModelRecord, ProviderRecord,
)
from aetheros_runtime.health import HealthMonitor, CircuitBreaker
from aetheros_runtime.privacy import (
    PrivacyDecision, PrivacyRouter, classify_text, redact_for_cloud
)
from aetheros_runtime.router import (
    IntelligentModelRouter, TaskRequirements, ModelDecisionTrace,
    QualityMemory, PROFILES, MODES
)
from aetheros_runtime.cache import ModelCache, WarmPool
from aetheros_runtime.runtime import (
    ContextBudgetManager, UsageRecord, parse_usage,
    ToolCall, normalize_tool_call, validate_tool_arguments,
    validate_structured, FallbackPlan, build_fallback,
    run_with_fallback, ComputeNode, ComputeMesh, ModelDownloadManager,
    Pricing, classify_error, RETRYABLE, NON_RETRYABLE
)


# ---------------------------------------------------------------------------
# ModelRecord / ProviderRecord tests
# ---------------------------------------------------------------------------

class TestModelRecord:
    def test_canonical_id(self):
        m = ModelRecord(model_id="gpt-4", provider_id="openai", version="2024-01")
        assert m.canonical_id == "openai/gpt-4@2024-01"
        
        m2 = ModelRecord(model_id="llama-3", provider_id="ollama")
        assert m2.canonical_id == "ollama/llama-3"

    def test_to_dict(self):
        m = ModelRecord(
            model_id="gpt-4", provider_id="openai",
            tool_calling=True, context_window=128000,
            locality="remote", status="healthy"
        )
        d = m.to_dict()
        assert d["canonical_id"] == "openai/gpt-4"
        assert d["tool_calling"] is True
        assert d["context_window"] == 128000
        assert d["locality"] == "remote"
        assert "pricing" in d
        assert "provenance" in d

    def test_from_dict(self):
        d = {
            "model_id": "gpt-4",
            "provider_id": "openai",
            "version": "2024-01",
            "tool_calling": True,
            "context_window": 128000,
            "locality": "remote",
            "status": "healthy",
            "pricing": {"input_per_1k": 0.03, "output_per_1k": 0.06, "unknown": False},
            "provenance": {"tool_calling": {"source": "provider_api", "at": 1.0, "by": "test"}}
        }
        m = ModelRecord.from_dict(d)
        assert m.model_id == "gpt-4"
        assert m.provider_id == "openai"
        assert m.version == "2024-01"
        assert m.tool_calling is True
        assert m.context_window == 128000
        assert m.pricing.input_per_1k == 0.03
        assert m.capabilities_provenance["tool_calling"].source == "provider_api"


class TestProviderRecord:
    def test_to_dict(self):
        p = ProviderRecord(
            provider_id="openai", name="OpenAI",
            kind=ProviderKind.CLOUD.value,
            endpoint="https://api.openai.com/v1",
            has_credential=True,
            health=HealthState.HEALTHY.value
        )
        d = p.to_dict()
        assert d["provider_id"] == "openai"
        assert d["name"] == "OpenAI"
        assert d["has_credential"] is True
        assert d["health"] == "healthy"
        assert "provenance" in d


# ---------------------------------------------------------------------------
# HealthMonitor / CircuitBreaker tests
# ---------------------------------------------------------------------------

class TestCircuitBreaker:
    def test_initial_state(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.allow() is True

    def test_open_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_s=60.0)
        cb.failure()
        cb.failure()
        assert cb.state == CircuitState.CLOSED
        cb.failure()  # 3rd failure
        assert cb.state == CircuitState.OPEN
        assert cb.allow() is False

    def test_half_open_after_cooldown(self):
        cb = CircuitBreaker(failure_threshold=2, cooldown_s=0.01)
        cb.failure()
        cb.failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.02)
        assert cb.allow() is True
        assert cb.state == CircuitState.HALF_OPEN
        cb.success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(failure_threshold=2, cooldown_s=0.01)
        cb.failure()
        cb.failure()
        time.sleep(0.02)
        assert cb.allow() is True
        cb.failure()
        assert cb.state == CircuitState.OPEN


class TestHealthMonitor:
    def test_initial_status(self):
        hm = HealthMonitor()
        status = hm.status("unknown-provider")
        assert status["state"] == "unknown"
        assert status["circuit"]["state"] == "closed"
        assert status["throttled"] is False

    def test_healthy_probe(self):
        hm = HealthMonitor()
        hm.record_probe("openai", {"ok": True, "latency_ms": 50})
        status = hm.status("openai")
        assert status["state"] == "healthy"
        assert status["latency_ms"] == 50
        assert status["circuit"]["state"] == "closed"

    def test_degraded_probe(self):
        hm = HealthMonitor()
        hm.record_probe("openai", {"ok": False, "class": "timeout", "reason": "timeout"})
        status = hm.status("openai")
        assert status["state"] == "degraded"

    def test_rate_limited_probe(self):
        hm = HealthMonitor()
        hm.record_probe("openai", {"ok": False, "class": "rate_limit", "retry_after_s": 10})
        status = hm.status("openai")
        assert status["state"] == "rate_limited"
        assert hm.throttled("openai") is True

    def test_circuit_opens_on_auth_error(self):
        hm = HealthMonitor()
        # Circuit breaker needs 5 failures by default, so call 5 times
        for _ in range(5):
            hm.record_probe("openai", {"ok": False, "class": "auth"})
        status = hm.status("openai")
        assert status["circuit"]["state"] == "open"


# ---------------------------------------------------------------------------
# Privacy tests
# ---------------------------------------------------------------------------

class TestPrivacyClassification:
    def test_classify_public(self):
        result = classify_text("hello world")
        assert result == "internal"  # default

    def test_classify_highly_sensitive_secrets(self):
        result = classify_text("my api key is sk-test-123")
        assert result == "highly_sensitive"
        
        result = classify_text("password = secret123")
        assert result == "highly_sensitive"

    def test_classify_sensitive_hints(self):
        result = classify_text("my ssn is 123-45-6789")
        assert result == "sensitive"
        
        result = classify_text("credit card 4111 1111 1111 1111")
        assert result == "sensitive"

    def test_classify_private_context(self):
        result = classify_text("my internal confidential project")
        assert result == "private"

    def test_explicit_label(self):
        result = classify_text("any text", user_label="public")
        assert result == "public"
        
        result = classify_text("any text", user_label="highly_sensitive")
        assert result == "highly_sensitive"

    def test_redact_for_cloud(self):
        text = "my api key is sk-test-123 and password is secret"
        result = redact_for_cloud(text)
        assert "[REDACTED]" in result["text"]
        assert result["redactions"] >= 1


class TestPrivacyRouter:
    def test_local_only_policy(self):
        pr = PrivacyRouter(mode="local_only")
        local_model = ModelRecord(model_id="local", provider_id="ollama", locality="local")
        remote_model = ModelRecord(model_id="cloud", provider_id="openai", locality="remote")
        
        dec1 = pr.gate(classification="internal", candidate=local_model)
        assert dec1.cloud_allowed is True
        assert dec1.escalation == "auto"
        
        dec2 = pr.gate(classification="internal", candidate=remote_model)
        assert dec2.cloud_allowed is False
        assert dec2.escalation == "never"

    def test_highly_sensitive_blocks_cloud(self):
        pr = PrivacyRouter(mode="ask_before_cloud", approve=lambda x: True)
        remote_model = ModelRecord(model_id="cloud", provider_id="openai", locality="remote")
        
        dec = pr.gate(classification="highly_sensitive", candidate=remote_model)
        assert dec.cloud_allowed is False
        assert dec.escalation == "never"

    def test_ask_before_cloud_with_approval(self):
        approved = []
        def approve(info):
            approved.append(info)
            return True
        
        pr = PrivacyRouter(mode="ask_before_cloud", approve=approve)
        remote_model = ModelRecord(model_id="cloud", provider_id="openai", locality="remote")
        
        dec = pr.gate(classification="internal", candidate=remote_model)
        assert dec.cloud_allowed is True
        assert dec.escalation == "ask"
        assert len(approved) == 1


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------

def _make_demo_models():
    return [
        ModelRecord(
            model_id='gpt-4', provider_id='openai', version='2024-01',
            display_name='GPT-4', tool_calling=True, reasoning=True, streaming=True,
            context_window=128000, locality='remote',
            pricing=Pricing(input_per_1k=0.03, output_per_1k=0.06, unknown=False),
            status='healthy'
        ),
        ModelRecord(
            model_id='llama-3-8b', provider_id='ollama', version='1.0',
            display_name='Llama 3 8B', tool_calling=True, streaming=True,
            context_window=8192, locality='local', hardware_gb=6.0,
            pricing=Pricing(unknown=True), status='healthy'
        ),
        ModelRecord(
            model_id='claude-3-opus', provider_id='anthropic', version='1.0',
            display_name='Claude 3 Opus', tool_calling=True, reasoning=True, streaming=True,
            context_window=200000, locality='remote',
            pricing=Pricing(input_per_1k=0.015, output_per_1k=0.075, unknown=False),
            status='healthy'
        ),
    ]


class TestIntelligentModelRouter:
    def test_basic_routing(self):
        models = _make_demo_models()
        router = IntelligentModelRouter(lambda: models, hardware_gb=16.0)
        
        req = TaskRequirements(
            task_type='coding', profile='coding',
            needs_reasoning=True, needs_tools=True,
            context_tokens=8000, mode='auto'
        )
        trace = router.route(req, task_id='test')
        
        assert trace.selected in [m.canonical_id for m in models]
        assert len(trace.eligible) >= 1
        assert trace.policy == 'auto'

    def test_local_only_mode(self):
        models = _make_demo_models()
        router = IntelligentModelRouter(lambda: models, hardware_gb=16.0)
        
        req = TaskRequirements(mode='local_only')
        trace = router.route(req, task_id='test')
        
        assert trace.selected == 'ollama/llama-3-8b@1.0'

    def test_cheapest_mode(self):
        models = _make_demo_models()
        router = IntelligentModelRouter(lambda: models, hardware_gb=16.0)
        
        req = TaskRequirements(mode='cheapest')
        trace = router.route(req, task_id='test')
        
        # Local model with unknown cost should be cheapest
        assert trace.selected == 'ollama/llama-3-8b@1.0'

    def test_reasoning_capability_filter(self):
        models = _make_demo_models()
        router = IntelligentModelRouter(lambda: models, hardware_gb=16.0)
        
        req = TaskRequirements(needs_reasoning=True)
        trace = router.route(req, task_id='test')
        
        # llama-3-8b doesn't have reasoning, should be rejected
        assert 'ollama/llama-3-8b@1.0' in trace.rejected
        assert 'missing capability: reasoning' in trace.rejected.get('ollama/llama-3-8b@1.0', '')

    def test_context_window_filter(self):
        models = _make_demo_models()
        router = IntelligentModelRouter(lambda: models, hardware_gb=16.0)
        
        req = TaskRequirements(context_tokens=150000)  # > llama and gpt-4
        trace = router.route(req, task_id='test')
        
        # Only claude-3-opus has 200k context
        assert trace.selected == 'anthropic/claude-3-opus@1.0'

    def test_blocked_model(self):
        models = _make_demo_models()
        models[0].blocked = True
        router = IntelligentModelRouter(lambda: models, hardware_gb=16.0)
        
        req = TaskRequirements(mode='auto')
        trace = router.route(req, task_id='test')
        
        assert 'openai/gpt-4@2024-01' in trace.rejected
        assert 'blocked by policy' in trace.rejected['openai/gpt-4@2024-01']


class TestQualityMemory:
    def test_record_and_score(self):
        qm = QualityMemory(half_life_days=30.0)
        qm.record('model1', 'coding', success=True, latency_s=1.0, cost_usd=0.01)
        qm.record('model1', 'coding', success=True, latency_s=1.0, cost_usd=0.01)
        qm.record('model1', 'coding', success=False, latency_s=10.0, cost_usd=0.1)
        
        score = qm.score('model1', 'coding')
        assert -1.0 <= score <= 1.0
        assert score > 0  # 2 successes, 1 failure

    def test_empty_score(self):
        qm = QualityMemory()
        score = qm.score('unknown', 'coding')
        assert score == 0.0


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------

class TestModelCache:
    def test_put_get(self):
        cache = ModelCache(max_entries=10)
        cache.put_meta("key1", {"value": "test"})
        result = cache.get_meta("key1")
        assert result == {"value": "test"}

    def test_expiry(self):
        cache = ModelCache(max_entries=10)
        cache.put_meta("key1", {"value": "test"})
        result = cache.get_meta("key1", max_age_s=0.001)
        time.sleep(0.01)
        result = cache.get_meta("key1", max_age_s=0.001)
        assert result is None

    def test_lru_eviction(self):
        cache = ModelCache(max_entries=2)
        cache.put_meta("key1", {"v": 1})
        cache.put_meta("key2", {"v": 2})
        cache.put_meta("key3", {"v": 3})  # Should evict key1
        assert cache.get_meta("key1") is None
        assert cache.get_meta("key2") is not None
        assert cache.get_meta("key3") is not None


class TestWarmPool:
    def test_load_within_budget(self):
        wp = WarmPool(vram_budget_gb=10.0)
        result = wp.load("model1", 2.0)
        assert result["loaded"] is True
        assert result["evicted"] == []

    def test_load_exceeds_budget(self):
        wp = WarmPool(vram_budget_gb=5.0)
        wp.load("model1", 3.0)
        result = wp.load("model2", 3.0)  # 3+3=6 > 5, evicts model1 to make room
        assert result["loaded"] is True  # Evicts model1 to make room
        assert "model1" in result["evicted"]
        # Verify model1 was evicted
        assert "model1" not in wp._loaded
        assert "model2" in wp._loaded

    def test_evict_running_never(self):
        wp = WarmPool(vram_budget_gb=5.0)
        wp.load("model1", 3.0)
        wp.mark_running("model1", True)
        evicted = wp.evict(need_gb=2.0)
        assert "model1" not in evicted  # Running models not evicted


# ---------------------------------------------------------------------------
# Runtime tests
# ---------------------------------------------------------------------------

class TestContextBudgetManager:
    def test_estimate(self):
        cbm = ContextBudgetManager(estimate_chars_per_token=4)
        assert cbm.estimate("hello") == 1
        assert cbm.estimate("a" * 100) == 25

    def test_budget_fits(self):
        cbm = ContextBudgetManager()
        budget = cbm.budget(system="sys", messages=[{"content": "hi"}], context_window=1000)
        assert budget["fits"] is True
        assert budget["total"] < 1000

    def test_budget_exceeds(self):
        cbm = ContextBudgetManager(estimate_chars_per_token=1)
        budget = cbm.budget(system="x" * 5000, context_window=1000)
        assert budget["fits"] is False
        assert "dropped" in budget


class TestUsageRecord:
    def test_parse_usage(self):
        raw = {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "cached_tokens": 10,
            "completion_tokens_details": {"reasoning_tokens": 5}
        }
        pricing = Pricing(input_per_1k=0.01, output_per_1k=0.02, unknown=False)
        usage = parse_usage(raw, pricing=pricing, task_id='t1', model='m1', provider='p1')
        
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.cached_tokens == 10
        assert usage.reasoning_tokens == 5
        assert usage.cost_usd == 0.002  # 100/1000*0.01 + 50/1000*0.02


class TestToolCallNormalization:
    def test_normalize_tool_call(self):
        raw = {"id": "call_1", "name": "search", "arguments": '{"query": "test"}', "model": "gpt-4"}
        call = normalize_tool_call(raw, provider="openai", allowed_tools=["search"])
        
        assert call.id == "call_1"
        assert call.name == "search"
        assert call.arguments == {"query": "test"}
        assert call.approval == "pending"

    def test_denied_tool(self):
        raw = {"id": "call_1", "name": "dangerous", "arguments": '{}', "model": "gpt-4"}
        call = normalize_tool_call(raw, provider="openai", allowed_tools=["search"])
        
        assert call.approval == "denied"

    def test_validate_tool_arguments(self):
        call = ToolCall(name="search", arguments={"query": "test"})
        result = validate_tool_arguments(call, schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]})
        assert result["ok"] is True

    def test_validate_missing_required(self):
        call = ToolCall(name="search", arguments={})
        result = validate_tool_arguments(call, schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]})
        assert result["ok"] is False
        assert "required" in result["reason"].lower()


class TestStructuredOutput:
    def test_valid_json(self):
        result = validate_structured('{"name": "test", "value": 42}', schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]})
        assert result["ok"] is True
        assert result["data"]["name"] == "test"

    def test_invalid_json(self):
        result = validate_structured('not json', schema={})
        assert result["ok"] is False


class TestFallback:
    def test_build_fallback(self):
        plan = build_fallback("model1", ["model2", "model3"], privacy_denied={"model2"})
        assert plan.chain == ["model1", "model3"]
        assert plan.privacy_veto == ["model2"]

    def test_run_with_fallback(self):
        def mock_invoke(model):
            if model == "model1":
                yield {"kind": "error", "error": "rate_limit exceeded"}
            elif model == "model3":
                yield {"kind": "delta", "text": "hello"}
                yield {"kind": "complete", "text": "hello"}
        
        events = list(run_with_fallback(["model1", "model3"], mock_invoke, max_attempts=2))
        
        # Should have warning, then delta, then complete
        kinds = [e["kind"] for e in events]
        assert "warning" in kinds
        assert "delta" in kinds
        assert "complete" in kinds


class TestComputeMesh:
    def test_pair_and_select(self):
        mesh = ComputeMesh()
        node = ComputeNode(node_id="node1", name="Test", endpoint="http://localhost:8080", models=["model1"], vram_gb=24.0)
        mesh.pair(node, "token")
        
        selected = mesh.select(model="model1", private=True)
        assert selected is not None
        assert selected.name == "Test"
        assert selected.trusted is True

    def test_private_selection(self):
        mesh = ComputeMesh()
        # Local node
        node1 = ComputeNode(node_id="node1", name="Local", endpoint="http://localhost:8080", models=["model1"], trusted=True)
        # Remote node
        node2 = ComputeNode(node_id="node2", name="Remote", endpoint="http://remote:8080", models=["model1"], trusted=True)
        mesh.pair(node1, "t1")
        mesh.pair(node2, "t2")
        
        # Private should prefer localhost
        selected = mesh.select(model="model1", private=True)
        assert selected.endpoint.startswith("http://localhost")

    def test_revoke(self):
        mesh = ComputeMesh()
        node = ComputeNode(node_id="node1", name="Test", endpoint="http://localhost:8080", models=["model1"], trusted=True)
        mesh.pair(node, "token")
        
        assert mesh.revoke("node1") is True
        assert mesh.nodes()[0].trusted is False
        assert mesh.select(model="model1") is None


class TestClassifyError:
    def test_rate_limit(self):
        assert classify_error(RuntimeError("rate limit exceeded")) == "rate_limit"
        assert classify_error(RuntimeError("429 too many requests")) == "rate_limit"

    def test_auth(self):
        assert classify_error(RuntimeError("unauthorized 401")) == "auth"
        assert classify_error(RuntimeError("invalid api key")) == "auth"

    def test_timeout(self):
        assert classify_error(RuntimeError("timeout after 30s")) == "timeout"

    def test_context_exceeded(self):
        assert classify_error(RuntimeError("context length exceeded")) == "context_exceeded"


# ---------------------------------------------------------------------------
# ModelDownloadManager tests (basic)
# ---------------------------------------------------------------------------

class TestModelDownloadManager:
    def test_init(self):
        mgr = ModelDownloadManager(disk_budget_gb=10.0)
        assert mgr.budget_gb == 10.0
        mgr.cancel()
        assert mgr._cancel.is_set()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
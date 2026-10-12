#!/usr/bin/env python
"""Test fallback and runtime components."""

from aetheros_runtime import (
    FallbackPlan, build_fallback, run_with_fallback,
    UsageRecord, parse_usage, Pricing,
    normalize_tool_call, validate_tool_arguments,
    validate_structured, ComputeNode, ComputeMesh,
    ContextBudgetManager
)

print('=== Fallback ===')
plan = build_fallback('model1', ['model2', 'model3'], privacy_denied={'model2'})
print('Plan:', plan.chain, plan.privacy_veto)

# Test run_with_fallback
def mock_invoke(model):
    if model == 'model1':
        yield {'kind': 'error', 'error': 'rate_limit exceeded'}
    elif model == 'model3':
        yield {'kind': 'delta', 'text': 'Hello from model3'}
        yield {'kind': 'complete', 'text': 'Hello from model3'}
    else:
        yield {'kind': 'error', 'error': 'unknown'}

events = list(run_with_fallback(['model1', 'model3'], mock_invoke, max_attempts=2))
print('Fallback events:', events)

# Test UsageRecord
print()
print('=== Usage Record ===')
raw = {'prompt_tokens': 100, 'completion_tokens': 50, 'cached_tokens': 10, 'completion_tokens_details': {'reasoning_tokens': 5}}
pricing = Pricing(input_per_1k=0.01, output_per_1k=0.02, unknown=False)
usage = parse_usage(raw, pricing=pricing, task_id='t1', model='m1', provider='p1')
print('Usage:', usage.input_tokens, usage.output_tokens, usage.cached_tokens, usage.reasoning_tokens, usage.cost_usd)

# Test tool calls
print()
print('=== Tool Calls ===')
raw_call = {'id': 'call_1', 'name': 'search', 'arguments': '{"query": "test"}', 'model': 'gpt-4'}
call = normalize_tool_call(raw_call, provider='openai', allowed_tools=['search', 'read'])
print('Normalized:', call.name, call.arguments, call.approval)

validation = validate_tool_arguments(call, schema={'type': 'object', 'properties': {'query': {'type': 'string'}}, 'required': ['query']})
print('Validation:', validation)

# Test structured output
print()
print('=== Structured Output ===')
result = validate_structured('{"name": "test", "value": 42}', schema={'type': 'object', 'properties': {'name': {'type': 'string'}, 'value': {'type': 'integer'}}, 'required': ['name']})
print('Structured:', result)

# Test ComputeMesh
print()
print('=== Compute Mesh ===')
mesh = ComputeMesh()
node = ComputeNode(node_id='node1', name='Test Node', endpoint='http://localhost:8080', models=['model1'], vram_gb=24.0, trusted=True)
mesh.pair(node, 'token123')
selected = mesh.select(model='model1', max_latency_ms=100, private=True)
print('Selected node:', selected.name if selected else None)

# Test ContextBudgetManager
print()
print('=== Context Budget ===')
cbm = ContextBudgetManager()
budget = cbm.budget(system='You are a helpful assistant.', messages=[{'role': 'user', 'content': 'Hello'}, {'role': 'assistant', 'content': 'Hi there!'}], tools=[{'name': 'search'}], context_window=4096)
print('Budget:', budget)
import asyncio
from agent.orchestration import (
    AgentRegistry, AgentRole, TaskSpec, TaskBudget, TaskPriority,
    initialize_agent_registry
)
from agent.orchestration.adapters import (
    CoreAgentAdapter, AutomationAgentAdapter, DelegateAgentAdapter
)
from agent.orchestration.router import (
    CapabilityRouter, RoutingContext, create_router
)

# Factory wrappers that accept **kwargs
async def core_factory(**kwargs):
    return await CoreAgentAdapter.create(kwargs.get('config', {}), kwargs.get('role', AgentRole.COORDINATOR))

def make_auto_factory(role):
    async def factory(**kwargs):
        return await AutomationAgentAdapter.create(kwargs.get('config', {}), role)
    return factory

async def delegate_leaf_factory(**kwargs):
    return await DelegateAgentAdapter.create(kwargs.get('config', {}), AgentRole.COORDINATOR)

async def delegate_orch_factory(**kwargs):
    return await DelegateAgentAdapter.create(kwargs.get('config', {}), AgentRole.COORDINATOR)

async def test_router():
    registry = await initialize_agent_registry()
    
    # Create adapter instances to get capabilities
    core_adapter = CoreAgentAdapter()
    auto_adapters = {role: AutomationAgentAdapter(role=role) for role in [
        AgentRole.DEVELOPER, AgentRole.RESEARCH, AgentRole.BROWSER, 
        AgentRole.WRITER, AgentRole.QA, AgentRole.DEPLOYMENT,
        AgentRole.SECURITY, AgentRole.FILE
    ]}
    delegate_leaf = DelegateAgentAdapter(role='leaf')
    delegate_orch = DelegateAgentAdapter(role='orchestrator')
    
    # Register agents
    await registry.register(
        agent_type='core',
        factory=core_factory,
        role=AgentRole.COORDINATOR,
        capabilities=core_adapter.capabilities,
        tags={'core', 'general'},
        priority=100
    )
    
    for role, adapter in auto_adapters.items():
        await registry.register(
            agent_type='automation:' + role.value,
            factory=make_auto_factory(role),
            role=role,
            capabilities=adapter.capabilities,
            tags={'automation', role.value},
            priority=50
        )
    
    await registry.register(
        agent_type='delegate:leaf',
        factory=delegate_leaf_factory,
        role=AgentRole.COORDINATOR,
        capabilities=delegate_leaf.capabilities,
        tags={'delegate', 'leaf'},
        priority=30
    )
    await registry.register(
        agent_type='delegate:orchestrator',
        factory=delegate_orch_factory,
        role=AgentRole.COORDINATOR,
        capabilities=delegate_orch.capabilities,
        tags={'delegate', 'orchestrator'},
        priority=30
    )
    
    # Create router
    router = create_router(registry)
    
    # Test 1: Route a coding task (core agent has both coding + file_operations)
    print('Test 1: Route a coding task (core agent)')
    task = TaskSpec(
        goal='Implement a REST API endpoint',
        required_capabilities=['coding', 'file_operations'],
        budget=TaskBudget(max_cost_usd=5.0)
    )
    decision = await router.route(task)
    print('  Selected: {} (agent: {}...)'.format(decision.role, decision.agent_id[:20]))
    print('  Confidence: {:.2f}'.format(decision.confidence))
    print('  Matched: {}'.format(decision.matched_capabilities))
    print('  Missing: {}'.format(decision.missing_capabilities))
    print('  Reasoning: {}'.format(decision.reasoning))
    print('  Estimated cost: ${:.4f}'.format(decision.estimated_cost))
    print('  Estimated latency: {:.1f}s'.format(decision.estimated_latency))
    
    # Test 2: Route with preferred DEVELOPER role (automation agent has coding but not file_operations)
    print('\nTest 2: Route with preferred DEVELOPER role')
    task = TaskSpec(
        goal='Write a function',
        required_capabilities=['coding'],
        preferred_agent_role=AgentRole.DEVELOPER,
        budget=TaskBudget(max_cost_usd=2.0)
    )
    decision = await router.route(task)
    print('  Selected: {}'.format(decision.role))
    print('  Confidence: {:.2f}'.format(decision.confidence))
    print('  Matched: {}'.format(decision.matched_capabilities))
    print('  Missing: {}'.format(decision.missing_capabilities))
    
    # Test 3: Research task
    print('\nTest 3: Research task')
    task = TaskSpec(
        goal='Research AI trends',
        required_capabilities=['web_search', 'research'],
        budget=TaskBudget(max_cost_usd=2.0)
    )
    decision = await router.route(task)
    print('  Selected: {}'.format(decision.role))
    print('  Matched: {}'.format(decision.matched_capabilities))
    
    # Test 4: Cost optimized routing
    print('\nTest 4: Cost optimized routing')
    task = TaskSpec(
        goal='Read a file',
        required_capabilities=['file_operations'],
        budget=TaskBudget(max_cost_usd=0.10)
    )
    ctx = RoutingContext(task=task, strategy='cost_optimized')
    decision = await router.route(task, ctx)
    print('  Selected: {} (cost: ${:.4f})'.format(decision.role, decision.estimated_cost))
    
    # Test 5: Latency optimized routing
    print('\nTest 5: Latency optimized routing')
    task = TaskSpec(
        goal='Quick code edit',
        required_capabilities=['coding'],
        budget=TaskBudget(max_cost_usd=1.0)
    )
    ctx = RoutingContext(task=task, strategy='latency_optimized')
    decision = await router.route(task, ctx)
    print('  Selected: {} (latency: {:.1f}s)'.format(decision.role, decision.estimated_latency))
    
    # Test 6: Local preferred
    print('\nTest 6: Local preferred')
    task = TaskSpec(
        goal='Local analysis',
        required_capabilities=['coding'],
        budget=TaskBudget(max_cost_usd=1.0)
    )
    ctx = RoutingContext(task=task, strategy='best_match', prefer_local=True)
    decision = await router.route(task, ctx)
    print('  Selected: {}'.format(decision.role))
    print('  Reasoning: {}'.format(decision.reasoning))
    
    # Test 7: Least loaded strategy
    print('\nTest 7: Least loaded strategy')
    task = TaskSpec(
        goal='Run tests',
        required_capabilities=['testing'],
        budget=TaskBudget(max_cost_usd=1.0)
    )
    ctx = RoutingContext(task=task, strategy='least_loaded')
    decision = await router.route(task, ctx)
    print('  Selected: {} (strategy: {})'.format(decision.role, decision.strategy))
    
    # Test 8: Round robin strategy
    print('\nTest 8: Round robin strategy')
    task = TaskSpec(
        goal='Process item',
        required_capabilities=['file_operations'],
        budget=TaskBudget(max_cost_usd=1.0)
    )
    ctx = RoutingContext(task=task, strategy='round_robin')
    decision = await router.route(task, ctx)
    print('  Selected: {} (strategy: {})'.format(decision.role, decision.strategy))
    
    # Test 9: Routing stats
    print('\nRouting stats: {}'.format(router.get_routing_stats()))
    
    await registry.stop()
    print('\nAll router tests passed!')

asyncio.run(test_router())
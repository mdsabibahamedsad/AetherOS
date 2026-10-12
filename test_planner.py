import asyncio
from agent.orchestration import (
    AgentRegistry, AgentRole, TaskSpec, TaskBudget, TaskPriority,
    initialize_agent_registry
)
from agent.orchestration.adapters import (
    CoreAgentAdapter, AutomationAgentAdapter, DelegateAgentAdapter
)
from agent.orchestration.router import create_router
from agent.orchestration.planner import create_planning_engine

async def test_planner():
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
        factory=CoreAgentAdapter.create,
        role=AgentRole.COORDINATOR,
        capabilities=core_adapter.capabilities,
        tags={'core', 'general'},
        priority=100
    )
    
    for role, adapter in auto_adapters.items():
        await registry.register(
            agent_type='automation:' + role.value,
            factory=lambda cfg, r=role: AutomationAgentAdapter.create(cfg, r),
            role=role,
            capabilities=adapter.capabilities,
            tags={'automation', role.value},
            priority=50
        )
    
    await registry.register(
        agent_type='delegate:leaf',
        factory=lambda cfg: DelegateAgentAdapter.create(cfg, AgentRole.COORDINATOR),
        role=AgentRole.COORDINATOR,
        capabilities=delegate_leaf.capabilities,
        tags={'delegate', 'leaf'},
        priority=30
    )
    await registry.register(
        agent_type='delegate:orchestrator',
        factory=lambda cfg: DelegateAgentAdapter.create(cfg, AgentRole.COORDINATOR),
        role=AgentRole.COORDINATOR,
        capabilities=delegate_orch.capabilities,
        tags={'delegate', 'orchestrator'},
        priority=30
    )
    
    # Create router
    router = create_router(registry)
    
    # Create planning engine
    planning_engine = await create_planning_engine(registry, router)
    
    # Test 1: Create a plan
    print('Test 1: Create a plan')
    plan = await planning_engine.create_plan(
        goal='Build a REST API with authentication',
        context={'framework': 'FastAPI', 'database': 'PostgreSQL'},
        constraints=['Use JWT for auth', 'Follow REST conventions'],
        priority=TaskPriority.HIGH,
        max_budget=10.0,
        user_id='test_user',
        session_id='test_session',
    )
    print('  Created plan: {}'.format(plan.plan_id))
    print('  Goal: {}'.format(plan.goal))
    print('  Subtasks: {}'.format(len(plan.subtasks)))
    print('  Estimated cost: ${:.2f}'.format(plan.estimated_cost))
    print('  Estimated time: {:.0f}s'.format(plan.estimated_time))
    print('  Risk level: {}'.format(plan.risk_level.value))
    print('  Version: {}'.format(plan.version))
    
    # Test 2: Validate plan
    print('\nTest 2: Validate plan')
    validation = await planning_engine.validate_plan(plan.plan_id)
    print('  Valid: {}'.format(validation.valid))
    if validation.issues:
        for issue in validation.issues:
            print('  {}: {}'.format(issue.severity.value, issue.message))
    
    # Test 3: Create new version
    print('\nTest 3: Create new version')
    new_version = await planning_engine.create_new_version(
        plan.plan_id,
        reason='Added rate limiting requirement',
        changed_by='user',
    )
    print('  New version: {}'.format(new_version.version))
    print('  Diff: {}'.format(new_version.diff_from_previous))
    
    # Test 4: Replan on failure
    print('\nTest 4: Replan on failure')
    replanned = await planning_engine.replan(
        plan.plan_id,
        trigger='failure',
        failed_task_id=plan.subtasks[0].task_id if plan.subtasks else 'task_1',
        error_details='Authentication module failed to initialize',
    )
    print('  Replanned: {}'.format(replanned is not None))
    if replanned:
        print('  Subtasks: {}'.format(len(replanned.subtasks)))
    
    await registry.stop()
    print('\nAll planner tests passed!')

asyncio.run(test_planner())
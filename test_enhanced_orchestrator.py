"""
Test script for Enhanced Task Orchestrator
"""

import asyncio
import sys
import os

# Add the aetheros directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'aetheros'))

from aetheros_automation.enhanced_orchestrator import EnhancedTaskOrchestrator
from aetheros_automation.identity.agent_identity import AgentRole as IdentityAgentRole, AgentStatus

async def test_enhanced_orchestrator():
    """Test the enhanced orchestrator functionality"""
    print("Testing Enhanced Task Orchestrator...")
    
    # Create orchestrator instance
    orchestrator = EnhancedTaskOrchestrator()
    
    # Test 1: Create agent identity
    print("\n1. Testing agent identity creation...")
    identity = await orchestrator.create_agent_identity_for_task(
        task=type('obj', (object,), {
            'agent_role': 'developer',
            'id': 'test-task-1',
            'tools': ['code_execution', 'terminal'],
            'description': 'Test task for identity creation',
            'estimated_duration': 100.0,
            'requires_approval': False,
            'max_retries': 3
        })(),
        mission_id="test-mission-1",
        workspace_id="test-workspace-1"
    )
    
    print(f"Created identity: {identity.agent_id}")
    print(f"Role: {identity.role.value}")
    print(f"Mission ID: {identity.mission_id}")
    print(f"Status: {identity.status.value}")
    
    # Test 2: Check lifecycle
    print("\n2. Testing lifecycle management...")
    lifecycle = orchestrator.lifecycle_registry.ensure(identity.agent_id)
    print(f"Current state: {lifecycle.get_current_state().value}")
    
    # Test transition
    success = lifecycle.transition(
        lifecycle_registry.AgentLifecycleState.READY,
        {"test": "transition"}
    )
    print(f"Transition to READY: {success}")
    print(f"New state: {lifecycle.get_current_state().value}")
    
    # Test 3: Get enhanced stats
    print("\n3. Testing enhanced statistics...")
    stats = orchestrator.get_enhanced_stats()
    print(f"Total identities: {stats['total_identities']}")
    print(f"Identities by status: {stats['identities_by_status']}")
    print(f"Lifecycle distribution: {stats['lifecycle_distribution']}")
    
    # Test 4: Test backward compatibility by accessing base methods
    print("\n4. Testing backward compatibility...")
    plan = await orchestrator.understand_objective("Test goal for backward compatibility")
    print(f"Understood objective: {plan.goal}")
    print(f"Plan ID: {plan.id}")
    
    print("\n✅ All tests passed!")
    return True

if __name__ == "__main__":
    # Run the test
    try:
        result = asyncio.run(test_enhanced_orchestrator())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

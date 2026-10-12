"""
Lifecycle management for agent identity system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import json


class AgentLifecycleState(Enum):
    """Possible lifecycle states for an agent."""
    INITIALIZING = "initializing"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    TERMINATED = "terminated"
    READY = "ready"  # Added based on test usage


@dataclass
class LifecycleTransition:
    """Represents a transition between lifecycle states."""
    from_state: AgentLifecycleState
    to_state: AgentLifecycleState
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transition to dictionary representation."""
        return {
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class AgentLifecycleTracker:
    """Tracks lifecycle state for a specific agent."""
    agent_id: str
    current_state: AgentLifecycleState = AgentLifecycleState.INITIALIZING
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def get_current_state(self) -> AgentLifecycleState:
        """Get current lifecycle state."""
        return self.current_state
    
    def transition(self, new_state: AgentLifecycleState, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Transition to a new lifecycle state."""
        if metadata is None:
            metadata = {}
        
        # Record the transition
        transition_record = {
            "from_state": self.current_state.value,
            "to_state": new_state.value,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata
        }
        self.state_history.append(transition_record)
        
        # Update current state
        self.current_state = new_state
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tracker to dictionary representation."""
        return {
            "agent_id": self.agent_id,
            "current_state": self.current_state.value,
            "state_history": self.state_history
        }


class LifecycleRegistry:
    """Registry for tracking lifecycle states of agents."""
    
    def __init__(self):
        self._agents: Dict[str, AgentLifecycleTracker] = {}
    
    def ensure(self, agent_id: str) -> AgentLifecycleTracker:
        """Get or create a lifecycle tracker for an agent."""
        if agent_id not in self._agents:
            self._agents[agent_id] = AgentLifecycleTracker(agent_id=agent_id)
        return self._agents[agent_id]
    
    def get_agent_state(self, agent_id: str) -> Optional[AgentLifecycleState]:
        """Get the current lifecycle state of an agent."""
        tracker = self._agents.get(agent_id)
        return tracker.get_current_state() if tracker else None
    
    @property
    def AgentLifecycleState(self):
        """Access to the AgentLifecycleState enum for backward compatibility."""
        return AgentLifecycleState


# Global lifecycle registry instance
lifecycle_registry = LifecycleRegistry()
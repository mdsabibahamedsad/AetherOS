"""
Agent Identity System for AetherOS Orchestration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import uuid
import time


class AgentRole(Enum):
    """Logical agent roles for specialization"""
    GENERAL_AGENT = "general_agent"
    PLANNER_AGENT = "planner_agent"
    RESEARCH_AGENT = "research_agent"
    CODING_AGENT = "coding_agent"
    ANALYSIS_AGENT = "analysis_agent"
    WRITING_AGENT = "writing_agent"
    DATA_AGENT = "data_agent"
    BROWSER_AGENT = "browser_agent"
    SYSTEM_AGENT = "system_agent"
    SECURITY_AGENT = "security_agent"
    REVIEW_AGENT = "review_agent"
    VERIFICATION_AGENT = "verification_agent"
    COORDINATOR_AGENT = "coordinator_agent"


class AgentStatus(Enum):
    """Agent lifecycle states"""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    PAUSED = "paused"
    BLOCKED = "blocked"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERING = "recovering"
    TERMINATED = "terminated"
    QUARANTINED = "quarantined"


class AutonomyLevel(Enum):
    """Levels of agent autonomy"""
    MANUAL = "manual"
    ASSISTED = "assisted"
    SUPERVISED = "supervised"
    AUTONOMOUS = "autonomous"
    RESTRICTED_AUTONOMOUS = "restricted_autonomous"


@dataclass
class AgentIdentity:
    """
    Complete identity for every running agent in the AetherOS system.
    
    Every running agent must have:
    - agentId
    - parentAgentId
    - missionId
    - taskId
    - workspaceId
    - role
    - createdAt
    - status
    - permissionScope
    - model
    - provider
    """
    
    # Core identification
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_agent_id: Optional[str] = None
    mission_id: Optional[str] = None
    task_id: Optional[str] = None
    workspace_id: Optional[str] = None
    
    # Agent specification
    role: AgentRole = AgentRole.GENERAL_AGENT
    autonomy_level: AutonomyLevel = AutonomyLevel.SUPERVISED
    
    # Lifecycle tracking
    status: AgentStatus = AgentStatus.CREATED
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    last_heartbeat: float = field(default_factory=time.time)
    
    # Execution context
    model: str = "gpt-4o"
    provider: str = "openai"
    permission_scope: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    
    # Resource tracking
    cpu_usage: float = 0.0
    memory_usage: float = 0.0  # in MB
    token_usage: int = 0
    api_calls: int = 0
    
    # Relationships
    child_agent_ids: List[str] = field(default_factory=list)
    spawned_tasks: List[str] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_active(self) -> bool:
        """Check if agent is currently active"""
        return self.status in [AgentStatus.RUNNING, AgentStatus.WAITING, 
                              AgentStatus.PAUSED, AgentStatus.VERIFYING]
    
    def is_terminal(self) -> bool:
        """Check if agent is in a terminal state"""
        return self.status in [AgentStatus.COMPLETED, AgentStatus.FAILED, 
                              AgentStatus.TERMINATED, AgentStatus.QUARANTINED]
    
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        if self.completed_at:
            return self.completed_at - self.created_at
        elif self.started_at:
            return time.time() - self.started_at
        else:
            return time.time() - self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "agent_id": self.agent_id,
            "parent_agent_id": self.parent_agent_id,
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "workspace_id": self.workspace_id,
            "role": self.role.value,
            "autonomy_level": self.autonomy_level.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "last_heartbeat": self.last_heartbeat,
            "model": self.model,
            "provider": self.provider,
            "permission_scope": self.permission_scope,
            "tools": self.tools,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "token_usage": self.token_usage,
            "api_calls": self.api_calls,
            "child_agent_ids": self.child_agent_ids,
            "spawned_tasks": self.spawned_tasks,
            "tags": self.tags,
            "metadata": self.metadata,
            "elapsed_time": self.elapsed_time(),
            "is_active": self.is_active(),
            "is_terminal": self.is_terminal()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentIdentity':
        """Create from dictionary"""
        identity = cls()
        identity.agent_id = data.get("agent_id", identity.agent_id)
        identity.parent_agent_id = data.get("parent_agent_id")
        identity.mission_id = data.get("mission_id")
        identity.task_id = data.get("task_id")
        identity.workspace_id = data.get("workspace_id")
        identity.role = AgentRole(data.get("role", AgentRole.GENERAL_AGENT.value))
        identity.autonomy_level = AutonomyLevel(data.get("autonomy_level", AutonomyLevel.SUPERVISED.value))
        identity.status = AgentStatus(data.get("status", AgentStatus.CREATED.value))
        identity.created_at = data.get("created_at", identity.created_at)
        identity.started_at = data.get("started_at")
        identity.completed_at = data.get("completed_at")
        identity.last_heartbeat = data.get("last_heartbeat", identity.last_heartbeat)
        identity.model = data.get("model", identity.model)
        identity.provider = data.get("provider", identity.provider)
        identity.permission_scope = data.get("permission_scope", [])
        identity.tools = data.get("tools", [])
        identity.cpu_usage = data.get("cpu_usage", 0.0)
        identity.memory_usage = data.get("memory_usage", 0.0)
        identity.token_usage = data.get("token_usage", 0)
        identity.api_calls = data.get("api_calls", 0)
        identity.child_agent_ids = data.get("child_agent_ids", [])
        identity.spawned_tasks = data.get("spawned_tasks", [])
        identity.tags = data.get("tags", [])
        identity.metadata = data.get("metadata", {})
        return identity


# Global identity registry
class IdentityRegistry:
    """Registry for tracking all agent identities"""
    
    def __init__(self):
        self._identities: Dict[str, AgentIdentity] = {}
        self._lock = __import__('threading').RLock()
    
    def register(self, identity: AgentIdentity) -> None:
        """Register an agent identity"""
        with self._lock:
            self._identities[identity.agent_id] = identity
    
    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent identity"""
        with self._lock:
            if agent_id in self._identities:
                del self._identities[agent_id]
                return True
            return False
    
    def get(self, agent_id: str) -> Optional[AgentIdentity]:
        """Get an agent identity by ID"""
        with self._lock:
            return self._identities.get(agent_id)
    
    def list_all(self) -> List[AgentIdentity]:
        """List all registered identities"""
        with self._lock:
            return list(self._identities.values())
    
    def list_by_mission(self, mission_id: str) -> List[AgentIdentity]:
        """List all identities for a specific mission"""
        with self._lock:
            return [identity for identity in self._identities.values() 
                   if identity.mission_id == mission_id]
    
    def list_by_workspace(self, workspace_id: str) -> List[AgentIdentity]:
        """List all identities for a specific workspace"""
        with self._lock:
            return [identity for identity in self._identities.values() 
                   if identity.workspace_id == workspace_id]
    
    def count_by_status(self, status: AgentStatus) -> int:
        """Count identities by status"""
        with self._lock:
            return sum(1 for identity in self._identities.values() 
                      if identity.status == status)
    
    def cleanup_terminal(self, max_age_hours: float = 24.0) -> int:
        """Remove terminal identities older than max_age_hours"""
        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0
        
        with self._lock:
            to_remove = []
            for agent_id, identity in self._identities.items():
                if identity.is_terminal() and identity.created_at < cutoff:
                    to_remove.append(agent_id)
            
            for agent_id in to_remove:
                del self._identities[agent_id]
                removed += 1
        
        return removed


# Global instance
identity_registry = IdentityRegistry()

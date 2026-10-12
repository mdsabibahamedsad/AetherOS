"""
Checkpoint Manager — checkpoint creation, storage, and management.

Supports periodic, on-demand, and event-triggered checkpoints.
"""

from __future__ import annotations

import logging
import threading
import time
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path

from kernel.core.types import (
    Checkpoint,
    AgentProcess,
    AgentLifecycleState,
    Intent,
    AuthorityGrant,
    ResourceAllocation,
    ProvenanceType,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class CheckpointMetadata:
    """Metadata for a stored checkpoint."""
    checkpoint_id: str
    agent_id: str
    process_id: str
    intent_id: str
    created_at: float
    size_bytes: int
    storage_path: str
    tags: List[str] = field(default_factory=list)


class CheckpointManager:
    """
    Manages checkpoint creation, storage, and retrieval.
    
    Checkpoints capture full agent state for recovery and migration.
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        # Storage
        self.checkpoint_dir = Path(config.checkpoint_dir or "~/.aetheros/checkpoints").expanduser()
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory index
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._metadata: Dict[str, CheckpointMetadata] = {}
        self._agent_checkpoints: Dict[str, List[str]] = {}  # agent_id -> checkpoint_ids

        # Callbacks for state capture
        self._state_capture_callbacks: Dict[str, Callable[[AgentProcess], Dict[str, Any]]] = {}

    def register_state_capture(self, name: str, callback: Callable[[AgentProcess], Dict[str, Any]]) -> None:
        """Register a callback to capture subsystem state."""
        self._state_capture_callbacks[name] = callback

    def create_checkpoint(
        self,
        agent_id: str,
        checkpoint_type: str = "periodic",
        tags: List[str] = None,
    ) -> Checkpoint:
        """Create a checkpoint for an agent."""
        # This would be called by the kernel with the actual process
        # For now, create a minimal checkpoint (type/tags live in metadata)
        checkpoint = Checkpoint(
            checkpoint_id=new_id("cp"),
            agent_id=agent_id,
            process_id="",
            intent_id="",
            metadata={"checkpoint_type": checkpoint_type, "tags": tags or []},
        )

        with self._lock:
            self._checkpoints[checkpoint.checkpoint_id] = checkpoint
            self._agent_checkpoints.setdefault(agent_id, []).append(checkpoint.checkpoint_id)

            # Limit checkpoints per agent
            max_cp = self.config.max_checkpoints_per_agent
            if len(self._agent_checkpoints[agent_id]) > max_cp:
                old_id = self._agent_checkpoints[agent_id].pop(0)
                self._checkpoints.pop(old_id, None)
                self._metadata.pop(old_id, None)

        # Persist to disk
        self._persist_checkpoint(checkpoint)

        if self.event_bus:
            self.event_bus.emit("checkpoint.created", {
                "checkpoint_id": checkpoint.checkpoint_id,
                "agent_id": agent_id,
                "type": checkpoint_type,
            })

        logger.debug("CheckpointManager: created checkpoint %s for agent %s",
                     checkpoint.checkpoint_id, agent_id)
        return checkpoint

    def create_full_checkpoint(self, process: AgentProcess) -> Checkpoint:
        """Create a full checkpoint with complete process state."""
        checkpoint = Checkpoint(
            checkpoint_id=new_id("cp"),
            agent_id=process.agent_id,
            process_id=process.process_id,
            intent_id=process.intent.intent_id if process.intent else "",
            intent=process.intent,
            state=process.state,
            context=self._capture_context(process),
            memory_refs=self._capture_memory_refs(process),
            authority=process.authority,
            capabilities=process.capabilities,
            resource_allocation=process.resource_allocation,
            model_state=self._capture_model_state(process),
            tool_state=self._capture_tool_state(process),
            artifacts=self._capture_artifacts(process),
            subtasks=self._capture_subtasks(process),
            event_offset=0,  # Would be set from event bus
        )

        # Call registered state capture callbacks
        for name, callback in self._state_capture_callbacks.items():
            try:
                checkpoint.metadata[name] = callback(process)
            except Exception as exc:
                logger.error("State capture callback %s failed: %s", name, exc)

        with self._lock:
            self._checkpoints[checkpoint.checkpoint_id] = checkpoint
            self._agent_checkpoints.setdefault(process.agent_id, []).append(checkpoint.checkpoint_id)

            # Limit checkpoints per agent
            max_cp = self.config.max_checkpoints_per_agent
            if len(self._agent_checkpoints[process.agent_id]) > max_cp:
                old_id = self._agent_checkpoints[process.agent_id].pop(0)
                self._checkpoints.pop(old_id, None)
                self._metadata.pop(old_id, None)

        # Persist to disk
        self._persist_checkpoint(checkpoint)

        if self.event_bus:
            self.event_bus.emit("checkpoint.created", {
                "checkpoint_id": checkpoint.checkpoint_id,
                "agent_id": process.agent_id,
                "process_id": process.process_id,
                "type": "full",
            })

        logger.info("CheckpointManager: created full checkpoint %s for agent %s",
                    checkpoint.checkpoint_id, process.agent_id)
        return checkpoint

    def _capture_context(self, process: AgentProcess) -> Dict[str, Any]:
        """Capture context state."""
        # Would integrate with context manager
        return {}

    def _capture_memory_refs(self, process: AgentProcess) -> List[str]:
        """Capture memory references."""
        # Would integrate with memory manager
        return []

    def _capture_model_state(self, process: AgentProcess) -> Dict[str, Any]:
        """Capture model state."""
        return {}

    def _capture_tool_state(self, process: AgentProcess) -> Dict[str, Any]:
        """Capture tool state."""
        return {}

    def _capture_artifacts(self, process: AgentProcess) -> List[str]:
        """Capture artifact references."""
        return []

    def _capture_subtasks(self, process: AgentProcess) -> List[str]:
        """Capture subtask references."""
        return []

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get a checkpoint by ID."""
        with self._lock:
            # Try memory first
            if checkpoint_id in self._checkpoints:
                return self._checkpoints[checkpoint_id]
            
            # Try disk
            return self._load_checkpoint(checkpoint_id)

    def list_checkpoints(self, agent_id: str = None) -> List[Checkpoint]:
        """List checkpoints, optionally filtered by agent."""
        with self._lock:
            if agent_id:
                ids = self._agent_checkpoints.get(agent_id, [])
                return [self._checkpoints[cid] for cid in ids if cid in self._checkpoints]
            return list(self._checkpoints.values())

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        with self._lock:
            checkpoint = self._checkpoints.pop(checkpoint_id, None)
            if not checkpoint:
                return False
            
            self._metadata.pop(checkpoint_id, None)
            agent_checkpoints = self._agent_checkpoints.get(checkpoint.agent_id, [])
            if checkpoint_id in agent_checkpoints:
                agent_checkpoints.remove(checkpoint_id)

        # Delete from disk
        path = self.checkpoint_dir / f"{checkpoint_id}.json"
        if path.exists():
            path.unlink()

        if self.event_bus:
            self.event_bus.emit("checkpoint.deleted", {
                "checkpoint_id": checkpoint_id,
            })

        return True

    def _persist_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Persist checkpoint to disk."""
        try:
            path = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
            data = checkpoint.to_dict()
            data["_persisted_at"] = _now()
            
            with open(path, 'w') as f:
                json.dump(data, f, default=str)
            
            # Update metadata
            size = path.stat().st_size
            self._metadata[checkpoint.checkpoint_id] = CheckpointMetadata(
                checkpoint_id=checkpoint.checkpoint_id,
                agent_id=checkpoint.agent_id,
                process_id=checkpoint.process_id,
                intent_id=checkpoint.intent_id,
                created_at=checkpoint.created_at,
                size_bytes=size,
                storage_path=str(path),
                tags=checkpoint.tags,
            )
        except Exception as exc:
            logger.error("Failed to persist checkpoint %s: %s", checkpoint.checkpoint_id, exc)

    def _load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load checkpoint from disk."""
        try:
            path = self.checkpoint_dir / f"{checkpoint_id}.json"
            if not path.exists():
                return None
            
            with open(path, 'r') as f:
                data = json.load(f)
            
            # Reconstruct checkpoint
            checkpoint = Checkpoint(
                checkpoint_id=data["checkpoint_id"],
                agent_id=data["agent_id"],
                process_id=data["process_id"],
                intent_id=data["intent_id"],
                intent=Intent(**data["intent"]) if data.get("intent") else None,
                state=AgentLifecycleState(data["state"]),
                context=data.get("context", {}),
                memory_refs=data.get("memory_refs", []),
                authority=AuthorityGrant(**data["authority"]) if data.get("authority") else None,
                capabilities=data.get("capabilities", []),
                resource_allocation=ResourceAllocation(**data["resource_allocation"]) if data.get("resource_allocation") else None,
                model_state=data.get("model_state", {}),
                tool_state=data.get("tool_state", {}),
                artifacts=data.get("artifacts", []),
                subtasks=data.get("subtasks", []),
                event_offset=data.get("event_offset", 0),
                created_at=data["created_at"],
                metadata=data.get("metadata", {}),
            )
            
            with self._lock:
                self._checkpoints[checkpoint_id] = checkpoint
                self._agent_checkpoints.setdefault(checkpoint.agent_id, []).append(checkpoint_id)
            
            return checkpoint
        except Exception as exc:
            logger.error("Failed to load checkpoint %s: %s", checkpoint_id, exc)
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get checkpoint manager statistics."""
        with self._lock:
            total = len(self._checkpoints)
            total_size = sum(m.size_bytes for m in self._metadata.values())
            by_agent: Dict[str, int] = {}
            for agent_id, cids in self._agent_checkpoints.items():
                by_agent[agent_id] = len(cids)

        return {
            "total_checkpoints": total,
            "total_size_bytes": total_size,
            "by_agent": by_agent,
            "storage_path": str(self.checkpoint_dir),
        }

    def shutdown(self) -> None:
        """Shutdown the checkpoint manager."""
        logger.info("CheckpointManager: shutting down")
        with self._lock:
            self._checkpoints.clear()
            self._metadata.clear()
            self._agent_checkpoints.clear()
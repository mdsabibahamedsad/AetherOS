"""
Multi-agent coordination handler for Aetheros agent runtime.
Integrates with the orchestration system's collaboration and sub-agent management.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from aetheros_automation.multi_agent.collaboration import AgentCollaborationManager
from aetheros_automation.multi_agent.sub_agent_manager import SubAgentManager
from aetheros_automation.models.models import AgentRole

logger = logging.getLogger(__name__)


class MultiAgentCoordinator:
    """
    Coordinates multi-agent activities for the Aetheros agent runtime.
    Manages collaboration sessions, sub-agents, and inter-agent communication.
    """
    
    def __init__(self):
        self.collaboration_manager = AgentCollaborationManager()
        self.sub_agent_manager = SubAgentManager()
        self._active_collaborations: Dict[str, Dict[str, Any]] = {}
        self._collaboration_contexts: Dict[str, Dict[str, Any]] = {}
        
    async def start_collaboration_session(
        self,
        agent_id: str,
        goal: str,
        participant_roles: Optional[List[AgentRole]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new collaboration session.
        
        Args:
            agent_id: The ID of the agent initiating the collaboration
            goal: The goal of the collaboration
            participant_roles: Optional list of roles to include in collaboration
            context: Optional context for the collaboration
            
        Returns:
            Collaboration session ID
        """
        try:
            # Determine participants
            participant_ids = [agent_id]  # Initiator is always a participant
            
            # If specific roles requested, we would create agents for those roles
            # For now, we'll just note the intent in context
            collab_context = {
                "initiator_agent_id": agent_id,
                "goal": goal,
                "participant_roles": [r.value for r in participant_roles] if participant_roles else [],
                "context": context or {},
                "started_at": time.time()
            }
            
            # Start collaboration
            collab_id = await self.collaboration_manager.start_collaboration(
                agent_ids=participant_ids,
                goal=goal,
                coordinator_id=agent_id
            )
            
            # Store context
            self._collaboration_contexts[collab_id] = collab_context
            self._active_collaborations[collab_id] = {
                "agent_id": agent_id,
                "goal": goal,
                "started_at": time.time(),
                "status": "active"
            }
            
            logger.info(f"Started collaboration session {collab_id} for agent {agent_id}")
            return collab_id
            
        except Exception as e:
            logger.error(f"Failed to start collaboration session: {e}")
            raise
    
    async def send_collaboration_message(
        self,
        collaboration_id: str,
        sender_id: str,
        content: str,
        message_type: str = "text",
        data: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Send a message within a collaboration session.
        
        Args:
            collaboration_id: The collaboration session ID
            sender_id: The ID of the sending agent
            content: The message content
            message_type: The type of message
            data: Optional data payload
            
        Returns:
            The sent message object
        """
        try:
            message = await self.collaboration_manager.send_message(
                collab_id=collaboration_id,
                sender_id=sender_id,
                content=content,
                msg_type=message_type,
                data=data
            )
            
            logger.debug(f"Sent collaboration message in {collaboration_id} from {sender_id}")
            return message
            
        except Exception as e:
            logger.error(f"Failed to send collaboration message: {e}")
            raise
    
    async def broadcast_to_collaboration(
        self,
        collaboration_id: str,
        sender_id: str,
        content: str,
        message_type: str = "broadcast"
    ) -> List[Dict[str, Any]]:
        """
        Broadcast a message to all participants in a collaboration.
        
        Args:
            collaboration_id: The collaboration session ID
            sender_id: The ID of the sending agent
            content: The message content
            message_type: The type of message
            
        Returns:
            List of sent message objects
        """
        try:
            messages = await self.collaboration_manager.broadcast(
                collab_id=collaboration_id,
                sender_id=sender_id,
                content=content,
                msg_type=message_type
            )
            
            logger.debug(f"Broadcasted message in {collaboration_id} from {sender_id} to {len(messages)} participants")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to broadcast collaboration message: {e}")
            raise
    
    async def share_collaboration_result(
        self,
        collaboration_id: str,
        agent_id: str,
        result_key: str,
        result_value: Any
    ) -> None:
        """
        Share a result within a collaboration session.
        
        Args:
            collaboration_id: The collaboration session ID
            agent_id: The ID of the agent sharing the result
            result_key: The key to identify the result
            result_value: The result value to share
        """
        try:
            await self.collaboration_manager.share_result(
                collab_id=collaboration_id,
                agent_id=agent_id,
                result_key=result_key,
                result_value=result_value
            )
            
            logger.debug(f"Shared result '{result_key}' in collaboration {collaboration_id} from agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to share collaboration result: {e}")
            raise
    
    def get_collaboration_result(
        self,
        collaboration_id: str,
        result_key: str
    ) -> Any:
        """
        Get a shared result from a collaboration session.
        
        Args:
            collaboration_id: The collaboration session ID
            result_key: The key identifying the result
            
        Returns:
            The result value, or None if not found
        """
        try:
            return self.collaboration_manager.get_shared_result(
                collab_id=collaboration_id,
                result_key=result_key
            )
        except Exception as e:
            logger.error(f"Failed to get collaboration result: {e}")
            return None
    
    def get_collaboration_context(
        self,
        collaboration_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the context for a collaboration session.
        
        Args:
            collaboration_id: The collaboration session ID
            
        Returns:
            The collaboration context, or None if not found
        """
        return self._collaboration_contexts.get(collaboration_id)
    
    async def end_collaboration_session(
        self,
        collaboration_id: str
    ) -> None:
        """
        End a collaboration session.
        
        Args:
            collaboration_id: The collaboration session ID
        """
        try:
            await self.collaboration_manager.end_collaboration(collab_id=collaboration_id)
            
            # Clean up context
            if collaboration_id in self._collaboration_contexts:
                del self._collaboration_contexts[collaboration_id]
                
            if collaboration_id in self._active_collaborations:
                del self._active_collaborations[collaboration_id]
                
            logger.info(f"Ended collaboration session {collaboration_id}")
            
        except Exception as e:
            logger.error(f"Failed to end collaboration session: {e}")
            raise
    
    async def create_sub_agent(
        self,
        parent_agent_id: str,
        role: AgentRole,
        goal: str,
        instructions: str = "",
        max_steps: int = 20,
        max_time: float = 300.0
    ) -> Dict[str, Any]:
        """
        Create a sub-agent for specialized task execution.
        
        Args:
            parent_agent_id: The ID of the parent agent
            role: The role of the sub-agent
            goal: The goal for the sub-agent
            instructions: Optional instructions for the sub-agent
            max_steps: Maximum steps for the sub-agent
            max_time: Maximum time in seconds for the sub-agent
            
        Returns:
            Information about the created sub-agent
        """
        try:
            # Delegate to the sub-agent manager
            sub_agent = await self.sub_agent_manager.create_sub_agent(
                parent_id=parent_agent_id,
                role=role,
                goal=goal,
                instructions=instructions,
                max_steps=max_steps,
                max_time=max_time
            )
            
            result = {
                "agent_id": sub_agent.agent_id,
                "role": sub_agent.role.value if hasattr(sub_agent.role, 'value') else str(sub_agent.role),
                "name": sub_agent.name,
                "goal": goal,
                "instructions": instructions,
                "max_steps": max_steps,
                "max_time": max_time,
                "created_at": time.time()
            }
            
            logger.info(f"Created sub-agent {sub_agent.agent_id} for parent {parent_agent_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create sub-agent: {e}")
            raise
    
    async def execute_sub_agent_task(
        self,
        sub_agent_id: str,
        task_goal: str,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a task using a sub-agent.
        
        Args:
            sub_agent_id: The ID of the sub-agent
            task_goal: The goal of the task
            task_description: Detailed description of the task
            context: Optional context for the task
            
        Returns:
            The task execution result
        """
        try:
            # Get the sub-agent
            sub_agent = self.sub_agent_manager.get_agent(sub_agent_id)
            if not sub_agent:
                raise ValueError(f"Sub-agent {sub_agent_id} not found")
            
            # Create a task for the sub-agent to execute
            from aetheros_automation.orchestrator.types import OrchestrationTask
            from aetheros_automation.models.models import TaskStatus
            
            task = OrchestrationTask(
                id=f"task_{int(time.time() * 1000)}",
                name=task_description[:50],
                description=task_description,
                agent_role=sub_agent.role,
                tools=sub_agent.tools,
                agent_id=sub_agent.agent_id,
                goal=task_goal
            )
            
            # Execute the task
            result = await self.sub_agent_manager.execute_task(
                sub_agent=sub_agent,
                task=task,
                context=context or {}
            )
            
            logger.info(f"Sub-agent {sub_agent_id} executed task: {task_goal}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute sub-agent task: {e}")
            raise
    
    def get_active_collaborations(self) -> List[str]:
        """
        Get list of active collaboration session IDs.
        
        Returns:
            List of active collaboration session IDs
        """
        return list(self._active_collaborations.keys())
    
    def get_collaboration_info(self, collaboration_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a collaboration session.
        
        Args:
            collaboration_id: The collaboration session ID
            
        Returns:
            Collaboration information, or None if not found
        """
        return self._active_collaborations.get(collaboration_id)
    
    def cleanup(self) -> None:
        """
        Clean up resources.
        """
        try:
            self._collaboration_contexts.clear()
            self._active_collaborations.clear()
            logger.info("Multi-agent coordinator cleaned up")
        except Exception as e:
            logger.error(f"Error during multi-agent coordinator cleanup: {e}")
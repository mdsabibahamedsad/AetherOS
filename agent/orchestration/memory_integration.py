"""Memory Integration for AetherOS Orchestration Layer.

Integrates with MASTER 9 Memory OS for planning context retrieval.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryIntegration:
    """Interface to MASTER 9 Memory OS for planning context."""
    
    def __init__(self):
        self._memory_store = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize memory integration."""
        try:
            # Try to import and initialize MASTER 9 memory
            from memory.memory_manager import MemoryManager
            self._memory_store = MemoryManager()
            await self._memory_store.initialize()
            self._initialized = True
            logger.info("Memory integration initialized")
        except ImportError:
            logger.warning("MASTER 9 Memory OS not available, using mock")
            self._initialized = False
        except Exception as e:
            logger.warning(f"Memory integration initialization failed: {e}")
            self._initialized = False
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """Search memory for relevant information."""
        if not self._initialized or not self._memory_store:
            return []
        
        try:
            results = await self._memory_store.search(
                query=query,
                limit=limit,
                filters=filters or {},
            )
            return results
        except Exception as e:
            logger.warning(f"Memory search failed: {e}")
            return []
    
    async def store(
        self,
        key: str,
        value: Any,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """Store information in memory."""
        if not self._initialized or not self._memory_store:
            return False
        
        try:
            await self._memory_store.store(
                key=key,
                value=value,
                metadata=metadata or {},
            )
            return True
        except Exception as e:
            logger.warning(f"Memory store failed: {e}")
            return False
    
    async def retrieve(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Any]:
        """Retrieve memory entries matching query."""
        if not self._initialized or not self._memory_store:
            return []
        
        try:
            results = await self._memory_store.retrieve(query, limit=limit)
            return results
        except Exception as e:
            logger.warning(f"Memory retrieve failed: {e}")
            return []
    
    async def search_similar_plans(
        self,
        goal: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search for similar past plans."""
        return await self.search(
            query=f"plan {goal}",
            limit=5,
            filters={"type": "plan"},
        )
    
    async def get_relevant_cases(
        self,
        trigger: str,
        task_id: str = "",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get relevant past cases for replanning."""
        query = f"replan {trigger}"
        return await self.search(query, limit=5)


# Global instance
_memory_integration: Optional[Any] = None


async def get_memory_integration() -> MemoryIntegration:
    """Get the global memory integration instance."""
    global _memory_integration
    if _memory_integration is None:
        _memory_integration = MemoryIntegration()
        await _memory_integration.initialize()
    return _memory_integration
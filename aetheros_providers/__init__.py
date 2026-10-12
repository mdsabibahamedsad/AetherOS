"""AetherOS AI Provider & Model Management System.

This package provides comprehensive provider and model management:
- Provider Manager (registration, lifecycle, health, priority, fallback)
- API Key Manager (secure storage, encryption, validation)
- Model Database (local cache, search, favorites, pinned)
- Model Selector & Filtering (reasoning, vision, code, fast, cheap, etc.)
- Default Model Registry (per-task model assignments)
- Failover System (retry, fallback model/provider, recovery)
- Local Model Manager (detect Ollama, LM Studio, vLLM, etc.)
- Provider Settings (per-provider configuration)
- Model Validator (comprehensive validation)
- Multi-Provider Orchestrator (route tasks to different providers)
"""

from aetheros_providers.provider_manager import ProviderManager, ProviderStatus, ProviderInfo
from aetheros_providers.api_key_manager import APIKeyManager, APIKeyInfo, KeyStatus
from aetheros_providers.model_database import ModelDatabase, ModelInfo, ModelCapability
from aetheros_providers.model_selector import ModelSelector, ModelFilter
from aetheros_providers.model_registry import DefaultModelRegistry, TaskType
from aetheros_providers.failover import FailoverManager, FailoverStrategy
from aetheros_providers.local_model_manager import LocalModelManager, LocalProvider
from aetheros_providers.provider_settings import ProviderSettingsManager, ProviderSettings
from aetheros_providers.model_validator import ModelValidator, ValidationResult
from aetheros_providers.multi_provider import MultiProviderOrchestrator, WorkflowStage

__all__ = [
    "ProviderManager", "ProviderStatus", "ProviderInfo",
    "APIKeyManager", "APIKeyInfo", "KeyStatus",
    "ModelDatabase", "ModelInfo", "ModelCapability",
    "ModelSelector", "ModelFilter",
    "DefaultModelRegistry", "TaskType",
    "FailoverManager", "FailoverStrategy",
    "LocalModelManager", "LocalProvider",
    "ProviderSettingsManager", "ProviderSettings",
    "ModelValidator", "ValidationResult",
    "MultiProviderOrchestrator", "WorkflowStage",
]
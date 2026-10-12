"""
Unified Model Registry for Aetheros - Phase 3

This module provides a unified model registry that serves as the 
single source of truth for model information across all providers, 
normalizing model data and providing efficient lookup capabilities.
"""

import time
import threading
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Set
from dataclasses import dataclass, field
from collections import defaultdict

if TYPE_CHECKING:
    from universal_provider_interface import ModelInfo as UPIModelInfo
    from provider_registry_enhanced import ProviderRegistryEnhanced

# Import existing systems
try:
    from aetheros_cli.providers import get_provider, resolve_provider_full, normalize_provider as _normalize_provider_name
    from agent.models_dev import get_provider_info as get_models_dev_provider_info
    from agent.models_dev import get_model_info as get_models_dev_model_info
    from agent.model_metadata import get_model_context_length
    HAS_MODEL_SYSTEM = True
except ImportError:
    HAS_MODEL_SYSTEM = False

# Import universal provider interface components
try:
    from universal_provider_interface import ModelInfo as UPIModelInfo, ProviderCapabilities as UPIProviderCapabilities
    HAS_UNIVERSAL_INTERFACE = True
except ImportError:
    HAS_UNIVERSAL_INTERFACE = False
    # Define fallback types for type checking
    UPIModelInfo = dict  # type: ignore
    UPIProviderCapabilities = dict  # type: ignore


@dataclass
class CachedModelInfo:
    """Cached information about a model."""
    model_info: object = None  # UPIModelInfo when available
    source: str = ""  # Where this model info came from (models.dev, provider, etc.)
    provider_id: str = ""  # Provider this model belongs to
    last_updated: float = field(default_factory=time.time)
    access_count: int = 0


@dataclass
class ModelAlias:
    """Represents a model alias mapping to a canonical model ID."""
    alias: str
    canonical_model_id: str
    provider_id: str
    is_primary: bool = False  # Whether this is the primary/recommended alias


class UnifiedModelRegistry:
    """
    Unified Model Registry that serves as a single source of truth for model information.
    
    This registry integrates:
    1. models.dev catalog for comprehensive model metadata
    2. Provider-specific model information from universal provider implementations
    3. Model aliases and normalization
    4. Caching and access tracking for performance
    5. Search and filtering capabilities
    """

    def __init__(self, cache_ttl: float = 3600.0, enable_background_updates: bool = True):
        """
        Initialize the unified model registry.
        
        Args:
            cache_ttl: Time-to-live for cached model information (seconds)
            enable_background_updates: Whether to perform background updates of model catalogs
        """
        self._cache_ttl = cache_ttl
        self._enable_background_updates = enable_background_updates
        self._model_cache: Dict[str, CachedModelInfo] = {}  # provider:model -> cached info
        self._provider_models: Dict[str, Set[str]] = defaultdict(set)  # provider_id -> set of model IDs
        self._model_aliases: Dict[str, ModelAlias] = {}  # alias -> ModelAlias
        self._reverse_aliases: Dict[str, Set[str]] = defaultdict(set)  # canonical_model_id -> set of aliases
        self._provider_registry: Optional[ProviderRegistryEnhanced] = None
        self._lock = threading.RLock()
        
    def set_provider_registry(self, provider_registry: 'ProviderRegistryEnhanced') -> None:
        """Set the provider registry for enhanced model information.
        
        Args:
            provider_registry: The enhanced provider registry to use for fetching provider instances
        """
        self._provider_registry = provider_registry

        self._update_thread = None
        self._stop_updates = False
        if self._enable_background_updates:
            self._start_background_updates()

    def _is_cache_valid(self, cached_info: CachedModelInfo) -> bool:
        """Check if cached model information is still valid."""
        return (time.time() - cached_info.last_updated) < self._cache_ttl

    def get_model_info(self, provider_id: str, model_id: str) -> Optional[object]:
        """
        Get model information for a specific provider and model.
        
        Args:
            provider_id: Unique identifier for the provider
            model_id: Identifier for the model (can be alias or canonical ID)
            
        Returns:
            Model information object if found, None otherwise
        """
        # First, resolve any aliases to get the canonical model ID
        canonical_model_id = self._resolve_model_alias(provider_id, model_id)
        if canonical_model_id is None:
            # If not an alias, treat the model_id as potentially canonical
            canonical_model_id = model_id
        
        cache_key = provider_id + ':' + canonical_model_id
        
        with self._lock:
            # Check cache first
            if cache_key in self._model_cache:
                cached_info = self._model_cache[cache_key]
                if self._is_cache_valid(cached_info):
                    cached_info.access_count += 1
                    return cached_info.model_info
            
            # Get from available sources
            model_info = self._fetch_model_info(provider_id, canonical_model_id)
            
            # Cache the result
            if model_info is not None:
                if cache_key not in self._model_cache:
                    self._model_cache[cache_key] = CachedModelInfo()
                
                self._model_cache[cache_key].model_info = model_info
                self._model_cache[cache_key].provider_id = provider_id
                self._model_cache[cache_key].last_updated = time.time()
                self._model_cache[cache_key].access_count = 1
                
                # Update provider's model set
                self._provider_models[provider_id].add(canonical_model_id)
            
            return model_info

    def _resolve_model_alias(self, provider_id: str, model_id: str) -> Optional[str]:
        """
        Resolve a model alias to its canonical model ID.
        
        Args:
            provider_id: Provider ID
            model_id: Model ID or alias
            
        Returns:
            Canonical model ID if alias found, None otherwise
        """
        # Normalize the lookup key
        lookup_key = (provider_id + ':' + model_id).lower()
        
        with self._lock:
            if lookup_key in self._model_aliases:
                alias_obj = self._model_aliases[lookup_key]
                return alias_obj.canonical_model_id
        
        return None

    def _fetch_model_info(self, provider_id: str, model_id: str) -> Optional[object]:
        """
        Fetch model information from available sources.
        
        Args:
            provider_id: Unique identifier for the provider
            model_id: Identifier for the model (canonical ID)
            
        Returns:
            Model information object if found, None otherwise
        """
        # Try to get from models.dev first (most comprehensive)
        if HAS_MODEL_SYSTEM:
            try:
                # Normalize provider ID for models.dev lookup
                normalized_provider_id = _normalize_provider_name(provider_id)
                model_info = get_models_dev_model_info(normalized_provider_id, model_id)
                if model_info is not None:
                    # Convert models.dev ModelInfo to universal ModelInfo if needed
                    if HAS_UNIVERSAL_INTERFACE:
                        return self._convert_models_dev_to_universal_model_info(model_info, provider_id)
                    else:
                        return model_info
            except Exception:
                pass  # Fall back to other sources if models.dev lookup fails
        
        # Try to get from universal provider interface if we have a provider instance
        if self._provider_registry is not None and HAS_UNIVERSAL_INTERFACE:
            try:
                provider_instance = self._provider_registry.get_or_create_provider_instance(provider_id)
                if provider_instance is not None:
                    # Try to get model info from the provider's universal interface
                    # Note: This depends on the provider implementation supporting get_model
                    # For now, we'll rely on models.dev as the primary source
                    pass
            except Exception:
                pass
        
        # If we still don't have info, create a basic model info with limited data
        return self._create_basic_model_info(provider_id, model_id)

    def _convert_models_dev_to_universal_model_info(self, models_dev_model: object, provider_id: str) -> object:
        """
        Convert a models.dev ModelInfo to a universal provider interface ModelInfo.
        
        Args:
            models_dev_model: ModelInfo from models.dev
            provider_id: Provider ID
            
        Returns:
            Universal provider interface ModelInfo object
        """
        if not HAS_UNIVERSAL_INTERFACE:
            return models_dev_model
        
        # Extract data from models.dev model
        model_id = getattr(models_dev_model, 'id', '')
        name = getattr(models_dev_model, 'name', model_id)
        family = getattr(models_dev_model, 'family', None)
        context_window = getattr(models_dev_model, 'context_window', 0)
        
        # Determine modalities
        input_modalities = list(getattr(models_dev_model, 'input_modalities', []))
        output_modalities = list(getattr(models_dev_model, 'output_modalities', []))
        
        # Determine capabilities
        reasoning_support = getattr(models_dev_model, 'reasoning', False)
        tool_support = getattr(models_dev_model, 'tool_call', False)
        vision_support = getattr(models_dev_model, 'supports_vision', lambda: False)() if hasattr(models_dev_model, 'supports_vision') else False
        audio_support = getattr(models_dev_model, 'supports_audio_input', lambda: False)() if hasattr(models_dev_model, 'supports_audio_input') else False
        structured_output_support = getattr(models_dev_model, 'structured_output', False)
        embedding_support = False  # Would need to be determined from other sources
        image_support = 'image' in input_modalities
        
        # Availability status
        status = getattr(models_dev_model, 'status', '').lower()
        if status == 'deprecated':
            availability = 'unavailable'
        elif status in ['alpha', 'beta']:
            availability = 'available'  # Treat alpha/beta as available but maybe with warnings
        else:
            availability = 'available'
        
        # Pricing metadata
        pricing_metadata = {}
        if hasattr(models_dev_model, 'cost_input') and hasattr(models_dev_model, 'cost_output'):
            pricing_metadata = {
                'input_cost_per_million_usd': getattr(models_dev_model, 'cost_input', 0.0),
                'output_cost_per_million_usd': getattr(models_dev_model, 'cost_output', 0.0),
                'cache_read_cost_per_million_usd': getattr(models_dev_model, 'cost_cache_read', None),
                'cache_write_cost_per_million_usd': getattr(models_dev_model, 'cost_cache_write', None)
            }
        
        # Limits metadata
        limits = {}
        if hasattr(models_dev_model, 'max_output'):
            limits['max_output_tokens'] = getattr(models_dev_model, 'max_output', None)
        if hasattr(models_dev_model, 'max_input'):
            limits['max_input_tokens'] = getattr(models_dev_model, 'max_input', None)
        
        # Create universal ModelInfo
        from universal_provider_interface import ModelInfo as UPIModelInfo
        
        return UPIModelInfo(
            id=model_id,
            provider_id=provider_id,
            display_name=name,
            canonical_id=model_id,  # Could be normalized further if needed
            family=family,
            version=None,  # Not typically in models.dev
            context_window=context_window,
            input_modalities=input_modalities,
            output_modalities=output_modalities,
            reasoning_support=reasoning_support,
            tool_support=tool_support,
            structured_output_support=structured_output_support,
            vision_support=vision_support,
            audio_support=audio_support,
            embedding_support=embedding_support,
            image_support=image_support,
            availability=availability,
            status=status,
            pricing_metadata=pricing_metadata,
            limits=limits,
            created_at=None,  # Not typically in models.dev
            updated_at=None   # Not typically in models.dev
        )

    def _create_basic_model_info(self, provider_id: str, model_id: str) -> Optional[object]:
        """
        Create a basic model info when no other sources are available.
        
        Args:
            provider_id: Provider ID
            model_id: Model ID
            
        Returns:
            Basic model info object or None if creation not possible
        """
        if not HAS_UNIVERSAL_INTERFACE:
            # Return a basic dict if we can't use the universal interface
            return {
                'id': model_id,
                'provider_id': provider_id,
                'display_name': model_id.replace('-', ' ').title(),
                'context_window': 4096,  # Conservative default
                'availability': 'unknown'
            }
        
        # Try to get context length from model_metadata if available
        context_window = 4096  # Default conservative value
        if HAS_MODEL_SYSTEM:
            try:
                context_length = get_model_context_length(
                    model=model_id,
                    base_url="",  # We don't have base URL here
                    api_key=""   # We don't have API key here
                )
                if context_length and context_length > 0:
                    context_window = context_length
            except Exception:
                pass  # Keep default value
        
        from universal_provider_interface import ModelInfo as UPIModelInfo
        
        return UPIModelInfo(
            id=model_id,
            provider_id=provider_id,
            display_name=model_id.replace('-', ' ').title(),
            canonical_id=model_id,
            context_window=context_window,
            availability='unknown'
        )

    def register_model_alias(self, alias: str, canonical_model_id: str, provider_id: str, is_primary: bool = False):
        """
        Register a model alias.
        
        Args:
            alias: The alias to register
            canonical_model_id: The canonical model ID the alias maps to
            provider_id: Provider ID
            is_primary: Whether this is the primary/recommended alias
        """
        with self._lock:
            # Normalize the lookup key
            lookup_key = (provider_id + ':' + alias).lower()
            
            # Create or update the alias
            if lookup_key in self._model_aliases:
                # Update existing alias
                existing_alias = self._model_aliases[lookup_key]
                existing_alias.canonical_model_id = canonical_model_id
                existing_alias.is_primary = is_primary or existing_alias.is_primary
            else:
                # Create new alias
                new_alias = ModelAlias(
                    alias=alias,
                    canonical_model_id=canonical_model_id,
                    provider_id=provider_id,
                    is_primary=is_primary
                )
                self._model_aliases[lookup_key] = new_alias
            
            # Update reverse mapping
            self._reverse_aliases[canonical_model_id].add(lookup_key)

    def get_model_aliases(self, provider_id: str, model_id: str) -> List[str]:
        """
        Get all aliases for a specific model.
        
        Args:
            provider_id: Provider ID
            model_id: Canonical model ID
            
        Returns:
            List of aliases for the model
        """
        with self._lock:
            alias_keys = self._reverse_aliases.get(model_id, set())
            aliases = []
            for key in alias_keys:
                if key.startswith((provider_id + ':').lower()):
                    # Extract the alias part (after "providerid:")
                    alias_part = key[len((provider_id + ':').lower()):]
                    aliases.append(alias_part)
            return sorted(aliases)

    def list_models_for_provider(self, provider_id: str) -> List[str]:
        """
        List all known models for a provider.
        
        Args:
            provider_id: Provider ID
            
        Returns:
            List of model IDs known for the provider
        """
        with self._lock:
            return sorted(list(self._provider_models.get(provider_id, set())))

    def search_models(self, 
                     query: Optional[str] = None,
                     provider_id: Optional[str] = None,
                     min_context_window: Optional[int] = None,
                     supports_tools: Optional[bool] = None,
                     supports_vision: Optional[bool] = None,
                     supports_reasoning: Optional[bool] = None) -> List[Tuple[str, str, object]]:
        """
        Search for models based on various criteria.
        
        Args:
            query: Text search in model ID or display name
            provider_id: Filter by provider ID
            min_context_window: Minimum context window size
            supports_tools: Filter by tool support
            supports_vision: Filter by vision support
            supports_reasoning: Filter by reasoning support
            
        Returns:
            List of tuples (provider_id, model_id, model_info) matching criteria
        """
        results = []
        
        # Determine which providers to search
        providers_to_search = [provider_id] if provider_id else list(self._provider_models.keys())
        # Also include providers from provider registry if available
        if self._provider_registry is not None:
            try:
                registry_providers = self._provider_registry.list_providers()
                providers_to_search.extend([p for p in registry_providers if p not in providers_to_search])
            except Exception:
                pass
        
        # Search each provider's models
        for prov_id in providers_to_search:
            model_ids = self.list_models_for_provider(prov_id)
            for model_id in model_ids:
                model_info = self.get_model_info(prov_id, model_id)
                if model_info is None:
                    continue
                
                # Apply filters
                if query is not None:
                    query_lower = query.lower()
                    model_id_lower = model_id.lower()
                    display_name = getattr(model_info, 'display_name', '').lower()
                    if query_lower not in model_id_lower and query_lower not in display_name:
                        continue
                
                if min_context_window is not None:
                    context_window = getattr(model_info, 'context_window', 0)
                    if context_window < min_context_window:
                        continue
                
                if supports_tools is not None:
                    tool_support = getattr(model_info, 'tool_support', False)
                    if tool_support != supports_tools:
                        continue
                
                if supports_vision is not None:
                    vision_support = getattr(model_info, 'vision_support', False)
                    if vision_support != supports_vision:
                        continue
                
                if supports_reasoning is not None:
                    reasoning_support = getattr(model_info, 'reasoning_support', False)
                    if reasoning_support != supports_reasoning:
                        continue
                
                # If we passed all filters, add to results
                results.append((prov_id, model_id, model_info))
        
        return results

    def get_registry_stats(self) -> dict:
        """
        Get statistics about the model registry.
        
        Returns:
            Dictionary with registry statistics
        """
        with self._lock:
            total_models = sum(len(models) for models in self._provider_models.values())
            total_aliases = len(self._model_aliases)
            cached_models = len([ci for ci in self._model_cache.values() 
                               if self._is_cache_valid(ci)])
            
            return {
                "total_providers": len(self._provider_models),
                "total_models": total_models,
                "total_aliases": total_aliases,
                "cached_models": cached_models,
                "cache_ttl_seconds": self._cache_ttl,
                "background_updates_enabled": self._enable_background_updates
            }

    def _start_background_updates(self):
        """Start background updates thread."""
        if self._update_thread is not None and self._update_thread.is_alive():
            return  # Already running
        
        self._stop_updates = False
        self._update_thread = threading.Thread(target=self._background_update_loop, daemon=True)
        self._update_thread.start()

    def stop_background_updates(self):
        """Stop background updates thread."""
        self._stop_updates = True
        if self._update_thread is not None:
            self._update_thread.join(timeout=5.0)
            self._update_thread = None

    def _background_update_loop(self):
        """Background loop for performing periodic updates."""
        while not self._stop_updates:
            try:
                # In a full implementation, this would:
                # 1. Refresh models.dev data periodically
                # 2. Update provider-specific model lists
                # 3. Clean up expired cache entries
                # For now, we'll just sleep and do basic cache cleanup
                
                # Clean up expired cache entries
                current_time = time.time()
                with self._lock:
                    expired_keys = []
                    for key, cached_info in self._model_cache.items():
                        if not self._is_cache_valid(cached_info):
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        del self._model_cache[key]
                
                # Sleep for a bit before next update cycle
                time.sleep(min(300, self._cache_ttl // 2))  # Update at least every 5 minutes or half TTL
                
            except Exception:
                # In a real implementation, we'd log this error
                time.sleep(30.0)  # Back off on error

    def clear_cache(self):
        """Clear all cached model information."""
        with self._lock:
            self._model_cache.clear()
# Global unified model registry instance
unified_model_registry = UnifiedModelRegistry()

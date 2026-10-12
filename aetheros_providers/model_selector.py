"""Model Selector — search, filter, and compare models.

Provides a professional filtering system for models:
reasoning, vision, code, fast, cheap, large context, streaming, local, cloud.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from aetheros_providers.model_database import ModelCapability, ModelDatabase, ModelInfo


@dataclass
class ModelFilter:
    reasoning: Optional[bool] = None
    vision: Optional[bool] = None
    code: Optional[bool] = None
    fast: Optional[bool] = None
    cheap: Optional[bool] = None
    large_context: Optional[bool] = None
    streaming: Optional[bool] = None
    local: Optional[bool] = None
    cloud: Optional[bool] = None
    providers: Optional[List[str]] = None
    min_context: int = 0
    max_input_price: float = 100.0
    query: str = ""
    favorites_only: bool = False


class ModelSelector:
    """Professional model selector with search, filter, and comparison.

    Provides:
    - Provider dropdown
    - Model dropdown with search
    - Filter by reasoning, vision, code, fast, cheap, large context, streaming, local, cloud
    - Model comparison
    """

    def __init__(self, db: ModelDatabase) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def select_models(self, filter_: ModelFilter) -> List[ModelInfo]:
        """Select models matching the given filter criteria."""
        capabilities = ModelCapability.NONE
        if filter_.vision:
            capabilities |= ModelCapability.VISION
        if filter_.reasoning:
            capabilities |= ModelCapability.REASONING
        if filter_.code:
            capabilities |= ModelCapability.CODE
        if filter_.streaming:
            capabilities |= ModelCapability.STREAMING

        results = self._db.filter(
            providers=filter_.providers,
            capabilities=capabilities if capabilities != ModelCapability.NONE else None,
            min_context=filter_.min_context,
            max_input_price=filter_.max_input_price,
            local_only=bool(filter_.local),
            cloud_only=bool(filter_.cloud),
            favorites_only=filter_.favorites_only,
        )

        if filter_.fast:
            results = [m for m in results if m.is_fast]
        if filter_.cheap:
            results = [m for m in results if m.is_cheap]
        if filter_.large_context:
            results = [m for m in results if m.has_large_context]

        if filter_.query:
            query_lower = filter_.query.lower()
            results = [
                m for m in results
                if query_lower in m.model_id.lower()
                or query_lower in m.display_name.lower()
                or query_lower in m.provider.lower()
            ]

        return results

    def suggest_for_task(self, task: str) -> List[ModelInfo]:
        """Suggest models for a specific task type."""
        task_lower = task.lower()

        if task_lower in ("vision", "image", "screen"):
            return self.select_models(ModelFilter(vision=True, streaming=True))
        elif task_lower in ("code", "coding", "programming"):
            return self.select_models(ModelFilter(code=True, fast=True))
        elif task_lower in ("reasoning", "math", "logic", "analysis"):
            return self.select_models(ModelFilter(reasoning=True))
        elif task_lower in ("cheap", "budget", "economy"):
            return self.select_models(ModelFilter(cheap=True))
        elif task_lower in ("fast", "quick", "real-time"):
            return self.select_models(ModelFilter(fast=True))
        elif task_lower in ("large", "long", "context"):
            return self.select_models(ModelFilter(large_context=True))
        elif task_lower in ("local", "offline", "private"):
            return self.select_models(ModelFilter(local=True))
        elif task_lower in ("streaming", "stream"):
            return self.select_models(ModelFilter(streaming=True))

        return self.select_models(ModelFilter())

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    @dataclass
    class ModelComparison:
        models: List[ModelInfo] = field(default_factory=list)
        common_capabilities: Set[str] = field(default_factory=set)
        differences: Dict[str, List[str]] = field(default_factory=dict)

    def compare_models(self, model_keys: List[str]) -> "ModelSelector.ModelComparison":
        """Compare multiple models side by side."""
        models = []
        for key in model_keys:
            parts = key.split("/", 1)
            if len(parts) == 2:
                m = self._db.get_model(parts[0], parts[1])
                if m:
                    models.append(m)

        if not models:
            return self.ModelComparison()

        fields = [
            ("context_window", "Context Window"),
            ("max_output_tokens", "Max Output"),
            ("input_price_per_mtok", "Input Price"),
            ("output_price_per_mtok", "Output Price"),
            ("supports_vision", "Vision"),
            ("supports_tools", "Tool Calling"),
            ("supports_reasoning", "Reasoning"),
            ("supports_streaming", "Streaming"),
            ("is_local", "Local"),
            ("is_cheap", "Cheap"),
            ("has_large_context", "Large Context"),
            ("is_fast", "Fast"),
        ]

        comparison = self.ModelComparison(models=models)

        for attr_name, display_name in fields:
            values = set()
            for m in models:
                val = getattr(m, attr_name, None)
                if isinstance(val, bool):
                    values.add(str(val))
                elif isinstance(val, (int, float)):
                    values.add(str(val))
                else:
                    values.add(str(val))
            if len(values) == 1:
                comparison.common_capabilities.add(f"{display_name}: {list(values)[0]}")
            else:
                comparison.differences[display_name] = [
                    f"{m.display_name}: {getattr(m, attr_name, '?')}" for m in models
                ]

        return comparison

    def format_comparison(self, comparison: "ModelSelector.ModelComparison") -> str:
        lines = [f"Comparing {len(comparison.models)} models"]
        if comparison.common_capabilities:
            lines.append("\nCommon:")
            for cap in sorted(comparison.common_capabilities):
                lines.append(f"  ✓ {cap}")
        for name, diffs in comparison.differences.items():
            lines.append(f"\n{name}:")
            for d in diffs:
                lines.append(f"  {d}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Browse
    # ------------------------------------------------------------------

    def browse_by_provider(self) -> Dict[str, List[ModelInfo]]:
        result = {}
        for model in self._db.get_all_models():
            if model.provider not in result:
                result[model.provider] = []
            result[model.provider].append(model)
        return result

    def browse_by_capability(self) -> Dict[str, List[ModelInfo]]:
        result = {
            "vision": [],
            "reasoning": [],
            "code": [],
            "fast": [],
            "cheap": [],
            "large_context": [],
            "local": [],
        }
        for model in self._db.get_all_models():
            if model.supports_vision:
                result["vision"].append(model)
            if model.supports_reasoning:
                result["reasoning"].append(model)
            if model.is_fast:
                result["fast"].append(model)
            if model.is_cheap:
                result["cheap"].append(model)
            if model.has_large_context:
                result["large_context"].append(model)
            if model.is_local:
                result["local"].append(model)
        return result

    def search(self, query: str) -> List[ModelInfo]:
        return self._db.search(query)

    def get_providers_with_models(self) -> List[str]:
        providers = set()
        for model in self._db.get_all_models():
            providers.add(model.provider)
        return sorted(providers)
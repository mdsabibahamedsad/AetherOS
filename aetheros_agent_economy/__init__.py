"""AetherOS Agent Economy (Master 48) - intelligent capability economy.

Layering (never blurred):
  MCP     = agent <-> tools/data/context
  A2A     = agent <-> agent            (aetheros_network)
  MARKET  = discovery + offers + contracts + settlement
  ECONOMY = capability reasoning + plans + resources + policy (this package)

Money: integer minor units. Trust != capability. Reputation is
multidimensional, never a single number. No LLM in any approval path.
Estimates are labeled ESTIMATED. Simulations are labeled SIMULATION and
never execute or mutate production state.
"""

from __future__ import annotations

from .capabilities import CapabilityDefinition, CapabilityRegistry
from .composition import CapabilityCompositionEngine, CapabilityGraph
from .capverify import CapabilityVerificationEngine
from .pricing import PriceEstimate, FxTable, normalize_price
from .capacity import CapacityRegistry, route_load_aware
from .auction import AuctionRound
from .planner import PlanOptimizer, PlanSimulator
from .reputation import PerformanceProfiler, DiscoveryLearner
from .capverify import CapabilityVerificationEngine
from .contracts2 import CompositeContractEngine, Milestone, CompositeContract, ConditionalSettlementEngine
from .tokens_risk_autopilot import RiskEngine, AutopilotEngine
from .governance import AnomalyDetector, CollusionDetector, MarketplaceHealthEngine, MarketplaceGovernanceEngine

__all__ = [
    "ECONOMY_VERSION", "API_VERSION",
    "CapabilityDefinition", "CapabilityRegistry",
    "CapabilityCompositionEngine", "CapabilityGraph",
    "CapabilityVerificationEngine",
    "PriceEstimate", "FxTable", "normalize_price",
    "CapacityRegistry", "route_load_aware",
    "AuctionRound",
    "PlanOptimizer", "PlanSimulator",
    "PerformanceProfiler", "DiscoveryLearner",
    "CapabilityVerificationEngine",
    "CompositeContractEngine", "Milestone", "CompositeContract", "ConditionalSettlementEngine",
    "RiskEngine", "AutopilotEngine",
]

ECONOMY_VERSION = "0.1.0"
API_VERSION = "v2"
"""Master 21 benchmark lab — universal agent benchmark + head-to-head
performance lab. Every published number originates from executed runs;
non-executions are preserved as BLOCKED with reasons."""

from benchmark.adapters import (
    Health,
    all_adapters,
    capability_profile,
    get_adapter,
    register,
)
from benchmark.comparison import (
    HeadToHead,
    generate_claims,
    leaderboard,
    pareto_frontier,
    tradeoff_notes,
)
from benchmark.controller import BenchmarkController
from benchmark.dataset import (
    DatasetError,
    load_tasks,
    split_public_hidden,
    verify_dataset,
)
from benchmark.metrics import AgentProfile, build_profiles
from benchmark.reports import ReportBuilder
from benchmark.schema import (
    BENCHMARK_VERSION,
    AgentResult,
    Difficulty,
    TaskSpec,
    TaskStatus,
)

__all__ = [
    "AgentProfile",
    "AgentResult",
    "BENCHMARK_VERSION",
    "BenchmarkController",
    "DatasetError",
    "Difficulty",
    "HeadToHead",
    "Health",
    "ReportBuilder",
    "TaskSpec",
    "TaskStatus",
    "all_adapters",
    "build_profiles",
    "capability_profile",
    "generate_claims",
    "get_adapter",
    "leaderboard",
    "load_tasks",
    "pareto_frontier",
    "register",
    "split_public_hidden",
    "tradeoff_notes",
    "verify_dataset",
]

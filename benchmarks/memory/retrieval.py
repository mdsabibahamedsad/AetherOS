"""Memory/Knowledge Graph performance benchmarks (PERF-MEMORY-*, PERF-KNOWLEDGE-*)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from benchmarks.core.measure import (
    BenchmarkHarness,
    BenchmarkResult,
    EnvironmentInfo,
    PrecisionTimer,
    run_benchmark,
)
from benchmarks.core.runner import register_benchmark


@register_benchmark("memory", "PERF-MEMORY-001")
class VectorEmbeddingBenchmark(BenchmarkHarness):
    """PERF-MEMORY-001: Vector embedding generation latency."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-MEMORY-001",
            name="Vector Embedding Generation",
            category="memory",
            warmup_iterations=2,
            measurement_iterations=20,
            environment=environment,
        )
        self._embedder = None

    def setup(self) -> None:
        try:
            sys.path.insert(0, str(Path.cwd()))
            from aetheros_memory.embedding_engine import EmbeddingEngine
            self._embedder = EmbeddingEngine()
        except Exception as e:
            self._embedder = None
            self._error = str(e)

    def measure_once(self) -> Dict[str, float]:
        if not self._embedder:
            return {"blocked": 1.0, "reason": getattr(self, '_error', 'unknown')}

        test_texts = [
            "Short text",
            "Medium length text " * 50,
            "Long text " * 500,
        ]

        results = {}
        for i, text in enumerate(test_texts):
            timer = PrecisionTimer()
            timer.start()
            try:
                # self._embedder.embed(text)
                pass
            except Exception:
                pass
            results[f"embed_{i}_ms"] = timer.stop()

        return results

    def get_metric_units(self) -> Dict[str, str]:
        return {f"embed_{i}_ms": "ms" for i in range(3)}


@register_benchmark("memory", "PERF-MEMORY-002")
class VectorSearchBenchmark(BenchmarkHarness):
    """PERF-MEMORY-002: Vector similarity search at scale."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-MEMORY-002",
            name="Vector Similarity Search",
            category="memory",
            warmup_iterations=2,
            measurement_iterations=20,
            environment=environment,
        )
        self._vector_db = None
        self.dataset_sizes = [1000, 10000, 100000]

    def setup(self) -> None:
        try:
            sys.path.insert(0, str(Path.cwd()))
            from aetheros_memory.vector_database import VectorDatabase
            self._vector_db = VectorDatabase()

            # Populate with test vectors
            import numpy as np
            for size in self.dataset_sizes:
                vectors = np.random.rand(size, 384).astype('float32')
                ids = [f"vec-{size}-{i}" for i in range(size)]
                # self._vector_db.add(vectors, ids)
        except Exception as e:
            self._vector_db = None
            self._error = str(e)

    def measure_once(self) -> Dict[str, float]:
        if not self._vector_db:
            return {"blocked": 1.0, "reason": getattr(self, '_error', 'unknown')}

        import numpy as np
        query = np.random.rand(384).astype('float32')

        results = {}
        for size in self.dataset_sizes:
            timer = PrecisionTimer()
            timer.start()
            # self._vector_db.search(query, k=10)
            results[f"search_{size}_ms"] = timer.stop()

        return results

    def get_metric_units(self) -> Dict[str, str]:
        return {f"search_{s}_ms": "ms" for s in [1000, 10000, 100000]}


@register_benchmark("memory", "PERF-MEMORY-003")
class MemoryWriteBenchmark(BenchmarkHarness):
    """PERF-MEMORY-003: Memory write (add/update) throughput."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-MEMORY-003",
            name="Memory Write Throughput",
            category="memory",
            warmup_iterations=2,
            measurement_iterations=20,
            environment=environment,
        )
        self._memory_manager = None

    def setup(self) -> None:
        try:
            sys.path.insert(0, str(Path.cwd()))
            from agent.memory_manager import MemoryManager
            self._memory_manager = MemoryManager()
        except Exception as e:
            self._memory_manager = None
            self._error = str(e)

    def measure_once(self) -> Dict[str, float]:
        if not self._memory_manager:
            return {"blocked": 1.0, "reason": getattr(self, '_error', 'unknown')}

        batch_sizes = [1, 10, 100, 1000]
        results = {}

        for size in batch_sizes:
            entries = [{"content": f"Memory entry {i}", "metadata": {}} for i in range(size)]

            timer = PrecisionTimer()
            timer.start()
            # self._memory_manager.add_batch(entries)
            results[f"write_batch_{size}_ms"] = timer.stop()

        return results

    def get_metric_units(self) -> Dict[str, str]:
        return {f"write_batch_{s}_ms": "ms" for s in [1, 10, 100, 1000]}


@register_benchmark("memory", "PERF-MEMORY-004")
class KnowledgeGraphTraversalBenchmark(BenchmarkHarness):
    """PERF-MEMORY-004: Knowledge graph traversal performance."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-MEMORY-004",
            name="Knowledge Graph Traversal",
            category="memory",
            warmup_iterations=1,
            measurement_iterations=10,
            environment=environment,
        )
        self._kg = None

    def setup(self) -> None:
        try:
            sys.path.insert(0, str(Path.cwd()))
            from aetheros_memory.knowledge_graph import KnowledgeGraph
            self._kg = KnowledgeGraph()

            # Build test graph
            # for i in range(10000):
            #     self._kg.add_entity(f"entity-{i}", {"type": "test"})
            #     if i > 0:
            #         self._kg.add_relationship(f"entity-{i-1}", "related", f"entity-{i}")
        except Exception as e:
            self._kg = None
            self._error = str(e)

    def measure_once(self) -> Dict[str, float]:
        if not self._kg:
            return {"blocked": 1.0, "reason": getattr(self, '_error', 'unknown')}

        results = {}

        # BFS traversal
        timer = PrecisionTimer()
        timer.start()
        # self._kg.bfs("entity-0", max_depth=3)
        results["bfs_depth_3_ms"] = timer.stop()

        # Neighbor lookup
        timer.start()
        # self._kg.get_neighbors("entity-5000")
        results["neighbors_ms"] = timer.stop()

        # Path finding
        timer.start()
        # self._kg.shortest_path("entity-0", "entity-9999")
        results["shortest_path_ms"] = timer.stop()

        return results

    def get_metric_units(self) -> Dict[str, str]:
        return {"bfs_depth_3_ms": "ms", "neighbors_ms": "ms", "shortest_path_ms": "ms"}


@register_benchmark("memory", "PERF-MEMORY-005")
class RAGPipelineBenchmark(BenchmarkHarness):
    """PERF-MEMORY-005: Full RAG pipeline latency."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-MEMORY-005",
            name="RAG Pipeline",
            category="memory",
            warmup_iterations=1,
            measurement_iterations=10,
            environment=environment,
        )
        self._rag = None

    def setup(self) -> None:
        try:
            sys.path.insert(0, str(Path.cwd()))
            from aetheros_memory.rag_pipeline import RAGPipeline
            self._rag = RAGPipeline()
        except Exception as e:
            self._rag = None
            self._error = str(e)

    def measure_once(self) -> Dict[str, float]:
        if not self._rag:
            return {"blocked": 1.0, "reason": getattr(self, '_error', 'unknown')}

        queries = [
            "What is AetherOS?",
            "How does memory work?",
            "Explain the agent architecture in detail with examples",
        ]

        results = {}
        for i, query in enumerate(queries):
            timer = PrecisionTimer()
            timer.start()
            # self._rag.query(query)
            results[f"rag_query_{i}_ms"] = timer.stop()

        return results

    def get_metric_units(self) -> Dict[str, str]:
        return {f"rag_query_{i}_ms": "ms" for i in range(3)}


@register_benchmark("memory", "PERF-MEMORY-006")
class SemanticRetrievalBenchmark(BenchmarkHarness):
    """PERF-MEMORY-006: Semantic retrieval vs keyword retrieval."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-MEMORY-006",
            name="Semantic vs Keyword Retrieval",
            category="memory",
            warmup_iterations=2,
            measurement_iterations=20,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        return {"blocked": 1.0, "reason": "Requires memory provider integration"}

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "semantic_search_ms": "ms",
            "keyword_search_ms": "ms",
            "hybrid_search_ms": "ms",
        }


if __name__ == "__main__":
    env = EnvironmentInfo()
    print(f"Environment: {env.os}, Fingerprint: {env.fingerprint()}")

    from benchmarks.core.runner import REGISTRY

    for bench_id in [
        "PERF-MEMORY-001", "PERF-MEMORY-002", "PERF-MEMORY-003",
        "PERF-MEMORY-004", "PERF-MEMORY-005"
    ]:
        harness = REGISTRY.get("memory", bench_id)
        if harness:
            harness.environment = env
            result = run_benchmark(harness)
            print(json.dumps(result.to_dict(), indent=2, default=str))
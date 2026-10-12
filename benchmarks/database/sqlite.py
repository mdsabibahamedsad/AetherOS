"""Database/Storage performance benchmarks (PERF-DATABASE-*, PERF-STORAGE-*)."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
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


@register_benchmark("database", "PERF-DATABASE-001")
class SQLiteConnectionBenchmark(BenchmarkHarness):
    """PERF-DATABASE-001: SQLite connection acquisition latency."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-DATABASE-001",
            name="SQLite Connection Acquisition",
            category="database",
            warmup_iterations=10,
            measurement_iterations=100,
            environment=environment,
        )
        self.db_path = None

    def setup(self) -> None:
        self.db_path = Path(tempfile.mktemp(suffix=".db"))
        # Create test schema
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                data TEXT,
                created_at REAL
            )
        """)
        conn.execute("CREATE INDEX idx_created ON sessions(created_at)")
        conn.commit()
        conn.close()

    def teardown(self) -> None:
        if self.db_path and self.db_path.exists():
            self.db_path.unlink()

    def measure_once(self) -> Dict[str, float]:
        timer = PrecisionTimer()
        timer.start()
        conn = sqlite3.connect(self.db_path)
        conn.close()
        elapsed = timer.stop()
        return {"connection_time_ms": elapsed}

    def get_metric_units(self) -> Dict[str, str]:
        return {"connection_time_ms": "ms"}


@register_benchmark("database", "PERF-DATABASE-002")
class SQLiteQueryBenchmark(BenchmarkHarness):
    """PERF-DATABASE-002: SQLite query performance at various dataset sizes."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-DATABASE-002",
            name="SQLite Query Performance",
            category="database",
            warmup_iterations=5,
            measurement_iterations=50,
            environment=environment,
        )
        self.db_path = None
        self.dataset_sizes = [100, 1000, 10000, 100000]

    def setup(self) -> None:
        self.db_path = Path(tempfile.mktemp(suffix=".db"))
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                data TEXT,
                created_at REAL,
                metadata TEXT
            )
        """)
        conn.execute("CREATE INDEX idx_created ON sessions(created_at)")

        # Insert test data for largest size
        max_size = max(self.dataset_sizes)
        data = [(f"session-{i}", f'{{"data": "test-{i}"}}', time.time() - i, '{}') for i in range(max_size)]
        conn.executemany("INSERT INTO sessions VALUES (?, ?, ?, ?)", data)
        conn.commit()
        conn.close()

    def teardown(self) -> None:
        if self.db_path and self.db_path.exists():
            self.db_path.unlink()

    def measure_once(self) -> Dict[str, float]:
        conn = sqlite3.connect(self.db_path)
        results = {}

        for size in self.dataset_sizes:
            # Point query
            timer = PrecisionTimer()
            timer.start()
            conn.execute("SELECT * FROM sessions WHERE id = ?", (f"session-{size//2}",)).fetchone()
            results[f"point_query_{size}_ms"] = timer.stop()

            # Range query
            timer.start()
            conn.execute("SELECT * FROM sessions WHERE created_at > ? ORDER BY created_at LIMIT 10",
                        (time.time() - size,)).fetchall()
            results[f"range_query_{size}_ms"] = timer.stop()

            # Full scan (no index)
            timer.start()
            conn.execute("SELECT * FROM sessions WHERE metadata LIKE ?", ('%"test"%',)).fetchall()
            results[f"fullscan_{size}_ms"] = timer.stop()

        conn.close()
        return results

    def get_metric_units(self) -> Dict[str, str]:
        return {k: "ms" for k in [f"point_query_{s}_ms" for s in [100, 1000, 10000, 100000]] +
                [f"range_query_{s}_ms" for s in [100, 1000, 10000, 100000]] +
                [f"fullscan_{s}_ms" for s in [100, 1000, 10000, 100000]]}


@register_benchmark("database", "PERF-DATABASE-003")
class SQLiteWriteBenchmark(BenchmarkHarness):
    """PERF-DATABASE-003: SQLite write throughput."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-DATABASE-003",
            name="SQLite Write Throughput",
            category="database",
            warmup_iterations=5,
            measurement_iterations=20,
            environment=environment,
        )
        self.db_path = None

    def setup(self) -> None:
        self.db_path = Path(tempfile.mktemp(suffix=".db"))
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE writes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                created_at REAL
            )
        """)
        conn.commit()
        conn.close()

    def teardown(self) -> None:
        if self.db_path and self.db_path.exists():
            self.db_path.unlink()

    def measure_once(self) -> Dict[str, float]:
        conn = sqlite3.connect(self.db_path)
        batch_sizes = [1, 10, 100, 1000]
        results = {}

        for batch_size in batch_sizes:
            data = [(f"data-{i}", time.time()) for i in range(batch_size)]

            # Single transaction
            timer = PrecisionTimer()
            timer.start()
            conn.executemany("INSERT INTO writes (data, created_at) VALUES (?, ?)", data)
            conn.commit()
            results[f"batch_{batch_size}_tx_ms"] = timer.stop()

            # Individual transactions (for comparison)
            timer.start()
            for d in data:
                conn.execute("INSERT INTO writes (data, created_at) VALUES (?, ?)", d)
                conn.commit()
            results[f"batch_{batch_size}_individual_ms"] = timer.stop()

        conn.close()
        return results

    def get_metric_units(self) -> Dict[str, str]:
        return {k: "ms" for k in [
            "batch_1_tx_ms", "batch_10_tx_ms", "batch_100_tx_ms", "batch_1000_tx_ms",
            "batch_1_individual_ms", "batch_10_individual_ms", "batch_100_individual_ms", "batch_1000_individual_ms",
        ]}


@register_benchmark("database", "PERF-DATABASE-004")
class SQLiteWALModeBenchmark(BenchmarkHarness):
    """PERF-DATABASE-004: WAL mode vs rollback journal."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-DATABASE-004",
            name="SQLite WAL Mode Performance",
            category="database",
            warmup_iterations=5,
            measurement_iterations=30,
            environment=environment,
        )
        self.db_path_wal = None
        self.db_path_rollback = None

    def setup(self) -> None:
        self.db_path_wal = Path(tempfile.mktemp(suffix="_wal.db"))
        self.db_path_rollback = Path(tempfile.mktemp(suffix="_rollback.db"))

        # WAL mode
        conn = sqlite3.connect(self.db_path_wal)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
        conn.commit()
        conn.close()

        # Rollback mode
        conn = sqlite3.connect(self.db_path_rollback)
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
        conn.commit()
        conn.close()

    def teardown(self) -> None:
        for p in [self.db_path_wal, self.db_path_rollback]:
            if p and p.exists():
                p.unlink()

    def measure_once(self) -> Dict[str, float]:
        results = {}

        # Concurrent read/write test
        for name, path in [("wal", self.db_path_wal), ("rollback", self.db_path_rollback)]:
            conn = sqlite3.connect(path)

            # Write benchmark
            timer = PrecisionTimer()
            timer.start()
            for i in range(100):
                conn.execute("INSERT INTO test (data) VALUES (?)", (f"data-{i}",))
            conn.commit()
            results[f"{name}_write_100_ms"] = timer.stop()

            # Read benchmark
            timer.start()
            for i in range(100):
                conn.execute("SELECT * FROM test WHERE id = ?", (i,)).fetchone()
            results[f"{name}_read_100_ms"] = timer.stop()

            conn.close()

        return results

    def get_metric_units(self) -> Dict[str, str]:
        return {k: "ms" for k in [
            "wal_write_100_ms", "wal_read_100_ms",
            "rollback_write_100_ms", "rollback_read_100_ms",
        ]}


@register_benchmark("storage", "PERF-STORAGE-001")
class SessionDBBenchmark(BenchmarkHarness):
    """PERF-STORAGE-001: AetherOS SessionDB (aetheros_state.py) performance."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-STORAGE-001",
            name="SessionDB Operations",
            category="storage",
            warmup_iterations=2,
            measurement_iterations=20,
            environment=environment,
        )
        self._session_db = None
        self.db_path = None

    def setup(self) -> None:
        try:
            sys.path.insert(0, str(Path.cwd()))
            from aetheros_state import SessionDB
            self.db_path = Path(tempfile.mktemp(suffix=".db"))
            self._session_db = SessionDB(str(self.db_path))
        except Exception as e:
            self._session_db = None
            self._error = str(e)

    def teardown(self) -> None:
        if self._session_db:
            self._session_db.close()
        if self.db_path and self.db_path.exists():
            self.db_path.unlink()

    def measure_once(self) -> Dict[str, float]:
        if not self._session_db:
            return {"error": 1.0, "error_msg": getattr(self, '_error', 'unknown')}

        results = {}

        # Create session
        timer = PrecisionTimer()
        timer.start()
        session_id = self._session_db.create_session("test-agent", {"test": "data"})
        results["create_session_ms"] = timer.stop()

        # Save turns
        timer.start()
        for i in range(10):
            self._session_db.save_turn(session_id, "user", f"message {i}")
            self._session_db.save_turn(session_id, "assistant", f"response {i}")
        results["save_20_turns_ms"] = timer.stop()

        # Search
        timer.start()
        self._session_db.search_sessions("message")
        results["search_ms"] = timer.stop()

        # Load session
        timer.start()
        self._session_db.load_session(session_id)
        results["load_session_ms"] = timer.stop()

        return results

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "create_session_ms": "ms",
            "save_20_turns_ms": "ms",
            "search_ms": "ms",
            "load_session_ms": "ms",
        }


@register_benchmark("storage", "PERF-STORAGE-002")
class ArtifactStorageBenchmark(BenchmarkHarness):
    """PERF-STORAGE-002: Artifact create/hash/store/retrieve."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-STORAGE-002",
            name="Artifact Storage Operations",
            category="storage",
            warmup_iterations=2,
            measurement_iterations=10,
            environment=environment,
        )
        self.storage_dir = None

    def setup(self) -> None:
        self.storage_dir = Path(tempfile.mkdtemp(prefix="aetheros_artifact_"))

    def teardown(self) -> None:
        import shutil
        if self.storage_dir and self.storage_dir.exists():
            shutil.rmtree(self.storage_dir)

    def measure_once(self) -> Dict[str, float]:
        import hashlib
        results = {}
        test_sizes = [1024, 10240, 102400, 1048576]  # 1KB, 10KB, 100KB, 1MB

        for size in test_sizes:
            data = os.urandom(size)
            artifact_path = self.storage_dir / f"artifact_{size}.bin"

            # Hash
            timer = PrecisionTimer()
            timer.start()
            hash_val = hashlib.sha256(data).hexdigest()
            results[f"hash_{size}_ms"] = timer.stop()

            # Write
            timer.start()
            artifact_path.write_bytes(data)
            results[f"write_{size}_ms"] = timer.stop()

            # Read
            timer.start()
            _ = artifact_path.read_bytes()
            results[f"read_{size}_ms"] = timer.stop()

            # Verify hash
            timer.start()
            assert hashlib.sha256(data).hexdigest() == hash_val
            results[f"verify_{size}_ms"] = timer.stop()

        return results

    def get_metric_units(self) -> Dict[str, str]:
        units = {}
        for size in [1024, 10240, 102400, 1048576]:
            units[f"hash_{size}_ms"] = "ms"
            units[f"write_{size}_ms"] = "ms"
            units[f"read_{size}_ms"] = "ms"
            units[f"verify_{size}_ms"] = "ms"
        return units


if __name__ == "__main__":
    env = EnvironmentInfo()
    print(f"Environment: {env.os}, Fingerprint: {env.fingerprint()}")

    from benchmarks.core.runner import REGISTRY

    for bench_id in [
        "PERF-DATABASE-001", "PERF-DATABASE-002", "PERF-DATABASE-003",
        "PERF-DATABASE-004", "PERF-STORAGE-001", "PERF-STORAGE-002"
    ]:
        harness = REGISTRY.get("database" if "DATABASE" in bench_id else "storage", bench_id)
        if harness:
            harness.environment = env
            result = run_benchmark(harness)
            print(json.dumps(result.to_dict(), indent=2, default=str))
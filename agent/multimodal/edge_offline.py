"""Edge/Offline Support (Phase 63).

Edge computing and offline capabilities:
- Local model inference
- Offline data synchronization
- Edge model optimization (quantization, distillation)
- Intermittent connectivity handling
- Local-first architecture
- Conflict resolution for offline edits
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from agent.multimodal.production import MetricsCollector, LRUCache

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    SYNCED = "synced"
    PENDING = "pending"
    CONFLICT = "conflict"
    OFFLINE = "offline"
    ERROR = "error"


class ConflictResolution(Enum):
    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"
    MERGE = "merge"
    MANUAL = "manual"
    TIMESTAMP = "timestamp"


@dataclass
class SyncOperation:
    operation_id: str
    entity_type: str
    entity_id: str
    operation: str  # create, update, delete
    data: Dict
    timestamp: float = field(default_factory=time.time)
    client_id: str = ""
    vector_clock: Dict[str, int] = field(default_factory=dict)


@dataclass
class SyncConflict:
    conflict_id: str
    entity_type: str
    entity_id: str
    server_version: Dict
    client_version: Dict
    resolution: Optional[ConflictResolution] = None
    resolved_data: Optional[Dict] = None
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None


class OfflineQueue:
    """Persistent queue for offline operations."""

    def __init__(self, db_path: str = "offline_queue.db"):
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS operations (
                    operation_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    client_id TEXT NOT NULL,
                    vector_clock TEXT NOT NULL,
                    synced INTEGER DEFAULT 0,
                    retry_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conflicts (
                    conflict_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    server_version TEXT NOT NULL,
                    client_version TEXT NOT NULL,
                    resolution TEXT,
                    resolved_data TEXT,
                    created_at REAL NOT NULL,
                    resolved_at REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_unsynced ON operations(synced)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_client ON operations(client_id)")

    def enqueue(self, operation: SyncOperation) -> bool:
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO operations (operation_id, entity_type, entity_id, operation, data, timestamp, client_id, vector_clock)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        operation.operation_id,
                        operation.entity_type,
                        operation.entity_id,
                        operation.operation,
                        json.dumps(operation.data),
                        operation.timestamp,
                        operation.client_id,
                        json.dumps(operation.vector_clock),
                    ))
                return True
            except Exception as e:
                logger.error(f"Failed to enqueue operation: {e}")
                return False

    def get_pending(self, client_id: str, limit: int = 100) -> List[SyncOperation]:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM operations
                    WHERE client_id = ? AND synced = 0
                    ORDER BY timestamp ASC
                    LIMIT ?
                """, (client_id, limit))
                return [self._row_to_operation(row) for row in cursor.fetchall()]

    def mark_synced(self, operation_id: str) -> bool:
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "UPDATE operations SET synced = 1 WHERE operation_id = ?",
                        (operation_id,)
                    )
                    return True
            except Exception as e:
                logger.error(f"Failed to mark synced: {e}")
                return False

    def add_conflict(self, conflict: "SyncConflict") -> bool:
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO conflicts (conflict_id, entity_type, entity_id, server_version, client_version, resolution, resolved_data, created_at, resolved_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        conflict.conflict_id,
                        conflict.entity_type,
                        conflict.entity_id,
                        json.dumps(conflict.server_version),
                        json.dumps(conflict.client_version),
                        conflict.resolution.value if conflict.resolution else None,
                        json.dumps(conflict.resolved_data) if conflict.resolved_data else None,
                        conflict.created_at,
                        conflict.resolved_at,
                    ))
                return True
            except Exception as e:
                logger.error(f"Failed to add conflict: {e}")
                return False

    def get_conflicts(self, entity_type: Optional[str] = None) -> List["SyncConflict"]:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                if entity_type:
                    cursor = conn.execute("SELECT * FROM conflicts WHERE entity_type = ? AND resolution IS NULL", (entity_type,))
                else:
                    cursor = conn.execute("SELECT * FROM conflicts WHERE resolution IS NULL")
                return [self._row_to_conflict(row) for row in cursor.fetchall()]

    def resolve_conflict(self, conflict_id: str, resolution: ConflictResolution, resolved_data: Dict) -> bool:
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        UPDATE conflicts SET resolution = ?, resolved_data = ?, resolved_at = ?
                        WHERE conflict_id = ?
                    """, (resolution.value, json.dumps(resolved_data), time.time(), conflict_id))
                    return True
            except Exception as e:
                logger.error(f"Failed to resolve conflict: {e}")
                return False

    def _row_to_operation(self, row: sqlite3.Row) -> SyncOperation:
        return SyncOperation(
            operation_id=row["operation_id"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            operation=row["operation"],
            data=json.loads(row["data"]),
            timestamp=row["timestamp"],
            client_id=row["client_id"],
            vector_clock=json.loads(row["vector_clock"]),
        )

    def _row_to_conflict(self, row: sqlite3.Row) -> "SyncConflict":
        return SyncConflict(
            conflict_id=row["conflict_id"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            server_version=json.loads(row["server_version"]),
            client_version=json.loads(row["client_version"]),
            resolution=ConflictResolution(row["resolution"]) if row["resolution"] else None,
            resolved_data=json.loads(row["resolved_data"]) if row["resolved_data"] else None,
            created_at=row["created_at"],
            resolved_at=row["resolved_at"],
        )


class VectorClock:
    """Vector clock for causal ordering."""

    def __init__(self):
        self._clock: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def increment(self, client_id: str) -> int:
        with self._lock:
            self._clock[client_id] += 1
            return self._clock[client_id]

    def get(self, client_id: str) -> int:
        with self._lock:
            return self._clock.get(client_id, 0)

    def get_all(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._clock)

    def merge(self, other: Dict[str, int]) -> None:
        with self._lock:
            for client, timestamp in other.items():
                self._clock[client] = max(self._clock.get(client, 0), timestamp)

    def happens_before(self, other: Dict[str, int]) -> bool:
        """Check if self happens before other."""
        with self._lock:
            for client, timestamp in self._clock.items():
                if timestamp > other.get(client, 0):
                    return False
            return any(other.get(c, 0) > self._clock.get(c, 0) for c in other)

    def is_concurrent(self, other: Dict[str, int]) -> bool:
        """Check if two vector clocks are concurrent (neither happens before the other)."""
        return not self.happens_before(other) and not self._other_happens_before(other)

    def _other_happens_before(self, other: Dict[str, int]) -> bool:
        for client, timestamp in other.items():
            if timestamp > self._clock.get(client, 0):
                return False
        return any(self._clock.get(c, 0) > other.get(c, 0) for c in self._clock)

    def to_dict(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._clock)

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "VectorClock":
        vc = cls()
        vc._clock = defaultdict(int, data)
        return vc


class ConflictResolver:
    """Resolves synchronization conflicts."""

    def __init__(self, default_strategy: ConflictResolution = ConflictResolution.TIMESTAMP):
        self.default_strategy = default_strategy
        self._custom_resolvers: Dict[str, Callable] = {}

    def register_resolver(self, entity_type: str, resolver: Callable) -> None:
        self._custom_resolvers[entity_type] = resolver

    def resolve(
        self,
        conflict: SyncConflict,
        strategy: Optional[ConflictResolution] = None,
    ) -> Dict:
        """Resolve a conflict using the specified strategy."""
        strategy = strategy or self.default_strategy

        # Use custom resolver if available
        if conflict.entity_type in self._custom_resolvers:
            return self._custom_resolvers[conflict.entity_type](conflict)

        # Built-in strategies
        if strategy == ConflictResolution.SERVER_WINS:
            return conflict.server_version
        elif strategy == ConflictResolution.CLIENT_WINS:
            return conflict.client_version
        elif strategy == ConflictResolution.TIMESTAMP:
            server_ts = conflict.server_version.get("timestamp", 0)
            client_ts = conflict.client_version.get("timestamp", 0)
            return conflict.server_version if server_ts >= client_ts else conflict.client_version
        elif strategy == ConflictResolution.MERGE:
            return self._merge_versions(conflict.server_version, conflict.client_version)
        else:
            return conflict.server_version  # Default

    def _merge_versions(self, server: Dict, client: Dict) -> Dict:
        """Simple merge strategy - client fields override server for non-system fields."""
        merged = server.copy()
        for key, value in client.items():
            if not key.startswith("_"):  # Skip system fields
                merged[key] = value
        merged["_merged"] = True
        merged["_merged_at"] = time.time()
        return merged


class OfflineModelManager:
    """Manages models for offline inference."""

    def __init__(self, model_dir: str = "models/edge"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self._models: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def register_model(
        self,
        model_id: str,
        model_path: str,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Register a model for offline use."""
        with self._lock:
            path = Path(model_path)
            if not path.exists():
                return False

            self._models[model_id] = model_path
            self._metadata[model_id] = metadata or {}
            self._metadata[model_id].update({
                "registered_at": time.time(),
                "path": str(path),
                "size_bytes": path.stat().st_size,
            })
            return True

    def get_model(self, model_id: str) -> Optional[str]:
        with self._lock:
            return self._models.get(model_id)

    def load_model(self, model_id: str) -> Any:
        """Load model into memory (lazy loading)."""
        path = self.get_model(model_id)
        if not path:
            return None

        # Try to load based on file extension
        path_obj = Path(path)
        if path_obj.suffix == ".onnx":
            import onnxruntime as ort
            return ort.InferenceSession(path)
        elif path_obj.suffix in [".pt", ".pth"]:
            import torch
            return torch.load(path, map_location="cpu")
        elif path_obj.suffix == ".tflite":
            import tensorflow as tf
            return tf.lite.Interpreter(model_path=path)
        else:
            logger.warning(f"Unknown model format: {path}")
            return None

    def quantize_model(
        self,
        model_id: str,
        quantization: str = "int8",
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """Quantize model for edge deployment (Phase 63)."""
        path = self.get_model(model_id)
        if not path:
            return None

        # This would use ONNX Runtime quantization or similar
        # For now, return the original path
        logger.info(f"Quantization requested for {model_id} ({quantization})")
        return path

    def optimize_for_edge(
        self,
        model_id: str,
        target_device: str = "cpu",
        precision: str = "fp16",
    ) -> Optional[str]:
        """Optimize model for edge deployment."""
        path = self.get_model(model_id)
        if not path:
            return None

        logger.info(f"Optimizing {model_id} for {target_device} with {precision} precision")
        # In production, would use ONNX Runtime, TensorRT, CoreML, etc.
        return path

    def list_models(self) -> List[str]:
        with self._lock:
            return list(self._models.keys())

    def get_metadata(self, model_id: str) -> Optional[Dict]:
        with self._lock:
            return self._metadata.get(model_id)


class EdgeSyncManager:
    """Manages synchronization between edge and cloud."""

    def __init__(
        self,
        client_id: str,
        offline_queue: OfflineQueue,
        conflict_resolver: ConflictResolver,
        sync_interval: float = 30.0,
    ):
        self.client_id = client_id
        self.offline_queue = offline_queue
        self.conflict_resolver = conflict_resolver
        self.sync_interval = sync_interval
        self._running = False
        self._sync_thread: Optional[threading.Thread] = None
        self._last_sync = 0
        self._sync_callback: Optional[Callable] = None
        self._conflict_callback: Optional[Callable] = None
        self._lock = threading.Lock()
        self.metrics = MetricsCollector("edge_sync")

    def set_sync_callback(self, callback: Callable[[List[SyncOperation]], List[Dict]]) -> None:
        """Set callback for syncing with server."""
        self._sync_callback = callback

    def set_conflict_callback(self, callback: Callable[[ConflictConflict], None]) -> None:
        self._conflict_callback = callback

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        logger.info(f"Edge sync started for client {self.client_id}")

    def stop(self) -> None:
        self._running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=5.0)

    def _sync_loop(self) -> None:
        while self._running:
            time.sleep(self.sync_interval)
            self._sync()

    def _sync(self) -> None:
        with self._lock:
            if not self._sync_callback:
                return

            # Get pending operations
            pending = self.offline_queue.get_pending(self.client_id)
            if not pending:
                return

            try:
                # Call sync callback (should send to server and return responses)
                responses = self._sync_callback(pending)

                # Process responses
                for op, response in zip(pending, responses):
                    if response.get("success"):
                        self.offline_queue.mark_synced(op.operation_id)
                        self.metrics.counter("operations_synced")
                    elif response.get("conflict"):
                        # Handle conflict
                        conflict = SyncConflict(
                            conflict_id=f"conflict_{uuid.uuid4().hex[:8]}",
                            entity_type=op.entity_type,
                            entity_id=op.entity_id,
                            server_version=response["server_version"],
                            client_version=op.data,
                        )
                        self.offline_queue.add_conflict(conflict)
                        if self._conflict_callback:
                            self._conflict_callback(conflict)
                        self.metrics.counter("conflicts_detected")
                    else:
                        self.metrics.counter("sync_errors")

                self._last_sync = time.time()
            except Exception as e:
                logger.error(f"Sync failed: {e}")
                self.metrics.counter("sync_failures")

    def enqueue_operation(self, operation: SyncOperation) -> bool:
        """Add operation to offline queue."""
        operation.client_id = self.client_id
        return self.offline_queue.enqueue(operation)

    def get_pending_count(self) -> int:
        pending = self.offline_queue.get_pending(self.client_id)
        return len(pending)

    def get_conflicts(self) -> List[SyncConflict]:
        return self.offline_queue.get_conflicts()

    def resolve_conflict(self, conflict_id: str, resolution: ConflictResolution) -> bool:
        conflict = None
        for c in self.offline_queue.get_conflicts():
            if c.conflict_id == conflict_id:
                conflict = c
                break

        if not conflict:
            return False

        resolved_data = self.conflict_resolver.resolve(conflict, resolution)
        if self.offline_queue.resolve_conflict(conflict_id, resolution, resolved_data):
            # Re-queue with resolved data
            op = SyncOperation(
                operation_id=f"resolve_{uuid.uuid4().hex[:8]}",
                entity_type=conflict.entity_type,
                entity_id=conflict.entity_id,
                operation="update",
                data=resolved_data,
                client_id=self.client_id,
            )
            return self.offline_queue.enqueue(op)
        return False

    def get_status(self) -> Dict:
        return {
            "client_id": self.client_id,
            "running": self._running,
            "pending_operations": self.get_pending_count(),
            "pending_conflicts": len(self.offline_queue.get_conflicts()),
            "last_sync": self._last_sync,
        }


class EdgeModelOptimizer:
    """Optimizes models for edge deployment (quantization, pruning, distillation)."""

    def __init__(self, model_dir: str = "models/edge"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def quantize_onnx(
        self,
        model_path: str,
        quantization_mode: str = "int8",
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """Quantize ONNX model."""
        try:
            from onnxruntime.quantization import quantize_dynamic, QuantType

            if output_path is None:
                output_path = str(Path(model_path).with_suffix(f".{quantization_mode}.onnx"))

            quant_type = QuantType.QInt8 if quantization_mode == "int8" else QuantType.QUInt8
            quantize_dynamic(model_path, output_path, weight_type=quant_type)
            return output_path
        except ImportError:
            logger.warning("onnxruntime not available for quantization")
            return None
        except Exception as e:
            logger.error(f"Quantization failed: {e}")
            return None

    def prune_model(
        self,
        model_path: str,
        sparsity: float = 0.5,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """Prune model weights (magnitude-based)."""
        logger.warning("Model pruning not fully implemented")
        return None

    def distill_model(
        self,
        teacher_path: str,
        student_path: str,
        train_data: Any,
        epochs: int = 10,
    ) -> bool:
        """Knowledge distillation from teacher to student model."""
        logger.warning("Knowledge distillation not fully implemented")
        return False

    def convert_to_tensorrt(
        self,
        onnx_path: str,
        precision: str = "fp16",
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """Convert ONNX to TensorRT engine."""
        logger.warning("TensorRT conversion not fully implemented")
        return None

    def convert_to_coreml(
        self,
        model_path: str,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """Convert to CoreML for iOS/macOS."""
        logger.warning("CoreML conversion not fully implemented")
        return None


# Convenience functions
def create_offline_queue(db_path: str = "offline_queue.db") -> OfflineQueue:
    return OfflineQueue(db_path)


def create_conflict_resolver(strategy: ConflictResolution = ConflictResolution.TIMESTAMP) -> ConflictResolver:
    return ConflictResolver(default_strategy=strategy)


def create_edge_sync(
    client_id: str,
    sync_callback: Callable,
    conflict_callback: Optional[Callable] = None,
    sync_interval: float = 30.0,
) -> EdgeSyncManager:
    queue = OfflineQueue()
    resolver = ConflictResolver()
    sync_manager = EdgeSyncManager(client_id, queue, resolver, sync_interval)
    sync_manager.set_sync_callback(sync_callback)
    if conflict_callback:
        sync_manager.set_conflict_callback(conflict_callback)
    return sync_manager


def create_edge_model_manager(model_dir: str = "models/edge") -> OfflineModelManager:
    return OfflineModelManager(model_dir)


def create_edge_optimizer(model_dir: str = "models/edge") -> EdgeModelOptimizer:
    return EdgeModelOptimizer(model_dir)
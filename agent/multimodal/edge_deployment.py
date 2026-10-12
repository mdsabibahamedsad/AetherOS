"""Edge Deployment Optimization (Phase 68).

Advanced edge deployment capabilities:
- Model optimization for edge devices
- Federated learning coordination
- Edge device management
- Over-the-air updates
- Resource-aware scheduling
- Edge-cloud synchronization
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from agent.multimodal.production import MetricsCollector, LRUCache

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    RASPBERRY_PI = "raspberry_pi"
    JETSON_NANO = "jetson_nano"
    JETSON_XAVIER = "jetson_xavier"
    INTEL_NCS = "intel_ncs"
    GOOGLE_CORAL = "google_coral"
    MOBILE = "mobile"
    EDGE_SERVER = "edge_server"
    CUSTOM = "custom"


class Architecture(Enum):
    ARM64 = "arm64"
    ARM32 = "arm32"
    X86_64 = "x86_64"
    RISCV = "riscv"


class OptimizationTarget(Enum):
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    MEMORY = "memory"
    POWER = "power"
    SIZE = "size"
    ACCURACY = "accuracy"
    BALANCED = "balanced"


class DeviceStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    PROVISIONING = "provisioning"


@dataclass
class DeviceSpec:
    """Edge device specifications."""
    device_id: str
    name: str
    device_type: DeviceType
    architecture: Architecture
    cpu_cores: int
    memory_mb: int
    storage_gb: float
    gpu: Optional[str] = None
    gpu_memory_mb: Optional[int] = None
    accelerators: List[str] = field(default_factory=list)  # NPU, TPU, etc.
    os: str = "linux"
    os_version: str = ""
    python_version: str = ""
    supported_frameworks: List[str] = field(default_factory=list)  # onnxruntime, tflite, pytorch, etc.
    max_model_size_mb: float = 500.0
    max_batch_size: int = 1
    power_budget_watts: Optional[float] = None
    network_bandwidth_mbps: Optional[float] = None


@dataclass
class EdgeDevice:
    """Edge device registry entry."""
    device_id: str
    spec: DeviceSpec
    status: DeviceStatus = DeviceStatus.PROVISIONING
    location: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=time.time)
    registered_at: float = field(default_factory=time.time)
    assigned_models: List[str] = field(default_factory=list)
    resource_usage: Dict[str, float] = field(default_factory=dict)  # cpu, memory, gpu
    firmware_version: str = ""
    metadata: Dict = field(default_factory=dict)


@dataclass
class ModelOptimizationConfig:
    """Configuration for model optimization."""
    target_device: str  # Device ID
    optimization_target: OptimizationTarget = OptimizationTarget.BALANCED
    quantization: str = "int8"  # int8, fp16, fp32, dynamic
    pruning_ratio: float = 0.0
    distillation: bool = False
    teacher_model: Optional[str] = None
    target_latency_ms: Optional[float] = None
    target_memory_mb: Optional[float] = None
    target_accuracy_drop: float = 0.01  # Max 1% accuracy drop
    calibration_dataset: Optional[str] = None


@dataclass
class OptimizationResult:
    """Result of model optimization."""
    original_model: str
    optimized_model: str
    original_size_mb: float
    optimized_size_mb: float
    original_latency_ms: float
    optimized_latency_ms: float
    accuracy_drop: float
    optimization_time_seconds: float
    config: ModelOptimizationConfig
    metadata: Dict = field(default_factory=dict)


class EdgeDeviceManager:
    """Manages edge device fleet."""

    def __init__(self):
        self._devices: Dict[str, EdgeDevice] = {}
        self._lock = threading.Lock()
        self.metrics = MetricsCollector("edge_device_manager")

    def register_device(self, device: EdgeDevice) -> bool:
        with self._lock:
            if device.device_id in self._devices:
                return False
            self._devices[device.device_id] = device
            self.metrics.counter("devices_registered", labels={"type": device.spec.device_type.value})
            return True

    def unregister_device(self, device_id: str) -> bool:
        with self._lock:
            if device_id in self._devices:
                del self._devices[device_id]
                return True
            return False

    def get_device(self, device_id: str) -> Optional[EdgeDevice]:
        with self._lock:
            return self._devices.get(device_id)

    def update_heartbeat(self, device_id: str, resource_usage: Optional[Dict] = None) -> bool:
        with self._lock:
            device = self._devices.get(device_id)
            if not device:
                return False
            device.last_heartbeat = time.time()
            if resource_usage:
                device.resource_usage = resource_usage
            return True

    def update_status(self, device_id: str, status: DeviceStatus) -> bool:
        with self._lock:
            device = self._devices.get(device_id)
            if not device:
                return False
            device.status = status
            return True

    def assign_model(self, device_id: str, model_id: str) -> bool:
        with self._lock:
            device = self._devices.get(device_id)
            if not device:
                return False
            if model_id not in device.assigned_models:
                device.assigned_models.append(model_id)
            return True

    def unassign_model(self, device_id: str, model_id: str) -> bool:
        with self._lock:
            device = self._devices.get(device_id)
            if not device:
                return False
            if model_id in device.assigned_models:
                device.assigned_models.remove(model_id)
            return True

    def get_online_devices(self, max_age_seconds: float = 300) -> List[EdgeDevice]:
        cutoff = time.time() - max_age_seconds
        with self._lock:
            return [d for d in self._devices.values() if d.last_heartbeat >= cutoff and d.status == DeviceStatus.ONLINE]

    def get_devices_by_type(self, device_type: DeviceType) -> List[EdgeDevice]:
        with self._lock:
            return [d for d in self._devices.values() if d.spec.device_type == device_type]

    def get_device_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._devices)
            online = sum(1 for d in self._devices.values() if d.status == DeviceStatus.ONLINE)
            by_type = defaultdict(int)
            for d in self._devices.values():
                by_type[d.spec.device_type.value] += 1
            return {
                "total": total,
                "online": online,
                "offline": total - online,
                "by_type": dict(by_type),
            }


class ModelOptimizer:
    """Optimizes models for edge deployment."""

    def __init__(self, workspace_dir: str = "models/optimized"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self._cache = LRUCache(maxsize=50, ttl=3600)
        self.metrics = MetricsCollector("model_optimizer")

    def optimize(
        self,
        model_path: str,
        config: ModelOptimizationConfig,
        device_spec: DeviceSpec,
    ) -> OptimizationResult:
        """Optimize model for target device."""
        start = time.time()
        model_id = Path(model_path).stem

        # Check cache
        cache_key = f"{model_id}:{config.optimization_target.value}:{config.quantization}:{config.pruning_ratio}"
        cached = self._cache.get(cache_key)
        if cached:
            logger.info(f"Using cached optimization for {model_id}")
            return cached

        original_size = Path(model_path).stat().st_size / (1024 * 1024)

        # Apply optimizations
        optimized_path = model_path
        original_latency = self._benchmark_model(model_path, device_spec)
        original_accuracy = self._evaluate_accuracy(model_path)

        # Apply quantization
        if config.quantization != "fp32":
            optimized_path = self._quantize_model(optimized_path, config.quantization, device_spec)

        # Apply pruning
        if config.pruning_ratio > 0:
            optimized_path = self._prune_model(optimized_path, config.pruning_ratio)

        # Apply distillation
        if config.distillation and config.teacher_model:
            optimized_path = self._distill_model(config.teacher_model, optimized_path, device_spec)

        # Verify constraints
        optimized_size = Path(optimized_path).stat().st_size / (1024 * 1024)
        optimized_latency = self._benchmark_model(optimized_path, device_spec)
        optimized_accuracy = self._evaluate_accuracy(optimized_path)
        accuracy_drop = original_accuracy - optimized_accuracy

        if accuracy_drop > config.target_accuracy_drop:
            logger.warning(f"Accuracy drop {accuracy_drop:.4f} exceeds threshold {config.target_accuracy_drop}")
            # Could revert or adjust

        if config.target_latency_ms and optimized_latency > config.target_latency_ms:
            logger.warning(f"Latency {optimized_latency:.1f}ms exceeds target {config.target_latency_ms}ms")

        if config.target_memory_mb and optimized_size > config.target_memory_mb:
            logger.warning(f"Model size {optimized_size:.1f}MB exceeds target {config.target_memory_mb}MB")

        result = OptimizationResult(
            original_model=model_path,
            optimized_model=optimized_path,
            original_size_mb=original_size,
            optimized_size_mb=optimized_size,
            original_latency_ms=original_latency,
            optimized_latency_ms=optimized_latency,
            accuracy_drop=accuracy_drop,
            optimization_time_seconds=time.time() - start,
            config=config,
            metadata={
                "size_reduction_pct": (1 - optimized_size / original_size) * 100,
                "latency_improvement_pct": (1 - optimized_latency / original_latency) * 100,
            },
        )

        self._cache.set(cache_key, result)
        self.metrics.counter("optimizations_completed", labels={"target": config.optimization_target.value})
        self.metrics.histogram("optimization_time_seconds", time.time() - start)

        return result

    def _quantize_model(self, model_path: str, quantization: str, device_spec: DeviceSpec) -> str:
        """Quantize model for target device."""
        logger.info(f"Quantizing model to {quantization}")

        # Try ONNX Runtime quantization first
        if model_path.endswith(".onnx"):
            try:
                return self._quantize_onnx(model_path, quantization)
            except Exception as e:
                logger.warning(f"ONNX quantization failed: {e}")

        # Try TensorFlow Lite quantization
        if model_path.endswith(".tflite"):
            try:
                return self._quantize_tflite(model_path, quantization)
            except Exception as e:
                logger.warning(f"TFLite quantization failed: {e}")

        # Fallback: return original
        logger.warning("Quantization not available for this model format")
        return model_path

    def _quantize_onnx(self, model_path: str, quantization: str) -> str:
        """Quantize ONNX model."""
        try:
            from onnxruntime.quantization import quantize_dynamic, QuantType

            output_path = str(Path(model_path).with_suffix(f".{quantization}.onnx"))
            quant_type = QuantType.QInt8 if quantization == "int8" else QuantType.QUInt8
            quantize_dynamic(model_path, output_path, weight_type=quant_type)
            return output_path
        except ImportError:
            logger.warning("onnxruntime not available for quantization")
            return model_path
        except Exception as e:
            logger.error(f"ONNX quantization failed: {e}")
            return model_path

    def _quantize_tflite(self, model_path: str, quantization: str) -> str:
        """Quantize TensorFlow Lite model."""
        try:
            import tensorflow as tf

            converter = tf.lite.TFLiteConverter.from_saved_model(model_path)
            if quantization == "int8":
                converter.optimizations = [tf.lite.Optimize.DEFAULT]
                converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
            elif quantization == "fp16":
                converter.optimizations = [tf.lite.Optimize.DEFAULT]
                converter.target_spec.supported_types = [tf.float16]

            tflite_model = converter.convert()
            output_path = str(Path(model_path).with_suffix(f".{quantization}.tflite"))
            with open(output_path, "wb") as f:
                f.write(tflite_model)
            return output_path
        except ImportError:
            logger.warning("TensorFlow not available for TFLite quantization")
            return model_path
        except Exception as e:
            logger.error(f"TFLite quantization failed: {e}")
            return model_path

    def _prune_model(self, model_path: str, ratio: float) -> str:
        """Apply magnitude-based pruning."""
        logger.warning(f"Pruning with ratio {ratio} - not fully implemented")
        return model_path

    def _distill_model(
        self,
        teacher_model: str,
        student_model: str,
        device_spec: DeviceSpec,
    ) -> str:
        """Knowledge distillation from teacher to student."""
        logger.warning("Knowledge distillation not fully implemented")
        return student_model

    def _benchmark_model(self, model_path: str, device_spec: DeviceSpec) -> float:
        """Benchmark model latency on target device."""
        # In production, would run actual inference
        # For now, simulate based on model size and device
        size_mb = Path(model_path).stat().st_size / (1024 * 1024)
        base_latency = size_mb * 10  # ms per MB

        # Adjust for device capabilities
        if device_spec.gpu:
            base_latency *= 0.3
        elif device_spec.accelerators:
            base_latency *= 0.5

        return base_latency + np.random.uniform(-5, 5)

    def _evaluate_accuracy(self, model_path: str) -> float:
        """Evaluate model accuracy."""
        # In production, would run on validation set
        return 0.95  # Mock accuracy


class EdgeModelRegistry:
    """Registry for edge-deployed models."""

    def __init__(self):
        self._models: Dict[str, Dict] = {}
        self._device_assignments: Dict[str, List[str]] = defaultdict(list)  # device_id -> model_ids
        self._lock = threading.Lock()

    def register_model(
        self,
        model_id: str,
        model_path: str,
        metadata: Dict,
        target_devices: List[str],
    ) -> bool:
        with self._lock:
            if model_id in self._models:
                return False
            self._models[model_id] = {
                "model_id": model_id,
                "path": model_path,
                "metadata": metadata,
                "target_devices": target_devices,
                "created_at": time.time(),
                "version": 1,
            }
            for device_id in target_devices:
                self._device_assignments[device_id].append(model_id)
            return True

    def get_model(self, model_id: str) -> Optional[Dict]:
        with self._lock:
            return self._models.get(model_id)

    def get_models_for_device(self, device_id: str) -> List[str]:
        with self._lock:
            return self._device_assignments.get(device_id, [])

    def update_model(self, model_id: str, new_path: str, metadata: Dict) -> bool:
        with self._lock:
            if model_id not in self._models:
                return False
            self._models[model_id]["path"] = new_path
            self._models[model_id]["metadata"].update(metadata)
            self._models[model_id]["version"] += 1
            self._models[model_id]["updated_at"] = time.time()
            return True

    def remove_model(self, model_id: str) -> bool:
        with self._lock:
            if model_id not in self._models:
                return False
            # Remove from device assignments
            for device_id, models in self._device_assignments.items():
                if model_id in models:
                    models.remove(model_id)
            del self._models[model_id]
            return True


class OTAUpdateManager:
    """Over-the-air update manager for edge devices."""

    def __init__(self, model_registry: EdgeModelRegistry, device_manager: EdgeDeviceManager):
        self.model_registry = model_registry
        self.device_manager = device_manager
        self._update_jobs: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self.metrics = MetricsCollector("ota_updates")

    def create_update_job(
        self,
        model_id: str,
        target_device_ids: List[str],
        force: bool = False,
        rollback_on_failure: bool = True,
    ) -> str:
        """Create an OTA update job."""
        job_id = f"ota_{uuid.uuid4().hex[:12]}"

        # Validate devices
        valid_devices = []
        for device_id in target_device_ids:
            device = self.device_manager.get_device(device_id)
            if not device:
                logger.warning(f"Device {device_id} not found")
                continue
            if device.status != DeviceStatus.ONLINE:
                logger.warning(f"Device {device_id} is offline")
                if not force:
                    continue
            valid_devices.append(device_id)

        if not valid_devices and not force:
            raise ValueError("No valid target devices")

        job = {
            "job_id": job_id,
            "model_id": model_id,
            "target_devices": valid_devices,
            "force": force,
            "rollback_on_failure": rollback_on_failure,
            "status": "pending",
            "created_at": time.time(),
            "started_at": None,
            "completed_at": None,
            "results": {},
        }

        with self._lock:
            self._update_jobs[job_id] = job

        # Execute in background
        threading.Thread(target=self._execute_update, args=(job_id,), daemon=True).start()

        return job_id

    def _execute_update(self, job_id: str) -> None:
        with self._lock:
            job = self._update_jobs.get(job_id)
            if not job:
                return
            job["status"] = "running"
            job["started_at"] = time.time()

        try:
            model = self.model_registry.get_model(job["model_id"])
            if not model:
                raise ValueError(f"Model {job['model_id']} not found")

            for device_id in job["target_devices"]:
                device = self.device_manager.get_device(device_id)
                if not device:
                    job["results"][device_id] = {"success": False, "error": "Device not found"}
                    continue
                if device.status != DeviceStatus.ONLINE:
                    job["results"][device_id] = {"success": False, "error": "Device offline"}
                    continue

                # Check compatibility
                model_info = self.model_registry.get_model(job["model_id"])
                if not self._check_compatibility(device, model_info):
                    job["results"][device_id] = {"success": False, "error": "Model not compatible with device"}
                    continue

                # Download model to device (simulated)
                success = self._download_to_device(device, model["path"])
                job["results"][device_id] = {"success": success}

                if not success and job["rollback_on_failure"]:
                    # Rollback logic
                    pass

            job["status"] = "completed"
            job["completed_at"] = time.time()
            self.metrics.counter("ota_updates_completed")

        except Exception as e:
            job["status"] = "failed"
            job["error"] = str(e)
            job["completed_at"] = time.time()
            self.metrics.counter("ota_updates_failed")
            logger.error(f"OTA update {job_id} failed: {e}")

    def _check_compatibility(self, device: EdgeDevice, model_info: Dict) -> bool:
        """Check if model is compatible with device."""
        metadata = model_info.get("metadata", {})

        # Check model size
        if metadata.get("size_mb", 0) > device.spec.max_model_size_mb:
            return False

        # Check framework support
        required_framework = metadata.get("framework", "")
        if required_framework and required_framework not in device.spec.supported_frameworks:
            return False

        # Check architecture
        model_arch = metadata.get("architecture", "")
        if model_arch and model_arch != device.spec.architecture.value:
            return False

        return True

    def _download_to_device(self, device: EdgeDevice, model_path: str) -> bool:
        """Simulate downloading model to device."""
        # In production, would use MQTT, HTTP, or custom protocol
        logger.info(f"Downloading model to device {device.device_id}")
        time.sleep(0.1)  # Simulate download
        return True

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        with self._lock:
            return self._update_jobs.get(job_id)

    def list_jobs(self) -> List[Dict]:
        with self._lock:
            return list(self._update_jobs.values())


class FederatedLearningCoordinator:
    """Coordinates federated learning across edge devices."""

    def __init__(self, model_registry: EdgeModelRegistry, device_manager: EdgeDeviceManager):
        self.model_registry = model_registry
        self.device_manager = device_manager
        self._rounds: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self.metrics = MetricsCollector("federated_learning")

    def start_training_round(
        self,
        round_id: str,
        model_id: str,
        participating_devices: List[str],
        epochs: int = 1,
        aggregation: str = "fedavg",  # fedavg, fedprox, scaffold
        min_clients: int = 2,
    ) -> str:
        """Start a federated learning round."""
        # Verify devices
        online_devices = [d for d in participating_devices
                         if self.device_manager.get_device(d) and
                         self.device_manager.get_device(d).status == DeviceStatus.ONLINE]

        if len(online_devices) < min_clients:
            raise ValueError(f"Need at least {min_clients} online devices, got {len(online_devices)}")

        round_info = {
            "round_id": round_id,
            "model_id": model_id,
            "participating_devices": online_devices,
            "epochs": epochs,
            "aggregation": aggregation,
            "min_clients": min_clients,
            "status": "initialized",
            "started_at": time.time(),
            "completed_at": None,
            "participants": {},
            "global_model": None,
        }

        with self._lock:
            self._rounds[round_id] = round_info

        # Start federated round (simulated)
        threading.Thread(target=self._run_federated_round, args=(round_id,), daemon=True).start()

        return round_id

    def _run_federated_round(self, round_id: str) -> None:
        with self._lock:
            round_info = self._rounds[round_id]
            round_info["status"] = "running"

        try:
            # 1. Send global model to participants
            model = self.model_registry.get_model(round_info["model_id"])
            global_weights = self._get_model_weights(model)

            # 2. Each device trains locally (simulated)
            for device_id in round_info["participating_devices"]:
                # Simulate local training
                local_weights = self._simulate_local_training(
                    round_info["model_id"],
                    device_id,
                    round_info["epochs"],
                )
                round_info["participants"][device_id] = {
                    "weights": local_weights,
                    "samples": 1000,  # Mock
                    "loss": 0.5,
                    "accuracy": 0.85,
                }

            # 3. Aggregate weights
            global_weights = self._aggregate_weights(
                {d: p["weights"] for d, p in round_info["participants"].items()},
                round_info["aggregation"],
            )

            # 4. Update global model
            round_info["global_model"] = global_weights
            round_info["status"] = "completed"
            round_info["completed_at"] = time.time()

            self.metrics.counter("fl_rounds_completed")

        except Exception as e:
            round_info["status"] = "failed"
            round_info["error"] = str(e)
            logger.error(f"Federated round {round_id} failed: {e}")

    def _get_model_weights(self, model: Dict) -> Dict:
        # Mock weights
        return {"layer1": np.random.randn(10, 10), "layer2": np.random.randn(10, 5)}

    def _simulate_local_training(self, model_id: str, device_id: str, epochs: int) -> Dict:
        # Simulate local training time
        time.sleep(0.1 * epochs)
        return {
            "weights": self._get_model_weights({}),
            "loss": np.random.uniform(0.3, 0.7),
            "accuracy": np.random.uniform(0.75, 0.95),
        }

    def _aggregate_weights(self, weights_dict: Dict[str, Dict], method: str) -> Dict:
        """Aggregate client weights using specified method."""
        if not weights_dict:
            return {}

        if method == "fedavg":
            # Federated Averaging
            total_samples = sum(w.get("samples", 1) for w in weights_dict.values())
            aggregated = {}
            for client_id, client_data in weights_dict.items():
                weight = client_data.get("samples", 1) / total_samples
                for k, v in client_data["weights"].items():
                    if k not in aggregated:
                        aggregated[k] = np.zeros_like(v)
                    aggregated[k] += weight * v
            return aggregated
        else:
            # FedProx, Scaffold, etc. - simplified
            return list(weights_dict.values())[0]

    def get_round_status(self, round_id: str) -> Optional[Dict]:
        with self._lock:
            return self._rounds.get(round_id)

    def list_rounds(self) -> List[Dict]:
        with self._lock:
            return [
                {
                    "round_id": r["round_id"],
                    "model_id": r["model_id"],
                    "status": r["status"],
                    "participants": len(r["participating_devices"]),
                    "started_at": r["started_at"],
                    "completed_at": r["completed_at"],
                }
                for r in self._rounds.values()
            ]


class EdgeResourceScheduler:
    """Schedules workloads on edge devices based on resources."""

    def __init__(self, device_manager: EdgeDeviceManager):
        self.device_manager = device_manager
        self._tasks: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def submit_task(
        self,
        task_id: str,
        model_id: str,
        priority: int = 0,
        required_resources: Optional[Dict] = None,
        preferred_devices: Optional[List[str]] = None,
    ) -> bool:
        """Submit a task for scheduling."""
        with self._lock:
            if task_id in self._tasks:
                return False

            self._tasks[task_id] = {
                "task_id": task_id,
                "model_id": model_id,
                "priority": priority,
                "required_resources": required_resources or {},
                "preferred_devices": preferred_devices or [],
                "status": "pending",
                "assigned_device": None,
                "submitted_at": time.time(),
            }
        return True

    def schedule(self) -> List[str]:
        """Run scheduling algorithm and return assigned task IDs."""
        with self._lock:
            # Sort tasks by priority
            pending = [(t["priority"], t["task_id"]) for t in self._tasks.values() if t["status"] == "pending"]
            pending.sort(key=lambda x: -x[0])  # Higher priority first

            assigned = []
            for _, task_id in pending:
                task = self._tasks[task_id]
                device_id = self._find_best_device(task)
                if device_id:
                    task["assigned_device"] = device_id
                    task["status"] = "assigned"
                    assigned.append(task_id)
                    # Update device resource usage
                    device = self.device_manager.get_device(device_id)
                    if device:
                        req = task["required_resources"]
                        device.resource_usage["cpu"] = device.resource_usage.get("cpu", 0) + req.get("cpu", 0.1)
                        device.resource_usage["memory"] = device.resource_usage.get("memory", 0) + req.get("memory", 50)

            return assigned

    def _find_best_device(self, task: Dict) -> Optional[str]:
        """Find best device for task based on resources and preferences."""
        preferred = task.get("preferred_devices", [])
        required = task.get("required_resources", {})

        # Check preferred devices first
        for device_id in preferred:
            device = self.device_manager.get_device(device_id)
            if device and device.status == DeviceStatus.ONLINE and self._has_capacity(device, task):
                return device_id

        # Find any suitable device
        online_devices = self.device_manager.get_online_devices()
        for device in online_devices:
            if self._has_capacity(device, task):
                return device.device_id

        return None

    def _has_capacity(self, device: EdgeDevice, task: Dict) -> bool:
        required = task.get("required_resources", {})
        cpu_needed = required.get("cpu", 0.1)
        mem_needed = required.get("memory", 50)  # MB

        available_cpu = 1.0 - device.resource_usage.get("cpu", 0)
        available_mem = device.spec.memory_mb - device.resource_usage.get("memory", 0)

        return available_cpu >= cpu_needed and available_mem >= mem_needed

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        with self._lock:
            return self._tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks and self._tasks[task_id]["status"] == "pending":
                self._tasks[task_id]["status"] = "cancelled"
                return True
            return False


class EdgeCloudSyncManager:
    """Manages synchronization between edge and cloud."""

    def __init__(
        self,
        device_manager: EdgeDeviceManager,
        model_registry: EdgeModelRegistry,
        sync_interval: float = 60.0,
    ):
        self.device_manager = device_manager
        self.model_registry = model_registry
        self.sync_interval = sync_interval
        self._running = False
        self._sync_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.metrics = MetricsCollector("edge_cloud_sync")

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=5.0)

    def _sync_loop(self) -> None:
        while self._running:
            time.sleep(self.sync_interval)
            self._sync_all_devices()

    def _sync_all_devices(self) -> None:
        devices = self.device_manager.get_online_devices()
        for device in devices:
            try:
                self._sync_device(device)
            except Exception as e:
                logger.error(f"Sync failed for device {device.device_id}: {e}")

    def _sync_device(self, device: EdgeDevice) -> None:
        """Sync device with cloud."""
        # 1. Report device status
        self._report_device_status(device)

        # 2. Check for model updates
        self._check_model_updates(device)

        # 3. Upload metrics/logs
        self._upload_metrics(device)

        # 4. Pull new configurations
        self._pull_configurations(device)

    def _report_device_status(self, device: EdgeDevice) -> None:
        # Report device health, resource usage, assigned models
        pass

    def _check_model_updates(self, device: EdgeDevice) -> None:
        # Check if any assigned models have updates
        for model_id in device.assigned_models:
            model = self.model_registry.get_model(model_id)
            if model and model.get("version", 1) > device.metadata.get(f"model_{model_id}_version", 0):
                # Trigger OTA update
                logger.info(f"Model update available for {model_id} on device {device.device_id}")

    def _upload_metrics(self, device: EdgeDevice) -> None:
        # Upload device metrics to cloud
        pass

    def _pull_configurations(self, device: EdgeDevice) -> None:
        # Pull latest configurations
        pass


# Convenience functions
def create_device_manager() -> EdgeDeviceManager:
    return EdgeDeviceManager()


def create_model_optimizer(workspace_dir: str = "models/optimized") -> ModelOptimizer:
    return ModelOptimizer(workspace_dir)


def create_model_registry() -> EdgeModelRegistry:
    return EdgeModelRegistry()


def create_ota_manager(model_registry: EdgeModelRegistry, device_manager: EdgeDeviceManager) -> OTAUpdateManager:
    return OTAUpdateManager(model_registry, device_manager)


def create_federated_coordinator(model_registry: EdgeModelRegistry, device_manager: EdgeDeviceManager) -> FederatedLearningCoordinator:
    return FederatedLearningCoordinator(model_registry, device_manager)


def create_resource_scheduler(device_manager: EdgeDeviceManager) -> EdgeResourceScheduler:
    return EdgeResourceScheduler(device_manager)


def create_sync_manager(
    device_manager: EdgeDeviceManager,
    model_registry: EdgeModelRegistry,
    sync_interval: float = 60.0,
) -> EdgeCloudSyncManager:
    return EdgeCloudSyncManager(device_manager, model_registry, sync_interval)


def create_model_optimizer_tool() -> EdgeModelOptimizer:
    return EdgeModelOptimizer()
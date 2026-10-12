"""Local Model Manager — detect and manage local AI providers.

Detects:
- Ollama
- LM Studio
- llama.cpp
- vLLM
- OpenAI-compatible servers

Supports auto-connect, health monitoring, installed model listing,
download progress, and GPU status.
"""

from __future__ import annotations

import enum
import json
import logging
import os
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aetheros_providers.local")


class LocalProvider(enum.Enum):
    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    LLAMA_CPP = "llama.cpp"
    VLLM = "vllm"
    LOCALAI = "localai"
    OPENAI_COMPATIBLE = "openai_compatible"


LOCAL_PROVIDER_DEFAULTS: Dict[LocalProvider, Dict[str, Any]] = {
    LocalProvider.OLLAMA: {
        "name": "Ollama",
        "base_url": "http://localhost:11434",
        "health_endpoint": "/api/tags",
        "models_endpoint": "/api/tags",
        "chat_endpoint": "/api/chat",
        "env_var": "OLLAMA_HOST",
        "detect_cmd": "ollama",
    },
    LocalProvider.LM_STUDIO: {
        "name": "LM Studio",
        "base_url": "http://localhost:1234",
        "health_endpoint": "/v1/models",
        "models_endpoint": "/v1/models",
        "chat_endpoint": "/v1/chat/completions",
        "env_var": "LM_STUDIO_HOST",
        "detect_cmd": "",
    },
    LocalProvider.LLAMA_CPP: {
        "name": "llama.cpp",
        "base_url": "http://localhost:8080",
        "health_endpoint": "/v1/models",
        "models_endpoint": "/v1/models",
        "chat_endpoint": "/v1/chat/completions",
        "env_var": "LLAMA_CPP_HOST",
        "detect_cmd": "",
    },
    LocalProvider.VLLM: {
        "name": "vLLM",
        "base_url": "http://localhost:8000",
        "health_endpoint": "/v1/models",
        "models_endpoint": "/v1/models",
        "chat_endpoint": "/v1/chat/completions",
        "env_var": "VLLM_HOST",
        "detect_cmd": "",
    },
    LocalProvider.LOCALAI: {
        "name": "LocalAI",
        "base_url": "http://localhost:8080",
        "health_endpoint": "/v1/models",
        "models_endpoint": "/v1/models",
        "chat_endpoint": "/v1/chat/completions",
        "env_var": "LOCALAI_HOST",
        "detect_cmd": "",
    },
}


@dataclass
class LocalProviderInstance:
    provider: LocalProvider
    base_url: str
    display_name: str
    connected: bool = False
    latency_ms: float = 0.0
    models: List[Dict[str, Any]] = field(default_factory=list)
    last_seen: float = 0.0
    gpu_info: Dict[str, Any] = field(default_factory=dict)
    version: str = ""


class LocalModelManager:
    """Detect and manage local AI providers.

    Automatically discovers running local providers on the machine.
    Monitors health, lists installed models, and tracks GPU status.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._instances: Dict[str, LocalProviderInstance] = {}
        self._detected: bool = False
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect_all(self, timeout: float = 3.0) -> Dict[str, LocalProviderInstance]:
        """Detect all running local providers."""
        results = {}

        for provider_type, defaults in LOCAL_PROVIDER_DEFAULTS.items():
            base_url = os.environ.get(defaults["env_var"], defaults["base_url"])
            instance = self._try_connect(provider_type, base_url, defaults, timeout)
            if instance:
                key = f"{provider_type.value}@{base_url}"
                results[key] = instance

        with self._lock:
            self._instances.update(results)
            self._detected = True

        logger.info("Detected %d local providers", len(results))
        return results

    def _try_connect(
        self,
        provider_type: LocalProvider,
        base_url: str,
        defaults: Dict[str, Any],
        timeout: float,
    ) -> Optional[LocalProviderInstance]:
        try:
            start = time.monotonic()
            host = self._parse_host(base_url)
            port = self._parse_port(base_url)

            sock = socket.create_connection((host, port), timeout=timeout)
            sock.close()

            elapsed = (time.monotonic() - start) * 1000

            display_name = defaults["name"]
            instance = LocalProviderInstance(
                provider=provider_type,
                base_url=base_url,
                display_name=display_name,
                connected=True,
                latency_ms=round(elapsed, 1),
                last_seen=time.time(),
            )

            models = self._fetch_local_models(provider_type, base_url)
            if models:
                instance.models = models

            logger.info("Detected %s at %s (%.0fms)", display_name, base_url, elapsed)
            return instance

        except (socket.timeout, ConnectionRefusedError, OSError):
            return None
        except Exception as exc:
            logger.debug("Failed to detect %s at %s: %s", defaults["name"], base_url, exc)
            return None

    def detect_single(self, provider_type: LocalProvider, base_url: str) -> Optional[LocalProviderInstance]:
        defaults = LOCAL_PROVIDER_DEFAULTS.get(provider_type, {})
        instance = self._try_connect(provider_type, base_url, defaults, 3.0)
        if instance:
            key = f"{provider_type.value}@{base_url}"
            with self._lock:
                self._instances[key] = instance
            return instance
        return None

    # ------------------------------------------------------------------
    # Model listing
    # ------------------------------------------------------------------

    def _fetch_local_models(self, provider_type: LocalProvider, base_url: str) -> List[Dict[str, Any]]:
        defaults = LOCAL_PROVIDER_DEFAULTS.get(provider_type, {})
        endpoint = defaults.get("models_endpoint", "/api/tags")
        url = f"{base_url.rstrip('/')}{endpoint}"

        try:
            import urllib.request as req
            with req.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode())

            if provider_type == LocalProvider.OLLAMA:
                return data.get("models", [])
            return data.get("data", []) or []

        except Exception as exc:
            logger.debug("Failed to fetch models from %s: %s", url, exc)
            return []

    def get_installed_models(self, instance_key: str) -> List[Dict[str, Any]]:
        with self._lock:
            instance = self._instances.get(instance_key)
            if instance:
                return instance.models
            return []

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def start_monitoring(self, interval: float = 30.0) -> None:
        if self._monitoring:
            return
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True,
            name="local-provider-monitor",
        )
        self._monitor_thread.start()
        logger.info("Local provider monitoring started (interval=%.0fs)", interval)

    def stop_monitoring(self) -> None:
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

    def _monitor_loop(self, interval: float) -> None:
        while self._monitoring:
            with self._lock:
                keys = list(self._instances.keys())
            for key in keys:
                with self._lock:
                    instance = self._instances.get(key)
                if instance:
                    new_instance = self._try_connect(
                        instance.provider, instance.base_url,
                        LOCAL_PROVIDER_DEFAULTS.get(instance.provider, {}),
                        3.0,
                    )
                    if new_instance:
                        with self._lock:
                            if key in self._instances:
                                self._instances[key].connected = True
                                self._instances[key].latency_ms = new_instance.latency_ms
                                self._instances[key].last_seen = time.time()
                    else:
                        with self._lock:
                            if key in self._instances:
                                self._instances[key].connected = False
            time.sleep(interval)

    # ------------------------------------------------------------------
    # GPU status
    # ------------------------------------------------------------------

    def get_gpu_info(self) -> Dict[str, Any]:
        """Get GPU information from local providers."""
        info = {"available": False, "devices": []}

        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.used,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                info["available"] = True
                for line in result.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 3:
                        info["devices"].append({
                            "index": parts[0],
                            "name": parts[1],
                            "memory_total_mb": parts[2] if len(parts) > 2 else "?",
                            "memory_used_mb": parts[3] if len(parts) > 3 else "?",
                            "utilization_pct": parts[4] if len(parts) > 4 else "?",
                        })
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass

        return info

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def instances(self) -> Dict[str, LocalProviderInstance]:
        with self._lock:
            return dict(self._instances)

    @property
    def connected_count(self) -> int:
        return sum(1 for inst in self._instances.values() if inst.connected)

    @property
    def is_any_connected(self) -> bool:
        return any(inst.connected for inst in self._instances.values())

    def summary(self) -> str:
        lines = ["Local Providers:"]
        for key, instance in self._instances.items():
            status = "✓" if instance.connected else "✗"
            lines.append(
                f"  {status} {instance.display_name:20s} @ {instance.base_url:25s}"
                f" ({instance.latency_ms:.0f}ms, {len(instance.models)} models)"
            )
        if not self._instances:
            lines.append("  No local providers detected")
        gpu = self.get_gpu_info()
        if gpu["available"]:
            for dev in gpu["devices"]:
                lines.append(f"  GPU {dev['index']}: {dev['name']} ({dev['memory_used_mb']}/{dev['memory_total_mb']}MB)")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_host(url: str) -> str:
        url = url.replace("http://", "").replace("https://", "").split(":")[0]
        return url or "localhost"

    @staticmethod
    def _parse_port(url: str) -> int:
        parts = url.replace("http://", "").replace("https://", "").split(":")
        return int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 80
"""
Local AI Engine for AetherOS Intelligence Engine.

Supports running models locally through:
    - Ollama
    - llama.cpp
    - vLLM
    - LM Studio
    - Local Transformers (Hugging Face)
    - Offline inference

Provides a unified interface for local model inference,
model management, and availability detection.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class LocalBackend(Enum):
    OLLAMA = "ollama"
    LLAMA_CPP = "llama.cpp"
    VLLM = "vllm"
    LM_STUDIO = "lm_studio"
    TRANSFORMERS = "transformers"
    AUTO = "auto"


@dataclass
class LocalModelInfo:
    """Information about a locally available model."""
    name: str
    backend: LocalBackend
    path: str = ""
    size_gb: float = 0.0
    quantized: bool = False
    context_length: int = 4096
    loaded: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class LocalAI:
    """Manages local model inference across multiple backends.

    Detects available backends, pulls/manages models, and provides
    a unified inference interface.

    Usage::

        local = LocalAI()
        available = local.detect_backends()
        models = local.list_available_models()
        result = local.infer("llama3.2:3b", "What is Python?")
    """

    def __init__(self) -> None:
        self._detected_backends: Dict[LocalBackend, bool] = {}
        self._models: Dict[str, LocalModelInfo] = {}
        self._loaded_models: Dict[str, Any] = {}
        self._detect_backends()

    # ------------------------------------------------------------------
    # Backend detection
    # ------------------------------------------------------------------

    def _detect_backends(self) -> None:
        """Detect which local AI backends are available."""
        for backend in LocalBackend:
            if backend == LocalBackend.AUTO:
                continue
            try:
                available = self._check_backend(backend)
                self._detected_backends[backend] = available
                if available:
                    logger.info("Detected local AI backend: %s", backend.value)
            except Exception:
                self._detected_backends[backend] = False

    def _check_backend(self, backend: LocalBackend) -> bool:
        """Check if a specific backend is available."""
        checks = {
            LocalBackend.OLLAMA: lambda: (
                shutil.which("ollama") is not None or
                self._check_url("http://localhost:11434")
            ),
            LocalBackend.LLAMA_CPP: lambda: (
                shutil.which("llama-cli") is not None or
                shutil.which("llama-server") is not None
            ),
            LocalBackend.VLLM: self._check_vllm,
            LocalBackend.LM_STUDIO: lambda: (
                self._check_url("http://localhost:1234")
            ),
            LocalBackend.TRANSFORMERS: self._check_transformers,
        }
        check = checks.get(backend)
        if check:
            return check()
        return False

    def _check_url(self, url: str) -> bool:
        try:
            import urllib.request
            req = urllib.request.Request(url, method="HEAD")
            urllib.request.urlopen(req, timeout=2)
            return True
        except Exception:
            return False

    def _check_vllm(self) -> bool:
        try:
            import vllm
            return True
        except ImportError:
            return False

    def _check_transformers(self) -> bool:
        try:
            import transformers
            return True
        except ImportError:
            return self._check_url("http://localhost:8000")

    # ------------------------------------------------------------------
    # Backend information
    # ------------------------------------------------------------------

    def detect_backends(self) -> Dict[str, Any]:
        """Get the status of all local AI backends."""
        return {
            backend.value: {
                "available": available,
                "name": backend.value,
            }
            for backend, available in self._detected_backends.items()
            if backend != LocalBackend.AUTO
        }

    def get_available_backends(self) -> List[str]:
        """Get list of available backend names."""
        return [
            backend.value
            for backend, available in self._detected_backends.items()
            if available and backend != LocalBackend.AUTO
        ]

    def is_any_available(self) -> bool:
        return any(self._detected_backends.values())

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    def list_available_models(self, backend: str = None) -> List[Dict[str, Any]]:
        """List models available through detected backends."""
        models = []

        if self._detected_backends.get(LocalBackend.OLLAMA):
            try:
                result = subprocess.run(
                    ["ollama", "list"],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.strip().split("\n")[1:]:
                    parts = line.split()
                    if parts:
                        models.append({
                            "name": parts[0],
                            "backend": "ollama",
                            "size": parts[2] if len(parts) > 2 else "unknown",
                        })
            except Exception as exc:
                logger.debug("Ollama list failed: %s", exc)

        if self._detected_backends.get(LocalBackend.TRANSFORMERS):
            models.append({
                "name": "transformers (any HF model)",
                "backend": "transformers",
                "size": "varies",
            })

        if self._detected_backends.get(LocalBackend.LM_STUDIO):
            models.append({
                "name": "lm-studio (loaded model)",
                "backend": "lm_studio",
                "size": "varies",
            })

        if backend:
            models = [m for m in models if m["backend"] == backend]

        return models

    def pull_model(self, name: str, backend: str = "ollama") -> Dict[str, Any]:
        """Pull a model through the specified backend."""
        if backend == "ollama":
            if not self._detected_backends.get(LocalBackend.OLLAMA):
                return {"error": "Ollama not available"}

            try:
                logger.info("Pulling Ollama model: %s", name)
                result = subprocess.run(
                    ["ollama", "pull", name],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    return {"success": True, "model": name, "backend": "ollama"}
                return {"error": result.stderr.strip()}
            except subprocess.TimeoutExpired:
                return {"error": "Pull timed out after 5 minutes"}
            except Exception as exc:
                return {"error": str(exc)}

        return {"error": f"Backend {backend} does not support pull"}

    def remove_model(self, name: str, backend: str = "ollama") -> Dict[str, Any]:
        """Remove a model from the specified backend."""
        if backend == "ollama":
            try:
                result = subprocess.run(
                    ["ollama", "rm", name],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    return {"success": True, "model": name}
                return {"error": result.stderr.strip()}
            except Exception as exc:
                return {"error": str(exc)}
        return {"error": f"Backend {backend} does not support remove"}

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def infer(self, model: str, prompt: str,
              system_prompt: str = "",
              temperature: float = 0.7,
              max_tokens: int = 2048,
              stream: bool = False,
              callback: Callable = None) -> Dict[str, Any]:
        """Run inference with a local model.

        Finds the appropriate backend and runs the model.
        """
        available = self.get_available_backends()
        if not available:
            return {"error": "No local AI backend available"}

        if "ollama" in available:
            return self._infer_ollama(
                model, prompt, system_prompt,
                temperature, max_tokens, stream, callback
            )

        if "lm_studio" in available:
            return self._infer_lm_studio(
                model, prompt, system_prompt,
                temperature, max_tokens
            )

        if "transformers" in available:
            return self._infer_transformers(
                model, prompt, system_prompt,
                temperature, max_tokens
            )

        return {"error": f"No backend available for model '{model}'"}

    def _infer_ollama(self, model: str, prompt: str,
                      system_prompt: str = "",
                      temperature: float = 0.7,
                      max_tokens: int = 2048,
                      stream: bool = False,
                      callback: Callable = None) -> Dict[str, Any]:
        try:
            import requests
            payload = {
                "model": model,
                "prompt": prompt,
                "system": system_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream,
            }
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json=payload,
                timeout=120,
                stream=stream,
            )
            if resp.status_code == 200:
                if stream:
                    return {"stream": resp.iter_lines(), "backend": "ollama"}
                data = resp.json()
                return {
                    "response": data.get("response", ""),
                    "backend": "ollama",
                    "duration_ms": data.get("total_duration", 0) / 1e6 if data.get("total_duration") else 0,
                    "tokens": data.get("eval_count", 0),
                }
            return {"error": f"Ollama error {resp.status_code}: {resp.text}"}
        except ImportError:
            return {"error": "requests library required for Ollama inference"}
        except Exception as exc:
            return {"error": str(exc)}

    def _infer_lm_studio(self, model: str, prompt: str,
                         system_prompt: str = "",
                         temperature: float = 0.7,
                         max_tokens: int = 2048) -> Dict[str, Any]:
        try:
            import requests
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }
            resp = requests.post(
                "http://localhost:1234/v1/chat/completions",
                json=payload,
                timeout=120,
            )
            if resp.status_code == 200:
                data = resp.json()
                choice = data.get("choices", [{}])[0]
                return {
                    "response": choice.get("message", {}).get("content", ""),
                    "backend": "lm_studio",
                    "model": data.get("model", model),
                }
            return {"error": f"LM Studio error {resp.status_code}: {resp.text}"}
        except ImportError:
            return {"error": "requests library required for LM Studio inference"}
        except Exception as exc:
            return {"error": str(exc)}

    def _infer_transformers(self, model: str, prompt: str,
                            system_prompt: str = "",
                            temperature: float = 0.7,
                            max_tokens: int = 2048) -> Dict[str, Any]:
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(model)
            model_obj = AutoModelForCausalLM.from_pretrained(model)
            inputs = tokenizer(prompt, return_tensors="pt")
            outputs = model_obj.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
            )
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return {
                "response": response,
                "backend": "transformers",
                "model": model,
            }
        except ImportError:
            return {"error": "transformers library not installed"}
        except Exception as exc:
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            "backends_detected": self.get_available_backends(),
            "backend_count": len(self.get_available_backends()),
            "ollama_available": self._detected_backends.get(LocalBackend.OLLAMA, False),
            "llama_cpp_available": self._detected_backends.get(LocalBackend.LLAMA_CPP, False),
            "vllm_available": self._detected_backends.get(LocalBackend.VLLM, False),
            "lm_studio_available": self._detected_backends.get(LocalBackend.LM_STUDIO, False),
            "transformers_available": self._detected_backends.get(LocalBackend.TRANSFORMERS, False),
        }

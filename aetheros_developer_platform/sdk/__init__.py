"""
AetherOS SDK Collection
=======================

Language-specific SDKs for building AetherOS extensions.

Available SDKs:
    - PythonSDK: Full-featured Python SDK with type hints
    - TypeScriptSDK: TypeScript SDK with full type definitions
    - JavaScriptSDK: JavaScript SDK (CommonJS/ESM)
    - GoSDK: Go SDK with idiomatic patterns
    - RustSDK: Rust SDK with safe abstractions
    - CSharpSDK: C# SDK for .NET ecosystem
    - JavaSDK: Java SDK for JVM ecosystem

Usage::

    from aetheros_developer_platform.sdk import SDKFactory
    sdk = SDKFactory.create("python")
    project = sdk.init_project("my-extension")
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SDKLanguage(Enum):
    """Supported SDK languages."""
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    GO = "go"
    RUST = "rust"
    CSHARP = "csharp"
    JAVA = "java"


@dataclass
class SDKProject:
    """Represents an SDK project."""
    name: str
    language: SDKLanguage
    directory: Path
    version: str = "0.1.0"
    manifest: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SDKConfig:
    """SDK configuration."""
    language: SDKLanguage
    template_dir: Optional[Path] = None
    output_dir: Optional[Path] = None
    aetheros_version: str = "1.0.0"
    sdk_version: str = "1.0.0"


class BaseSDK(ABC):
    """Base class for all SDKs."""

    def __init__(self, config: Optional[SDKConfig] = None) -> None:
        self._config = config or SDKConfig(language=self.language)

    @property
    @abstractmethod
    def language(self) -> SDKLanguage:
        """Return the SDK language."""
        ...

    @abstractmethod
    def init_project(self, name: str, directory: Optional[Path] = None) -> SDKProject:
        """Initialize a new extension project."""
        ...

    @abstractmethod
    def build_project(self, project: SDKProject) -> bool:
        """Build the extension project."""
        ...

    @abstractmethod
    def test_project(self, project: SDKProject) -> Dict[str, Any]:
        """Run tests for the extension project."""
        ...

    @abstractmethod
    def package_project(self, project: SDKProject) -> Optional[Path]:
        """Package the extension for distribution."""
        ...

    @abstractmethod
    def get_template(self, plugin_type: str) -> str:
        """Get a code template for a specific plugin type."""
        ...


class SDKFactory:
    """Factory for creating SDK instances."""

    _sdk_classes: Dict[SDKLanguage, type] = {}

    @classmethod
    def register(cls, language: SDKLanguage, sdk_class: type) -> None:
        """Register an SDK class for a language."""
        cls._sdk_classes[language] = sdk_class

    @classmethod
    def create(cls, language: str, config: Optional[SDKConfig] = None) -> BaseSDK:
        """Create an SDK instance for the specified language."""
        lang = SDKLanguage(language)
        sdk_class = cls._sdk_classes.get(lang)
        if sdk_class is None:
            raise ValueError(f"No SDK registered for language: {language}")
        return sdk_class(config)


def _register_default_sdks() -> None:
    """Register all default SDK implementations."""
    from aetheros_developer_platform.sdk.python_sdk import PythonSDK
    from aetheros_developer_platform.sdk.typescript_sdk import TypeScriptSDK
    from aetheros_developer_platform.sdk.javascript_sdk import JavaScriptSDK
    from aetheros_developer_platform.sdk.go_sdk import GoSDK
    from aetheros_developer_platform.sdk.rust_sdk import RustSDK
    from aetheros_developer_platform.sdk.csharp_sdk import CSharpSDK
    from aetheros_developer_platform.sdk.java_sdk import JavaSDK

    SDKFactory.register(SDKLanguage.PYTHON, PythonSDK)
    SDKFactory.register(SDKLanguage.TYPESCRIPT, TypeScriptSDK)
    SDKFactory.register(SDKLanguage.JAVASCRIPT, JavaScriptSDK)
    SDKFactory.register(SDKLanguage.GO, GoSDK)
    SDKFactory.register(SDKLanguage.RUST, RustSDK)
    SDKFactory.register(SDKLanguage.CSHARP, CSharpSDK)
    SDKFactory.register(SDKLanguage.JAVA, JavaSDK)


# Auto-register SDKs on import
_register_default_sdks()

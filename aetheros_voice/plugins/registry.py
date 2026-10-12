from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class VoicePlugin(ABC):
    name: str = "base"
    version: str = "1.0.0"
    description: str = ""

    @abstractmethod
    async def initialize(self, voice_engine):
        ...

    async def shutdown(self):
        pass


class VoicePluginRegistry:
    def __init__(self):
        self._plugins: dict[str, VoicePlugin] = {}

    def register(self, plugin: VoicePlugin):
        self._plugins[plugin.name] = plugin

    async def initialize_all(self, voice_engine):
        for name, plugin in self._plugins.items():
            try:
                await plugin.initialize(voice_engine)
            except Exception as e:
                print(f"Plugin {name} init failed: {e}")

    async def shutdown_all(self):
        for name, plugin in self._plugins.items():
            try:
                await plugin.shutdown()
            except Exception:
                pass

    def get(self, name: str) -> VoicePlugin | None:
        return self._plugins.get(name)

    def list(self) -> list[VoicePlugin]:
        return list(self._plugins.values())

    def unregister(self, name: str):
        self._plugins.pop(name, None)

"""Plugin Runtime.

Dynamic tool plugin system:
- Discovery from directories
- Hot reload
- Enable/disable
- Sandbox isolation
- Version compatibility checking
"""

from __future__ import annotations

from tool_runtime.plugins.runtime import PluginRuntime

__all__ = ["PluginRuntime"]

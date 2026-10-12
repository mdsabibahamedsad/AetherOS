"""Execution adapters — thin facades over the production engines.

BrowserAdapter → :mod:`tools.browser_tool` (the shipping agent-browser /
CDP / cloud browser surface).
DesktopAdapter → :mod:`tools.computer_use` (the shipping per-OS desktop
backends + permission + audit layer).

These adapters *reuse* the production implementations; they never re-implement
browser or desktop control. They translate a unified
:class:`~aetheros_actions.model.Action` into the native call shape.
"""

from aetheros_actions.adapters.browser import BrowserAdapter
from aetheros_actions.adapters.desktop import DesktopAdapter

__all__ = ["BrowserAdapter", "DesktopAdapter"]
"""Tests for cross-platform capability detection (computer_use capabilities)."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tools.computer_use.capabilities import (
    DISPLAY,
    APP_LAUNCH,
    POINTER,
    SYSTEM_INFO,
    WINDOWS,
    backend_capabilities,
    backend_supports_action,
    detect_platform_info,
)


class TestPlatformInfo:
    def test_windows_detection(self):
        with patch("tools.computer_use.capabilities.platform") as pm, \
             patch.dict("os.environ", {"SESSIONNAME": "Console", "CI": ""}):
            pm.system.return_value = "Windows"
            pm.release.return_value = "11"
            pm.machine.return_value = "AMD64"
            pm.platform.return_value = "Windows-11"
            with patch.object(sys, "platform", "win32"):
                info = detect_platform_info(_platform=pm)
        assert info.os == "windows"
        assert info.session_type == "windows"
        assert info.display
        assert info.pointer and info.keyboard and info.clipboard
        assert info.windows and info.app_launch

    def test_macos_detection(self):
        with patch("tools.computer_use.capabilities.platform") as pm:
            pm.system.return_value = "Darwin"
            pm.release.return_value = "26.0"
            pm.machine.return_value = "arm64"
            pm.platform.return_value = "macOS-26"
            with patch.object(sys, "platform", "darwin"):
                info = detect_platform_info(_platform=pm)
        assert info.os == "darwin"
        assert info.session_type == "macos"
        assert info.background  # cua-driver posts events without focus steal
        assert info.elements

    def test_linux_x11_detection(self):
        with patch("tools.computer_use.capabilities.platform") as pm, \
             patch.dict("os.environ", {"DISPLAY": ":0", "WAYLAND_DISPLAY": ""}), \
             patch("tools.computer_use.capabilities._probe", return_value=True):
            pm.system.return_value = "Linux"
            pm.release.return_value = "6.8"
            pm.machine.return_value = "x86_64"
            pm.platform.return_value = "Linux-6.8"
            with patch.object(sys, "platform", "linux"):
                info = detect_platform_info(_platform=pm)
        assert info.session_type == "x11"
        assert info.display
        assert info.pointer and info.windows and info.app_launch

    def test_linux_wayland_honest(self):
        with patch("tools.computer_use.capabilities.platform") as pm, \
             patch.dict("os.environ", {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ""}):
            pm.system.return_value = "Linux"
            pm.release.return_value = "6.8"
            pm.machine.return_value = "x86_64"
            pm.platform.return_value = "Linux-6.8"
            with patch.object(sys, "platform", "linux"):
                info = detect_platform_info(_platform=pm)
        assert info.session_type == "wayland"
        # Wayland has no global automation contract — no pointer/window caps.
        assert not info.pointer
        assert not info.windows

    def test_system_info_capability_always_present(self):
        with patch("tools.computer_use.capabilities.platform") as pm, \
             patch.dict("os.environ", {"DISPLAY": "", "WAYLAND_DISPLAY": ""}):
            pm.system.return_value = "Linux"
            pm.release.return_value = "6.8"
            pm.machine.return_value = "x86_64"
            pm.platform.return_value = "Linux-6.8"
            with patch.object(sys, "platform", "linux"):
                info = detect_platform_info(_platform=pm)
        assert SYSTEM_INFO in info.capabilities

    def test_to_dict_contract(self):
        with patch("tools.computer_use.capabilities.platform") as pm:
            pm.system.return_value = "Windows"
            pm.release.return_value = "11"
            pm.machine.return_value = "AMD64"
            pm.platform.return_value = "Windows-11"
            with patch.object(sys, "platform", "win32"):
                d = detect_platform_info(_platform=pm).to_dict()
        assert d["os"] == "windows"
        assert d["session_type"] == "windows"
        assert isinstance(d["capabilities"], list)

    def test_never_raises_on_unknown(self):
        with patch("tools.computer_use.capabilities.platform") as pm:
            pm.system.return_value = "Plan9"
            pm.release.return_value = ""
            pm.machine.return_value = ""
            pm.platform.side_effect = RuntimeError("boom")
            with patch.object(sys, "platform", "plan9"):
                info = detect_platform_info(_platform=pm)
        assert info.session_type == "unknown"


class TestBackendCapabilities:
    def test_common_actions_all_backends(self):
        for name in ("cua", "win32", "linux", "noop"):
            actions = backend_capabilities(name)
            assert "capture" in actions
            assert "get_capabilities" in actions
            assert "system_info" in actions
            assert "click" in actions

    def test_win32_has_app_launch(self):
        assert "launch_app" in backend_capabilities("win32")
        assert "close_app" in backend_capabilities("win32")

    def test_supports_action(self):
        assert backend_supports_action("win32", "launch_app")
        assert backend_supports_action("cua", "close_app")
        assert not backend_supports_action("linux", "nope_never")

    def test_alias_normalization(self):
        assert backend_capabilities("windows") == backend_capabilities("win32")
        assert backend_capabilities("cua-driver") == backend_capabilities("cua")
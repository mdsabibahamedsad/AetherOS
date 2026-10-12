"""Tests for the Linux computer-use backend.

The OS access layer (``_os_*`` functions) is monkeypatched throughout, so
these tests never spawn real xdotool/wmctrl and run on any platform.
"""

from __future__ import annotations

import base64
import io
import os
import sys
from unittest.mock import patch

import pytest

import tools.computer_use.linux_backend as lx
from tools.computer_use.backend import ActionResult


@pytest.fixture
def backend():
    b = lx.LinuxBackend()
    b.start()
    return b


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

class TestKeyParsing:
    def test_simple_key(self):
        key, mods = lx._parse_key_combo("return")
        assert key == "Return"
        assert mods == []

    def test_modifier_combo(self):
        key, mods = lx._parse_key_combo("ctrl+alt+t")
        assert key == "t"
        assert set(mods) == {"ctrl", "alt"}

    def test_super_alias(self):
        key, mods = lx._parse_key_combo("cmd+shift+s")
        assert key == "s"
        assert set(mods) == {"super", "shift"}

    def test_unknown_key_passes_through(self):
        key, mods = lx._parse_key_combo("zzz")
        assert key == "zzz"  # unknown keys pass through to xdotool which errors

    def test_all_modifiers_returns_none_key(self):
        key, mods = lx._parse_key_combo("ctrl+shift")
        assert key is None
        assert set(mods) == {"ctrl", "shift"}


class TestWmctrlParsing:
    def test_parses_window_lines(self):
        out = (
            "0x01000001  0 host1 firefox.Firefox Untitled - Mozilla Firefox\n"
            "0x01000002  1 host1 gnome-terminal-server.Gnome-terminal ~/project\n"
        )
        windows = lx._parse_wmctrl_output(out)
        assert len(windows) == 2
        assert windows[0]["id"] == "0x01000001"
        assert windows[0]["app"] == "firefox.Firefox"
        assert windows[0]["title"] == "Untitled - Mozilla Firefox"
        assert windows[1]["title"] == "~/project"

    def test_skips_malformed_lines(self):
        windows = lx._parse_wmctrl_output("too short\n")
        assert windows == []


class TestDisplayDetection:
    def test_is_wayland_when_env_set(self):
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}, clear=False):
            assert lx._is_wayland() is True

    def test_is_x11_when_display_set(self):
        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=False):
            assert lx._is_x11() is True


# ---------------------------------------------------------------------------
# Backend behaviour with a mocked OS layer
# ---------------------------------------------------------------------------

class TestAvailability:
    def test_is_available_false_on_non_linux(self):
        if sys.platform.startswith("linux"):
            pytest.skip("runs only on non-Linux")
        b = lx.LinuxBackend()
        assert b.is_available() is False

    def test_is_available_false_on_wayland(self):
        if not sys.platform.startswith("linux"):
            pytest.skip("runs only on Linux")
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}, clear=False):
            with patch("tools.computer_use.linux_backend._tool_available", return_value=True):
                assert lx.LinuxBackend().is_available() is False


class TestScreenSize:
    @patch("tools.computer_use.linux_backend._os_xdotool",
           return_value=(0, "1920 1080\n", ""))
    def test_get_screen_size(self, mock_xd, backend):
        assert backend.get_screen_size() == (1920, 1080)
        mock_xd.assert_called_once_with(["getdisplaygeometry"])

    @patch("tools.computer_use.linux_backend._os_xdotool", return_value=(1, "", "err"))
    def test_get_screen_size_failure(self, mock_xd, backend):
        assert backend.get_screen_size() == (0, 0)


class TestCapture:
    def _png(self):
        from PIL import Image
        img = Image.new("RGB", (640, 480), color=(1, 2, 3))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @patch("tools.computer_use.linux_backend._os_capture_screen")
    def test_capture(self, mock_cap, backend):
        mock_cap.return_value = self._png()
        res = backend.capture(mode="som")
        assert res.width == 640
        assert res.height == 480
        assert res.png_b64
        assert "note" in res.meta  # honest AX degradation

    @patch("tools.computer_use.linux_backend._os_capture_screen",
           side_effect=RuntimeError("Wayland unsupported"))
    def test_capture_wayland_degrades(self, mock_cap, backend):
        res = backend.capture()
        assert res.png_b64 is None
        assert "Wayland" in (res.window_title or "")


class TestPointerActions:
    @patch("tools.computer_use.linux_backend._os_xdotool", return_value=(0, "", ""))
    def test_move_mouse(self, mock_xd, backend):
        res = backend.move_mouse(10, 20)
        assert res.ok
        args = mock_xd.call_args[0][0]
        assert args[:2] == ["mousemove", "10"]

    @patch("tools.computer_use.linux_backend._os_xdotool", return_value=(0, "", ""))
    def test_click(self, mock_xd, backend):
        res = backend.click(x=5, y=6, button="right")
        assert res.ok
        args = mock_xd.call_args[0][0]
        assert "3" in args  # right button number

    @patch("tools.computer_use.linux_backend._os_xdotool", return_value=(0, "", ""))
    def test_drag(self, mock_xd, backend):
        res = backend.drag(from_xy=(0, 0), to_xy=(10, 10))
        assert res.ok
        args = mock_xd.call_args[0][0]
        assert "mousedown" in args and "mouseup" in args

    @patch("tools.computer_use.linux_backend._os_xdotool", return_value=(0, "", ""))
    def test_scroll_up(self, mock_xd, backend):
        res = backend.scroll(direction="up", amount=2)
        assert res.ok
        args = mock_xd.call_args[0][0]
        assert "4" in args  # scroll-up button

    @patch("tools.computer_use.linux_backend._os_xdotool", return_value=(0, "", ""))
    def test_scroll_down(self, mock_xd, backend):
        res = backend.scroll(direction="down", amount=3)
        assert res.ok
        args = mock_xd.call_args[0][0]
        assert "5" in args


class TestKeyboard:
    @patch("tools.computer_use.linux_backend._os_xdotool", return_value=(0, "", ""))
    def test_type_text(self, mock_xd, backend):
        res = backend.type_text("hello")
        assert res.ok
        mock_xd.assert_called_once_with(["type", "--delay", "1", "hello"])

    @patch("tools.computer_use.linux_backend._os_xdotool", return_value=(0, "", ""))
    def test_key_combo(self, mock_xd, backend):
        res = backend.key("ctrl+alt+t")
        assert res.ok
        args = mock_xd.call_args[0][0]
        assert "ctrl+alt+t" in args


class TestClipboard:
    @patch("tools.computer_use.linux_backend._tool_available", return_value=False)
    def test_read_clipboard_needs_xclip(self, mock_avail, backend):
        res = backend.read_clipboard()
        assert not res.ok
        assert "xclip" in res.message

    @patch("tools.computer_use.linux_backend._tool_available", return_value=True)
    @patch("tools.computer_use.linux_backend._os_run",
           return_value=(0, "clipboard text\n", ""))
    def test_read_clipboard(self, mock_run, mock_avail, backend):
        res = backend.read_clipboard()
        assert res.ok
        assert res.meta["text"] == "clipboard text"

    @patch("tools.computer_use.linux_backend._tool_available", return_value=True)
    @patch("tools.computer_use.linux_backend.subprocess.run")
    def test_copy_clipboard(self, mock_run, mock_avail, backend):
        mock_run.return_value.returncode = 0
        res = backend.copy_clipboard("data")
        assert res.ok


class TestWindows:
    @patch("tools.computer_use.linux_backend._os_wmctrl",
           return_value=(0, "0x01000001  0 host1 firefox.Firefox Calc\n", ""))
    def test_list_windows(self, mock_wc, backend):
        windows = backend.list_windows()
        assert len(windows) == 1
        assert windows[0]["title"] == "Calc"

    @patch("tools.computer_use.linux_backend._os_wmctrl", side_effect=[
        (0, "0x01000001  0 host1 firefox.Firefox Calc\n", ""),   # list (-lx)
        (0, "", ""),                                              # activate (-ia)
    ])
    def test_focus_window_by_title(self, mock_wc, backend):
        res = backend.focus_window(title="Calc")
        assert res.ok
        assert mock_wc.call_args_list[-1][0][0] == ["-ia", "0x01000001"]

    @patch("tools.computer_use.linux_backend._os_wmctrl",
           return_value=(1, "", "wmctrl: error"))
    def test_focus_window_missing(self, mock_wc, backend):
        res = backend.focus_window(title="Nope")
        assert not res.ok

    @patch("tools.computer_use.linux_backend._os_wmctrl", side_effect=[
        (0, "0x01000001  0 host1 firefox.Firefox Calc\n", ""),   # list (-lx)
        (0, "", ""),                                              # close (-c)
    ])
    def test_close_window_graceful_wmctrl(self, mock_close, backend):
        res = backend.close_window(title="Calc")
        assert res.ok
        assert mock_close.call_args_list[-1][0][0] == ["-c", "0x01000001"]

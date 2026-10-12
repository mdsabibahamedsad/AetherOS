"""Tests for the Win32 computer-use backend.

The OS access layer (``_os_*`` functions) is monkeypatched throughout, so
these tests never touch a real Windows session and run on any platform.
"""

from __future__ import annotations

import base64
import io
import sys
from unittest.mock import MagicMock, patch

import pytest

import tools.computer_use.win32_backend as w32
from tools.computer_use.backend import ActionResult, UIElement


@pytest.fixture
def backend():
    b = w32.Win32Backend()
    b.start()
    return b


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

class TestKeyParsing:
    def test_simple_key(self):
        vk, mods = w32._parse_key_combo("return")
        assert vk == 0x0D
        assert mods == []

    def test_modifier_combo(self):
        vk, mods = w32._parse_key_combo("ctrl+alt+t")
        assert vk == ord("T")
        assert set(mods) == {0x11, 0x12}

    def test_alias_normalization(self):
        vk, mods = w32._parse_key_combo("control+shift+esc")
        assert vk == 0x1B
        assert set(mods) == {0x11, 0x10}

    def test_unknown_key_returns_none(self):
        vk, mods = w32._parse_key_combo("notakey")
        assert vk is None

    def test_function_keys(self):
        vk, _ = w32._parse_key_combo("f5")
        assert vk == 0x74


class TestRegionClamping:
    def test_fully_inside(self):
        assert w32._clamp_region(10, 10, 100, 100, 1920, 1080) == (10, 10, 100, 100)

    def test_clamped_to_bounds(self):
        assert w32._clamp_region(1900, 1000, 100, 100, 1920, 1080) == (1900, 1000, 20, 80)

    def test_negative_origin(self):
        assert w32._clamp_region(-50, 0, 100, 100, 1920, 1080) == (0, 0, 50, 100)

    def test_invalid_size(self):
        assert w32._clamp_region(0, 0, 0, 100, 1920, 1080) is None
        assert w32._clamp_region(0, 0, 100, -1, 1920, 1080) is None

    def test_outside_screen(self):
        assert w32._clamp_region(2000, 2000, 100, 100, 1920, 1080) is None


class TestKeyMapInvariants:
    def test_common_keys_present(self):
        for key in ("a", "z", "0", "9", "f1", "f12", "return", "tab",
                    "escape", "shift", "ctrl", "alt", "left", "up"):
            assert key in w32.KEY_TO_VK, key

    def test_alphabet_coverage(self):
        for letter in "abcdefghijklmnopqrstuvwxyz":
            assert w32.KEY_TO_VK[letter] == ord(letter.upper())


# ---------------------------------------------------------------------------
# Backend behaviour with a mocked OS layer
# ---------------------------------------------------------------------------

class TestAvailability:
    def test_is_available_matches_platform(self):
        assert w32.Win32Backend().is_available() is (sys.platform == "win32")


class TestCapture:
    @patch("tools.computer_use.win32_backend._os_capture_virtual_screen")
    def test_capture_returns_png_b64(self, mock_cap, backend):
        from PIL import Image
        img = Image.new("RGB", (800, 600), color=(10, 20, 30))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        mock_cap.return_value = buf.getvalue()

        res = backend.capture(mode="vision")
        assert res.width == 800
        assert res.height == 600
        assert res.png_b64
        decoded = base64.b64decode(res.png_b64)
        assert decoded.startswith(b"\x89PNG")
        # som/ax degrade with a note, never fake elements.
        assert res.elements == []
        assert "note" in res.meta

    @patch("tools.computer_use.win32_backend._os_capture_virtual_screen",
           side_effect=RuntimeError("not on Windows"))
    def test_capture_degrades_on_unsupported(self, mock_cap, backend):
        res = backend.capture()
        assert res.png_b64 is None


class TestCaptureRegion:
    @patch("tools.computer_use.win32_backend._os_get_virtual_screen",
           return_value=(0, 0, 1920, 1080))
    @patch("tools.computer_use.win32_backend._os_capture_virtual_screen")
    def test_crop(self, mock_cap, mock_vs, backend):
        from PIL import Image
        img = Image.new("RGB", (1920, 1080), color=(255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        mock_cap.return_value = buf.getvalue()

        res = backend.capture_region(100, 100, 200, 150)
        assert res.width == 200
        assert res.height == 150

    @patch("tools.computer_use.win32_backend._os_get_virtual_screen",
           return_value=(0, 0, 1920, 1080))
    @patch("tools.computer_use.win32_backend._os_capture_virtual_screen")
    def test_region_outside_screen_returns_empty(self, mock_cap, mock_vs, backend):
        from PIL import Image
        img = Image.new("RGB", (1920, 1080))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        mock_cap.return_value = buf.getvalue()
        res = backend.capture_region(5000, 5000, 100, 100)
        assert res.png_b64 is None


class TestPointerActions:
    @patch("tools.computer_use.win32_backend._os_set_cursor_pos", return_value=True)
    def test_move_mouse(self, mock_move, backend):
        res = backend.move_mouse(10, 20)
        assert res.ok
        mock_move.assert_called_once_with(10, 20)

    @patch("tools.computer_use.win32_backend._os_mouse_event")
    @patch("tools.computer_use.win32_backend._os_set_cursor_pos", return_value=True)
    def test_click_left(self, mock_pos, mock_evt, backend):
        res = backend.click(x=5, y=6, button="left")
        assert res.ok
        # down + up
        assert mock_evt.call_count == 2

    @patch("tools.computer_use.win32_backend._os_mouse_event")
    @patch("tools.computer_use.win32_backend._os_set_cursor_pos", return_value=True)
    def test_click_right_button(self, mock_pos, mock_evt, backend):
        res = backend.click(x=5, y=6, button="right")
        assert res.ok

    def test_click_requires_coords(self, backend):
        res = backend.click(element=3)
        assert not res.ok

    @patch("tools.computer_use.win32_backend._os_mouse_event")
    @patch("tools.computer_use.win32_backend._os_set_cursor_pos", return_value=True)
    def test_drag(self, mock_pos, mock_evt, backend):
        res = backend.drag(from_xy=(0, 0), to_xy=(10, 10))
        assert res.ok
        assert mock_evt.call_count == 2  # down + up

    @patch("tools.computer_use.win32_backend._os_mouse_event")
    @patch("tools.computer_use.win32_backend._os_set_cursor_pos", return_value=True)
    def test_scroll_up_positive_delta(self, mock_pos, mock_evt, backend):
        res = backend.scroll(direction="up", amount=2)
        assert res.ok
        # delta positive (up), clamped amount.
        assert mock_evt.call_args[0][3] == 120 * 2

    @patch("tools.computer_use.win32_backend._os_mouse_event")
    @patch("tools.computer_use.win32_backend._os_set_cursor_pos", return_value=True)
    def test_scroll_down_negative_delta(self, mock_pos, mock_evt, backend):
        res = backend.scroll(direction="down", amount=3)
        assert res.ok
        assert mock_evt.call_args[0][3] == -120 * 3


class TestKeyboard:
    @patch("tools.computer_use.win32_backend._os_send_unicode_chars", return_value=True)
    def test_type_text(self, mock_send, backend):
        res = backend.type_text("héllo wörld")
        assert res.ok
        mock_send.assert_called_once_with("héllo wörld")

    @patch("tools.computer_use.win32_backend._os_key_event")
    def test_key_combo(self, mock_key, backend):
        res = backend.key("ctrl+s")
        assert res.ok
        # modifiers down, key down, key up, modifiers up.
        assert mock_key.call_count == 4

    @patch("tools.computer_use.win32_backend._os_key_event")
    def test_key_bad_parse(self, mock_key, backend):
        res = backend.key("??unknown??")
        assert not res.ok
        assert mock_key.call_count == 0


class TestClipboard:
    @patch("tools.computer_use.win32_backend._os_clipboard_read_text", return_value="hello")
    def test_read_clipboard(self, mock_read, backend):
        res = backend.read_clipboard()
        assert res.ok
        assert res.meta["text"] == "hello"
        assert res.meta["length"] == 5

    @patch("tools.computer_use.win32_backend._os_clipboard_write_text", return_value=True)
    def test_copy_clipboard(self, mock_write, backend):
        res = backend.copy_clipboard("data")
        assert res.ok
        mock_write.assert_called_once_with("data")

    @patch("tools.computer_use.win32_backend._os_clipboard_clear", return_value=True)
    def test_clear_clipboard(self, mock_clear, backend):
        res = backend.clear_clipboard()
        assert res.ok


class TestWindows:
    @patch("tools.computer_use.win32_backend._os_get_virtual_screen",
           return_value=(0, 0, 1920, 1080))
    @patch("tools.computer_use.win32_backend._os_enum_visible_windows",
           return_value=[(0x1A2B, 1234), (0x2B3C, 5678)])
    @patch("tools.computer_use.win32_backend._os_get_window_title",
           side_effect=lambda hwnd: {0x1A2B: "Calculator", 0x2B3C: "Notepad"}[hwnd])
    @patch("tools.computer_use.win32_backend._os_get_window_rect",
           side_effect=lambda hwnd: {0x1A2B: (10, 10, 400, 300), 0x2B3C: (0, 0, 800, 600)}[hwnd])
    def test_list_windows(self, mock_rect, mock_title, mock_enum, mock_vs, backend):
        windows = backend.list_windows()
        assert len(windows) == 2
        calc = [w for w in windows if w["title"] == "Calculator"][0]
        assert calc["hwnd"] == 0x1A2B
        assert calc["pid"] == 1234
        assert calc["width"] == 400
        assert calc["height"] == 300

    @patch("tools.computer_use.win32_backend._os_get_foreground_window", return_value=0x1A2B)
    @patch("tools.computer_use.win32_backend._os_get_window_title", return_value="Calculator")
    @patch("tools.computer_use.win32_backend._os_get_window_rect", return_value=(0, 0, 400, 300))
    @patch("tools.computer_use.win32_backend._os_get_virtual_screen", return_value=(0, 0, 1920, 1080))
    def test_get_active_window(self, mock_vs, mock_rect, mock_title, mock_fg, backend):
        win = backend.get_active_window()
        assert win["title"] == "Calculator"
        assert win["hwnd"] == 0x1A2B

    @patch("tools.computer_use.win32_backend._os_get_virtual_screen", return_value=(0, 0, 1920, 1080))
    @patch("tools.computer_use.win32_backend._os_enum_visible_windows", return_value=[(0x10, 1)])
    @patch("tools.computer_use.win32_backend._os_get_window_title", return_value="Notes")
    @patch("tools.computer_use.win32_backend._os_get_window_rect", return_value=(0, 0, 100, 100))
    @patch("tools.computer_use.win32_backend._os_set_foreground_window", return_value=True)
    def test_focus_window_by_title(self, mock_fg, mock_rect, mock_title, mock_enum, mock_vs, backend):
        res = backend.focus_window(title="Note")
        assert res.ok
        mock_fg.assert_called_once_with(0x10)

    @patch("tools.computer_use.win32_backend._os_get_virtual_screen", return_value=(0, 0, 1920, 1080))
    @patch("tools.computer_use.win32_backend._os_enum_visible_windows", return_value=[(0x10, 1)])
    @patch("tools.computer_use.win32_backend._os_get_window_title", return_value="Notes")
    @patch("tools.computer_use.win32_backend._os_get_window_rect", return_value=(0, 0, 100, 100))
    def test_focus_window_not_found(self, mock_rect, mock_title, mock_enum, mock_vs, backend):
        res = backend.focus_window(title="NothingHere")
        assert not res.ok

    @patch("tools.computer_use.win32_backend._os_get_virtual_screen", return_value=(0, 0, 1920, 1080))
    @patch("tools.computer_use.win32_backend._os_enum_visible_windows", return_value=[(0x10, 1)])
    @patch("tools.computer_use.win32_backend._os_get_window_title", return_value="Notes")
    @patch("tools.computer_use.win32_backend._os_get_window_rect", return_value=(0, 0, 100, 100))
    @patch("tools.computer_use.win32_backend._os_show_window", return_value=True)
    def test_minimize_and_maximize(self, mock_show, mock_rect, mock_title, mock_enum, mock_vs, backend):
        assert backend.minimize_window(title="Notes").ok
        assert mock_show.call_args[0][1] == w32._SW_MINIMIZE
        assert backend.maximize_window(title="Notes").ok
        assert mock_show.call_args[0][1] == w32._SW_MAXIMIZE

    @patch("tools.computer_use.win32_backend._os_get_virtual_screen", return_value=(0, 0, 1920, 1080))
    @patch("tools.computer_use.win32_backend._os_enum_visible_windows", return_value=[(0x10, 1)])
    @patch("tools.computer_use.win32_backend._os_get_window_title", return_value="Notes")
    @patch("tools.computer_use.win32_backend._os_get_window_rect", return_value=(0, 0, 100, 100))
    @patch("tools.computer_use.win32_backend._os_post_close", return_value=True)
    def test_close_window_graceful(self, mock_close, mock_rect, mock_title, mock_enum, mock_vs, backend):
        res = backend.close_window(title="Notes")
        assert res.ok
        mock_close.assert_called_once_with(0x10)


class TestFindText:
    def _png(self):
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @patch("tools.computer_use.win32_backend._os_capture_virtual_screen")
    def test_find_text_via_ocr(self, mock_cap, backend):
        mock_cap.return_value = self._png()

        class _Box:
            x = 10
            y = 20
            width = 50
            height = 12

        class _Block:
            text = "Save Document"
            box = _Box()

        class _Extraction:
            success = True
            blocks = [_Block()]

        fake_engine = MagicMock()
        fake_engine.extract_bytes.return_value = _Extraction()

        with patch("aetheros_vision.ocr.create_ocr_engine", return_value=fake_engine):
            found = backend.find_text("save")
        assert len(found) == 1
        assert found[0].label == "Save Document"
        assert found[0].bounds == (10, 20, 50, 12)

    @patch("tools.computer_use.win32_backend._os_capture_virtual_screen")
    def test_find_text_no_match_empty(self, mock_cap, backend):
        mock_cap.return_value = self._png()

        class _Extraction:
            success = True
            blocks = []

        fake_engine = MagicMock()
        fake_engine.extract_bytes.return_value = _Extraction()
        with patch("aetheros_vision.ocr.create_ocr_engine", return_value=fake_engine):
            found = backend.find_text("nothing")
        assert found == []


class TestListApps:
    @patch("tools.computer_use.win32_backend._os_get_virtual_screen", return_value=(0, 0, 1920, 1080))
    @patch("tools.computer_use.win32_backend._os_enum_visible_windows",
           return_value=[(0x1, 100), (0x2, 100), (0x3, 200)])
    @patch("tools.computer_use.win32_backend._os_get_window_title",
           side_effect=lambda hwnd: {0x1: "Calc", 0x2: "Calc", 0x3: "Term"}[hwnd])
    @patch("tools.computer_use.win32_backend._os_get_window_rect",
           side_effect=lambda hwnd: (0, 0, 100, 100))
    def test_groups_by_pid(self, mock_rect, mock_title, mock_enum, mock_vs, backend):
        apps = backend.list_apps()
        by_pid = {a["pid"]: a for a in apps}
        assert by_pid[100]["windows"] == 2
        assert by_pid[200]["windows"] == 1

"""Master 15 additive browser tools: download/upload/tab guards and
form fill/submit confirmation + duplicate protection.

Pure-layer contracts only — CDP calls are monkeypatched; no real browser.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def _payload(raw):
    data = json.loads(raw)
    assert isinstance(data, dict)
    return data


# ---------------------------------------------------------------------------
# browser_download (Phases 17, 52, 73)
# ---------------------------------------------------------------------------

class TestBrowserDownload:
    def test_private_url_blocked_before_network(self, monkeypatch):
        import requests as _requests

        from tools.browser_transfer_tools import browser_download

        def boom(*a, **k):
            raise AssertionError("network must not be touched for blocked URLs")

        monkeypatch.setattr(_requests, "get", boom)
        out = _payload(browser_download(url="http://169.254.169.254/latest/meta-data"))
        assert out["success"] is False
        assert "blocked" in out["error"].lower() or "private" in out["error"].lower()

    def test_non_http_scheme_blocked(self):
        from tools.browser_transfer_tools import browser_download

        out = _payload(browser_download(url="file:///etc/passwd"))
        assert out["success"] is False and "scheme" in out["error"]

    def _allow_dns(self, monkeypatch):
        """Unit-test seam: bypass live-DNS-dependent SSRF resolution.
        (SSRF blocking itself is covered by test_private_url_blocked.)"""
        import tools.url_safety as us

        monkeypatch.setattr(us, "is_safe_url", lambda url: True)

    def test_secret_in_url_blocked(self, monkeypatch):
        import tools.browser_transfer_tools as browser_download_mod
        from tools.browser_transfer_tools import browser_download

        self._allow_dns(monkeypatch)
        out = _payload(browser_download(url="https://logs.example/?tok=sk-abcdefghijklmnop12"))
        assert out["success"] is False and ("credential" in out["error"].lower()
                                            or "exfiltration" in out["error"].lower())

    def test_success_writes_file_and_records_idempotency(self, monkeypatch, tmp_path):
        from aetheros_constants import get_aetheros_home
        from aetheros_computer import idempotency as idem
        import tools.browser_transfer_tools as btt

        self._allow_dns(monkeypatch)
        idem.reset()
        monkeypatch.setenv("AETHEROS_HOME", str(get_aetheros_home()))

        class FakeResp:
            headers = {"Content-Type": "text/plain", "Content-Length": "5"}

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def raise_for_status(self):
                pass

            def iter_content(self, chunk_size=8192):
                yield b"hello"

        calls = {"n": 0}
        def fake_get(url, **k):
            calls["n"] += 1
            return FakeResp()

        import requests as _requests
        monkeypatch.setattr(_requests, "get", fake_get)

        out = _payload(btt.browser_download(url="https://files.example/hello.txt",
                                            task_id="dl-test"))
        assert out["success"] is True
        assert Path(out["path"]).read_text() == "hello"
        assert out["sha256"] and len(out["sha256"]) == 64
        assert out["executable_content"] is False

        # Duplicate URL within TTL is suppressed without a second fetch.
        out2 = _payload(btt.browser_download(url="https://files.example/hello.txt",
                                             task_id="dl-test"))
        assert out2.get("duplicate") is True and calls["n"] == 1
        idem.reset()

    def test_oversize_content_length_rejected(self, monkeypatch):
        import tools.browser_transfer_tools as btt

        self._allow_dns(monkeypatch)

        class FakeResp:
            headers = {"Content-Length": str(500 * 1024 * 1024)}

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def raise_for_status(self):
                pass

            def iter_content(self, chunk_size=8192):
                return iter(())

        import requests as _requests
        monkeypatch.setattr(_requests, "get", lambda *a, **k: FakeResp())

        out = _payload(btt.browser_download(url="https://big.example/iso.img"))
        assert out["success"] is False and "large" in out["error"]


# ---------------------------------------------------------------------------
# browser_upload (Phase 18) — source screening + CDP contract
# ---------------------------------------------------------------------------

class TestBrowserUpload:
    def test_credential_store_refused(self, tmp_path):
        from tools.browser_transfer_tools import browser_upload

        secret = tmp_path / ".env"
        secret.write_text("X=1")
        out = _payload(browser_upload(selector="#f", file_path=str(secret)))
        assert out["success"] is False and "refused" in out["error"].lower()

    def test_missing_selector_flagged(self, tmp_path):
        from tools.browser_transfer_tools import browser_upload

        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")
        out = _payload(browser_upload(file_path=str(f)))
        assert out["success"] is False and out.get("needs_selector") is True

    def test_no_cdp_reports_unsupported_backend(self, tmp_path, monkeypatch):
        import tools.browser_transfer_tools as btt

        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")

        def fake_resolve():
            return ""

        monkeypatch.setattr(btt, "_resolve_cdp_endpoint", fake_resolve, raising=False)
        # _cdp imports inside function; patch module-level via monkeypatching _cdp itself
        orig = btt._cdp
        monkeypatch.setattr(btt, "_cdp",
                            lambda m, p, t=None: (_ for _ in ()).throw(
                                RuntimeError("no CDP endpoint configured")))
        out = _payload(btt.browser_upload(selector="#file", file_path=str(f)))
        assert out["success"] is False and out.get("unsupported_backend") is True

    def test_happy_path_calls_setfileinputfiles(self, tmp_path, monkeypatch):
        import tools.browser_transfer_tools as btt

        f = tmp_path / "report.pdf"
        f.write_bytes(b"%PDF-1.4 test")
        seen = []

        def fake_cdp(method, params, target_id=None):
            seen.append((method, params))
            if method == "DOM.getDocument":
                return {"result": {"root": {"nodeId": 1}}}
            if method == "DOM.querySelector":
                return {"result": {"nodeId": 42}}
            return {}

        monkeypatch.setattr(btt, "_cdp", fake_cdp)
        out = _payload(btt.browser_upload(selector="#fileInput", file_path=str(f)))
        assert out["success"] is True and out["uploaded"] is True
        methods = [m for m, _ in seen]
        assert methods == ["DOM.getDocument", "DOM.querySelector", "DOM.setFileInputFiles"]
        set_call = dict(seen[-1][1])
        assert set_call["files"] == [str(Path(out["file"]).resolve())]


# ---------------------------------------------------------------------------
# browser_tab (Phase 15) — CDP contract
# ---------------------------------------------------------------------------

class TestBrowserTab:
    def test_list_filters_page_targets(self, monkeypatch):
        import tools.browser_transfer_tools as btt

        def fake_cdp(method, params, target_id=None):
            return {"result": {"targetInfos": [
                {"targetId": "t1", "type": "page", "title": "Docs", "url": "https://d.example"},
                {"targetId": "t2", "type": "iframe", "title": "x", "url": "about:blank"},
            ]}}

        monkeypatch.setattr(btt, "_cdp", fake_cdp)
        out = _payload(btt.browser_tab(action="list"))
        assert out["count"] == 1 and out["tabs"][0]["target_id"] == "t1"

    def test_new_tab_validates_url(self, monkeypatch):
        import tools.browser_transfer_tools as btt

        monkeypatch.setattr(btt, "_cdp", lambda *a, **k: {})
        out = _payload(btt.browser_tab(action="new", url="http://127.0.0.1:8080/admin"))
        assert out["success"] is False  # SSRF guard applies to tabs too

    def test_close_requires_target(self):
        from tools.browser_transfer_tools import browser_tab

        out = _payload(browser_tab(action="close"))
        assert out["success"] is False


# ---------------------------------------------------------------------------
# Form fill / submit (Phases 19, 20, 52)
# ---------------------------------------------------------------------------

class TestFormFlow:
    def _fake_browser_tool(self, monkeypatch, fail_on=None):
        import tools.browser_tool as bt

        clicks = []
        types = []

        def fake_type(ref, text, full=False, user_task=None, task_id="default"):
            types.append((ref, text))
            if fail_on and ref == fail_on:
                return json.dumps({"success": False, "error": "no such element"})
            return json.dumps({"success": True})

        def fake_click(ref, full=False, user_task=None, task_id="default"):
            clicks.append(ref)
            return json.dumps({"success": True})

        monkeypatch.setattr(bt, "browser_type", fake_type)
        monkeypatch.setattr(bt, "browser_click", fake_click)
        return types, clicks

    def test_fill_then_confirm_gate_then_submit_once(self, monkeypatch):
        from aetheros_computer.idempotency import reset as idem_reset
        from tools.browser_form_tools import browser_form_fill, browser_submit, _FORM_STATE

        idem_reset(); _FORM_STATE.clear()
        types, clicks = self._fake_browser_tool(monkeypatch)

        out = _payload(browser_form_fill(
            fields={"@e1": "John", "@e2": "hunter2"},
            field_meta={"@e2": {"name": "password"}},
            task_id="form-t1"))
        assert out["success"] is True
        assert out["classifications"]["@e2"] == "credential"
        assert out["sensitive_present"] is True
        assert len(types) == 2

        # Phase 20: no submit without confirmation
        gate = _payload(browser_submit(ref="@e9", task_id="form-t1"))
        assert gate["needs_confirmation"] is True
        assert clicks == []
        # Credential value must be masked in the summary text
        summary = "\n".join(gate["summary"].splitlines())
        pw_line = [l for l in gate["summary"].splitlines() if "@e2" in l][0]
        assert "hunter2" not in pw_line and "*" in pw_line

        # Confirm → one click
        ok = _payload(browser_submit(ref="@e9", confirm=True, task_id="form-t1"))
        assert ok["submitted"] is True and clicks == ["@e9"]

        # Phase 52: identical payload within TTL blocked
        _FORM_STATE["form-t1"] = {  # restore state consumed on success
            "fields": {"@e1": "John", "@e2": "hunter2"},
            "classifications": {"@e1": "personal", "@e2": "credential"},
        }
        dup = _payload(browser_submit(ref="@e9", confirm=True, task_id="form-t1"))
        assert dup.get("duplicate") is True and len(clicks) == 1
        idem_reset(); _FORM_STATE.clear()

    def test_fill_failure_aborts_and_reports(self, monkeypatch):
        from tools.browser_form_tools import browser_form_fill

        self._fake_browser_tool(monkeypatch, fail_on="@e2")
        raw = browser_form_fill(fields={"@e1": "a", "@e2": "b"}, task_id="ff-fail")
        data = json.loads(raw)
        assert data["success"] is False
        assert data["results"][0]["filled"] and not data["results"][1]["filled"]

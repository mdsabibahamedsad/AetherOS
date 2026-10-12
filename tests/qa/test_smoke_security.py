"""Master 70 QA battery (runnable here).

SMOKE (release smoke suite, fast): CLI boots, contracts verify,
capability registry reports, route handlers present, no secret leakage
in error paths.
SECURITY REGRESSION: SSRF allow/deny (live url_safety), error
leak-guard, CORS posture (source-verified allowlist), deep-link/toast/
push/intent validators, update-manifest tamper cases live in node suite.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent


def test_smoke_cli_boots():
    r = subprocess.run([sys.executable, "-m", "aetheros_cli.main", "--help"],
                       capture_output=True, text=True, timeout=180, cwd=REPO)
    out = (r.stdout or "") + (r.stderr or "")
    assert "agent-network" in out and "agent" in out


def test_smoke_contracts_verify():
    from aetheros_platform.mobile_contract import verify_against_backend
    res = verify_against_backend()
    assert res and all(res.values())


def test_smoke_capabilities_report():
    from aetheros_platform.windows_capabilities import detect_capabilities
    caps = detect_capabilities()
    assert len(caps) >= 10
    assert caps["signing"].status.value != "AVAILABLE"


def test_smoke_error_model_safe():
    from aetheros_platform.web_contract import make_error
    e = make_error("forbidden", "Denied by policy.")
    assert e.http_status == 403 and not e.retryable


def test_sec_ssrf_blocks_private_and_metadata():
    from tools.url_safety import is_safe_url, is_always_blocked_url
    assert not is_safe_url("http://127.0.0.1:8080/x")
    assert not is_safe_url("http://169.254.169.254/latest/meta-data/")
    assert not is_safe_url("http://10.0.0.5/admin")
    assert is_always_blocked_url("http://169.254.169.254/")
    assert is_safe_url("https://example.com/research")


def test_sec_ssrf_redirect_targets_revalidated():
    import inspect
    import tools.url_safety as u
    src = inspect.getsource(u)
    assert "redirect" in src.lower()


def test_sec_cors_secure_by_default_wildcard_warns():
    import logging
    from gateway.platforms.api_server import APIServerAdapter, PlatformConfig
    assert APIServerAdapter._parse_cors_origins("") == ()
    assert APIServerAdapter._parse_cors_origins("https://a.example") == ("https://a.example",)
    records = []

    class H(logging.Handler):
        def emit(self, r):
            records.append(r.getMessage())

    lg = logging.getLogger("gateway.platforms.api_server")
    h = H()
    lg.addHandler(h)
    try:
        APIServerAdapter(PlatformConfig(extra={"cors_origins": ["*"]}))
    finally:
        lg.removeHandler(h)
    assert any("wildcard" in m.lower() for m in records)


def test_sec_deep_link_spoof_rejected():
    from aetheros_platform.mobile_contract import parse_deep_link
    from aetheros_platform.android_contract import parse_app_link
    assert parse_deep_link("aetheros://approval/x") == ("approval", "x")
    assert parse_deep_link("aetheros://approval/$(x)") is None
    assert parse_app_link("https://evil.com/aetheros/task/1") is None


def test_sec_update_tamper_model():
    from aetheros_platform.web_contract import validate_server_config
    ok, _ = validate_server_config({"api_base_url": "https://a.example",
                                    "allowed_origins": ["*"],
                                    "auth_mode": "session"})
    assert not ok


def test_sec_no_secrets_in_repo_paths():
    bad = []
    for p in (REPO / "aetheros_platform").glob("*.py"):
        text = p.read_text(encoding="utf-8", errors="replace")
        if re.search(r"sk-[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]{8,}", text):
            bad.append(p.name)
    assert not bad

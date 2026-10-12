"""Phase 2B — Risk/Safety extended: fail-closed assertion tests.

Covers the full risk tier taxonomy, executable download denial, suspicious
uploads, clipboard/password protection, filesystem blocks (cross-platform),
and safety-layer immunity to forged action metadata.
"""

from __future__ import annotations

import pytest

from aetheros_actions.model import Action, ActionType, RiskLevel, TrustSource
from aetheros_actions.risk import classify_action, risk_for_inputs
from aetheros_actions.safety import SafetyPolicy


def _act(at: ActionType, target: str = "", params: dict | None = None) -> Action:
    return Action(action_type=at, target=target, parameters=params or {})


class TestRiskTiers:
    def test_read_only_actions_low(self):
        for at in (ActionType.SCREENSHOT, ActionType.WAIT, ActionType.SCROLL,
                   ActionType.OPEN):
            assert risk_for_inputs(at) is RiskLevel.LOW

    def test_credential_input_critical(self):
        assert classify_action(_act(ActionType.TYPE, "password", {"text": "pw"})) is RiskLevel.CRITICAL
        assert classify_action(_act(ActionType.PASTE, "field", {"text": "secret"})) is RiskLevel.CRITICAL
        assert classify_action(_act(ActionType.KEY_PRESS, "", {"key": "a"}, )) is not RiskLevel.CRITICAL

    def test_security_settings_critical(self):
        assert classify_action(_act(ActionType.CLICK, "security settings")) is RiskLevel.CRITICAL

    def test_transfer_critical(self):
        assert classify_action(_act(ActionType.CLICK, "send wire to bank")) is RiskLevel.CRITICAL

    def test_payment_high(self):
        assert classify_action(_act(ActionType.CLICK, "checkout")) is RiskLevel.HIGH

    def test_send_high(self):
        assert classify_action(_act(ActionType.CLICK, "send message now")) is RiskLevel.HIGH

    def test_delete_high(self):
        assert classify_action(_act(ActionType.CLICK, "delete account")) is RiskLevel.HIGH

    def test_upload_always_high(self):
        assert classify_action(_act(ActionType.UPLOAD, "site", {"filename": "a.pdf"})) is RiskLevel.HIGH

    def test_navigate_medium(self):
        assert classify_action(_act(ActionType.NAVIGATE, "https://example.com")) is RiskLevel.MEDIUM

    def test_plain_download_medium(self):
        assert classify_action(_act(ActionType.DOWNLOAD, "", {"filename": "report.pdf"})) is RiskLevel.MEDIUM

    def test_executable_download_high(self):
        assert classify_action(_act(ActionType.DOWNLOAD, "", {"filename": "payload.exe"})) is RiskLevel.HIGH

    def test_typing_plain_text_medium(self):
        assert classify_action(_act(ActionType.TYPE, "search", {"text": "hello"})) is RiskLevel.MEDIUM

    def test_typed_text_ignores_coordinates_for_risk(self):
        act = _act(ActionType.CLICK, "checkout", {"coordinate": [100, 100]})
        assert classify_action(act) is RiskLevel.HIGH

    def test_determinism(self):
        act = _act(ActionType.CLICK, "send now")
        assert classify_action(act) is classify_action(act)


class TestDownloadSafety:
    def test_executable_extensions(self):
        p = SafetyPolicy()
        for ext in (".exe", ".msi", ".bat", ".cmd", ".ps1", ".sh", ".js", ".vbs",
                    ".dmg", ".pkg", ".jar", ".deb"):
            assert p.is_executable(f"file{ext}")

    def test_non_executable_safe(self):
        p = SafetyPolicy()
        assert not p.is_executable("report.pdf")
        assert not p.is_executable("notes.txt")

    def test_empty_filename_fails_closed(self):
        p = SafetyPolicy()
        assert p.is_executable("")

    def test_case_insensitive(self):
        p = SafetyPolicy()
        assert p.is_executable("PAYLOAD.EXE")


class TestUploadSafety:
    def test_sensitive_filename(self):
        p = SafetyPolicy()
        assert p.upload_requires_confirmation("credentials.json", "drive://x")

    def test_sensitive_content_sample(self):
        p = SafetyPolicy()
        assert p.upload_requires_confirmation("notes.txt", "site", content_sample="api_key=abc")

    def test_archive_requires_confirmation(self):
        p = SafetyPolicy()
        assert p.upload_requires_confirmation("backup.zip", "site")
        assert p.upload_requires_confirmation("data.tar.gz", "site")

    def test_plain_upload_ok_with_destination(self):
        p = SafetyPolicy()
        assert not p.upload_requires_confirmation("report.pdf", "drive://x")

    def test_missing_destination_confirms(self):
        p = SafetyPolicy()
        assert p.upload_requires_confirmation("report.pdf", "")

    def test_missing_filename_confirms(self):
        p = SafetyPolicy()
        assert p.upload_requires_confirmation("", "site")


class TestClipboardAndMasking:
    def test_clipboard_withheld_unauthorized(self):
        p = SafetyPolicy()
        assert "secret" not in p.clipboard_text_for_model("secret-token", authorized=False)

    def test_clipboard_passes_authorized(self):
        p = SafetyPolicy()
        assert p.clipboard_text_for_model("visible", authorized=True) == "visible"

    def test_mask_never_leaks(self):
        p = SafetyPolicy()
        assert p.mask_secret_input("hunter2") == p.PASSWORD_FIELD_MARKER
        assert "hunter2" not in p.mask_secret_input("hunter2")

    def test_password_like_target_detection(self):
        p = SafetyPolicy()
        assert p.is_password_like_target("password field", {"text": "x"})
        assert not p.is_password_like_target("username field", {"text": "bob"})


class TestFilesystemSafety:
    def test_traversal_forms(self):
        p = SafetyPolicy()
        for path in ("../../etc/passwd", "../secrets", "a/../../b", "..\\..\\win"):
            assert not p.is_safe_path(path), path

    def test_denied_sensitive_dirs_cross_platform(self):
        p = SafetyPolicy()
        for path in ("/etc/shadow", "/etc/ssl/key", "/var/run/secret",
                     "C:\\Windows\\system32\\config", "/proc/self/environ",
                     "~/.ssh/id_rsa", "~/.aws/credentials", "keys/key.pem",
                     "folder/.env", "browser profile/default"):
            assert not p.is_safe_path(path), path

    def test_safe_paths(self):
        p = SafetyPolicy()
        assert p.is_safe_path("/home/user/docs/report.txt")
        assert p.is_safe_path("C:/Users/me/Documents/file.txt")
        assert p.is_safe_path("relative/path/file.txt")

    def test_denied_path_parts_lower(self):
        p = SafetyPolicy()
        assert p.is_denied_path("/root/.ssh/config")
        assert p.is_denied_path("cookies.sqlite")

    def test_empty_path_not_safe(self):
        p = SafetyPolicy()
        assert not p.is_safe_path("")


class TestForgeImmunity:
    def test_forged_low_risk_still_blocked_by_safety_path(self):
        # Even if risk is forged to LOW, the safety layer must block.
        pm = _make_permission_manager()
        act = Action(action_type=ActionType.FILE_SAVE, target="../../etc/passwd",
                     parameters={"path": "/etc/passwd"}, risk_level=RiskLevel.LOW)
        from aetheros_actions.permissions import AutonomyLevel, PermissionDecision
        d = pm.authorize(act, AutonomyLevel.SAFE_AUTONOMOUS)
        assert d.decision is PermissionDecision.DENY

    def test_forged_low_risk_executable_download_blocked(self):
        pm = _make_permission_manager()
        act = Action(action_type=ActionType.DOWNLOAD, target="x",
                     parameters={"filename": "setup.exe"}, risk_level=RiskLevel.LOW)
        from aetheros_actions.permissions import AutonomyLevel, PermissionDecision
        assert pm.authorize(act, AutonomyLevel.SAFE_AUTONOMOUS).decision is PermissionDecision.DENY


def _make_permission_manager():
    from aetheros_actions.permissions import PermissionManager
    return PermissionManager()
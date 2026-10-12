"""Tests for Android contracts (Master 68). All executable here."""

import xml.etree.ElementTree as ET
from pathlib import Path

from aetheros_platform.android_contract import (
    WorkKind,
    WorkRequest,
    audit_manifest,
    parse_app_link,
    validate_fcm_payload,
    validate_intent,
    validate_work,
)

REPO = Path(__file__).resolve().parent.parent.parent
MANIFEST = REPO / "apps/android/app/src/main/AndroidManifest.xml"
NS = "{http://schemas.android.com/apk/res/android}"


def _manifest_model() -> dict:
    root = ET.parse(MANIFEST).getroot()
    app = root.find("application")
    perms, justified, components, services = [], [], [], []
    for p in root.findall("uses-permission"):
        name = p.get(f"{NS}name")
        perms.append(name)
        if name in ("android.permission.CAMERA", "android.permission.RECORD_AUDIO"):
            justified.append(name)  # user-invoked capture/voice only
    for act in app.findall("activity"):
        for f in act.findall("intent-filter"):
            exported = act.get(f"{NS}exported") == "true"
            if f.find("data") is not None:
                components.append({"name": act.get(f"{NS}name"),
                                   "exported": exported,
                                   "permission": "autoVerify-app-link"})
            elif exported:
                components.append({"name": act.get(f"{NS}name"),
                                   "exported": True,
                                   "permission": "launcher-main"})
    return {"package": root.get("package"), "minSdk": 26, "targetSdk": 36,
            "permissions": perms, "justified": justified,
            "components": components, "services": services,
            "debuggable": app.get(f"{NS}debuggable") == "true",
            "cleartext": app.get(f"{NS}usesCleartextTraffic") == "true"}


def test_manifest_file_audits_clean():
    ok, problems = audit_manifest(_manifest_model())
    assert ok, problems


def test_manifest_audit_catches_violations():
    bad = {"package": "com.evil.x", "minSdk": 21, "targetSdk": 30,
           "permissions": ["android.permission.READ_SMS"], "justified": [],
           "components": [{"name": ".X", "exported": True}],
           "services": [{"name": ".S", "foreground": True}],
           "debuggable": True, "cleartext": False}
    ok, problems = audit_manifest(bad)
    assert not ok and len(problems) >= 5


def test_app_links():
    assert parse_app_link("https://aetheros.example/aetheros/task/abc-1") == ("task", "abc-1")
    assert parse_app_link("aetheros://approval/x_2") == ("approval", "x_2")
    assert parse_app_link("https://evil.com/aetheros/task/1") is None
    assert parse_app_link("aetheros://wipe/all") is None
    assert parse_app_link("aetheros://task/$(x)") is None


def test_fcm_rules():
    ok, _ = validate_fcm_payload({"notification_id": "n", "title": "Hi"})
    assert ok
    ok, p = validate_fcm_payload({"task_id": "t", "refresh_token": "x"})
    assert not ok
    ok, _ = validate_fcm_payload({"title": "no ref"})
    assert not ok


def test_work_policy():
    assert validate_work(WorkRequest(WorkKind.SYNC, False, ("network",)))[0]
    ok, msg = validate_work(WorkRequest(WorkKind.SYNC, True, ()))
    assert not ok and "daemon" in msg
    ok, _ = validate_work(WorkRequest(WorkKind.UPLOAD, True, ("network",),
                                      justification="user-visible export"))
    assert ok
    ok, _ = validate_work(WorkRequest(WorkKind.SYNC, False, ("always",)))
    assert not ok


def test_intent_validation():
    assert validate_intent("android.intent.action.SEND",
                           "content://media/1", "image/png", 100)[0]
    assert not validate_intent("android.intent.action.EVIL", "x", "text/plain", 1)[0]
    assert not validate_intent("android.intent.action.SEND", "x", "text/plain", -1)[0]
    assert not validate_intent("android.intent.action.SEND", "x`y`", "text/plain", 1)[0]

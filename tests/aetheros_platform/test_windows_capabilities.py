"""Tests for the Windows capability registry (Master 64.1 A1).

Assert structure and honesty contracts, never specific availability:
a detector must report a valid status with diagnostics, and the registry
must never raise.
"""

from aetheros_platform.windows_capabilities import (
    CapabilityStatus,
    detect_capabilities,
)

VALID = {s.value for s in CapabilityStatus}

REQUIRED_IDS = {
    "toastNotifications", "toastActions", "uiAutomation", "windowsHello",
    "eventLog", "startup", "backgroundMode", "tray", "signing", "msix",
    "update", "rollback", "screenCapture", "isAdmin",
}


def test_registry_covers_all_capabilities():
    caps = detect_capabilities()
    assert REQUIRED_IDS <= set(caps)


def test_every_entry_is_honest():
    for cap in detect_capabilities().values():
        assert cap.status.value in VALID
        assert cap.id
        assert cap.diagnostics, cap.id
        assert cap.permission, cap.id
        assert cap.last_checked > 0


def test_signing_never_claims_available_without_provider():
    cap = detect_capabilities()["signing"]
    assert cap.status != CapabilityStatus.AVAILABLE


def test_msix_is_explicitly_not_supported():
    assert detect_capabilities()["msix"].status == CapabilityStatus.NOT_SUPPORTED


def test_hello_never_reports_verified_biometrics():
    cap = detect_capabilities()["windowsHello"]
    assert cap.status == CapabilityStatus.UNAVAILABLE
    assert "never replaces server auth" in cap.diagnostics


def test_serialization_round_trip():
    import json
    caps = detect_capabilities()
    blob = json.dumps({k: v.to_dict() for k, v in caps.items()})
    back = json.loads(blob)
    assert back["tray"]["status"] in VALID

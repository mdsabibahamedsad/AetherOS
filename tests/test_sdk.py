"""
Tests for the Aetheros SDK package.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from sdk.api import (
    PluginAPI, ToolAPI, EventAPI, WorkflowAPI,
    AgentAPI, MemoryAPI, InteractionAPI, EngineeringAPI, ClusterAPI,
    ToolDef, Event, WorkflowDef, WorkflowStep,
)
from sdk.context import ExtensionContext, ExtensionManifest
from sdk.lifecycle import (
    PluginLifecycle, LifecycleState, get_lifecycle,
)
from sdk.permissions import (
    Permission, PermissionSet, PermissionAudit,
    PERMISSION_FILESYSTEM_READ, PERMISSION_NETWORK_CONNECT,
)
from sdk.versioning import Version, VersionRange, BreakingChange, MigrationWarning
from sdk.compatibility import (
    check_aetheros_compatibility, check_sdk_compatibility,
    check_platform_compatibility, CompatibilityResult,
)
from sdk.validator import validate_plugin_manifest, validate_extension_manifest
from sdk.packaging import pack_plugin, unpack_plugin, PluginPackage
from sdk.signing import sign_package, verify_signature, PublisherKey, SignatureError
from sdk.templates import scaffold_plugin, list_templates


# ===========================================================================
# Versioning Tests
# ===========================================================================

class TestVersion:
    def test_parse_simple(self):
        v = Version("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert str(v) == "1.2.3"

    def test_parse_prerelease(self):
        v = Version("1.0.0-alpha.1")
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0
        assert v.prerelease == "alpha.1"
        assert v.is_prerelease

    def test_comparison(self):
        assert Version("1.0.0") < Version("2.0.0")
        assert Version("1.0.0") > Version("0.9.9")
        assert Version("1.0.0") == Version("1.0.0")
        assert Version("1.0.0-alpha") < Version("1.0.0")

    def test_invalid(self):
        with pytest.raises(ValueError):
            Version("not-a-version")

    def test_hashed(self):
        s = {Version("1.0.0"), Version("1.0.0"), Version("2.0.0")}
        assert len(s) == 2


class TestVersionRange:
    def test_contains(self):
        vr = VersionRange.parse(">=1.0.0,<2.0.0")
        assert vr.contains(Version("1.5.0"))
        assert vr.contains(Version("1.0.0"))
        assert not vr.contains(Version("2.0.0"))
        assert not vr.contains(Version("0.9.0"))

    def test_exact(self):
        vr = VersionRange.parse("==1.0.0")
        assert vr.contains(Version("1.0.0"))
        assert not vr.contains(Version("1.0.1"))

    def test_wildcard(self):
        vr = VersionRange.parse("*")
        assert vr.contains(Version("99.99.99"))


# ===========================================================================
# Permissions Tests
# ===========================================================================

class TestPermission:
    def test_create(self):
        p = Permission("filesystem:read")
        assert p.name == "filesystem:read"
        assert p.category == "filesystem"
        assert p.action == "read"

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            Permission("invalid")

    def test_permission_set(self):
        ps = PermissionSet([PERMISSION_FILESYSTEM_READ, PERMISSION_NETWORK_CONNECT])
        assert ps.has(PERMISSION_FILESYSTEM_READ)
        assert ps.has(Permission("network:connect"))
        assert not ps.has(Permission("clipboard:read"))


class TestPluginLifecycle:
    def test_initial_state(self):
        lc = PluginLifecycle("test")
        assert lc.state == LifecycleState.INSTALLED
        assert lc.is_installed

    def test_transition_to_enabled(self):
        lc = PluginLifecycle("test")
        lc.transition_to(LifecycleState.ENABLED, reason="testing")
        assert lc.is_enabled

    def test_invalid_transition(self):
        lc = PluginLifecycle("test")
        lc.transition_to(LifecycleState.ENABLED)
        with pytest.raises(ValueError):
            lc.transition_to(LifecycleState.INSTALLED)

    def test_rollback(self):
        lc = PluginLifecycle("test")
        lc.enable()
        assert lc.is_enabled
        lc.rollback()
        assert lc.is_installed

    def test_transition_history(self):
        lc = PluginLifecycle("test")
        lc.enable()
        lc.disable()
        assert len(lc.get_transition_history()) == 2


# ===========================================================================
# Compatibility Tests
# ===========================================================================

class TestCompatibility:
    def test_aetheros_version_ok(self):
        result = check_aetheros_compatibility(
            "1.0.0", min_version="0.5.0",
        )
        assert result.compatible

    def test_aetheros_version_too_old(self):
        result = check_aetheros_compatibility(
            "0.4.0", min_version="0.5.0",
        )
        assert not result.compatible

    def test_platform_compatible(self):
        import sys
        current = sys.platform
        result = check_platform_compatibility([current])
        assert result.compatible

    def test_platform_incompatible(self):
        result = check_platform_compatibility(["nonexistent_os"])
        assert not result.compatible


# ===========================================================================
# Validator Tests
# ===========================================================================

class TestValidator:
    def test_valid_minimal_manifest(self):
        manifest = {"name": "test-plugin", "version": "1.0.0"}
        errors = validate_plugin_manifest(manifest)
        assert errors == []

    def test_missing_name(self):
        errors = validate_plugin_manifest({"version": "1.0.0"})
        assert any("name" in e for e in errors)

    def test_missing_version(self):
        errors = validate_plugin_manifest({"name": "test"})
        assert any("version" in e for e in errors)

    def test_invalid_kind(self):
        manifest = {"name": "test", "version": "1.0.0", "kind": "invalid_kind"}
        errors = validate_plugin_manifest(manifest)
        assert any("kind" in e for e in errors)

    def test_valid_permissions(self):
        manifest = {
            "name": "test", "version": "1.0.0",
            "permissions": ["filesystem:read", "network:connect"],
        }
        errors = validate_plugin_manifest(manifest)
        assert errors == []

    def test_invalid_permission_format(self):
        manifest = {
            "name": "test", "version": "1.0.0",
            "permissions": ["invalid"],
        }
        errors = validate_plugin_manifest(manifest)
        assert any("permission" in e for e in errors)


# ===========================================================================
# Packaging Tests
# ===========================================================================

class TestPackaging:
    def test_pack_unpack_roundtrip(self, tmp_path):
        # Create a minimal plugin directory
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.yaml").write_text(
            "name: test-plugin\nversion: 1.0.0\n", encoding="utf-8"
        )
        (plugin_dir / "__init__.py").write_text(
            "def register(ctx): pass\n", encoding="utf-8"
        )

        # Pack
        pkg = pack_plugin(plugin_dir, output_path=tmp_path / "test.aep")
        assert pkg.package_path.exists()
        assert pkg.file_size > 0
        assert pkg.file_hash

        # Unpack
        target = tmp_path / "extracted"
        unpacked = unpack_plugin(pkg.package_path, target_dir=target)
        assert unpacked.source_dir.exists()
        assert (unpacked.source_dir / "manifest.yaml").exists()


# ===========================================================================
# API Tests
# ===========================================================================

class TestEventAPI:
    def test_publish_subscribe(self):
        ctx = _make_mock_context()
        api = EventAPI(ctx)
        received = []

        @api.on("test:event")
        def handler(event):
            received.append(event)

        api.publish("test:event", {"key": "value"})
        assert len(received) == 1
        assert received[0].data["key"] == "value"

    def test_list_event_types(self):
        ctx = _make_mock_context()
        api = EventAPI(ctx)

        @api.on("type:a")
        def handle_a(event):
            pass

        @api.on("type:b")
        def handle_b(event):
            pass

        types = api.list_event_types()
        assert "type:a" in types
        assert "type:b" in types


class TestWorkflowAPI:
    def test_define_and_register(self):
        ctx = _make_mock_context()
        api = WorkflowAPI(ctx)
        wf = api.define_workflow("test", "A test workflow")
        wf.steps.append(WorkflowStep("step1", "do_thing", {"input": "x"}))
        wf.steps.append(WorkflowStep("step2", "do_other", depends_on=["step1"]))
        api.register_workflow(wf)

        loaded = api.get_workflow("test")
        assert loaded is not None
        assert len(loaded.steps) == 2


# ===========================================================================
# Helpers
# ===========================================================================

def _make_mock_context():
    """Create a minimal ExtensionContext for testing."""
    manifest = ExtensionManifest(
        name="test-extension",
        version="1.0.0",
        description="Test extension",
    )
    return ExtensionContext(manifest=manifest, extension_dir=Path(tempfile.mkdtemp()))

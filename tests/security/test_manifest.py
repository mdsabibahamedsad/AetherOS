"""Tests for aetheros_security.manifest (tool permission manifests)."""

from aetheros_security.manifest import (
    FilesystemManifest,
    ManifestRegistry,
    NetworkManifest,
    ToolManifest,
)


class TestToolManifest:
    def test_read_write_separation(self):
        manifest = ToolManifest(
            tool_id="file.read",
            filesystem=FilesystemManifest(read=["workspace/**"]),
        )
        assert manifest.can_read("workspace/a.txt")
        assert not manifest.can_write("workspace/a.txt")
        assert not manifest.can_delete("workspace/a.txt")

    def test_write_does_not_imply_delete(self):
        manifest = ToolManifest(
            tool_id="file.editor",
            filesystem=FilesystemManifest(write=["workspace/**"]),
        )
        assert manifest.can_write("workspace/a.txt")
        assert not manifest.can_delete("workspace/a.txt")

    def test_delete_requires_delete_scope(self):
        manifest = ToolManifest(
            tool_id="file.cleaner",
            filesystem=FilesystemManifest(delete=["workspace/tmp/**"]),
        )
        assert manifest.can_delete("workspace/tmp/x.txt")
        assert not manifest.can_delete("workspace/keep/x.txt")

    def test_denied_paths_win(self):
        manifest = ToolManifest(
            tool_id="file.read",
            filesystem=FilesystemManifest(
                read=["**"], denied_paths=["**/.env", "**/.ssh/**"]),
        )
        assert manifest.can_read("anything.txt")
        assert not manifest.can_read(".env")
        assert not manifest.can_read(".ssh/id_rsa")

    def test_execute_separate(self):
        manifest = ToolManifest(
            tool_id="script.run",
            filesystem=FilesystemManifest(execute=["scripts/**"]),
        )
        assert manifest.can_execute("scripts/deploy.py")
        assert not manifest.can_read("scripts/deploy.py")

    def test_network_outbound_denied_by_default(self):
        manifest = ToolManifest(tool_id="tool", network=NetworkManifest())
        assert not manifest.allows_host("example.com")

    def test_network_allowlist(self):
        manifest = ToolManifest(
            tool_id="web",
            network=NetworkManifest(allowed_hosts=["api.example.com"],
                                    outbound=True),
        )
        assert manifest.allows_host("api.example.com")
        assert not manifest.allows_host("evil.com")

    def test_network_denylist_wins(self):
        manifest = ToolManifest(
            tool_id="web",
            network=NetworkManifest(allowed_hosts=["*.example.com"],
                                    denied_hosts=["blocked.example.com"],
                                    outbound=True),
        )
        assert manifest.allows_host("ok.example.com")
        assert not manifest.allows_host("blocked.example.com")

    def test_resource_scoping(self):
        manifest = ToolManifest(
            tool_id="db",
            resources=["database:reports", "database:analytics"],
        )
        assert manifest.allows_resource("database:reports")
        assert not manifest.allows_resource("database:users")

    def test_shell_gating(self):
        no_shell = ToolManifest(tool_id="safe")
        assert not no_shell.shell
        shell = ToolManifest(tool_id="runner", shell=True)
        assert shell.shell

    def test_to_dict_roundtrip_safe(self):
        manifest = ToolManifest(
            tool_id="file.read",
            filesystem=FilesystemManifest(read=["workspace/**"]),
        )
        data = manifest.to_dict()
        assert data["tool_id"] == "file.read"
        assert data["filesystem"]["read"] == ["workspace/**"]


class TestManifestRegistry:
    def test_register_and_deny_by_default(self):
        reg = ManifestRegistry()
        reg.register(ToolManifest(tool_id="file.read",
                                  filesystem=FilesystemManifest(
                                      read=["workspace/**"])))
        assert reg.allows("file.read", "read", "workspace/a.txt")
        assert not reg.allows("file.read", "delete", "workspace/a.txt")
        # Unknown tool -> deny.
        assert not reg.allows("unknown.tool", "read", "x")

    def test_requires_tool_id(self):
        reg = ManifestRegistry()
        try:
            reg.register(ToolManifest(tool_id=""))
            assert False, "should raise"
        except Exception:
            pass

    def test_grants_alias(self):
        reg = ManifestRegistry()
        reg.register(ToolManifest(tool_id="t",
                                  filesystem=FilesystemManifest(read=["**"])))
        assert reg.grants("t", "read", "anything")
        assert not reg.grants("t", "shell")

    def test_network_and_shell_checks(self):
        reg = ManifestRegistry()
        reg.register(ToolManifest(tool_id="web", network=NetworkManifest(
            allowed_hosts=["api.x.com"], outbound=True)))
        reg.register(ToolManifest(tool_id="runner", shell=True))
        assert reg.allows("web", "connect", "api.x.com")
        assert not reg.allows("web", "connect", "evil.com")
        assert reg.allows("runner", "shell")
        assert not reg.allows("web", "shell")

    def test_unregister(self):
        reg = ManifestRegistry()
        reg.register(ToolManifest(tool_id="t"))
        assert reg.unregister("t")
        assert not reg.unregister("t")

    def test_list_and_stats(self):
        reg = ManifestRegistry()
        reg.register(ToolManifest(tool_id="t1"))
        reg.register(ToolManifest(tool_id="t2", shell=True))
        assert len(reg.list_manifests()) == 2
        assert reg.get_stats()["total_manifests"] == 2
        assert reg.get_stats()["shell_allowed"] == 1
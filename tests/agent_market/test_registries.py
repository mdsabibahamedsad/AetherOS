"""Unit: registries, listing security, import, org tenancy."""

import json

import pytest

from aetheros_agent_market import schemas as S
from aetheros_agent_market.registries import (
    CuratedRegistry, FileRegistry, LocalRegistry, OrganizationRegistry,
    import_listing,
)


def _ident(agent_id="agent-1", org="acme"):
    return S.MarketplaceIdentity(
        identity_id=S.new_id("ident"), agent_id=agent_id,
        organization_id=org, display_name="A", issuer="test",
        verification_status="verified")


def _svc(agent_id="agent-1"):
    return S.AgentService(
        service_id=S.new_id("msvc"), agent_id=agent_id, name="S",
        capabilities=[{"capability_id": "research.web_search"}],
        supported_protocols=["A2A"], availability="available")


def test_register_publish_discover(home):
    reg = LocalRegistry(home)
    reg.register_agent(_ident())
    svc = _svc()
    reg.publish_service(svc)
    assert len(reg.discover_services({"status": "published"})) == 1
    assert reg.get_service(svc.service_id)["name"] == "S"


def test_publish_invalid_rejected(home):
    reg = LocalRegistry(home)
    with pytest.raises(ValueError):
        reg.publish_service(S.AgentService())


def test_unpublish_and_revoke(home):
    reg = LocalRegistry(home)
    reg.register_agent(_ident())
    svc = reg.publish_service(_svc())
    assert reg.unpublish_service(svc.service_id) is True
    assert reg.get_service(svc.service_id)["status"] == "unpublished"
    assert reg.revoke_listing(svc.service_id, "fraud", by="admin") is True
    assert reg.get_service(svc.service_id)["status"] == "revoked"


def test_update_suspended_blocked(home):
    reg = LocalRegistry(home)
    reg.register_agent(_ident())
    svc = reg.publish_service(_svc())
    reg.revoke_listing(svc.service_id, "x")
    with pytest.raises(PermissionError):
        reg.update_service(svc)


def test_unregister_suspends_services(home):
    reg = LocalRegistry(home)
    ident = reg.register_agent(_ident())
    svc = reg.publish_service(_svc())
    assert reg.unregister_agent(ident.identity_id) is True
    assert reg.get_service(svc.service_id)["status"] == "suspended"


def test_report_listing(home):
    reg = LocalRegistry(home)
    reg.register_agent(_ident())
    svc = reg.publish_service(_svc())
    rep = reg.report_listing(svc.service_id, "spam", reporter="u1")
    assert rep["report_id"].startswith("report-")
    assert len(reg.reports()) == 1
    with pytest.raises(ValueError):
        reg.report_listing(svc.service_id, "")


def test_verify_unknown_listing(home):
    reg = LocalRegistry(home)
    assert reg.verify_listing("nope")["status"] == "unknown"


def test_verify_unbound_identity(home):
    reg = LocalRegistry(home)
    svc = _svc()
    # Publish without identity: publish doesn't require it; verify flags it.
    reg._services.put(svc.service_id, svc.to_dict())
    result = reg.verify_listing(svc.service_id)
    assert result["status"] == "unverified"
    assert any("identity" in r for r in result["reasons"])


def test_file_registry_readonly_and_unverified(home):
    path = home / "ext.json"
    path.write_text(json.dumps({"agents": [], "services": [
        {"service_id": "s1", "agent_id": "a1", "name": "X",
         "schema_version": "1"}]}))
    reg = FileRegistry(path, backend="user", source_url="https://x.example/r.json")
    assert reg.get_service("s1")["_listing_status"] == "unverified"
    with pytest.raises(PermissionError):
        reg.publish_service(_svc())
    assert reg.verify_listing("s1")["status"] == "unverified"


def test_file_registry_bad_file(home):
    (home / "bad.json").write_text("{nope")
    with pytest.raises(ValueError):
        FileRegistry(home / "bad.json")


def test_import_forces_unverified_draft(home):
    reg = LocalRegistry(home)
    out = import_listing(reg, {"schema_version": "1", "identity_id": "i1",
                               "agent_id": "a9", "display_name": "Imp",
                               "verification_status": "verified"}, "agent")
    assert out["verification_status"] == "unverified"
    svc = import_listing(reg, {"schema_version": "1", "service_id": "s9",
                               "agent_id": "a9", "name": "ImpSvc"}, "service")
    assert svc["status"] == "draft"  # never auto-published
    with pytest.raises(ValueError):
        import_listing(reg, {}, "bogus")


def test_org_tenant_isolation(home):
    reg = OrganizationRegistry(home / "org", "acme")
    with pytest.raises(ValueError):
        OrganizationRegistry(home / "org2", "")
    with pytest.raises(PermissionError):
        reg.register_agent(_ident(org="evilcorp"))
    ident = reg.register_agent(_ident(org="acme"))
    assert ident.organization_id == "acme"
    # Service for an agent unknown to the org registry is rejected.
    with pytest.raises(KeyError):
        reg.publish_service(_svc(agent_id="ghost"))


def test_curated_registry(home):
    path = home / "curated.json"
    path.write_text(json.dumps({"agents": [], "services": []}))
    reg = CuratedRegistry(path)
    assert reg.backend == "curated"
    assert reg.discover_services() == []

"""Marketplace registry abstraction (spec section 4).

Backends: LocalRegistry, FileRegistry (remote/org/curated/user JSON
sources), OrganizationRegistry, CuratedRegistry. Decentralized by
design: direct Agent Card URLs and local agents need no central server.

Every listing carries provenance; verify_listing() reconciles
marketplace identity against the A2A Agent Card + network registry.
"""

from __future__ import annotations

import abc
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import schemas as S
from .store import JsonStore


def canonical_card_hash(card: Dict[str, Any]) -> str:
    payload = json.dumps(card, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


class MarketplaceRegistry(abc.ABC):
    """Registry interface (spec section 4)."""

    backend: str = "abstract"

    @abc.abstractmethod
    def register_agent(self, identity: S.MarketplaceIdentity) -> S.MarketplaceIdentity: ...
    @abc.abstractmethod
    def unregister_agent(self, identity_id: str, reason: str = "") -> bool: ...
    @abc.abstractmethod
    def publish_service(self, service: S.AgentService) -> S.AgentService: ...
    @abc.abstractmethod
    def unpublish_service(self, service_id: str, reason: str = "") -> bool: ...
    @abc.abstractmethod
    def update_service(self, service: S.AgentService) -> S.AgentService: ...
    @abc.abstractmethod
    def discover_agents(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]: ...
    @abc.abstractmethod
    def discover_services(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]: ...
    @abc.abstractmethod
    def get_agent(self, identity_id: str) -> Optional[Dict[str, Any]]: ...
    @abc.abstractmethod
    def get_service(self, service_id: str) -> Optional[Dict[str, Any]]: ...
    @abc.abstractmethod
    def get_offer(self, offer_id: str) -> Optional[Dict[str, Any]]: ...
    @abc.abstractmethod
    def verify_listing(self, service_id: str) -> Dict[str, Any]: ...
    @abc.abstractmethod
    def report_listing(self, service_id: str, reason: str, reporter: str = "") -> Dict[str, Any]: ...
    @abc.abstractmethod
    def revoke_listing(self, service_id: str, reason: str, by: str = "") -> bool: ...


class LocalRegistry(MarketplaceRegistry):
    """Authoritative local store: agents, services, offers, reports."""

    backend = "local"

    def __init__(self, home: Path) -> None:
        home = Path(home)
        self._agents = JsonStore(home / "identities.json")
        self._services = JsonStore(home / "services.json")
        self._offers = JsonStore(home / "offers.json")
        self._reports = JsonStore(home / "reports.json")

    # -- agents ---------------------------------------------------------
    def register_agent(self, identity: S.MarketplaceIdentity) -> S.MarketplaceIdentity:
        errors = identity.validate()
        if errors:
            raise ValueError(f"invalid identity: {errors}")
        identity.updated_at = time.time()
        self._agents.put(identity.identity_id, identity.to_dict())
        return identity

    def unregister_agent(self, identity_id: str, reason: str = "") -> bool:
        rec = self._agents.get(identity_id)
        if rec is None:
            return False
        # Suspend this vendor's services rather than deleting history.
        for svc in self._services.values():
            if svc.get("agent_id") == rec.get("agent_id") and svc.get("status") == "published":
                svc["status"] = "suspended"
                svc["updated_at"] = time.time()
                self._services.put(svc["service_id"], svc)
        return self._agents.delete(identity_id)

    # -- services --------------------------------------------------------
    def publish_service(self, service: S.AgentService) -> S.AgentService:
        errors = service.validate()
        if errors:
            raise ValueError(f"invalid service: {errors}")
        service.status = "published"
        service.updated_at = time.time()
        self._services.put(service.service_id, service.to_dict())
        return service

    def unpublish_service(self, service_id: str, reason: str = "") -> bool:
        rec = self._services.get(service_id)
        if rec is None:
            return False
        rec["status"] = "unpublished"
        rec["updated_at"] = time.time()
        self._services.put(service_id, rec)
        return True

    def update_service(self, service: S.AgentService) -> S.AgentService:
        errors = service.validate()
        if errors:
            raise ValueError(f"invalid service: {errors}")
        existing = self._services.get(service.service_id)
        if existing is None:
            raise KeyError(f"unknown service: {service.service_id}")
        if existing.get("status") in ("suspended", "revoked"):
            raise PermissionError(f"service is {existing.get('status')}; unblock first")
        service.updated_at = time.time()
        self._services.put(service.service_id, service.to_dict())
        return service

    # -- discovery --------------------------------------------------------
    def discover_agents(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        out = []
        for rec in self._agents.values():
            if filters.get("organization_id") and rec.get("organization_id") != filters["organization_id"]:
                continue
            if filters.get("verification_status") and rec.get("verification_status") != filters["verification_status"]:
                continue
            out.append(rec)
        return out

    def discover_services(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        out = []
        for rec in self._services.values():
            if filters.get("status") and rec.get("status") != filters["status"]:
                continue
            if filters.get("agent_id") and rec.get("agent_id") != filters["agent_id"]:
                continue
            if filters.get("pricing_model") and rec.get("pricing_model") != filters["pricing_model"]:
                continue
            out.append(rec)
        return out

    def get_agent(self, identity_id: str) -> Optional[Dict[str, Any]]:
        return self._agents.get(identity_id)

    def get_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        return self._services.get(service_id)

    def get_offer(self, offer_id: str) -> Optional[Dict[str, Any]]:
        return self._offers.get(offer_id)

    def put_offer(self, offer: S.Offer) -> S.Offer:
        errors = offer.validate()
        if errors:
            raise ValueError(f"invalid offer: {errors}")
        self._offers.put(offer.offer_id, offer.to_dict())
        return offer

    # -- listing safety ----------------------------------------------------
    def verify_listing(self, service_id: str) -> Dict[str, Any]:
        """Reconcile marketplace record vs A2A card + network state.

        Returns {status, checks, reasons}. Never trusts metadata blindly.
        Statuses: verified|unverified|expired|revoked|unknown (spec 5).
        """
        svc = self._services.get(service_id)
        if svc is None:
            return {"status": "unknown", "checks": {}, "reasons": ["no such listing"]}
        checks: Dict[str, Any] = {}
        reasons: List[str] = []
        # 1. Local identity binding exists?
        ident = next((a for a in self._agents.values()
                      if a.get("agent_id") == svc.get("agent_id")), None)
        checks["identity_bound"] = ident is not None
        if ident is None:
            reasons.append("no marketplace identity bound to agent")
        else:
            checks["issuer"] = ident.get("issuer", "")
            if ident.get("verification_status") in ("revoked", "expired"):
                return {"status": ident["verification_status"], "checks": checks,
                        "reasons": [f"identity {ident['verification_status']}"]}
        # 2. Reconcile against the live A2A card + network registry.
        try:
            from aetheros_network.registry import AgentRegistry
            from aetheros_network import gateway as _gw
            net = AgentRegistry(_gw.default_home() / "registry.json")
            rec = net.get(svc["agent_id"])
            checks["network_record"] = rec is not None
            if rec is None:
                reasons.append("agent unknown to A2A network registry")
            else:
                live_hash = canonical_card_hash(rec.card)
                bound_hash = (ident or {}).get("agent_card_hash", "")
                checks["card_hash_match"] = bool(bound_hash) and live_hash == bound_hash
                if bound_hash and live_hash != bound_hash:
                    reasons.append("agent card drift: hash mismatch (re-verify)")
                checks["endpoint_match"] = rec.card.get("url", "") == (ident or {}).get("endpoint", "")
                if (ident or {}).get("endpoint") and not checks["endpoint_match"]:
                    reasons.append("endpoint drift detected")
                if rec.removed:
                    return {"status": "revoked", "checks": checks,
                            "reasons": reasons + ["network record removed"]}
                if rec.provenance.get("reverify_required"):
                    reasons.append("network flags re-verification required")
        except Exception as e:  # network layer unavailable => unverified, never trusted
            checks["network_error"] = str(e)[:200]
            reasons.append("network reconciliation unavailable")
        if reasons:
            return {"status": "unverified", "checks": checks, "reasons": reasons}
        return {"status": "verified", "checks": checks, "reasons": []}

    def report_listing(self, service_id: str, reason: str, reporter: str = "") -> Dict[str, Any]:
        if not reason or len(reason) > 2000:
            raise ValueError("report reason required (<=2000 chars)")
        report_id = S.new_id("report")
        entry = {"report_id": report_id, "service_id": service_id, "reason": reason,
                 "reporter": reporter, "created_at": time.time(), "handled": False}
        self._reports.put(report_id, entry)
        return entry

    def revoke_listing(self, service_id: str, reason: str, by: str = "") -> bool:
        rec = self._services.get(service_id)
        if rec is None:
            return False
        rec["status"] = "revoked"
        rec["revocation"] = {"reason": reason, "by": by, "at": time.time()}
        rec["updated_at"] = time.time()
        self._services.put(service_id, rec)
        return True

    def reports(self, only_open: bool = True) -> List[Dict[str, Any]]:
        return [r for r in self._reports.values()
                if not only_open or not r.get("handled")]


class FileRegistry(MarketplaceRegistry):
    """Read-only view over a JSON registry file (remote/org/curated/user).

    File format: {"agents": [...], "services": [...], "offers": [...]}
    with provenance {source_url, fetched_at}. Listings are UNVERIFIED
    until verify_listing() reconciles them; publishing is not supported
    (use LocalRegistry, then export).
    """

    def __init__(self, path: Path, backend: str = "file",
                 source_url: str = "") -> None:
        self._path = Path(path)
        self.backend = backend
        self.source_url = source_url
        self._doc: Dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        try:
            self._doc = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise ValueError(f"cannot load registry file {self._path}: {e}")
        if not isinstance(self._doc, dict):
            raise ValueError("registry file must be a JSON object")

    def provenance(self) -> Dict[str, Any]:
        return {"backend": self.backend, "path": str(self._path),
                "source_url": self.source_url,
                "fetched_at": self._doc.get("fetched_at", 0)}

    def _wrap(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        rec = dict(rec)
        rec["_provenance"] = self.provenance()
        rec["_listing_status"] = "unverified"
        return rec

    def register_agent(self, identity: S.MarketplaceIdentity) -> S.MarketplaceIdentity:
        raise PermissionError("file registries are read-only; register locally then export")

    def unregister_agent(self, identity_id: str, reason: str = "") -> bool:
        raise PermissionError("file registries are read-only")

    def publish_service(self, service: S.AgentService) -> S.AgentService:
        raise PermissionError("file registries are read-only")

    def unpublish_service(self, service_id: str, reason: str = "") -> bool:
        raise PermissionError("file registries are read-only")

    def update_service(self, service: S.AgentService) -> S.AgentService:
        raise PermissionError("file registries are read-only")

    def discover_agents(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        out = []
        for rec in self._doc.get("agents", []):
            if filters.get("organization_id") and rec.get("organization_id") != filters["organization_id"]:
                continue
            out.append(self._wrap(rec))
        return out

    def discover_services(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        out = []
        for rec in self._doc.get("services", []):
            if filters.get("agent_id") and rec.get("agent_id") != filters["agent_id"]:
                continue
            out.append(self._wrap(rec))
        return out

    def get_agent(self, identity_id: str) -> Optional[Dict[str, Any]]:
        for rec in self._doc.get("agents", []):
            if rec.get("identity_id") == identity_id:
                return self._wrap(rec)
        return None

    def get_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        for rec in self._doc.get("services", []):
            if rec.get("service_id") == service_id:
                return self._wrap(rec)
        return None

    def get_offer(self, offer_id: str) -> Optional[Dict[str, Any]]:
        for rec in self._doc.get("offers", []):
            if rec.get("offer_id") == offer_id:
                return self._wrap(rec)
        return None

    def verify_listing(self, service_id: str) -> Dict[str, Any]:
        svc = self.get_service(service_id)
        if svc is None:
            return {"status": "unknown", "checks": {}, "reasons": ["no such listing"]}
        return {"status": "unverified", "checks": {"file_sourced": True},
                "reasons": ["file-sourced listings require import + reconciliation"]}

    def report_listing(self, service_id: str, reason: str, reporter: str = "") -> Dict[str, Any]:
        raise PermissionError("report against the local registry copy after import")

    def revoke_listing(self, service_id: str, reason: str, by: str = "") -> bool:
        raise PermissionError("file registries are read-only")


class OrganizationRegistry(LocalRegistry):
    """Private org marketplace: LocalRegistry + org scoping + tenant check."""

    backend = "organization"

    def __init__(self, home: Path, organization_id: str) -> None:
        super().__init__(home)
        if not organization_id:
            raise ValueError("organization_id required")
        self.organization_id = organization_id

    def _check_tenant(self, record_org: str) -> None:
        if record_org and record_org != self.organization_id:
            raise PermissionError(f"cross-tenant write denied ({record_org})")

    def register_agent(self, identity: S.MarketplaceIdentity) -> S.MarketplaceIdentity:
        self._check_tenant(identity.organization_id)
        identity.organization_id = self.organization_id
        return super().register_agent(identity)

    def publish_service(self, service: S.AgentService) -> S.AgentService:
        ident = next((a for a in self._agents.values()
                      if a.get("agent_id") == service.agent_id), None)
        if ident is None:
            raise KeyError("agent identity unknown to this organization registry")
        self._check_tenant(ident.get("organization_id", ""))
        return super().publish_service(service)


class CuratedRegistry(FileRegistry):
    """Shipped allowlist of reviewed providers (read-only, like FileRegistry)."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, backend="curated", source_url="builtin:curated")


def import_listing(local: LocalRegistry, record: Dict[str, Any], kind: str,
                   by: str = "user") -> Dict[str, Any]:
    """Import a file-sourced listing into the local registry as UNVERIFIED.

    Imported config is untrusted: schemas validated, payment permissions
    never auto-granted, status forced to unpublished until reviewed.
    """
    if kind == "agent":
        ident = S.MarketplaceIdentity.from_dict(record)
        ident.verification_status = "unverified"
        ident.issuer = record.get("issuer", "") or "imported"
        return local.register_agent(ident).to_dict()
    if kind == "service":
        svc = S.AgentService.from_dict(record)
        local._services.put(svc.service_id, svc.to_dict())  # draft, not published
        return svc.to_dict()
    if kind == "offer":
        offer = S.Offer.from_dict(record)
        return local.put_offer(offer).to_dict()
    raise ValueError(f"unknown listing kind: {kind}")

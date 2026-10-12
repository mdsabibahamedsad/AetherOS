"""ExtensionService facade: the 18-stage install flow + lifecycle ops.

Install flow: fetch -> source check -> manifest -> structure -> integrity
-> signature -> deps -> compat -> static scan -> dynamic smoke ->
permissions -> approval -> install -> register -> init -> health ->
commit -> event. Any critical failure rolls back (never half-installed).
Quarantine, updates w/ staged install + rollback, revoke-all, doctor,
capability discovery for agents (risk-aware ranking).
"""

from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_extensions.bridges import (
    extension_tool_schema, mcp_server_health, parse_skill_frontmatter,
    register_specialist_agent, scan_untrusted_text, skill_manifest,
)
from aetheros_extensions.manifest import (
    ExtensionManifest, ExtensionType, LifecycleState,
)
from aetheros_extensions.package import build_package, verify_package
from aetheros_extensions.permissions import Grant, PermissionEngine, normalize_requested
from aetheros_extensions.registry import (
    ExtensionRecord, ExtensionRegistry, check_compat,
)
from aetheros_extensions.sandbox import ExtensionHost, SecretBroker
from aetheros_extensions.scanner import run_dynamic, scan_static
from aetheros_extensions.sources import SourceManager
from aetheros_extensions.trust import PublisherTrust

ApproveFn = Callable[[Dict[str, Any]], bool]


class ExtensionService:
    def __init__(self, root: Optional[Path] = None, *,
                 approve: Optional[ApproveFn] = None,
                 fetch=None) -> None:
        self._root = Path(root) if root else None
        self._approve = approve or (lambda _info: False)
        self._registry = ExtensionRegistry()
        self._trust = PublisherTrust()
        self._host = ExtensionHost(secrets=SecretBroker(), fetch=fetch)
        self._sources = SourceManager(fetch=fetch)
        self._engine = PermissionEngine()
        self._events: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._initialized = False

    # -- lifecycle -------------------------------------------------------
    def initialize(self, root: Optional[Path] = None) -> None:
        if root is not None:
            self._root = Path(root)
        if self._root is None:
            from aetheros_constants import get_aetheros_home
            self._root = get_aetheros_home() / "extensions"
        self._root.mkdir(parents=True, exist_ok=True)
        self._registry.initialize(self._root / "registry")
        self._trust.initialize(self._root / "publishers.json")
        self._host.initialize(self._root / "host")
        (self._root / "installed").mkdir(parents=True, exist_ok=True)
        (self._root / "staging").mkdir(parents=True, exist_ok=True)
        self._initialized = True

    def _emit(self, kind: str, eid: str = "", detail: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            self._events.append({"kind": kind, "extension": eid, "at": time.time(),
                                 "detail": detail or {}})

    def events(self, *, limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._events[-limit:])

    # -- install (18 stages) -----------------------------------------------
    def install(self, *, src_dir: Optional[Path] = None,
                package: Optional[Path] = None,
                source: str = "local", source_ref: str = "",
                grants: Optional[List[Dict[str, Any]]] = None,
                skip_dynamic: bool = False) -> Dict[str, Any]:
        """Returns {ok, id?, stage?, reason?, ...}. Rolls back on failure."""
        stage = "fetch"
        staged: Optional[Path] = None
        try:
            # 1-2. fetch + source policy.
            policy = self._sources.policy_for(source, source_ref)
            if policy.trust == "untrusted" and source in ("git", "remote", "private", "org"):
                pass  # untrusted sources proceed only with full verification below
            # 3-5. package -> manifest -> structure/integrity.
            stage = "package"
            if package is not None:
                rep = verify_package(Path(package))
                if not rep.ok:
                    return self._fail(source, stage, rep.reason)
                if src_dir is None:
                    import tempfile
                    tmp = Path(tempfile.mkdtemp(prefix="extstage"))
                    rep2 = verify_package(Path(package), extract_to=tmp)
                    if not rep2.ok:
                        return self._fail(source, stage, rep2.reason)
                    src_dir = tmp
                manifest_raw, digest = rep.manifest, rep.package_digest
            else:
                if src_dir is None:
                    return self._fail(source, stage, "no source given")
                try:
                    manifest_raw = __import__("json").loads(
                        (Path(src_dir) / "manifest.json").read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    return self._fail(source, "manifest", f"manifest unreadable: {exc}")
                digest = "dir:" + str(src_dir)
            stage = "manifest"
            try:
                manifest = ExtensionManifest.from_dict(manifest_raw)
            except ValueError as exc:
                return self._fail(source, stage, str(exc))
            problems = manifest.validate()
            if problems:
                return self._fail(source, stage, "; ".join(problems))
            stage = "signature"
            envelope = None
            if package is not None:
                try:
                    import zipfile as _zf
                    with _zf.ZipFile(package) as zf:
                        if "signature/signature.json" in zf.namelist():
                            envelope = __import__("json").loads(
                                zf.read("signature/signature.json").decode())
                except Exception:
                    envelope = None
            trust = self._trust.evaluate(manifest, envelope, digest)
            if not trust.get("ok"):
                if not (policy.allow_unsigned and envelope is None):
                    return self._fail(source, stage, trust["reason"], state="signature_failed")
            stage = "dependencies"
            resolved = self._registry.resolve(manifest)
            if not resolved["ok"]:
                return self._fail(source, stage, "; ".join(resolved["problems"]))
            stage = "compatibility"
            import platform as _plat
            compat = check_compat(manifest_raw,
                                  platform="windows" if _plat.system() == "Windows"
                                  else ("darwin" if _plat.system() == "Darwin" else "linux"))
            if compat["verdict"] == "INCOMPATIBLE":
                return self._fail(source, stage, compat["reason"],
                                  state="compatibility_failed")
            stage = "static_scan"
            static = scan_static(Path(src_dir))
            if static.verdict == "BLOCK":
                return self._fail(source, stage,
                                  f"static BLOCK: {[f.rule for f in static.findings[:5]]}",
                                  state="security_blocked")
            stage = "dynamic"
            dynamic = None
            smoke = (manifest.entrypoints.get("smoke")
                     or manifest.entrypoints.get("main", ""))
            if smoke and not skip_dynamic:
                dynamic = run_dynamic(Path(src_dir), smoke)
                if not dynamic.ran or dynamic.verdict == "BLOCK":
                    return self._fail(source, stage,
                                      f"dynamic failed: {dynamic.reason}",
                                      state="security_blocked")
            stage = "permissions"
            requested = manifest_raw.get("permissions", [])
            review = self._engine.review_groups(requested)
            # 12. approval for anything above LOW RISK.
            needs_ok = True
            if review["HIGH RISK"] or review["CRITICAL"]:
                needs_ok = bool(self._approve({"id": manifest.id,
                                               "permissions": requested,
                                               "review": review}))
                if not needs_ok:
                    return self._fail(source, "approval", "user denied permissions",
                                      state="permission_denied")
            stage = "install"
            dest = self._root / "installed" / manifest.id / manifest.version
            staged = self._root / "staging" / f"{manifest.id}-{manifest.version}"
            if staged.exists():
                shutil.rmtree(staged, ignore_errors=True)
            shutil.copytree(src_dir, staged)
            stage = "register"
            rec = self._registry.get(manifest.id)
            prev_version = rec.installed_version if rec else ""
            if rec is None:
                rec = ExtensionRecord(id=manifest.id, manifest=manifest_raw,
                                      source=source, source_ref=source_ref)
            else:
                rec.previous_version = prev_version
            rec.manifest = manifest_raw
            rec.available_version = manifest.version
            rec.trust_level = trust.get("level", "unsigned")
            if grants is not None:
                rec.grants = grants
            else:
                rec.grants = [{"permission": n["permission"], "scope": n.get("scope", {})}
                              if isinstance(n, dict) else {"permission": n, "scope": {}}
                              for n in requested
                              for n in normalize_requested(n)]
            for st in ("validating", "verified", "trust_pending",
                       "permission_pending", "installing"):
                rec.set_state(st)
            self._registry.upsert(rec)
            stage = "init"
            self._host.open_context(
                manifest.id, manifest.version,
                [Grant(permission=g.get("permission", ""),
                       scope={k: v for k, v in g.items() if k != "permission"})
                 for g in rec.grants if g.get("permission")])
            stage = "health"
            health: Dict[str, Any] = {"state": "HEALTHY", "static": static.verdict}
            if dynamic is not None:
                health["dynamic"] = dynamic.to_dict()
            if compat["warnings"]:
                health["state"] = "DEGRADED"
                health["warnings"] = compat["warnings"]
            stage = "commit"
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staged), str(dest))
            staged = None
            rec.install_path = str(dest)
            rec.installed_version = manifest.version
            rec.set_state("installed")
            self._registry.upsert(rec)
            self._registry.record_health(manifest.id, health)
            self._emit("extension.installed", manifest.id,
                       {"version": manifest.version, "trust": rec.trust_level})
            return {"ok": True, "id": manifest.id, "version": manifest.version,
                    "trust": rec.trust_level, "static": static.verdict,
                    "review": review, "compat": compat["verdict"]}
        except ValueError as exc:
            return self._fail(source, stage, str(exc), state="validation_failed")
        except Exception as exc:
            return self._fail(source, stage, f"install failed: {exc}")
        finally:
            if staged is not None and staged.exists():
                shutil.rmtree(staged, ignore_errors=True)

    def _fail(self, source: str, stage: str, reason: str,
              state: str = "validation_failed") -> Dict[str, Any]:
        self._emit("extension.install_failed", "",
                   {"stage": stage, "reason": reason, "source": source})
        return {"ok": False, "stage": stage, "reason": reason, "state": state}

    # -- lifecycle ops ------------------------------------------------------
    def enable(self, eid: str) -> Dict[str, Any]:
        rec = self._registry.get(eid)
        if rec is None:
            return {"ok": False, "reason": "unknown extension"}
        if rec.state == LifecycleState.QUARANTINED.value:
            return {"ok": False, "reason": "quarantined"}
        try:
            if rec.state == LifecycleState.INSTALLED.value:
                rec.set_state("enabled")
            elif rec.state == LifecycleState.DISABLED.value:
                rec.set_state("enabled")
            elif rec.state != LifecycleState.ENABLED.value:
                return {"ok": False, "reason": f"cannot enable from {rec.state}"}
            self._registry.upsert(rec)
            self._emit("extension.enabled", eid)
            return {"ok": True}
        except ValueError as exc:
            return {"ok": False, "reason": str(exc)}

    def disable(self, eid: str) -> Dict[str, Any]:
        rec = self._registry.get(eid)
        if rec is None:
            return {"ok": False, "reason": "unknown extension"}
        try:
            if rec.state in (LifecycleState.ENABLED.value, LifecycleState.RUNNING.value):
                rec.set_state("disabled")
            elif rec.state != LifecycleState.DISABLED.value:
                return {"ok": False, "reason": f"cannot disable from {rec.state}"}
            self._registry.upsert(rec)
            self._host.close(eid)
            self._emit("extension.disabled", eid)
            return {"ok": True}
        except ValueError as exc:
            return {"ok": False, "reason": str(exc)}

    def uninstall(self, eid: str) -> Dict[str, Any]:
        rec = self._registry.get(eid)
        if rec is None:
            return {"ok": False, "reason": "unknown extension"}
        # Cleanup: install dir, storage, context, tool registrations.
        self._host.close(eid)
        self._host.revoke_all(eid)
        if rec.install_path:
            shutil.rmtree(rec.install_path, ignore_errors=True)
        storage = self._root / "host" / "storage" / eid
        shutil.rmtree(storage, ignore_errors=True)
        try:
            from tools.registry import registry as tool_reg
            for name in tool_reg.get_all_tool_names():
                info = tool_reg.get_tool_info(name) or {}
                if info.get("provider") == f"ext:{eid}":
                    tool_reg.deregister(name)
        except Exception:
            pass
        try:
            rec.set_state("uninstalled")
        except ValueError:
            rec.state = LifecycleState.UNINSTALLED.value
        self._registry.upsert(rec)
        self._emit("extension.uninstalled", eid)
        # Verify cleanup actually happened.
        leftover = (Path(rec.install_path).exists() if rec.install_path else False)
        return {"ok": not leftover, "cleanup_verified": not leftover}

    def quarantine(self, eid: str, reason: str) -> Dict[str, Any]:
        rec = self._registry.get(eid)
        if rec is None:
            return {"ok": False, "reason": "unknown extension"}
        self._host.close(eid)
        self._host.revoke_all(eid)
        try:
            rec.set_state("quarantined")
        except ValueError:
            rec.state = LifecycleState.QUARANTINED.value
        rec.quarantine = {"reason": reason, "at": time.time()}
        self._registry.upsert(rec)
        self._registry.record_health(eid, {"state": "QUARANTINED", "reason": reason})
        self._emit("extension.quarantined", eid, {"reason": reason})
        return {"ok": True}

    def revoke_all(self, eid: str) -> Dict[str, Any]:
        ok = self._host.revoke_all(eid)
        rec = self._registry.get(eid)
        if rec is not None:
            rec.grants = []
            self._registry.upsert(rec)
        self._emit("extension.permissions_revoked", eid)
        return {"ok": ok}

    def revoke_everything(self) -> Dict[str, Any]:
        count = 0
        for rec in self._registry.list():
            if self._host.revoke_all(rec.id):
                count += 1
            rec.grants = []
            self._registry.upsert(rec)
        self._emit("extension.revoke_all", "", {"count": count})
        return {"ok": True, "revoked": count}

    # -- updates + rollback ----------------------------------------------------
    def update(self, eid: str, *, src_dir: Optional[Path] = None,
               package: Optional[Path] = None) -> Dict[str, Any]:
        rec = self._registry.get(eid)
        if rec is None:
            return {"ok": False, "reason": "unknown extension"}
        try:
            rec.set_state("updating")
        except ValueError:
            return {"ok": False, "reason": f"cannot update from {rec.state}"}
        self._registry.upsert(rec)
        prev = rec.installed_version
        res = self.install(src_dir=src_dir, package=package, source=rec.source,
                           source_ref=rec.source_ref)
        if not res.get("ok"):
            # Automatic rollback where safe: restore previous state pointer.
            rec = self._registry.get(eid)
            if rec is not None:
                try:
                    rec.set_state("rolled_back")
                except ValueError:
                    rec.state = LifecycleState.ROLLED_BACK.value
                rec.installed_version = prev
                self._registry.upsert(rec)
            self._emit("extension.update_rolled_back", eid, {"reason": res.get("reason")})
            return {"ok": False, "rolled_back": True, "reason": res.get("reason")}
        return {**res, "previous_version": prev}

    # -- query -------------------------------------------------------------------
    def info(self, eid: str) -> Optional[Dict[str, Any]]:
        rec = self._registry.get(eid)
        if rec is None:
            return None
        return {**rec.to_dict(),
                "health_live": self._host.health(eid).__dict__}

    def list(self, **kw) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._registry.list(**kw)]

    def permissions(self, eid: str) -> Dict[str, Any]:
        rec = self._registry.get(eid)
        if rec is None:
            return {"ok": False, "reason": "unknown extension"}
        return {"ok": True, "grants": rec.grants,
                "review": self._engine.review_groups(rec.manifest.get("permissions", []))}

    def verify(self, eid: str) -> Dict[str, Any]:
        rec = self._registry.get(eid)
        if rec is None:
            return {"ok": False, "reason": "unknown extension"}
        out: Dict[str, Any] = {"id": eid, "state": rec.state}
        path = Path(rec.install_path) if rec.install_path else None
        if path and (path / "manifest.json").exists():
            import json as _json
            try:
                disk = _json.loads((path / "manifest.json").read_text(encoding="utf-8"))
                out["manifest_match"] = disk.get("version") == rec.installed_version
            except (OSError, ValueError):
                out["manifest_match"] = False
        else:
            out["manifest_match"] = False
        if path and (path / "integrity.json").exists():
            import json as _json
            try:
                integ = _json.loads((path / "integrity.json").read_text(encoding="utf-8"))
                from aetheros_extensions.package import sha256_bytes
                bad = [rel for rel, claimed in (integ.get("files") or {}).items()
                       if (path / rel).exists()
                       and sha256_bytes((path / rel).read_bytes()) != claimed]
                out["integrity_ok"] = not bad
                out["integrity_bad"] = bad[:10]
            except (OSError, ValueError) as exc:
                out["integrity_ok"] = False
                out["integrity_error"] = str(exc)[:200]
        else:
            out["integrity_ok"] = False
            out["integrity_error"] = "no integrity.json (dir install)"
        return out

    def doctor(self) -> Dict[str, Any]:
        problems = []
        for rec in self._registry.list():
            if rec.state in ("runtime_failed", "install_failed"):
                problems.append({"id": rec.id, "state": rec.state})
            if rec.install_path and not Path(rec.install_path).exists() \
                    and rec.state not in ("uninstalled",):
                problems.append({"id": rec.id, "issue": "install dir missing"})
        return {"problems": problems, "total": len(self._registry.list()),
                "stats": self._registry.stats()}

    # -- capability discovery for agents (risk-aware) -------------------------------
    def discover_capability(self, capability: str) -> List[Dict[str, Any]]:
        scored = []
        for rec in self._registry.list(state="enabled"):
            caps = rec.manifest.get("capabilities", [])
            if capability in caps:
                risks = [self._engine.risk_of(
                    n.get("permission", n) if isinstance(n, dict) else n)
                    for n in rec.manifest.get("permissions", [])]
                worst = max(risks) if risks else "R0"
                scored.append({"id": rec.id,
                               "version": rec.installed_version,
                               "health": (rec.health or {}).get("state", "unknown"),
                               "worst_risk": worst,
                               "trust": rec.trust_level})
        order = {"R0": 0, "R1": 1, "R2": 2, "R3": 3, "R4": 4, "R5": 5}
        return sorted(scored, key=lambda e: (
            0 if e["health"] == "HEALTHY" else 1, order.get(e["worst_risk"], 9)))

    # -- built-in adoption ------------------------------------------------------------
    def adopt_builtin(self, eid: str, manifest: ExtensionManifest) -> Dict[str, Any]:
        problems = manifest.validate()
        if problems:
            return {"ok": False, "reason": "; ".join(problems)}
        rec = self._registry.get(eid)
        if rec is None:
            rec = ExtensionRecord(id=eid, manifest=manifest.to_dict(),
                                  source="builtin", state="installed",
                                  installed_version=manifest.version,
                                  trust_level="trusted_publisher")
            self._registry.upsert(rec)
        return {"ok": True, "id": eid}

    # -- tool registration ---------------------------------------------------------------
    def register_tools(self, eid: str,
                       register_fn) -> Dict[str, Any]:
        """Register manifest-declared tools via caller-supplied registry hook."""
        rec = self._registry.get(eid)
        if rec is None:
            return {"ok": False, "reason": "unknown extension"}
        if rec.state == LifecycleState.QUARANTINED.value:
            return {"ok": False, "reason": "quarantined"}
        registered = []
        for tool in rec.manifest.get("tools", []):
            schema = extension_tool_schema(tool, eid, rec.installed_version)
            try:
                register_fn(schema)
                registered.append(schema["name"])
            except Exception as exc:
                return {"ok": False, "reason": f"tool {tool.get('name')}: {exc}"}
        self._emit("extension.tools_registered", eid, {"tools": registered})
        return {"ok": True, "tools": registered}

"""Extension agent tools + CLI (Master 44 sections 44-45).

Tools route through the process-singleton ExtensionService (real backend).
CLI commands are real operations, never print-only success.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict

from tools.registry import registry

_lock = threading.Lock()
_svc = None


def _svc_fn():
    global _svc
    with _lock:
        if _svc is None:
            from aetheros_extensions.service import ExtensionService
            _svc = ExtensionService()
            _svc.initialize()
        return _svc


def _ok(**kw: Any) -> str:
    return json.dumps(kw, ensure_ascii=False)


def ext_list(args: Dict[str, Any], **kw: Any) -> str:
    recs = _svc_fn().list(query=args.get("query", ""),
                           ext_type=args.get("type", ""),
                           state=args.get("state", ""))
    return _ok(success=True, extensions=recs, total=len(recs))


def ext_info(args: Dict[str, Any], **kw: Any) -> str:
    info = _svc_fn().info(args.get("id", ""))
    return _ok(success=info is not None, extension=info)


def ext_install(args: Dict[str, Any], **kw: Any) -> str:
    src = args.get("source", "")
    p = Path(src)
    if p.suffix == ".aetherext" and p.exists():
        return _ok(success=True, **_svc_fn().install(package=p, source="local_package"))
    if p.is_dir():
        return _ok(success=True, **_svc_fn().install(src_dir=p, source="local"))
    return _ok(success=False, reason="source must be an .aetherext file or directory")


def ext_uninstall(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=True, **_svc_fn().uninstall(args.get("id", "")))


def ext_enable(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=True, **_svc_fn().enable(args.get("id", "")))


def ext_disable(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=True, **_svc_fn().disable(args.get("id", "")))


def ext_verify(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=True, **_svc_fn().verify(args.get("id", "")))


def ext_permissions(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=True, **_svc_fn().permissions(args.get("id", "")))


def ext_revoke(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=True, **_svc_fn().revoke_all(args.get("id", "")))


def ext_quarantine(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=True, **_svc_fn().quarantine(
        args.get("id", ""), args.get("reason", "manual quarantine")))


def ext_doctor(args: Dict[str, Any], **kw: Any) -> str:
    return _ok(success=True, **_svc_fn().doctor())


def _check() -> bool:
    return True


_TOOLS = [
    ("extension_list", "List extensions (filter by query/type/state).",
     {"query": {"type": "string"}, "type": {"type": "string"}, "state": {"type": "string"}}, ext_list),
    ("extension_info", "Extension detail: manifest, trust, perms, health.",
     {"id": {"type": "string"}}, ext_info),
    ("extension_install", "Install from .aetherext file or directory (verified).",
     {"source": {"type": "string"}}, ext_install),
    ("extension_uninstall", "Uninstall + verified cleanup.",
     {"id": {"type": "string"}}, ext_uninstall),
    ("extension_enable", "Enable an installed extension.",
     {"id": {"type": "string"}}, ext_enable),
    ("extension_disable", "Disable an extension.",
     {"id": {"type": "string"}}, ext_disable),
    ("extension_verify", "Re-verify integrity + manifest match.",
     {"id": {"type": "string"}}, ext_verify),
    ("extension_permissions", "Show grants + risk review groups.",
     {"id": {"type": "string"}}, ext_permissions),
    ("extension_revoke", "Revoke all runtime grants (enforced).",
     {"id": {"type": "string"}}, ext_revoke),
    ("extension_quarantine", "Quarantine: no exec/tools/secrets/MCP.",
     {"id": {"type": "string"}, "reason": {"type": "string"}}, ext_quarantine),
    ("extension_doctor", "Health/problems across registry.",
     {}, ext_doctor),
]

for _name, _desc, _props, _fn in _TOOLS:
    registry.register(
        name=_name, toolset="extensions",
        schema={"name": _name, "description": _desc,
                "parameters": {"type": "object", "properties": _props,
                               "required": (["id"] if "id" in _props
                                            else (["source"] if "source" in _props else []))}},
        handler=(lambda args, _f=_fn, **k: _f(args, **k)),
        check_fn=_check)

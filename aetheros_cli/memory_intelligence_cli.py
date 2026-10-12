"""``aetheros memory-intelligence`` CLI handler.

Thin command layer over the fabric facade.  All reads/writes go through
``MemoryIntelligence`` so boundary enforcement + auditing are always active.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from aetheros_cli.config import load_config
from aetheros_memory_intelligence.boundaries import AccessContext
from aetheros_memory_intelligence.config import load_config as load_fabric_config
from aetheros_memory_intelligence.manager import MemoryIntelligence


def _get_intelligence() -> Optional[MemoryIntelligence]:
    """Build (and initialize) the fabric from the merged user config."""
    cfg = load_config()
    fabric_cfg = load_fabric_config(cfg)
    mi = MemoryIntelligence(fabric_cfg)
    try:
        mi.initialize()
    except Exception as exc:  # pragma: no cover - defensive
        _err(f"failed to initialize memory intelligence: {exc}")
        return None
    return mi


def _ok(msg: str) -> None:
    print(f"  \033[32mOK\033[0m  {msg}")


def _err(msg: str) -> None:
    print(f"  \033[31mERR\033[0m  {msg}")


def _actor(args: Any) -> AccessContext:
    return AccessContext(
        user_id=getattr(args, "user", "") or "",
        workspace_id=getattr(args, "workspace", "") or "",
        session_id=getattr(args, "session", "") or "",
        agent_id=getattr(args, "agent", "") or "",
    )


def _cmd_status(args: Any) -> int:
    mi = _get_intelligence()
    if mi is None:
        return 1
    status = mi.status()
    print("Memory Intelligence Fabric")
    print(f"  store:        {status['store']['entry_count']} entries "
          f"(quarantined={status['store']['quarantined']})")
    print(f"  by_type:      {json.dumps(status['store']['by_type'])}")
    print(f"  by_boundary:  {json.dumps(status['store']['by_boundary'])}")
    print(f"  by_state:     {json.dumps(status['store']['by_state'])}")
    print(f"  audit:        {status['audit']['entries']} records "
          f"(chain_valid={status['audit']['chain_valid']})")
    print(f"  cache:        {status['cache']['entries']} entries "
          f"({status['cache']['total_hits']} hits)")
    print(f"  conflicts:    {status['conflicts']}")
    print(f"  audit_enabled:{mi.config.audit_enabled}")
    return 0


def _cmd_recall(args: Any) -> int:
    mi = _get_intelligence()
    if mi is None:
        return 1
    actor = _actor(args)
    top_k = getattr(args, "top_k", 0) or None
    result = mi.recall(args.query, actor, top_k=top_k, use_cache=False)
    print(f"Query: {args.query}")
    print(f"Found: {result.total_found}  (eligible={result.total_eligible}, "
          f"filtered_by_boundary={result.total_filtered_by_boundary})")
    for m in result.memories:
        print(f"  [{m.score:0.3f} trust={m.trust:0.2f} conf={m.confidence:0.2f}] "
              f"({m.entry.memory_type.value}/{m.entry.boundary.value})")
        print(f"    {m.text[:140]}")
    if not result.memories:
        print("  (nothing above the grounding threshold)")
    return 0


def _cmd_integrity(args: Any) -> int:
    mi = _get_intelligence()
    if mi is None:
        return 1
    report = mi.integrity_check()
    print(f"checked={report['checked']} corrupted={report['corrupted']} "
          f"quarantined={report['quarantined']} audit_chain_valid={report['audit_chain_valid']}")
    return 0 if report["corrupted"] == 0 and report["audit_chain_valid"] else 1


def _cmd_audit(args: Any) -> int:
    mi = _get_intelligence()
    if mi is None:
        return 1
    if getattr(args, "verify", False):
        valid = mi.audit.verify_chain()
        print(f"audit chain: {'VALID' if valid else 'TAMPERED'}")
        return 0 if valid else 1
    entries = mi.audit.entries(operation=getattr(args, "operation", "") or "",
                               limit=getattr(args, "limit", 50) or 50)
    for e in entries:
        print(f"  {e.get('ts', 0):.0f}  {e.get('operation', '?'):<12} "
              f"entry={e.get('entry_id', '')[:8]} actor={e.get('actor', '')}")
    print(f"({len(entries)} entries)")
    return 0


def _cmd_export(args: Any) -> int:
    mi = _get_intelligence()
    if mi is None:
        return 1
    result = mi.export(Path(args.destination),
                       include_archived=getattr(args, "include_archived", False))
    _ok(f"exported {result.entry_count} entries to {result.path} "
        f"(checksum={result.checksum[:12]}...)")
    return 0


def _cmd_import(args: Any) -> int:
    mi = _get_intelligence()
    if mi is None:
        return 1
    report = mi.import_bundle(Path(args.source))
    print(f"imported={report.imported} rejected={report.rejected}")
    for reason in report.rejected_reasons[:10]:
        print(f"  rejected: {reason}")
    return 0 if report.rejected == 0 else 1


def _cmd_retention(args: Any) -> int:
    mi = _get_intelligence()
    if mi is None:
        return 1
    actor = AccessContext(
        user_id=getattr(args, "user", "") or "",
        workspace_id=getattr(args, "workspace", "") or "",
    )
    result = mi.run_retention(actor)
    _ok(f"purged={result['purged']} archived={result['archived']}")
    return 0


def _cmd_backup(args: Any) -> int:
    mi = _get_intelligence()
    if mi is None:
        return 1
    result = mi.fabric_backup(Path(args.destination))
    _ok(f"backup with {result.entry_count} entries at {result.path}")
    return 0


def _cmd_restore(args: Any) -> int:
    mi = _get_intelligence()
    if mi is None:
        return 1
    report = mi.fabric_restore(Path(args.source))
    print(f"restored={report['restored']} rejected={report['rejected']}")
    return 0 if report["rejected"] == 0 else 1


def memory_intelligence_command(args: Any) -> int:
    """Dispatch ``aetheros memory-intelligence <verb>``."""
    cmd = getattr(args, "memory_intelligence_command", None) or "status"
    handlers = {
        "status": _cmd_status,
        "recall": _cmd_recall,
        "integrity": _cmd_integrity,
        "audit": _cmd_audit,
        "export": _cmd_export,
        "import": _cmd_import,
        "retention": _cmd_retention,
        "backup": _cmd_backup,
        "restore": _cmd_restore,
    }
    handler = handlers.get(cmd)
    if handler is None:
        _err(f"unknown memory-intelligence command: {cmd}")
        return 1
    return handler(args)
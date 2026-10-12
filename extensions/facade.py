"""Universal capability facade (Master 12, Phases 1–6).

Read-only projection of the four production capability families —

    * core tools   (``tools/registry.py``  — canonical for execution)
    * skills       (``SKILL.md`` trees)
    * plugins      (``plugin.yaml`` directories)
    * MCP servers  (``mcp_servers`` config entries)

— into a single queryable model. This module never registers, mutates,
or executes capabilities; discovery here implies nothing about trust.

Stable identifiers (Phase 3) use namespaced IDs:

    aetheros.tool.<name>          built-in / core tools
    <provider>.tool.<name>        foreign-provider registry entries (e.g. mcp)
    aetheros.skill.<name>
    aetheros.plugin.<name>
    aetheros.mcp.<server>

Every record carries its historical raw name in ``aliases`` so existing
lookups keep resolving (alias-map rollout; no re-registration anywhere).
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CapabilityType(str, Enum):
    TOOL = "tool"
    SKILL = "skill"
    PLUGIN = "plugin"
    MCP_SERVER = "mcp_server"
    MCP_TOOL = "mcp_tool"
    API = "api"
    CLI = "cli"
    CONNECTOR = "connector"
    WORKFLOW = "workflow"


class TrustState(str, Enum):
    """Phase 39 trust ladder. Popularity is not trust."""

    UNKNOWN = "unknown"
    UNTRUSTED = "untrusted"
    REVIEW_REQUIRED = "review_required"
    TRUSTED = "trusted"
    BLOCKED = "blocked"
    QUARANTINED = "quarantined"


class HealthState(str, Enum):
    """Phase 19 lifecycle health (Phase 77 adds reachability flavor)."""

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    DISABLED = "disabled"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class CapabilityRecord:
    """One projected capability (Phase 1 universal model)."""

    capability_id: str
    name: str
    type: CapabilityType
    provider: str = "aetheros"
    version: str = ""
    description: str = ""
    installation_source: str = "bundled"  # bundled|config|user|project|pip|hub:<src>
    trust_state: TrustState = TrustState.UNKNOWN
    health: HealthState = HealthState.UNKNOWN
    availability: bool = False
    permissions: tuple = ()
    risk_level: str = "UNKNOWN"
    platform_support: tuple = ()
    aliases: tuple = ()
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    def matches_text(self, query: str) -> bool:
        q = query.strip().lower()
        if not q:
            return True
        haystack = " ".join(
            (
                self.capability_id,
                self.name,
                self.description,
                self.provider,
                self.type.value,
            )
        ).lower()
        return q in haystack


def capability_id_for(cap_type: CapabilityType, provider: str, name: str) -> str:
    provider = (provider or "aetheros").strip().lower()
    if cap_type is CapabilityType.MCP_SERVER:
        return f"aetheros.mcp.{name}"
    if provider in ("aetheros", ""):
        return f"aetheros.{cap_type.value}.{name}"
    return f"{provider}.{cap_type.value}.{name}"


# ---------------------------------------------------------------------------
# Adapters (lazy imports — importing this module must stay cheap)
# ---------------------------------------------------------------------------


def _tool_capabilities() -> List[CapabilityRecord]:
    from tools.registry import discover_builtin_tools, registry

    try:
        # Idempotent; ensures the registry is populated even when the
        # facade is queried before model_tools has been imported.
        discover_builtin_tools()
    except Exception as e:
        logger.debug("builtin tool discovery failed: %s", e)

    records: List[CapabilityRecord] = []
    # Snapshot: get_tool_info()/get_tool_health() below may lazily import
    # modules that register additional tools, mutating the dict.
    entries = sorted((getattr(registry, "_tools", {}) or {}).items())
    for name, entry in entries:
        provider = (getattr(entry, "provider", "") or "aetheros").lower()
        cap_type = CapabilityType.MCP_TOOL if provider == "mcp" else CapabilityType.TOOL
        health = HealthState.UNKNOWN
        availability = False
        try:
            info = registry.get_tool_info(name) or {}
            availability = bool(info.get("available", False))
        except Exception:
            info = {}
        try:
            h = registry.get_tool_health(name) or {}
            status = str(h.get("status", "unknown"))
            health = (
                HealthState.HEALTHY
                if status == "healthy"
                else HealthState.DEGRADED
                if status == "degraded"
                else HealthState.OFFLINE
                if status == "unhealthy"
                else HealthState.UNKNOWN
            )
        except Exception:
            pass
        schema = getattr(entry, "schema", None) or {}
        records.append(
            CapabilityRecord(
                capability_id=capability_id_for(cap_type, provider, name),
                name=name,
                type=cap_type,
                provider=provider,
                description=str(schema.get("description", ""))[:200],
                installation_source="bundled" if provider == "aetheros" else f"provider:{provider}",
                trust_state=TrustState.TRUSTED if provider == "aetheros" else TrustState.REVIEW_REQUIRED,
                health=health,
                availability=availability,
                aliases=(name,),
                metadata={
                    "toolset": getattr(entry, "toolset", ""),
                    "requires_env": tuple(getattr(entry, "requires_env", ()) or ()),
                    "input_schema": schema.get("parameters", {}),
                    "output_schema": getattr(entry, "output_schema", None),
                    # Registration-time contract check (Phase 7).
                    "schema_valid": bool(getattr(entry, "_schema_valid", False)),
                },
            )
        )
    return records


def _skill_capabilities() -> List[CapabilityRecord]:
    from pathlib import Path

    try:
        from agent.skill_utils import get_all_skills_dirs, parse_frontmatter
    except Exception as e:  # pragma: no cover - optional surface
        logger.debug("skill adapter unavailable: %s", e)
        return []

    repo_root = str(Path(__file__).resolve().parent.parent)

    records: List[CapabilityRecord] = []
    repo_root = Path(__file__).resolve().parent.parent
    # get_all_skills_dirs() is home-scoped (installed/user skills); the
    # repo-shipped trees live alongside this package and are always visible.
    roots = list(get_all_skills_dirs() or []) + [
        repo_root / "skills",
        repo_root / "optional-skills",
    ]
    repo_root_str = str(repo_root)
    seen_dirs = set()
    for skills_root in roots:
        try:
            root = str(skills_root)
        except Exception:
            continue
        if root in seen_dirs:
            continue
        seen_dirs.add(root)
        try:
            candidates = sorted(skills_root.glob("*/SKILL.md")) + sorted(
                skills_root.glob("SKILL.md")
            )
        except Exception:
            continue
        for skill_md in candidates:
            try:
                frontmatter, _body = parse_frontmatter(
                    skill_md.read_text(encoding="utf-8")
                )
            except Exception:
                continue
            meta = frontmatter or {}
            name = str(meta.get("name") or skill_md.parent.name)
            version = str(meta.get("version") or "")
            platforms = tuple(meta.get("platforms") or ())
            records.append(
                CapabilityRecord(
                    capability_id=capability_id_for(CapabilityType.SKILL, "aetheros", name),
                    name=name,
                    type=CapabilityType.SKILL,
                    description=str(meta.get("description") or "")[:200],
                    installation_source=root,
                    # Repo-shipped trees are reviewed content; anything under
                    # the user's AETHEROS_HOME stays unproven until scanned.
                    trust_state=(
                        TrustState.TRUSTED
                        if str(skill_md).startswith(repo_root_str)
                        else TrustState.REVIEW_REQUIRED
                    ),
                    platform_support=platforms,
                    aliases=(name,),
                    metadata={"path": str(skill_md), "version": version},
                )
            )
    return records


def _plugin_capabilities() -> List[CapabilityRecord]:
    """Project plugin.yaml manifests without loading plugin code."""
    from pathlib import Path

    from aetheros_constants import get_aetheros_home

    roots = []
    bundled = Path(__file__).resolve().parent.parent / "plugins"
    roots.append((bundled, "bundled", TrustState.TRUSTED))
    roots.append((get_aetheros_home() / "plugins", "user", TrustState.UNKNOWN))

    records: List[CapabilityRecord] = []
    seen_names = set()
    try:
        import yaml
    except ImportError:  # pragma: no cover
        yaml = None

    for base, source, trust in roots:
        if not base.is_dir():
            continue
        for manifest_path in sorted(base.glob("*/plugin.yaml")):
            data: Dict[str, Any] = {}
            if yaml is not None:
                try:
                    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
                except Exception:
                    data = {}
            name = str(data.get("name") or manifest_path.parent.name)
            if name in seen_names:
                continue  # later sources override earlier, mirroring loader order
            seen_names.add(name)
            records.append(
                CapabilityRecord(
                    capability_id=capability_id_for(CapabilityType.PLUGIN, "aetheros", name),
                    name=name,
                    type=CapabilityType.PLUGIN,
                    description=str(data.get("description") or "")[:200],
                    installation_source=source,
                    trust_state=trust,
                    version=str(data.get("version") or ""),
                    permissions=tuple(data.get("permissions") or ()),
                    aliases=(name,),
                    metadata={"manifest": str(manifest_path)},
                )
            )
    return records


def _mcp_server_capabilities() -> List[CapabilityRecord]:
    try:
        from aetheros_cli.config import read_raw_config

        servers = (read_raw_config() or {}).get("mcp_servers") or {}
    except Exception as e:  # pragma: no cover - config-free environments
        logger.debug("mcp adapter unavailable: %s", e)
        return []

    records: List[CapabilityRecord] = []
    if isinstance(servers, dict):
        for server_name, cfg in servers.items():
            cfg = cfg if isinstance(cfg, dict) else {}
            transport = str(cfg.get("transport") or ("stdio" if cfg.get("command") else "http"))
            records.append(
                CapabilityRecord(
                    capability_id=capability_id_for(CapabilityType.MCP_SERVER, "mcp", server_name),
                    name=str(server_name),
                    type=CapabilityType.MCP_SERVER,
                    provider="mcp",
                    description=str(cfg.get("description") or "")[:200],
                    installation_source="config",
                    # Configured ≠ trusted: remote services are separate
                    # trust boundaries until policy says otherwise.
                    trust_state=TrustState.REVIEW_REQUIRED,
                    aliases=(str(server_name),),
                    metadata={
                        "transport": transport,
                        "url": cfg.get("url", ""),
                        "command": cfg.get("command", ""),
                    },
                )
            )
    return records


# ---------------------------------------------------------------------------
# Public query surface (Phases 2, 5, 6)
# ---------------------------------------------------------------------------

_ADAPTERS = (
    _tool_capabilities,
    _skill_capabilities,
    _plugin_capabilities,
    _mcp_server_capabilities,
)


def all_capabilities() -> List[CapabilityRecord]:
    records: List[CapabilityRecord] = []
    for adapter in _ADAPTERS:
        try:
            records.extend(adapter())
        except Exception as e:
            logger.debug("capability adapter %r failed: %s", adapter.__name__, e)
    return records


def find(
    query: str = "",
    *,
    cap_type: Optional[CapabilityType] = None,
    provider: Optional[str] = None,
    risk_level: Optional[str] = None,
    name_glob: Optional[str] = None,
) -> List[CapabilityRecord]:
    """Filter capabilities (Phase 5 search). All filters AND-composed."""
    out: List[CapabilityRecord] = []
    for rec in all_capabilities():
        if cap_type is not None and rec.type is not cap_type:
            continue
        if provider is not None and rec.provider != provider.lower():
            continue
        if risk_level is not None and rec.risk_level != risk_level.upper():
            continue
        if name_glob is not None and not fnmatch.fnmatch(rec.name, name_glob):
            continue
        if query and not rec.matches_text(query):
            continue
        out.append(rec)
    return out


def resolve_capability(identifier: str) -> Optional[CapabilityRecord]:
    """Resolve a stable ID **or** a legacy raw name/alias (Phase 3 map)."""
    if not identifier:
        return None
    ident = identifier.strip()
    for rec in all_capabilities():
        if rec.capability_id == ident or ident in rec.aliases or rec.name == ident:
            return rec
    return None


def ecosystem_summary() -> Dict[str, int]:
    """Coarse counts per family — cheap observability hook (Phase 74)."""
    counts: Dict[str, int] = {}
    for rec in all_capabilities():
        counts[rec.type.value] = counts.get(rec.type.value, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Health + requirement surfaces (Phases 6, 19–20, 77)
# ---------------------------------------------------------------------------


def _reachability(rec: CapabilityRecord) -> str:
    """Phase 77 flavor: LOCAL vs REMOTE vs OFFLINE/DEGRADED derivation."""
    if rec.type is CapabilityType.MCP_SERVER:
        return "REMOTE"
    if rec.type is CapabilityType.TOOL and rec.provider not in ("aetheros", ""):
        return "REMOTE"
    if rec.health in (HealthState.OFFLINE, HealthState.QUARANTINED):
        return "OFFLINE"
    if rec.health is HealthState.DEGRADED or not rec.availability:
        return "DEGRADED"
    return "LOCAL"


def health_report() -> Dict[str, Any]:
    """Aggregate health across every projected capability (Phases 19–20).

    Safe and bounded: reads registry counters/config only; performs no
    network probes and executes nothing.
    """
    import time as _time

    capabilities = all_capabilities()
    rows = []
    counts: Dict[str, int] = {}
    for rec in capabilities:
        reach = _reachability(rec)
        row = {
            "capability_id": rec.capability_id,
            "type": rec.type.value,
            "availability": rec.availability,
            "health": rec.health.value,
            "reachability": reach,
            "trust_state": rec.trust_state.value,
        }
        rows.append(row)
        key = f"{rec.type.value}:{rec.health.value}"
        counts[key] = counts.get(key, 0) + 1
    return {
        "generated_at": _time.time(),
        "total": len(rows),
        "counts": counts,
        "capabilities": rows,
    }


def skill_requirement_conflicts(meta: Dict[str, Any]) -> List[str]:
    """Detect unmet tool/toolset requirements declared by a skill (Phase 49-lite).

    ``meta`` is SKILL.md frontmatter (or the ``metadata.aetheros`` subtree).
    Checks ``requires_tools`` against registered tools and
    ``requires_toolsets`` against known toolsets. Read-only.
    """
    problems: List[str] = []
    from tools.registry import discover_builtin_tools, registry

    try:
        discover_builtin_tools()
    except Exception as e:
        logger.debug("discovery failed during conflict check: %s", e)

    known_tools = set((getattr(registry, "_tools", {}) or {}).keys())
    for tool_name in (meta.get("requires_tools") or []):
        if str(tool_name) not in known_tools:
            problems.append(f"missing tool: {tool_name}")

    try:
        from toolsets import get_all_toolsets

        known_toolsets = set(get_all_toolsets() or [])
    except Exception:
        known_toolsets = set()
    for ts_name in (meta.get("requires_toolsets") or []):
        if str(ts_name) not in known_toolsets:
            problems.append(f"missing toolset: {ts_name}")

    # Alias targets must resolve too — a dangling alias is a conflict.
    aliases = getattr(registry, "_toolset_aliases", {}) or {}
    for ts_name in (meta.get("requires_toolsets") or []):
        target = aliases.get(str(ts_name))
        if target is not None and target not in known_toolsets:
            problems.append(f"dangling toolset alias: {ts_name} -> {target}")

    return problems

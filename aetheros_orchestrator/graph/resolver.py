from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SubsystemDef:
    name: str
    deps: list[str] = field(default_factory=list)
    optional_deps: list[str] = field(default_factory=list)
    config: dict = field(default_factory=dict)
    enabled: bool = True


@dataclass
class ResolutionResult:
    order: list[str]
    cycles: list[list[str]] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    omitted: list[str] = field(default_factory=list)


BUILTIN_SUBSYSTEMS: dict[str, SubsystemDef] = {
    "logging": SubsystemDef("logging"),
    "config": SubsystemDef("config"),
    "bus": SubsystemDef("bus"),
    "mcp": SubsystemDef("mcp", deps=["logging", "config"]),
    "reasoning": SubsystemDef("reasoning", deps=["logging", "config", "mcp"]),
    "skills": SubsystemDef("skills", deps=["logging", "config"]),
    "platform": SubsystemDef("platform", deps=["logging", "config"]),
    "knowledge": SubsystemDef("knowledge", deps=["logging", "config", "platform"], optional_deps=["mcp"]),
    "ui": SubsystemDef("ui", deps=["logging", "config", "bus"]),
    "desktop": SubsystemDef("desktop", deps=["logging", "config", "bus", "api"]),
    "api": SubsystemDef("api", deps=["bus", "logging", "config"], optional_deps=["knowledge"]),
    "daemon": SubsystemDef("daemon", deps=["api", "bus", "logging", "config"]),
}


class DependencyGraph:
    def __init__(self, subsystems: dict[str, SubsystemDef] | None = None):
        self._subsystems = subsystems or BUILTIN_SUBSYSTEMS.copy()

    def resolve(self, enabled_subsystems: set[str] | None = None) -> ResolutionResult:
        if enabled_subsystems is None:
            enabled_subsystems = {n for n, s in self._subsystems.items() if s.enabled}

        adj: dict[str, list[str]] = {}
        for name, sub in self._subsystems.items():
            adj[name] = sub.deps[:]

        cycles = self._find_cycles(adj)
        unvisited = {n for n in enabled_subsystems if n in self._subsystems}
        order: list[str] = []

        while unvisited:
            batch = {n for n in unvisited if all(d not in unvisited for d in adj.get(n, []))}
            if not batch:
                break
            order.extend(sorted(batch))
            unvisited -= batch

        missing = [n for n in enabled_subsystems if n not in self._subsystems]
        omitted = sorted(unvisited)

        return ResolutionResult(order=order, cycles=cycles, missing=missing, omitted=omitted)

    def _find_cycles(self, adj: dict[str, list[str]]) -> list[list[str]]:
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {n: WHITE for n in adj}
        parent: dict[str, str | None] = {}
        cycles: list[list[str]] = []

        def dfs(u: str):
            color[u] = GRAY
            for v in adj.get(u, []):
                if v not in color:
                    continue
                if color[v] == GRAY:
                    cycle: list[str] = [v, u]
                    p = parent.get(u)
                    while p is not None and p != v:
                        cycle.append(p)
                        p = parent.get(p)
                    if p == v:
                        cycle.append(v)
                    cycle.reverse()
                    cycles.append(cycle)
                elif color[v] == WHITE:
                    parent[v] = u
                    dfs(v)
            color[u] = BLACK

        for n in adj:
            if color[n] == WHITE:
                dfs(n)
        return cycles

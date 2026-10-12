"""Digital twins (Phase K, §54-63, §141): state-backed simulacra for
repository / browser / automation / swarm / A2A / MCP. Twins answer
'what would happen if...?' WITHOUT touching the real environment.
Repository twin performs real filesystem simulation on an overlay copy.
Mock execution is always labeled mock — never equal to real (§63).
"""

from __future__ import annotations

import copy
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .models import TwinMode


class DigitalTwin:
    kind = "base"

    def __init__(self, mode: str = TwinMode.SIMULATION.value):
        self.mode = mode
        self.fidelity_notes: List[str] = []

    def snapshot_state(self) -> Dict[str, Any]:
        raise NotImplementedError

    def apply_simulated(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Simulated effect; MUST NOT touch real environment unless mode
        is CONTROLLED_EXECUTION (explicit opt-in)."""
        raise NotImplementedError

    def diff(self, real: Dict[str, Any]) -> Dict[str, Any]:
        return {"twin": self.snapshot_state(), "real": real,
                "note": "twin is a PREDICTION aid, reality is authoritative"}


class RepositoryTwin(DigitalTwin):
    """§57-58: files/deps/imports/tests/build/git state; dependency +
    test impact simulated on an overlay copy (§58)."""
    kind = "repository"

    def __init__(self, root: Path,
                 mode: str = TwinMode.SIMULATION.value):
        super().__init__(mode)
        self.root = Path(root)
        self.overlay = Path(tempfile.mkdtemp(prefix="twin_repo_"))
        self._sync()

    def _sync(self) -> None:
        if self.overlay.exists():
            shutil.rmtree(self.overlay, ignore_errors=True)
        shutil.copytree(self.root, self.overlay,
                        ignore=shutil.ignore_patterns(".git", "__pycache__",
                                                      ".venv", "node_modules"))

    def snapshot_state(self) -> Dict[str, Any]:
        files = [str(p.relative_to(self.overlay))
                 for p in self.overlay.rglob("*") if p.is_file()][:500]
        return {"root": str(self.root), "files": len(files),
                "sample": files[:20]}

    def apply_simulated(self, action: Dict[str, Any]) -> Dict[str, Any]:
        typ = action.get("type")
        params = action.get("parameters", {})
        if typ == "write_file":
            target = self.overlay / params.get("path", "sim_out.txt")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(params.get("content", ""),
                              encoding="utf-8")
            return {"simulated": True, "wrote": str(
                target.relative_to(self.overlay))}
        if typ == "delete_file":
            target = self.overlay / params.get("path", "")
            existed = target.exists()
            if existed:
                target.unlink()
            return {"simulated": True, "deleted": existed}
        if typ == "impact_analysis":
            changed = set(params.get("changed", []))
            dependents = [f for f in changed]  # conservative: direct set
            return {"simulated": True, "changed": sorted(changed),
                    "direct_dependents": dependents,
                    "note": "static filename-level; not a real build"}
        return {"simulated": False,
                "reason": f"unsupported action {typ}"}


class BrowserTwin(DigitalTwin):
    """§59: tabs/DOM-a11y snapshot summary, nav/form state, transitions."""
    kind = "browser"

    def __init__(self, mode: str = TwinMode.SIMULATION.value):
        super().__init__(mode)
        self.tabs: Dict[str, Dict[str, Any]] = {}
        self.current: Optional[str] = None

    def open_tab(self, tab_id: str, url: str) -> None:
        self.tabs[tab_id] = {"url": url, "forms": {}, "history": [url]}
        self.current = tab_id

    def snapshot_state(self) -> Dict[str, Any]:
        return {"tabs": copy.deepcopy(self.tabs), "current": self.current}

    def apply_simulated(self, action: Dict[str, Any]) -> Dict[str, Any]:
        typ = action.get("type")
        params = action.get("parameters", {})
        tab = self.tabs.get(params.get("tab", self.current or ""))
        if tab is None:
            return {"simulated": False,
                    "reason": "unknown tab — cannot predict"}
        if typ == "navigate":
            url = params.get("url", "")
            tab["history"].append(url)
            tab["url"] = url
            return {"simulated": True, "url": url,
                    "redirects_predicted": "unknown — verify live (§108)"}
        if typ == "fill_form":
            tab["forms"][params.get("field", "?")] = "[value]"
            return {"simulated": True, "forms": dict(tab["forms"])}
        return {"simulated": False, "reason": f"unsupported {typ}"}


class AutomationTwin(DigitalTwin):
    """§60/§114: trigger/workflow dry-run without side effects."""
    kind = "automation"

    def __init__(self, workflow: Optional[Dict[str, Any]] = None,
                 mode: str = TwinMode.SIMULATION.value):
        super().__init__(mode)
        self.workflow = workflow or {"steps": []}

    def snapshot_state(self) -> Dict[str, Any]:
        return copy.deepcopy(self.workflow)

    def apply_simulated(self, action: Dict[str, Any]) -> Dict[str, Any]:
        if action.get("type") == "dry_run":
            steps = self.workflow.get("steps", [])
            trace = [{"step": s, "would_run": True} for s in steps]
            return {"simulated": True, "dry_run": trace,
                    "side_effects": "none — dry run only"}
        return {"simulated": False, "reason": "unsupported"}


class SwarmTwin(DigitalTwin):
    """§61/§115: assignment/parallelism/handoff/conflict/cost estimates."""
    kind = "swarm"

    def snapshot_state(self) -> Dict[str, Any]:
        return {"agents": [], "note": "configure via plan()"}

    def plan(self, tasks: List[str], agents: int,
             handoff_cost_ms: float = 50.0,
             conflict_p: float = 0.05) -> Dict[str, Any]:
        import math
        parallel = max(1, agents)
        waves = math.ceil(len(tasks) / parallel)
        return {"simulated": True, "agents": agents,
                "waves": waves,
                "expected_handoffs": max(0, len(tasks) - 1),
                "handoff_overhead_ms": (max(0, len(tasks) - 1)
                                        * handoff_cost_ms),
                "conflict_risk": round(1 - (1 - conflict_p) ** len(tasks),
                                       4),
                "note": "estimate from counts, not a real swarm run"}


class A2ATwin(DigitalTwin):
    """§62/§116: reliability/latency/capability from verified history."""
    kind = "a2a"

    def __init__(self, history: Optional[List[Dict]] = None,
                 mode: str = TwinMode.SIMULATION.value):
        super().__init__(mode)
        self.history = history or []

    def snapshot_state(self) -> Dict[str, Any]:
        return {"samples": len(self.history)}

    def predict_peer(self) -> Dict[str, Any]:
        if not self.history:
            return {"simulated": True, "reliability": None,
                    "reason": "I don't know — no verified history (§0.6)"}
        ok = sum(1 for h in self.history if h.get("ok"))
        lat = [h.get("latency_ms", 0) for h in self.history]
        return {"simulated": True,
                "reliability": ok / len(self.history),
                "mean_latency_ms": sum(lat) / len(lat),
                "n": len(self.history),
                "note": "historical frequencies, not guarantees"}


class MCPTwin(DigitalTwin):
    """§63: deterministic mocks where registered; else UNAVAILABLE."""
    kind = "mcp"

    def __init__(self, mocks: Optional[Dict[str, Callable]] = None,
                 mode: str = TwinMode.SIMULATION.value):
        super().__init__(mode)
        self.mocks = mocks or {}

    def snapshot_state(self) -> Dict[str, Any]:
        return {"mocked_tools": sorted(self.mocks)}

    def apply_simulated(self, action: Dict[str, Any]) -> Dict[str, Any]:
        tool = action.get("tool", action.get("type", ""))
        fn = self.mocks.get(tool)
        if fn is None:
            return {"simulated": False,
                    "reason": "SIMULATION_UNAVAILABLE — no mock; "
                              "mock execution never equals real MCP (§63)"}
        return {"simulated": True, "mock_result": fn(
            action.get("parameters", {}))}

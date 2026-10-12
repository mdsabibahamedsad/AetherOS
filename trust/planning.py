"""Physical Task Planner (§55): decomposes objectives into DAG task graphs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WorkflowStep:
    """A step in a physical task workflow."""
    id: int
    step: str
    deps: List[int] = field(default_factory=list)


@dataclass
class PhysicalTaskPlan:
    """DAG of steps for a physical task."""
    objective: str = ""
    kind: str = ""
    dag: List[WorkflowStep] = field(default_factory=list)


class PhysicalTaskPlanner:
    """Decomposes objectives into DAG task graphs (§55)."""

    TEMPLATES = {
        "move_object": ["observe", "locate_object", "locate_destination",
                        "verify_path", "check_robot", "simulate",
                        "plan_grasp", "plan_motion", "approve?",
                        "execute", "verify", "report"],
        "inspect": ["observe", "locate_target", "capture", "analyze",
                    "report"],
        "measure": ["observe", "locate_target", "calibrate_check",
                    "measure", "verify", "report"],
    }

    def plan(self, objective: str, kind: str = "move_object") -> PhysicalTaskPlan:
        steps = self.TEMPLATES.get(kind, self.TEMPLATES["inspect"])
        return PhysicalTaskPlan(
            objective=objective,
            kind=kind,
            dag=[{"id": i, "step": s, "deps": [i - 1] if i else []}
                 for i, s in enumerate(steps)])
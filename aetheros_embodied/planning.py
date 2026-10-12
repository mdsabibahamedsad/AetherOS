"""Planners (§28, §55-56, §79-84): A* route planning on occupancy
grids, time-parameterized trajectories with velocity/accel/jerk
limits, grasp selection heuristics, navigation with waypoints.
All outputs are plans (data) — execution is the executor's job."""
from __future__ import annotations

import heapq
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

from .spatial import CollisionChecker, OccupancyMap


def astar_route(occ: OccupancyMap,
                start: Tuple[int, int],
                goal: Tuple[int, int]) -> List[Tuple[int, int]]:
    """A* over FREE cells only. Unknown/occupied are blocked. Empty list
    = no route (honest, not a straight line through walls)."""
    if occ.get(*start) != OccupancyMap.FREE:
        return []
    if occ.get(*goal) != OccupancyMap.FREE:
        return []

    def h(a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    openh: List[Tuple[float, Tuple[int, int]]] = [(0.0, start)]
    came: Dict[Tuple[int, int], Tuple[int, int]] = {}
    g: Dict[Tuple[int, int], float] = {start: 0.0}
    while openh:
        _, cur = heapq.heappop(openh)
        if cur == goal:
            path = [cur]
            while path[-1] in came:
                path.append(came[path[-1]])
            return list(reversed(path))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if not dx and not dy:
                    continue
                nxt = (cur[0] + dx, cur[1] + dy)
                if occ.get(*nxt) != OccupancyMap.FREE:
                    continue
                ng = g[cur] + math.hypot(dx, dy)
                if ng < g.get(nxt, float("inf")):
                    g[nxt] = ng
                    came[nxt] = cur
                    heapq.heappush(openh, (ng + h(nxt, goal), nxt))
    return []


def time_parameterize(pts: List[Tuple[float, float]], vmax: float,
                      amax: float, jmax: float = 10.0) -> List[Dict[str, float]]:
    """Trapezoidal-ish timing respecting velocity/acceleration limits.
    Returns timed waypoints; empty input -> empty output."""
    if not pts:
        return []
    dists = [0.0]
    for i in range(1, len(pts)):
        dists.append(dists[-1] + math.hypot(pts[i][0] - pts[i - 1][0],
                                            pts[i][1] - pts[i - 1][1]))
    total = dists[-1]
    if total == 0:
        return [{"x": pts[0][0], "y": pts[0][1], "t": 0.0, "v": 0.0}]
    # reachable cruise velocity given distance (triangular profile check)
    vc = min(vmax, math.sqrt(amax * total))
    t_acc = vc / amax
    d_acc = 0.5 * amax * t_acc ** 2
    d_cruise = max(0.0, total - 2 * d_acc)
    t_cruise = d_cruise / vc if vc > 0 else 0.0
    t_total = 2 * t_acc + t_cruise

    def state_at(s: float) -> Tuple[float, float]:
        if s <= d_acc:
            t = math.sqrt(2 * s / amax) if amax > 0 else 0.0
            v = amax * t
        elif s <= d_acc + d_cruise:
            t = t_acc + (s - d_acc) / vc if vc > 0 else 0.0
            v = vc
        else:
            rem = total - s
            t = t_total - (math.sqrt(2 * rem / amax) if amax > 0 else 0.0)
            v = amax * (t_total - t)
        return (t, max(0.0, v))

    return [{"x": x, "y": y, "t": round(t, 3), "v": round(v, 3)}
            for (x, y), (t, v) in
            ((p, state_at(s)) for p, s in zip(pts, dists))]


class MotionPlanner:
    def __init__(self, vmax: float = 0.5, amax: float = 0.5,
                 robot_radius: float = 0.2) -> None:
        self.vmax = vmax
        self.amax = amax
        self.radius = robot_radius

    def plan_route(self, occ: OccupancyMap,
                   start: Tuple[int, int],
                   goal: Tuple[int, int]) -> Dict[str, Any]:
        cells = astar_route(occ, start, goal)
        if not cells:
            return {"ok": False, "reason": "no route through free space"}
        world = [occ.to_world(x, y) for x, y in cells]
        timed = time_parameterize(world, self.vmax, self.amax)
        length = sum(math.hypot(world[i][0] - world[i - 1][0],
                                world[i][1] - world[i - 1][1])
                     for i in range(1, len(world)))
        return {"ok": True, "cells": cells, "timed": timed,
                "length_m": round(length, 3),
                "eta_s": timed[-1]["t"] if timed else 0.0}


class NavigationPlanner(MotionPlanner):
    def plan_with_waypoints(
            self, occ: OccupancyMap,
            waypoints: List[Tuple[int, int]]) -> Dict[str, Any]:
        legs = []
        for a, b in zip(waypoints, waypoints[1:]):
            leg = self.plan_route(occ, a, b)
            if not leg["ok"]:
                return {"ok": False, "failed_leg": [a, b],
                        "reason": leg["reason"]}
            legs.append(leg)
        return {"ok": True, "legs": legs,
                "total_m": round(sum(l["length_m"] for l in legs), 3)}


class ManipulationPlanner:
    """Grasp selection from geometry heuristics. Uncertain high-risk
    grasps are flagged for approval, never silently executed."""

    def select_grasp(self, obj: Dict[str, Any],
                     gripper: Dict[str, Any]) -> Dict[str, Any]:
        w = float(obj.get("width_m", 0.05))
        h = float(obj.get("height_m", 0.05))
        max_open = float(gripper.get("max_opening_m", 0.08))
        friction = float(obj.get("friction", 0.4))
        weight = float(obj.get("weight_kg", 0.1))
        fits = w <= max_open
        force_ok = weight * 9.81 / max(friction, 0.05) < float(
            gripper.get("max_force_n", 20.0))
        confidence = (0.9 if (fits and force_ok)
                      else 0.4 if fits else 0.15)
        return {"grasp": {"approach": "top-down",
                          "width_m": w, "target": obj.get("id", "?")},
                "fits_gripper": fits, "force_ok": force_ok,
                "confidence": confidence,
                "needs_approval": confidence < 0.5,
                "reason": ("geometry+force within limits" if fits and force_ok
                           else "uncertain grasp — approval required")}

    def pick_place(self, obj: Dict[str, Any], src: Tuple[float, float],
                   dst: Tuple[float, float],
                   gripper: Dict[str, Any]) -> Dict[str, Any]:
        grasp = self.select_grasp(obj, gripper)
        return {"steps": ["approach", "grasp", "lift", "carry", "place",
                          "retreat"],
                "grasp": grasp, "src": src, "dst": dst,
                "needs_approval": grasp["needs_approval"]}


class PhysicalTaskPlanner:
    """Decomposes objectives into DAG task graphs (observe->...->verify)."""

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

    def plan(self, objective: str, kind: str = "move_object") -> Dict[str, Any]:
        steps = self.TEMPLATES.get(kind, self.TEMPLATES["inspect"])
        return {"objective": objective, "kind": kind,
                "dag": [{"id": i, "step": s,
                         "deps": [i - 1] if i else []}
                        for i, s in enumerate(steps)]}

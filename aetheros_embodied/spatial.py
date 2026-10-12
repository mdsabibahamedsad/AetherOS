"""Spatial intelligence (§14-18, §27): occupancy maps, A*-ready grids,
semantic zones, dead-reckoning localization, circle/AABB collision
checking. Real geometry, no invented obstacles."""
from __future__ import annotations

import heapq
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Zone:
    name: str
    kind: str  # KEEP_OUT|SLOW_ZONE|SAFE_ZONE|COLLABORATIVE|EMERGENCY|WORK
    bounds: Tuple[float, float, float, float]  # x0,y0,x1,y1
    speed_limit: float = 1.0


class OccupancyMap:
    """2D occupancy grid. Unknown cells are unknown — not free."""

    FREE, OCCUPIED, UNKNOWN = 0, 1, 2

    def __init__(self, width: int, height: int,
                 resolution_m: float = 0.1) -> None:
        self.w = width
        self.h = height
        self.res = resolution_m
        self.grid = [[self.UNKNOWN] * width for _ in range(height)]

    def set(self, x: int, y: int, v: int) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.grid[y][x] = v

    def get(self, x: int, y: int) -> int:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.grid[y][x]
        return self.OCCUPIED  # outside map = blocked (fail closed)

    def to_world(self, x: int, y: int) -> Tuple[float, float]:
        return (x * self.res, y * self.res)

    def to_grid(self, wx: float, wy: float) -> Tuple[int, int]:
        return (int(wx / self.res), int(wy / self.res))

    def stats(self) -> Dict[str, int]:
        flat = [c for row in self.grid for c in row]
        return {"free": flat.count(0), "occupied": flat.count(1),
                "unknown": flat.count(2)}


class SpatialWorldModel:
    def __init__(self) -> None:
        self.rooms: Dict[str, Dict[str, Any]] = {}
        self.zones: List[Zone] = []
        self.objects: Dict[str, Dict[str, Any]] = {}
        self.obstacles: List[Dict[str, Any]] = []

    def add_room(self, name: str, bounds: Tuple[float, float, float,
                                                float]) -> None:
        self.rooms[name] = {"bounds": bounds}

    def add_zone(self, zone: Zone) -> None:
        self.zones.append(zone)

    def zone_at(self, x: float, y: float) -> Optional[Zone]:
        for z in self.zones:
            x0, y0, x1, y1 = z.bounds
            if x0 <= x <= x1 and y0 <= y <= y1:
                return z
        return None

    def place_object(self, obj_id: str, x: float, y: float,
                     cls: str = "object", confidence: float = 1.0,
                     mode: str = "OBSERVED") -> None:
        self.objects[obj_id] = {"x": x, "y": y, "class": cls,
                                "confidence": confidence, "mode": mode,
                                "at": time.time()}

    def add_obstacle(self, x: float, y: float, r: float) -> None:
        self.obstacles.append({"x": x, "y": y, "r": r})


class MappingEngine:
    """Builds occupancy + semantic maps from observations only."""

    def __init__(self, width: int = 40, height: int = 40,
                 resolution_m: float = 0.1) -> None:
        self.occ = OccupancyMap(width, height, resolution_m)
        self.semantic: Dict[str, str] = {}

    def observe_free(self, cells: List[Tuple[int, int]]) -> None:
        for x, y in cells:
            if self.occ.get(x, y) == OccupancyMap.UNKNOWN:
                self.occ.set(x, y, OccupancyMap.FREE)

    def observe_obstacle(self, cells: List[Tuple[int, int]]) -> None:
        for x, y in cells:
            self.occ.set(x, y, OccupancyMap.OCCUPIED)

    def label(self, cell: Tuple[int, int], label: str) -> None:
        self.semantic[f"{cell[0]},{cell[1]}"] = label


class LocalizationEngine:
    """Dead-reckoning adapter core: integrates odometry deltas with
    growing uncertainty. Absolute fixes (fiducial/GPS) reset drift."""

    def __init__(self) -> None:
        self.x, self.y, self.theta = 0.0, 0.0, 0.0
        self.uncertainty = 0.0

    def odometry(self, dx: float, dy: float, dtheta: float,
                 noise: float = 0.01) -> Dict[str, float]:
        self.x += dx
        self.y += dy
        self.theta += dtheta
        self.uncertainty += noise
        return self.pose()

    def fix(self, x: float, y: float, theta: float,
            uncertainty: float = 0.01) -> Dict[str, float]:
        self.x, self.y, self.theta = x, y, theta
        self.uncertainty = uncertainty
        return self.pose()

    def pose(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "theta": self.theta,
                "uncertainty": self.uncertainty}


class CollisionChecker:
    """Circle-vs-circle (2D) and AABB checks against known obstacles."""

    @staticmethod
    def circle_hits(x: float, y: float, r: float,
                    obstacles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        hits = []
        for o in obstacles:
            d = math.hypot(x - o["x"], y - o["y"])
            if d < r + o.get("r", 0.0):
                hits.append(o)
        return hits

    @staticmethod
    def path_clear(pts: List[Tuple[float, float]], r: float,
                   obstacles: List[Dict[str, Any]]) -> Dict[str, Any]:
        for i, (x, y) in enumerate(pts):
            hits = CollisionChecker.circle_hits(x, y, r, obstacles)
            if hits:
                return {"clear": False, "at_index": i, "hits": hits}
        return {"clear": True, "at_index": -1, "hits": []}

    @staticmethod
    def aabb_overlap(a: Tuple[float, ...],
                     b: Tuple[float, ...]) -> bool:
        # (x0,y0,z0,x1,y1,z1)
        return not (a[3] < b[0] or b[3] < a[0] or a[4] < b[1]
                    or b[4] < a[1] or a[5] < b[2] or b[5] < a[2])

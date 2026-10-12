"""Coordinate frames + SE(3)-lite transforms (§15-16).

Frames: world | room | robot | camera | sensor | tool | object.
Transforms are explicit (translation + unit quaternion); frames are
never mixed silently — every point carries its frame and a timestamp.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Frame:
    name: str
    parent: str = "world"
    confidence: float = 1.0
    updated_at: float = field(default_factory=time.time)


@dataclass
class Transform:
    """Rigid transform parent <- child: p_parent = R(q) p_child + t."""
    src: str  # child frame
    dst: str  # parent frame
    translation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    quaternion: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        x, y, z, w = self.quaternion
        n = math.sqrt(x * x + y * y + z * z + w * w)
        if n == 0:
            raise ValueError("zero quaternion")
        self.quaternion = (x / n, y / n, z / n, w / n)


def _rot(q: Tuple[float, float, float, float],
         p: Tuple[float, float, float]) -> Tuple[float, float, float]:
    x, y, z, w = q
    # rotation matrix from unit quaternion (standard formula)
    r00 = 1 - 2 * (y * y + z * z)
    r01 = 2 * (x * y - z * w)
    r02 = 2 * (x * z + y * w)
    r10 = 2 * (x * y + z * w)
    r11 = 1 - 2 * (x * x + z * z)
    r12 = 2 * (y * z - x * w)
    r20 = 2 * (x * z - y * w)
    r21 = 2 * (y * z + x * w)
    r22 = 1 - 2 * (x * x + y * y)
    px, py, pz = p
    return (r00 * px + r01 * py + r02 * pz,
            r10 * px + r11 * py + r12 * pz,
            r20 * px + r21 * py + r22 * pz)


def transform_point(t: Transform,
                    p: Tuple[float, float, float]) -> Tuple[float, float, float]:
    rp = _rot(t.quaternion, p)
    tx, ty, tz = t.translation
    return (rp[0] + tx, rp[1] + ty, rp[2] + tz)


class FrameTree:
    """Registered frames + transforms with timestamp/confidence checks."""

    def __init__(self) -> None:
        self.frames: Dict[str, Frame] = {"world": Frame("world", "")}
        self.transforms: Dict[str, Transform] = {}

    def add_frame(self, name: str, parent: str = "world") -> None:
        if parent not in self.frames:
            raise ValueError(f"unknown parent frame {parent}")
        self.frames[name] = Frame(name, parent)

    def set_transform(self, t: Transform, max_age_s: float = 5.0) -> None:
        if t.src not in self.frames or t.dst not in self.frames:
            raise ValueError("transform references unknown frame")
        if time.time() - t.timestamp > max_age_s:
            raise ValueError("stale transform rejected")
        if t.confidence <= 0:
            raise ValueError("zero-confidence transform rejected")
        self.transforms[f"{t.src}->{t.dst}"] = t

    def to_world(self, frame: str,
                 p: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Walk src->...->world applying transforms. No silent mixing:
        every hop must be registered."""
        cur, pt = frame, p
        hops = 0
        while cur != "world":
            key = next((k for k in self.transforms
                        if k.startswith(cur + "->")), None)
            if key is None:
                raise ValueError(f"no transform path from {frame} (stuck at {cur})")
            t = self.transforms[key]
            pt = transform_point(t, pt)
            cur = t.dst
            hops += 1
            if hops > 16:
                raise ValueError("transform chain too deep")
        return pt

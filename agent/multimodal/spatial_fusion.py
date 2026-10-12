"""Spatial Fusion Engine (Phase 24 of Master Prompt 10).

Aligns and fuses multi-modal spatial data:
- Image + depth map fusion (RGB-D)
- Image + LiDAR point cloud fusion
- Camera + LiDAR calibration
- 3D scene reconstruction from multi-view
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from agent.multimodal.media_abstraction import MediaObject, MediaType

logger = logging.getLogger(__name__)


class SpatialAlignmentMethod(Enum):
    """Methods for spatial alignment."""

    CALIBRATION_MATRIX = "calibration_matrix"  # Known camera intrinsics/extrinsics
    FEATURE_MATCHING = "feature_matching"  # ORB/SIFT feature matching
    ICP = "icp"  # Iterative Closest Point for point clouds
    DEPTH_FROM_STEREO = "depth_from_stereo"  # Stereo disparity
    LEARNED = "learned"  # Learned depth/pose estimation


@dataclass
class CameraIntrinsics:
    """Camera intrinsic parameters."""

    fx: float  # Focal length x
    fy: float  # Focal length y
    cx: float  # Principal point x
    cy: float  # Principal point y
    width: int
    height: int
    distortion: Optional[np.ndarray] = None


@dataclass
class CameraExtrinsics:
    """Camera extrinsic parameters (pose)."""

    rotation: np.ndarray  # 3x3 rotation matrix
    translation: np.ndarray  # 3x1 translation vector


@dataclass
class PointCloud:
    """3D point cloud with optional colors."""

    points: np.ndarray  # Nx3 (x, y, z)
    colors: Optional[np.ndarray] = None  # Nx3 RGB
    normals: Optional[np.ndarray] = None  # Nx3 normals
    timestamp: float = 0.0


@dataclass
class DepthMap:
    """Depth map with camera intrinsics."""

    depth: np.ndarray  # HxW depth values (meters)
    intrinsics: CameraIntrinsics
    timestamp: float = 0.0


@dataclass
class SpatialFusionResult:
    """Result of spatial fusion."""

    fused_pointcloud: Optional[PointCloud] = None
    fused_depth: Optional[DepthMap] = None
    registered_views: List[Dict] = field(default_factory=list)
    alignment_method: str = ""
    alignment_quality: float = 0.0
    transformation: Optional[Dict] = None  # Relative poses
    metadata: Dict = field(default_factory=dict)


class SpatialFusionEngine:
    """Engine for spatial fusion of multi-modal spatial data (Phase 24)."""

    def __init__(
        self,
        method: str = "feature_matching",
        config: Optional[Dict] = None,
    ):
        self.method = method
        self.config = config or {}
        self._camera_intrinsics: Dict[str, CameraIntrinsics] = {}
        self._camera_extrinsics: Dict[str, CameraExtrinsics] = {}

    def register_camera(self, camera_id: str, intrinsics: CameraIntrinsics, extrinsics: Optional[CameraExtrinsics] = None) -> None:
        """Register camera calibration."""
        self._camera_intrinsics[camera_id] = intrinsics
        if extrinsics:
            self._camera_extrinsics[camera_id] = extrinsics

    def rgb_depth_fusion(
        self,
        rgb_image: np.ndarray,
        depth_map: DepthMap,
        intrinsics: Optional[CameraIntrinsics] = None,
    ) -> np.ndarray:
        """Fuse RGB image with depth map to create colored point cloud (RGB-D fusion).

        Args:
            rgb_image: HxWx3 RGB image
            depth_map: Depth map with intrinsics
            intrinsics: Camera intrinsics (uses depth_map.intrinsics if not provided)

        Returns:
            Nx6 array [x, y, z, r, g, b] point cloud
        """
        intr = intrinsics or depth_map.intrinsics
        depth = depth_map.depth
        h, w = depth.shape

        # Create pixel coordinates
        u, v = np.meshgrid(np.arange(w), np.arange(h))

        # Unproject depth to 3D
        z = depth.flatten()
        x = (u.flatten() - intr.cx) * z / intr.fx
        y = (v.flatten() - intr.cy) * z / intr.fy

        # Filter valid depths
        valid = z > 0
        x, y, z = x[valid], y[valid], z[valid]

        # Get colors
        colors = rgb_image.reshape(-1, 3)[valid] / 255.0

        points = np.stack([x, y, z], axis=1)
        return np.hstack([points, colors])

    def multi_view_stereo(
        self,
        images: List[np.ndarray],
        poses: List[Dict],  # Each with rotation, translation
        intrinsics: List[CameraIntrinsics],
    ) -> np.ndarray:
        """Multi-view stereo reconstruction (simplified).

        In production, would use COLMAP, OpenMVS, or learned MVS.
        """
        # Placeholder: would implement multi-view stereo
        logger.warning("Multi-view stereo not fully implemented")
        return np.array([])

    def pointcloud_icp(
        self,
        source: np.ndarray,  # Nx3
        target: np.ndarray,  # Nx3
        max_iterations: int = 50,
        tolerance: float = 1e-6,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Iterative Closest Point (ICP) registration.

        Returns:
            (transformation_matrix, transformed_source)
        """
        # Simplified ICP using numpy
        src_pts = source
        tgt_pts = target

        # Center points
        src_centroid = np.mean(src_pts, axis=0)
        tgt_centroid = np.mean(tgt_pts, axis=0)
        src_centered = src_pts - src_centroid
        tgt_centered = tgt_pts - tgt_centroid

        # SVD for rotation
        H = src_centered.T @ tgt_centered
        U, _, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T

        # Ensure proper rotation (det = 1)
        if np.linalg.det(R) < 0:
            Vt[-1, :] *= -1
            R = Vt.T @ U.T

        t = tgt_centroid - R @ src_centroid

        # Apply transformation
        transformed = (R @ source.T + t.reshape(3, 1)).T

        transform = np.eye(4)
        transform[:3, :3] = R
        transform[:3, 3] = t

        return transform, transformed

    def project_depth_to_camera(
        self,
        depth_map: np.ndarray,
        intrinsics: CameraIntrinsics,
        target_intrinsics: CameraIntrinsics,
        target_extrinsics: np.ndarray,
    ) -> np.ndarray:
        """Project depth map from one camera to another."""
        # Unproject to 3D, then project to target camera
        points = self._depth_to_points(depth_map, intrinsics)
        # Transform to target camera
        # Simplified: would apply extrinsic transformation
        return depth_map  # Placeholder

    def _depth_to_points(self, depth_map: np.ndarray, intrinsics: CameraIntrinsics) -> np.ndarray:
        """Convert depth map to 3D points."""
        h, w = depth_map.shape

        u, v = np.meshgrid(np.arange(w), np.arange(h))
        z = depth_map.flatten()
        x = (u.flatten() - intrinsics.cx) * z / intrinsics.fx
        y = (v.flatten() - intrinsics.cy) * z / intrinsics.fy

        valid = z > 0
        return np.stack([x[valid], y[valid], z[valid]], axis=1)


def create_rgbd_pointcloud(
    rgb: np.ndarray,
    depth: np.ndarray,
    intrinsics: CameraIntrinsics,
) -> np.ndarray:
    """Quick utility to create RGB-D point cloud."""
    engine = SpatialFusionEngine()
    depth_map = DepthMap(depth=depth, intrinsics=intrinsics)
    return engine.rgb_depth_fusion(rgb, depth_map)


def register_camera_calibration(
    camera_id: str,
    fx: float, fy: float, cx: float, cy: float,
    width: int, height: int,
    rotation: Optional[np.ndarray] = None,
    translation: Optional[np.ndarray] = None,
) -> Tuple[CameraIntrinsics, Optional[CameraExtrinsics]]:
    """Convenience function to create camera calibration."""
    intr = CameraIntrinsics(fx=fx, fy=fy, cx=cx, cy=cy, width=width, height=height)
    extr = None
    if rotation is not None and translation is not None:
        extr = CameraExtrinsics(rotation=rotation, translation=translation)
    return intr, extr
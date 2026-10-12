from __future__ import annotations

import difflib
import json
import logging
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _version_root() -> Path:
    root = Path.home() / ".aetheros" / "automation" / "versions"
    root.mkdir(parents=True, exist_ok=True)
    return root


class VersionManager:
    """Track and restore file versions with metadata."""

    @staticmethod
    async def save_version(file_path: str, message: str = "") -> str:
        src = Path(file_path).resolve()
        if not src.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        version_id = uuid.uuid4().hex[:12]
        root = _version_root()
        file_key = src.name
        file_dir = root / file_key
        file_dir.mkdir(parents=True, exist_ok=True)

        version_file = file_dir / f"{version_id}{src.suffix}"
        shutil.copy2(str(src), str(version_file))

        meta = {
            "version_id": version_id,
            "file_path": str(src),
            "file_name": src.name,
            "message": message,
            "created_at": time.time(),
            "size": src.stat().st_size,
        }
        (file_dir / f"{version_id}.json").write_text(json.dumps(meta, indent=2))
        logger.info("Version %s saved for %s", version_id, file_path)
        return version_id

    @staticmethod
    async def list_versions(file_path: str) -> list[dict[str, Any]]:
        src = Path(file_path).resolve()
        root = _version_root()
        file_dir = root / src.name
        if not file_dir.is_dir():
            return []

        versions: list[dict[str, Any]] = []
        for meta_file in sorted(file_dir.glob("*.json")):
            if meta_file.stem == "index":
                continue
            data = json.loads(meta_file.read_text())
            versions.append(data)

        return sorted(versions, key=lambda v: v["created_at"], reverse=True)

    @staticmethod
    async def restore_version(file_path: str, version_id: str) -> None:
        src = Path(file_path).resolve()
        root = _version_root()
        file_dir = root / src.name
        if not file_dir.is_dir():
            raise FileNotFoundError(f"No versions found for {file_path}")

        meta_file = file_dir / f"{version_id}.json"
        if not meta_file.is_file():
            raise FileNotFoundError(f"Version not found: {version_id}")

        meta = json.loads(meta_file.read_text())
        suffix = Path(meta["file_path"]).suffix
        version_file = file_dir / f"{version_id}{suffix}"
        if not version_file.is_file():
            raise FileNotFoundError(f"Version file missing: {version_file}")

        src.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(version_file), str(src))
        logger.info("Version %s restored to %s", version_id, file_path)

    @staticmethod
    async def diff_versions(file_path: str, v1: str, v2: str) -> str:
        root = _version_root()
        file_dir = root / Path(file_path).name
        if not file_dir.is_dir():
            raise FileNotFoundError(f"No versions found for {file_path}")

        meta1 = json.loads((file_dir / f"{v1}.json").read_text())
        meta2 = json.loads((file_dir / f"{v2}.json").read_text())
        suffix = Path(meta1["file_path"]).suffix

        content1 = (file_dir / f"{v1}{suffix}").read_text()
        content2 = (file_dir / f"{v2}{suffix}").read_text()

        diff = "\n".join(
            difflib.unified_diff(
                content1.splitlines(),
                content2.splitlines(),
                fromfile=f"v1:{v1}",
                tofile=f"v2:{v2}",
                lineterm="",
            )
        )
        return diff

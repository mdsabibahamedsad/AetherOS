from __future__ import annotations

import logging
import os
import shutil
import tarfile
import zipfile
from pathlib import Path
from typing import Any

from aetheros_automation.models.models import FileOperation

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet
    import base64
    import hashlib

    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False
    logger.warning("cryptography not available; encrypt/decrypt disabled")

try:
    import pyAesCrypt

    _HAS_AESCRYPT = True
except ImportError:
    _HAS_AESCRYPT = False


class FileOperations:
    """Unified file and directory operations with safety and logging."""

    @staticmethod
    async def read(path: str, encoding: str = "utf-8") -> str:
        p = Path(path).resolve()
        logger.debug("read %s", p)
        return p.read_text(encoding=encoding)

    @staticmethod
    async def write(path: str, content: str, encoding: str = "utf-8") -> None:
        p = Path(path).resolve()
        logger.debug("write %s (%d chars)", p, len(content))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding=encoding)

    @staticmethod
    async def append(path: str, content: str, encoding: str = "utf-8") -> None:
        p = Path(path).resolve()
        logger.debug("append %s (%d chars)", p, len(content))
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding=encoding) as fh:
            fh.write(content)

    @staticmethod
    async def delete(path: str) -> None:
        p = Path(path).resolve()
        logger.debug("delete %s", p)
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()

    @staticmethod
    async def move(src: str, dst: str) -> None:
        src_p = Path(src).resolve()
        dst_p = Path(dst).resolve()
        logger.debug("move %s -> %s", src_p, dst_p)
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_p), str(dst_p))

    @staticmethod
    async def copy(src: str, dst: str) -> None:
        src_p = Path(src).resolve()
        dst_p = Path(dst).resolve()
        logger.debug("copy %s -> %s", src_p, dst_p)
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        if src_p.is_dir():
            shutil.copytree(str(src_p), str(dst_p), dirs_exist_ok=True)
        else:
            shutil.copy2(str(src_p), str(dst_p))

    @staticmethod
    async def rename(src: str, new_name: str) -> None:
        src_p = Path(src).resolve()
        dst_p = src_p.parent / new_name
        logger.debug("rename %s -> %s", src_p, dst_p)
        src_p.rename(dst_p)

    @staticmethod
    async def list_dir(path: str, pattern: str | None = None) -> list[str]:
        p = Path(path).resolve()
        logger.debug("list_dir %s pattern=%s", p, pattern)
        if pattern:
            return sorted(str(x) for x in p.glob(pattern))
        return sorted(str(x) for x in p.iterdir())

    @staticmethod
    async def exists(path: str) -> bool:
        return Path(path).resolve().exists()

    @staticmethod
    async def mkdir(path: str, parents: bool = True) -> None:
        p = Path(path).resolve()
        logger.debug("mkdir %s parents=%s", p, parents)
        p.mkdir(parents=parents, exist_ok=True)

    @staticmethod
    async def rmdir(path: str, recursive: bool = False) -> None:
        p = Path(path).resolve()
        logger.debug("rmdir %s recursive=%s", p, recursive)
        if recursive:
            shutil.rmtree(p)
        else:
            p.rmdir()

    @staticmethod
    async def compress(paths: list[str], output_path: str, format: str = "zip") -> str:
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("compress %d paths -> %s (%s)", len(paths), out, format)

        if format == "zip":
            with zipfile.ZipFile(str(out), "w", zipfile.ZIP_DEFLATED) as zf:
                for p in paths:
                    src = Path(p).resolve()
                    if src.is_dir():
                        for f in src.rglob("*"):
                            zf.write(str(f), str(f.relative_to(src.parent)))
                    else:
                        zf.write(str(src), src.name)
        elif format in ("tar", "gz", "bz2", "xz"):
            mode = f"w:{format}" if format != "tar" else "w"
            with tarfile.open(str(out), mode) as tf:
                for p in paths:
                    src = Path(p).resolve()
                    tf.add(str(src), arcname=src.name)
        else:
            msg = f"Unsupported archive format: {format}"
            raise ValueError(msg)

        return str(out)

    @staticmethod
    async def extract(archive: str, dest: str) -> str:
        arc = Path(archive).resolve()
        dst = Path(dest).resolve()
        dst.mkdir(parents=True, exist_ok=True)
        logger.debug("extract %s -> %s", arc, dst)

        if zipfile.is_zipfile(str(arc)):
            with zipfile.ZipFile(str(arc), "r") as zf:
                zf.extractall(str(dst))
        elif tarfile.is_tarfile(str(arc)):
            with tarfile.open(str(arc)) as tf:
                tf.extractall(str(dst))
        else:
            msg = f"Unsupported archive: {archive}"
            raise ValueError(msg)

        return str(dst)

    @staticmethod
    async def encrypt(file_path: str, output_path: str, password: str) -> str:
        src = Path(file_path).resolve()
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        if _HAS_AESCRYPT:
            logger.debug("encrypt (pyAesCrypt) %s", src)
            pyAesCrypt.encryptFile(str(src), str(out), password)
        elif _HAS_CRYPTO:
            logger.debug("encrypt (cryptography) %s", src)
            key = base64.urlsafe_b64encode(
                hashlib.sha256(password.encode()).digest()
            )
            f = Fernet(key)
            data = src.read_bytes()
            out.write_bytes(f.encrypt(data))
        else:
            raise ImportError(
                "encrypt requires pyAesCrypt or cryptography"
            )

        return str(out)

    @staticmethod
    async def decrypt(file_path: str, output_path: str, password: str) -> str:
        src = Path(file_path).resolve()
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        if _HAS_AESCRYPT:
            logger.debug("decrypt (pyAesCrypt) %s", src)
            pyAesCrypt.decryptFile(str(src), str(out), password)
        elif _HAS_CRYPTO:
            logger.debug("decrypt (cryptography) %s", src)
            key = base64.urlsafe_b64encode(
                hashlib.sha256(password.encode()).digest()
            )
            f = Fernet(key)
            data = src.read_bytes()
            out.write_bytes(f.decrypt(data))
        else:
            raise ImportError(
                "decrypt requires pyAesCrypt or cryptography"
            )

        return str(out)

    @staticmethod
    async def get_info(path: str) -> dict[str, Any]:
        p = Path(path).resolve()
        stat = p.stat()
        return {
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": getattr(stat, "st_birthtime", stat.st_ctime),
            "is_dir": p.is_dir(),
            "is_file": p.is_file(),
            "is_symlink": p.is_symlink(),
            "permissions": oct(stat.st_mode),
            "extension": p.suffix,
            "name": p.name,
            "parent": str(p.parent),
        }

    @staticmethod
    async def read_binary(path: str) -> bytes:
        p = Path(path).resolve()
        logger.debug("read_binary %s", p)
        return p.read_bytes()

    @staticmethod
    async def write_binary(path: str, data: bytes) -> None:
        p = Path(path).resolve()
        logger.debug("write_binary %s (%d bytes)", p, len(data))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    @staticmethod
    async def from_operation(op: FileOperation) -> str | bytes | None:
        """Dispatch a FileOperation dataclass to the right method."""
        action = op.action
        if action == "read":
            return await FileOperations.read(op.source_path)
        if action == "write":
            await FileOperations.write(op.source_path, op.content or "")
            return None
        if action == "append":
            await FileOperations.append(op.source_path, op.content or "")
            return None
        if action == "delete":
            await FileOperations.delete(op.source_path)
            return None
        if action == "move":
            await FileOperations.move(op.source_path, op.dest_path)
            return None
        if action == "copy":
            await FileOperations.copy(op.source_path, op.dest_path)
            return None
        if action == "compress":
            return await FileOperations.compress(
                op.content.splitlines() if op.content else [],
                op.dest_path,
                op.compress_format,
            )
        if action == "extract":
            return await FileOperations.extract(op.source_path, op.dest_path)
        if action == "encrypt":
            return await FileOperations.encrypt(
                op.source_path, op.dest_path, op.content or ""
            )
        if action == "decrypt":
            return await FileOperations.decrypt(
                op.source_path, op.dest_path, op.content or ""
            )
        raise ValueError(f"Unknown FileOperation action: {action}")

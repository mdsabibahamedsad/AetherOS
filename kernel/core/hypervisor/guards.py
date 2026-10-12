"""
AetherOS Agent Hypervisor 1.0 — path & network escape guards (§19, §21).

Pure, deterministic, dependency-free checks used by the capsule filesystem,
mount validation, and network policy. Every rejection names its reason —
no opaque blocks.
"""

from __future__ import annotations

import ipaddress
import os
import re
from pathlib import PurePath, PureWindowsPath
from typing import List, Optional, Tuple
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Path guard (§19)
# ---------------------------------------------------------------------------

_WINDOWS_DEVICE_RE = re.compile(
    r"^(\\\\\.\\|\\\\\?\\|\\\\\?\\UNC\\)", re.IGNORECASE)
_UNC_RE = re.compile(r"^\\\\[^\\]+\\[^\\]+")
_DRIVE_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_NTFS_STREAM_RE = re.compile(r":[^\\/]+$")  # alternate data streams zone


def _has_ntfs_stream_suffix(path: str) -> bool:
    # A colon in the final component that is not a drive letter => ADS risk.
    base = path.replace("/", "\\").rsplit("\\", 1)[-1]
    if re.match(r"^[A-Za-z]:$", base):
        return False
    return ":" in base


class PathEscapeError(ValueError):
    """Raised when a capsule path request attempts to escape its root."""


def validate_capsule_path(
    capsule_root: str,
    requested: str,
    *,
    allow_symlink_escape: bool = False,
    existing_paths: Optional[dict] = None,
) -> str:
    """Resolve `requested` against `capsule_root` and enforce containment.

    Defends against: `../`, absolute host paths, symlink/junction escapes,
    NTFS reparse-point/ADS escapes, UNC paths, and Windows device paths.

    Returns the validated absolute host path. Raises PathEscapeError with
    an explicit reason on any violation.

    `existing_paths` is an optional test hook mapping host path -> bool
    (islink) used instead of touching the real filesystem in unit tests.
    """
    if not requested or not requested.strip():
        raise PathEscapeError("empty path")

    req = requested.strip()

    # UNC abuse (§19): never allow network paths inside a capsule.
    if _UNC_RE.match(req.replace("/", "\\")):
        raise PathEscapeError(f"UNC path rejected: {requested!r}")
    # Windows device paths (\\.\, \\?\, CON/PRN/AUX/NUL/COMx/LPTx).
    if _WINDOWS_DEVICE_RE.match(req):
        raise PathEscapeError(f"device path rejected: {requested!r}")
    tail = PureWindowsPath(req).name.upper()
    if tail in {"CON", "PRN", "AUX", "NUL"} or re.match(r"^(COM\d+|LPT\d+)$", tail):
        raise PathEscapeError(f"reserved device name rejected: {requested!r}")
    # NTFS alternate-data-stream suffix.
    if _has_ntfs_stream_suffix(req):
        raise PathEscapeError(f"NTFS stream suffix rejected: {requested!r}")
    # Absolute host paths: POSIX root or drive-absolute.
    if req.startswith("/") or _DRIVE_ABSOLUTE_RE.match(req):
        raise PathEscapeError(f"absolute host path rejected: {requested!r}")
    # Windows absolute without drive (e.g. \\foo, C: relative forms handled).
    if req.startswith("\\"):
        raise PathEscapeError(f"absolute host path rejected: {requested!r}")
    # Null bytes can truncate downstream consumers.
    if "\x00" in req:
        raise PathEscapeError("null byte rejected")

    root = os.path.abspath(capsule_root)
    # normpath collapses ../ and ./ lexically; containment is then verified.
    joined = os.path.normpath(os.path.join(root, req))
    if joined != root and not joined.startswith(root + os.sep):
        raise PathEscapeError(f"path traversal rejected: {requested!r}")

    # Symlink / junction / reparse-point escape: resolve the deepest existing
    # prefix and require it to stay within the root.
    if not allow_symlink_escape:
        probe = joined
        while probe != root and not os.path.lexists(probe):
            probe = os.path.dirname(probe)
        if probe != root:
            if existing_paths is not None:
                if existing_paths.get(probe, False):
                    raise PathEscapeError(f"symlink escape rejected: {requested!r}")
            elif os.path.islink(probe) or not os.path.realpath(probe).startswith(root):
                # os.path.islink covers symlinks; realpath covers junctions/
                # reparse points whose targets leave the root.
                raise PathEscapeError(f"symlink/junction escape rejected: {requested!r}")

    return joined


def validate_mount_host_path(host_path: str) -> str:
    """Validate an explicitly configured host mount source (§18-§19)."""
    if not host_path or not host_path.strip():
        raise PathEscapeError("empty host mount path")
    hp = host_path.strip()
    if _UNC_RE.match(hp.replace("/", "\\")):
        raise PathEscapeError(f"UNC mount source rejected: {host_path!r}")
    if _WINDOWS_DEVICE_RE.match(hp):
        raise PathEscapeError(f"device mount source rejected: {host_path!r}")
    if _has_ntfs_stream_suffix(hp):
        raise PathEscapeError(f"NTFS stream mount source rejected: {host_path!r}")
    if "\x00" in hp:
        raise PathEscapeError("null byte rejected")
    return os.path.abspath(hp)


# ---------------------------------------------------------------------------
# Network guard (§21)
# ---------------------------------------------------------------------------

_METADATA_IP_STRINGS = {"169.254.169.254", "fd00:ec2::254", "100.100.100.200"}


def _ip_from_numeric_host(host: str) -> Optional[str]:
    """Decode decimal/octal/hex IPv4 tricks (e.g. 2130706433, 0x7f.1)."""
    h = host.strip().lower()
    if not h:
        return None
    # Pure decimal 32-bit integer form.
    if re.fullmatch(r"\d{1,10}", h):
        try:
            n = int(h)
            if 0 <= n <= 0xFFFFFFFF:
                return str(ipaddress.IPv4Address(n))
        except ValueError:
            return None
        return None
    # Hex 32-bit integer form (0x7f000001).
    if re.fullmatch(r"0x[0-9a-f]{1,8}", h):
        try:
            return str(ipaddress.IPv4Address(int(h, 16)))
        except ValueError:
            return None
    parts = h.split(".")
    if len(parts) == 4:
        nums: List[int] = []
        for p in parts:
            try:
                if p.startswith("0x"):
                    nums.append(int(p, 16))
                elif len(p) > 1 and p.startswith("0") and p.isdigit():
                    nums.append(int(p, 8))
                elif p.isdigit():
                    nums.append(int(p, 10))
                else:
                    return None
            except ValueError:
                return None
        if all(0 <= n <= 255 for n in nums):
            return ".".join(str(n) for n in nums)
    return None


def parse_host_ips(host: str) -> List[str]:
    """Return candidate IP literals for a hostname without doing DNS."""
    host = (host or "").strip().rstrip(".").lower()
    if not host:
        return []
    decoded = _ip_from_numeric_host(host)
    if decoded is not None:
        return [decoded]
    try:
        return [str(ipaddress.ip_address(host))]
    except ValueError:
        return []


def is_prohibited_ip_literal(ip_str: str) -> Tuple[bool, str]:
    """True when an IP literal must never be a capsule egress target."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False, ""
    if ip_str in _METADATA_IP_STRINGS:
        return True, "cloud metadata endpoint"
    if ip.is_loopback:
        return True, "loopback target"
    if ip.is_link_local:
        return True, "link-local target"
    if ip.is_private:
        return True, "private-network target"
    if ip.is_reserved or ip.is_unspecified:
        return True, "reserved/unspecified target"
    if getattr(ip, "is_global", False) is False and not (
            ip.is_loopback or ip.is_link_local or ip.is_private):
        return True, "non-global target"
    return False, ""


def check_egress_url(
    url: str,
    *,
    allow_private: bool = False,
    allow_localhost: bool = False,
) -> Tuple[bool, str]:
    """Pre-connection SSRF/DNS-rebinding screen for a capsule egress URL.

    Blocks: metadata endpoints, localhost/private/loopback/link-local
    literals, decimal/octal/hex IP tricks, non-http(s) schemes, and
    credentials embedded in the URL. Hostnames that are not IP literals
    are returned as (True, "hostname: resolution-time validation required")
    because rebinding can only be decided at resolve+connect time.
    """
    if not url or not url.strip():
        return False, "empty URL"
    try:
        parsed = urlparse(url.strip())
    except ValueError as exc:
        return False, f"unparseable URL: {exc}"
    if parsed.scheme not in ("http", "https"):
        return False, f"scheme not permitted: {parsed.scheme or '(none)'}"
    if parsed.username or parsed.password:
        return False, "credentials embedded in URL"
    host = (parsed.hostname or "").strip().rstrip(".")
    if not host:
        return False, "missing host"
    if host in _METADATA_IP_STRINGS:
        return False, "cloud metadata endpoint"
    lits = parse_host_ips(host)
    if lits:
        blocked, reason = is_prohibited_ip_literal(lits[0])
        if blocked:
            low = reason
            if "loopback" in low or "localhost" in host:
                if allow_localhost:
                    pass
                else:
                    return False, f"{reason}: {host}"
            elif "private" in low or "link-local" in low:
                if allow_private:
                    pass
                else:
                    return False, f"{reason}: {host}"
            else:
                return False, f"{reason}: {host}"
        return True, "literal IP permitted"
    # DNS name: static screen cannot rule out rebinding; the connector must
    # resolve, re-check each IP with is_prohibited_ip_literal, and pin.
    if host.lower() in ("localhost",):
        return (True, "localhost permitted by policy") if allow_localhost else (False, "localhost target")
    if host.lower().endswith((".localhost", ".internal", ".local", ".lan", ".home", ".corp")):
        if not allow_private:
            return False, f"internal-name target: {host}"
    return True, "hostname: resolution-time validation required"


def normalize_domain(domain: str) -> str:
    return (domain or "").strip().lower().rstrip(".")


def domain_matches_allowlist(domain: str, allowlist: List[str]) -> bool:
    d = normalize_domain(domain)
    for entry in allowlist:
        e = normalize_domain(entry)
        if d == e or d.endswith("." + e):
            return True
    return False

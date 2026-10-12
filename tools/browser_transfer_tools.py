"""
Master 15 browser transfer tools — purely ADDITIVE (Phases 15, 17, 18, 71, 73).

Adds browser_download / browser_upload / browser_tab to the existing ``browser``
toolset without modifying any working module. Auto-discovery imports this file;
exposure is granted by names appended to toolsets.py's ``browser`` entry.

Every URL guard REUSES the production navigation defenses (tools/url_safety.py,
tools/website_policy.py, agent.redact patterns) — no parallel policy exists.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
CDP_TIMEOUT_SECONDS = 20.0

_SECRET_FILENAME_RE = re.compile(
    r"(^|/)(\.env|auth\.json|credentials?\.json|id_rsa[^/]*|.*\.pem)$", re.IGNORECASE
)


def _err(msg: str, **extra) -> str:
    return json.dumps({"success": False, "error": msg, **extra}, ensure_ascii=False)


def _ok(payload: Dict[str, Any]) -> str:
    return json.dumps({"success": True, **payload}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Shared outbound-URL validation (mirrors browser_navigate guards)
# ---------------------------------------------------------------------------

def validate_outbound_url(url: str) -> Optional[str]:
    """Return a blocking reason, or None when the URL may proceed."""
    from tools.url_safety import (
        is_always_blocked_url as _is_always_blocked,
        is_safe_url as _is_safe_url,
        normalize_url_for_request as _normalize,
    )

    url = str(url or "").strip()
    if not url:
        return "url is required"
    scheme = (urlparse(url).scheme or "").lower()
    if scheme not in ("http", "https"):
        return f"blocked scheme '{scheme}' — only http/https allowed"

    try:
        normalized = _normalize(url)
    except Exception:
        normalized = url

    if _is_always_blocked(normalized):
        return "URL is always-blocked (cloud metadata / link-local)"

    try:
        from tools.website_policy import check_website_access

        block = check_website_access(normalized)
    except Exception:
        block = None
    if block:
        reason = block.get("reason", "blocked") if isinstance(block, dict) else str(block)
        return f"website policy block: {reason}"

    if not _is_safe_url(normalized):
        return "URL resolves to private/internal address (SSRF guard)"

    # Credential-token-in-URL exfiltration guard (raw + percent-decoded).
    try:
        from urllib.parse import unquote

        from agent.redact import _PREFIX_RE

        for candidate in (url, unquote(url)):
            if _PREFIX_RE.search(candidate or ""):
                return "URL contains credential-shaped token (exfiltration guard)"
    except Exception:
        pass

    # Phase 71 phishing advisory — hard-block only at high score.
    try:
        from aetheros_computer.dataflow import check_suspicious_url

        verdict = check_suspicious_url(normalized)
        if verdict.get("score", 0) >= 6:
            return "suspicious URL blocked: " + ", ".join(verdict["reasons"])
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# browser_download (Phases 17, 52, 73)
# ---------------------------------------------------------------------------

def browser_download(url: str = "", filename: str = "", task_id: str = "default",
                     **kw) -> str:
    task_id = kw.get("task_id") or task_id
    reason = validate_outbound_url(url)
    if reason:
        return _err(reason)

    from aetheros_computer.idempotency import check_and_record, make_key

    parsed = urlparse(url)
    base = parsed._replace(params="", query="", fragment="").geturl() or url
    idem_key = make_key("download", base)
    if check_and_record(idem_key):
        return _err("duplicate download skipped (same URL within TTL)",
                    duplicate=True, idempotency_key=idem_key)

    try:
        import requests
    except ImportError:
        return _err("requests library unavailable")

    from aetheros_constants import get_aetheros_home

    dest_dir = Path(get_aetheros_home()) / "downloads" / _safe_component(task_id)
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _err(f"cannot create download dir: {exc}")

    name = _safe_filename(filename or _basename_of(url))
    dest = _unique_path(dest_dir / name)
    max_bytes = _max_download_bytes()

    written = 0
    content_type = ""
    tmp_name = None
    try:
        with requests.get(url, stream=True, timeout=30, allow_redirects=True,
                          headers={"User-Agent": "aetheros-browser-download"}) as resp:
            resp.raise_for_status()
            length_hdr = resp.headers.get("Content-Length")
            if length_hdr and length_hdr.isdigit() and int(length_hdr) > max_bytes:
                return _err(f"download too large ({length_hdr} bytes > cap {max_bytes})")
            content_type = (resp.headers.get("Content-Type") or "").lower()
            fd, tmp_name = tempfile.mkstemp(dir=str(dest_dir), suffix=".part")
            with os.fdopen(fd, "wb") as out:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    written += len(chunk)
                    if written > max_bytes:
                        return _err(f"download exceeded cap {max_bytes} mid-stream")
                    out.write(chunk)
        os.replace(tmp_name, dest)
        tmp_name = None
        try:
            os.chmod(dest, 0o644)  # never executable (POSIX best-effort)
        except OSError:
            pass
    except Exception as exc:
        if tmp_name:
            Path(tmp_name).unlink(missing_ok=True)
        return _err(f"download failed: {exc}")

    executable_like = (
        any(t in content_type for t in ("executable", "octet-stream"))
        or dest.suffix.lower() in {
            ".exe", ".msi", ".dll", ".bat", ".cmd", ".sh", ".scr", ".com", ".apk",
        }
    )
    return _ok({
        "path": str(dest),
        "bytes": written,
        "sha256": _sha256_file(dest),
        "content_type": content_type,
        "executable_content": bool(executable_like),
        "note": "downloaded only — never executed automatically (Phase 73)",
    })


def _max_download_bytes() -> int:
    raw = os.getenv("AETHEROS_MAX_DOWNLOAD_MB", "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw) * 1024 * 1024
    return MAX_DOWNLOAD_BYTES


def _safe_component(text: str) -> str:
    cleaned = "".join(c for c in str(text or "default") if c.isalnum() or c in "-_")
    return (cleaned or "default")[:80]


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", str(name or "")).strip("._")
    return (cleaned or "download.bin")[:120]


def _basename_of(url: str) -> str:
    try:
        path = urlparse(url).path
        base = path.rsplit("/", 1)[-1] if path else ""
        return base or ("dl_" + hashlib.sha256(url.encode()).hexdigest()[:10])
    except Exception:
        return "download.bin"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for i in range(1, 1000):
        candidate = path.with_name(f"{path.stem}-{i}{path.suffix}")
        if not candidate.exists():
            return candidate
    return path.with_name(f"{path.stem}-{os.getpid()}{path.suffix}")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(128 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# CDP helper shared by upload/tab
# ---------------------------------------------------------------------------

def _cdp(method: str, params: Dict[str, Any], target_id: Optional[str] = None) -> Dict[str, Any]:
    from tools.browser_cdp_tool import _cdp_call, _resolve_cdp_endpoint, _run_async

    endpoint = _resolve_cdp_endpoint()
    if not endpoint:
        raise RuntimeError(
            "no CDP endpoint configured — set BROWSER_CDP_URL or browser.cdp_url "
            "(local agent-browser sessions do not expose one)"
        )
    result = _run_async(_cdp_call(endpoint, method, params, target_id, CDP_TIMEOUT_SECONDS))
    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(f"CDP {method}: {result['error']}")
    return result


def _cdp_error(exc: Exception) -> str:
    msg = str(exc)
    extra = {"unsupported_backend": True} if "no CDP endpoint" in msg else {}
    return _err(msg, **extra)


# ---------------------------------------------------------------------------
# browser_upload (Phases 18, 22)
# ---------------------------------------------------------------------------

def browser_upload(selector: str = "", file_path: str = "", target_id: str = "",
                   task_id: str = "default", **kw) -> str:
    del task_id, kw
    src = Path(str(file_path or "")).expanduser()
    if not src.exists() or not src.is_file():
        return _err(f"file not found: {src}")
    try:
        size = src.stat().st_size
    except OSError as exc:
        return _err(f"stat failed: {exc}")
    if size > MAX_UPLOAD_BYTES:
        return _err(f"file too large ({size} > {MAX_UPLOAD_BYTES})")

    resolved = str(src.resolve())
    if _SECRET_FILENAME_RE.search(resolved.replace("\\", "/")):
        return _err("refused: source file looks like a credential store")
    try:
        from tools.file_tools import _check_sensitive_path

        sensitive = _check_sensitive_path(resolved, "upload-screen")
    except Exception:
        sensitive = None
    if sensitive:
        return _err(f"refused by sensitive-path guard: {sensitive}")

    if not selector:
        return _err(
            "CSS selector of the <input type=file> is required — snapshot refs "
            "cannot be mapped to DOM nodes without extra state",
            needs_selector=True,
        )

    try:
        doc = _cdp("DOM.getDocument", {"depth": 0})
        root = (doc.get("result", {}).get("root") or {}).get("nodeId")
        if not root:
            return _err("DOM.getDocument returned no root node")
        node = _cdp("DOM.querySelector", {"nodeId": root, "selector": selector})
        node_id = (node.get("result") or {}).get("nodeId")
        if not node_id:
            return _err(f"element not found for selector: {selector}")
        _cdp("DOM.setFileInputFiles", {"files": [resolved], "nodeId": node_id},
             target_id=target_id or None)
    except RuntimeError as exc:
        return _cdp_error(exc)
    except Exception as exc:
        return _err(f"upload failed: {exc}")

    return _ok({
        "uploaded": True,
        "file": resolved,
        "bytes": size,
        "selector": selector,
        "next_step": "call browser_submit with confirm=true to submit",
    })


# ---------------------------------------------------------------------------
# browser_tab (Phase 15)
# ---------------------------------------------------------------------------

def browser_tab(action: str = "list", url: str = "", target_id: str = "", **kw) -> str:
    del kw
    action = (action or "list").lower()
    try:
        if action == "list":
            info = _cdp("Target.getTargets", {})
            pages = [
                {"target_id": t.get("targetId"), "title": t.get("title"), "url": t.get("url")}
                for t in (info.get("result", {}).get("targetInfos") or [])
                if t.get("type") == "page"
            ]
            return _ok({"tabs": pages, "count": len(pages)})
        if action == "new":
            if not url:
                return _err("url required for action=new")
            reason = validate_outbound_url(url)
            if reason:
                return _err(reason)
            created = _cdp("Target.createTarget", {"url": url})
            return _ok({"created": (created.get("result") or {}).get("targetId"), "url": url})
        if action == "switch":
            if not target_id:
                return _err("target_id required for action=switch")
            _cdp("Target.activateTarget", {"targetId": target_id})
            return _ok({"activated": target_id})
        if action == "close":
            if not target_id:
                return _err("target_id required for action=close")
            _cdp("Target.closeTarget", {"targetId": target_id})
            return _ok({"closed": target_id})
        return _err(f"unknown action '{action}' (list/new/switch/close)")
    except RuntimeError as exc:
        return _cdp_error(exc)
    except Exception as exc:
        return _err(f"tab operation failed: {exc}")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
from tools.registry import registry  # noqa: E402

registry.register(
    name="browser_download",
    toolset="browser",
    schema={
        "name": "browser_download",
        "description": "Download a file over validated http(s) into the profile downloads folder. Guards: SSRF/private-address block, website policy, credential-token-in-URL block, size cap, duplicate-URL suppression within TTL. Files are saved ONLY — never executed.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Direct download URL"},
                "filename": {"type": "string", "description": "Optional save name"},
            },
            "required": ["url"],
        },
    },
    handler=lambda args, **kw: browser_download(
        url=args.get("url", ""), filename=args.get("filename", ""),
        task_id=kw.get("task_id") or "default",
    ),
)


registry.register(
    name="browser_upload",
    toolset="browser",
    schema={
        "name": "browser_upload",
        "description": "Upload a local file into an <input type=file> via CDP DOM.setFileInputFiles. Source files are screened (credential-store names and sensitive-path guards refuse). Requires a CSS selector; snapshot refs cannot address DOM nodes. After uploading, submit explicitly with browser_submit confirm=true.",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector of the file input"},
                "file_path": {"type": "string", "description": "Local file to upload"},
                "target_id": {"type": "string", "description": "Optional CDP targetId"},
            },
            "required": ["selector", "file_path"],
        },
    },
    handler=lambda args, **kw: browser_upload(
        selector=args.get("selector", ""), file_path=args.get("file_path", ""),
        target_id=args.get("target_id", ""),
    ),
)


registry.register(
    name="browser_tab",
    toolset="browser",
    schema={
        "name": "browser_tab",
        "description": "Manage browser tabs via CDP Target domain: list open tabs, open new tab (URL validated like browser_navigate), switch to a tab, or close one.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "new", "switch", "close"]},
                "url": {"type": "string", "description": "For action=new"},
                "target_id": {"type": "string", "description": "For switch/close"},
            },
            "required": ["action"],
        },
    },
    handler=lambda args, **kw: browser_tab(
        action=args.get("action", "list"), url=args.get("url", ""),
        target_id=args.get("target_id", ""),
    ),
)

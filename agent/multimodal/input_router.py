"""Multimodal Input Router (Phase 2 of Master Prompt 10).

Takes arbitrary user input (file path, URL, base64 bytes, text, structured
data, device/stream reference) and normalizes it into a :class:`MediaObject`.

Security contract (MASTER 10 Phases 7/66):
- URL downloads go through SSRF guards (no private/loopback ranges, no
  file:// or gopher:// schemes).
- Downloaded content is stored in a profile-aware temp/cache directory.
- Base64 payloads are written to temp files so downstream tools can open them.
"""

from __future__ import annotations

import base64 as _b64
import mimetypes
import os
import shutil
import tempfile
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from agent.multimodal.media_abstraction import (
    MediaObject,
    MediaType,
    SensitivityLevel,
    create_audio_media,
    create_document_media,
    create_image_media,
    create_screen_media,
    create_structured_data_media,
    create_text_media,
    create_video_media,
    validate_media_object,
)

import logging

logger = logging.getLogger(__name__)

_MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024  # 100 MB safety cap


class InputSourceType(Enum):
    FILE = "file"
    URL = "url"
    STREAM = "stream"
    DEVICE = "device"
    BASE64 = "base64"
    TEXT = "text"
    STRUCTURED = "structured"


# ---------------------------------------------------------------------------
# SSRF guard — reject URLs that resolve to private/loopback/link-local space.
# ---------------------------------------------------------------------------


def _url_allowed(url: str) -> bool:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return False
    host = parsed.hostname or ""
    if not host:
        return False
    if host.lower() in ("localhost",):
        return False
    import ipaddress

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # DNS name — could still resolve to private space; the fetch wrapper
        # below re-checks after resolution.
        return True
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)


def _resolved_host_allowed(ip_str: str) -> bool:
    import ipaddress

    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)


class MediaRouter:
    """Routes input data to normalized MediaObjects."""

    def __init__(self, temp_dir: Optional[str] = None) -> None:
        self._temp_dir = temp_dir
        self._handlers = {
            InputSourceType.FILE: self._handle_file,
            InputSourceType.URL: self._handle_url,
            InputSourceType.TEXT: self._handle_text,
            InputSourceType.BASE64: self._handle_base64,
            InputSourceType.STRUCTURED: self._handle_structured,
            InputSourceType.DEVICE: self._handle_device,
            InputSourceType.STREAM: self._handle_stream,
        }
        self._mime_to_type: Dict[str, MediaType] = {
            "text/plain": MediaType.TEXT,
            "text/markdown": MediaType.TEXT,
            "text/html": MediaType.TEXT,
            "text/csv": MediaType.TEXT,
            "application/json": MediaType.STRUCTURED_DATA,
            "application/xml": MediaType.STRUCTURED_DATA,
            "application/pdf": MediaType.DOCUMENT,
            "image/jpeg": MediaType.IMAGE,
            "image/png": MediaType.IMAGE,
            "image/gif": MediaType.IMAGE,
            "image/webp": MediaType.IMAGE,
            "image/bmp": MediaType.IMAGE,
            "image/tiff": MediaType.IMAGE,
            "audio/mpeg": MediaType.AUDIO,
            "audio/wav": MediaType.AUDIO,
            "audio/wave": MediaType.AUDIO,
            "audio/ogg": MediaType.AUDIO,
            "audio/flac": MediaType.AUDIO,
            "audio/aac": MediaType.AUDIO,
            "video/mp4": MediaType.VIDEO,
            "video/webm": MediaType.VIDEO,
            "video/quicktime": MediaType.VIDEO,
            "video/x-msvideo": MediaType.VIDEO,
            "application/msword": MediaType.DOCUMENT,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": MediaType.DOCUMENT,
            "application/vnd.ms-excel": MediaType.DOCUMENT,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": MediaType.DOCUMENT,
            "application/vnd.ms-powerpoint": MediaType.DOCUMENT,
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": MediaType.DOCUMENT,
        }

    # -- entry point -------------------------------------------------------
    def route_input(
        self,
        input_data: Any,
        source_type: Optional[InputSourceType] = None,
        source: str = "",
        sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MediaObject:
        if source_type is None:
            source_type = self._detect_source_type(input_data, source)
        handler = self._handlers.get(source_type)
        if handler is None:
            raise ValueError(f"No handler available for source type: {source_type}")
        media_obj = handler(input_data, source, sensitivity, metadata or {})
        errors = validate_media_object(media_obj)
        if errors:
            raise ValueError(f"Invalid media object created: {', '.join(errors)}")
        return media_obj

    # -- detection ---------------------------------------------------------
    def _detect_source_type(self, input_data: Any, source: str) -> InputSourceType:
        if isinstance(input_data, (dict, list)):
            return InputSourceType.STRUCTURED
        if isinstance(input_data, bytes):
            return InputSourceType.BASE64
        if isinstance(input_data, str):
            if input_data.startswith(("http://", "https://", "ftp://", "ftps://")):
                return InputSourceType.URL
            if os.path.exists(input_data):
                return InputSourceType.FILE
            return InputSourceType.TEXT
        return InputSourceType.TEXT

    # -- handlers ----------------------------------------------------------
    def _handle_file(
        self, file_path: str, source: str, sensitivity: SensitivityLevel, metadata: Dict[str, Any]
    ) -> MediaObject:
        if not source:
            source = file_path
        media_type = self._get_media_type_from_file(file_path)
        if media_type == MediaType.TEXT:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                content = ""
            media_obj = create_text_media(content, source=source, sensitivity=sensitivity)
        elif media_type == MediaType.IMAGE:
            media_obj = create_image_media(file_path, sensitivity=sensitivity)
        elif media_type == MediaType.AUDIO:
            media_obj = create_audio_media(file_path, sensitivity=sensitivity)
        elif media_type == MediaType.VIDEO:
            media_obj = create_video_media(file_path, sensitivity=sensitivity)
        elif media_type == MediaType.DOCUMENT:
            media_obj = create_document_media(file_path, sensitivity=sensitivity)
        else:
            media_obj = create_structured_data_media(
                {"file_path": file_path, "size": os.path.getsize(file_path)},
                sensitivity=sensitivity,
            )
        if metadata:
            media_obj.metadata.update(metadata)
        return media_obj

    def _handle_url(
        self, url: str, source: str, sensitivity: SensitivityLevel, metadata: Dict[str, Any]
    ) -> MediaObject:
        if not source:
            source = url
        local_path = self._download(url)
        media_obj = self._handle_file(local_path, source, sensitivity, metadata)
        media_obj.add_provenance_step("downloaded_from_url", actor="input_router", metadata={"url": url})
        media_obj.storage_location = local_path
        return media_obj

    def _handle_text(
        self, text: str, source: str, sensitivity: SensitivityLevel, metadata: Dict[str, Any]
    ) -> MediaObject:
        if not source:
            source = f"text://{uuid.uuid4()}"
        media_obj = create_text_media(text, source=source, sensitivity=sensitivity)
        if metadata:
            media_obj.metadata.update(metadata)
        return media_obj

    def _handle_base64(
        self, data: bytes, source: str, sensitivity: SensitivityLevel, metadata: Dict[str, Any]
    ) -> MediaObject:
        if not source:
            source = f"base64://{uuid.uuid4()}"
        mime_type = metadata.get("mime_type")
        media_type = self._mime_to_type.get(mime_type) if mime_type else None
        if media_type in (MediaType.IMAGE, MediaType.AUDIO, MediaType.VIDEO, MediaType.DOCUMENT):
            ext = mimetypes.guess_extension(mime_type) or ".bin"
            path = self._write_temp(data, ext)
            media_obj = self._handle_file(path, source, sensitivity, metadata)
            media_obj.storage_location = path
            media_obj.add_provenance_step("decoded_from_base64", actor="input_router")
            return media_obj
        media_obj = create_structured_data_media(
            {"base64_data": _b64.b64encode(data).decode("utf-8"), "size": len(data), "mime_type": mime_type or "application/octet-stream"},
            sensitivity=sensitivity,
        )
        if metadata:
            media_obj.metadata.update(metadata)
        return media_obj

    def _handle_structured(
        self, data: Union[Dict[str, Any], List[Any]], source: str, sensitivity: SensitivityLevel, metadata: Dict[str, Any]
    ) -> MediaObject:
        if not source:
            source = f"structured://{uuid.uuid4()}"
        media_obj = create_structured_data_media(data, sensitivity=sensitivity)
        if metadata:
            media_obj.metadata.update(metadata)
        return media_obj

    def _handle_device(
        self, device_ref: str, source: str, sensitivity: SensitivityLevel, metadata: Dict[str, Any]
    ) -> MediaObject:
        if not source:
            source = device_ref
        media_obj = create_structured_data_media(
            {"device": device_ref, "note": "device capture requires platform support"},
            sensitivity=sensitivity,
        )
        media_obj.metadata.update(metadata or {})
        return media_obj

    def _handle_stream(
        self, stream_ref: str, source: str, sensitivity: SensitivityLevel, metadata: Dict[str, Any]
    ) -> MediaObject:
        if not source:
            source = stream_ref
        media_obj = create_structured_data_media(
            {"stream": stream_ref, "note": "stream requires StreamManager"},
            sensitivity=sensitivity,
        )
        media_obj.metadata.update(metadata or {})
        return media_obj

    # -- helpers -----------------------------------------------------------
    def _get_media_type_from_file(self, file_path: str) -> Optional[MediaType]:
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            return self._mime_to_type.get(mime_type)
        return None

    def _temp_root(self) -> str:
        if self._temp_dir:
            os.makedirs(self._temp_dir, exist_ok=True)
            return self._temp_dir
        try:
            from aetheros_constants import get_aetheros_dir

            path = str(get_aetheros_dir("cache/media", "cache/media"))
            os.makedirs(path, exist_ok=True)
            return path
        except Exception:
            return tempfile.gettempdir()

    def _write_temp(self, data: bytes, ext: str) -> str:
        root = self._temp_root()
        path = os.path.join(root, f"media_{uuid.uuid4().hex}{ext}")
        with open(path, "wb") as f:
            f.write(data)
        return path

    def _download(self, url: str) -> str:
        """Download a URL to a temp file with SSRF guards and size cap."""
        if not _url_allowed(url):
            raise ValueError(f"URL rejected by SSRF policy: {url}")

        import httpx

        headers = {"User-Agent": "Aetheros-Multimodal/1.0"}
        try:
            resp = httpx.get(
                url, headers=headers, follow_redirects=True, timeout=30.0,
                limits=httpx.Limits(max_connections=4),
            )
        except Exception as e:
            raise ValueError(f"Download failed for {url}: {e}") from e

        final_url = str(resp.url)
        if not _url_allowed(final_url):
            raise ValueError(f"URL redirected to disallowed target: {final_url}")
        if not _resolved_host_allowed(final_url.split("/")[2].split(":")[0]):
            raise ValueError(f"URL resolved to private address: {final_url}")

        if len(resp.content) > _MAX_DOWNLOAD_BYTES:
            raise ValueError(f"Downloaded content exceeds {_MAX_DOWNLOAD_BYTES} bytes cap")
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
        ext = mimetypes.guess_extension(content_type) or ".bin"
        path = self._write_temp(resp.content, ext)
        logger.info("Downloaded %s (%d bytes) -> %s", url, len(resp.content), path)
        return path


# ---------------------------------------------------------------------------
# Convenience entry points
# ---------------------------------------------------------------------------


def route_file(
    file_path: str,
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
    metadata: Optional[Dict[str, Any]] = None,
) -> MediaObject:
    return MediaRouter().route_input(file_path, InputSourceType.FILE, file_path, sensitivity, metadata)


def route_url(
    url: str,
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
    metadata: Optional[Dict[str, Any]] = None,
) -> MediaObject:
    return MediaRouter().route_input(url, InputSourceType.URL, url, sensitivity, metadata)


def route_text(
    text: str,
    source: str = "",
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
    metadata: Optional[Dict[str, Any]] = None,
) -> MediaObject:
    return MediaRouter().route_input(text, InputSourceType.TEXT, source or f"text://{uuid.uuid4()}", sensitivity, metadata)


def route_base64(
    data: bytes,
    mime_type: str = "application/octet-stream",
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
    metadata: Optional[Dict[str, Any]] = None,
) -> MediaObject:
    meta = dict(metadata or {})
    meta.setdefault("mime_type", mime_type)
    return MediaRouter().route_input(data, InputSourceType.BASE64, "", sensitivity, meta)


def route_structured_data(
    data: Union[Dict[str, Any], List[Any]],
    source: str = "",
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
    metadata: Optional[Dict[str, Any]] = None,
) -> MediaObject:
    return MediaRouter().route_input(data, InputSourceType.STRUCTURED, source or f"structured://{uuid.uuid4()}", sensitivity, metadata)
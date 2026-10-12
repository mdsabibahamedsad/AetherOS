"""Media subcommand group for aetheros (Phase 92 of Master Prompt 10).

Provides a top-level ``media`` command with subcommands:
    media ingest   — normalize input to a MediaObject
    media inspect  — show metadata + privacy classification
    media ocr      — run OCR on image/document/screen
    media transcribe — transcribe audio/video
    media analyze  — describe image/video/document with a question
    media embed    — store media reference (+ optional embedding)
    media search   — retrieve by token overlap (light RAG)
    media convert  — resize/change image format
    media stream   — push a frame into a bounded stream
    media export   — dump media metadata to JSON

Each subcommand mirrors the stable API in agent.multimodal.api and returns
pretty-printed JSON.  No core changes are required; this is pure CLI surface.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from agent.multimodal.api import (
    media_analyze,
    media_convert,
    media_embed,
    media_export,
    media_ingest,
    media_inspect,
    media_ocr,
    media_search,
    media_stream,
    media_transcribe,
    new_trackers,
)
from agent.multimodal.memory import MultimodalMemoryStore
from agent.multimodal.media_abstraction import (
    MediaObject,
    SensitivityLevel,
    create_audio_media,
    create_document_media,
    create_image_media,
    create_video_media,
)
from aetheros_constants import get_aetheros_home

logger = None  # set in _main()


def _json_print(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _store_from_args(ns: argparse.Namespace) -> MultimodalMemoryStore:
    if getattr(ns, "store", None) == "shared":
        return MultimodalMemoryStore()
    return MultimodalMemoryStore(str(get_aetheros_home() / "memory" / "multimodal"))


def cmd_ingest(ns: argparse.Namespace) -> int:
    payload = media_ingest(
        source=ns.source,
        source_type=ns.type,
        sensitivity=ns.sensitivity,
        metadata={"description": ns.description} if ns.description else None,
    )
    _json_print(payload)
    return 0 if payload.get("success") else 1


def cmd_inspect(ns: argparse.Namespace) -> int:
    # Build MediaObject from --source or --media-id
    if ns.media_id:
        # naive lookup; in reality we would query the store
        return _err(f"--media-id lookup not implemented in this stub")
    media_obj: MediaObject
    if ns.source.startswith("http://") or ns.source.startswith("https://"):
        media_obj = route_url(ns.source, sensitivity=SensitivityLevel(ns.sensitivity))
    else:
        media_obj = route_file(ns.source, sensitivity=SensitivityLevel(ns.sensitivity))
    payload = media_inspect(media_obj)
    _json_print(payload)
    return 0 if payload.get("success") else 1


def cmd_ocr(ns: argparse.Namespace) -> int:
    # Build MediaObject
    if ns.source.startswith("http://") or ns.source.startswith("https://"):
        media = route_url(ns.source, sensitivity=SensitivityLevel(ns.sensitivity))
    else:
        media = route_file(ns.source, sensitivity=SensitivityLevel(ns.sensitivity))
    trackers = new_trackers() if ns.track else None
    payload = media_ocr(media, language=ns.language, trackers=trackers)
    _json_print(payload)
    return 0 if payload.get("success") else 1


def cmd_transcribe(ns: argparse.Namespace) -> int:
    if ns.source.startswith("http://") or ns.source.startswith("https://"):
        media = route_url(ns.source, sensitivity=SensitivityLevel(ns.sensitivity))
    else:
        media = route_file(ns.source, sensitivity=SensitivityLevel(ns.sensitivity))
    trackers = new_trackers() if ns.track else None
    payload = media_transcribe(media, trackers=trackers)
    _json_print(payload)
    return 0 if payload.get("success") else 1


def cmd_analyze(ns: argparse.Namespace) -> int:
    if ns.source.startswith("http://") or ns.source.startswith("https://"):
        media = route_url(ns.source, sensitivity=SensitivityLevel(ns.sensitivity))
    else:
        media = route_file(ns.source, sensitivity=SensitivityLevel(ns.sensitivity))
    trackers = new_trackers() if ns.track else None
    payload = media_analyze(media, question=ns.question, trackers=trackers)
    _json_print(payload)
    return 0 if payload.get("success") else 1


def cmd_embed(ns: argparse.Namespace) -> int:
    if ns.source.startswith("http://") or ns.source.startswith("https://"):
        media = route_url(ns.source, sensitivity=SensitivityLevel(ns.sensitivity))
    else:
        media = route_file(ns.source, sensitivity=SensitivityLevel(ns.sensitivity))
    store = _store_from_args(ns)
    payload = media_embed(media, model=ns.model, store=store)
    _json_print(payload)
    return 0 if payload.get("success") else 1


def cmd_search(ns: argparse.Namespace) -> int:
    store = _store_from_args(ns)
    payload = media_search(ns.query, limit=ns.limit, kinds=ns.kind.split(",") if ns.kind else None, store=store)
    _json_print(payload)
    return 0 if payload.get("success") else 1


def cmd_convert(ns: argparse.Namespace) -> int:
    # Build MediaObject
    if ns.source.startswith("http://") or ns.source.startswith("https://"):
        media = route_url(ns.source, sensitivity=SensitivityLevel(ns.sensitivity))
    else:
        media = route_file(ns.source, sensitivity=SensitivityLevel(ns.sensitivity))
    payload = media_convert(media, target_format=ns.format, output_path=ns.output)
    _json_print(payload)
    return 0 if payload.get("success") else 1


def cmd_stream(ns: argparse.Namespace) -> int:
    payload = media_stream(ns.source, kind=ns.kind, max_frames=ns.max_frames)
    _json_print(payload)
    return 0 if payload.get("success") else 1


def cmd_export(ns: argparse.Namespace) -> int:
    # Build MediaObject
    if ns.source.startswith("http://") or ns.source.startswith("https://"):
        media = route_url(ns.source, sensitivity=SensitivityLevel(ns.sensitivity))
    else:
        media = route_file(ns.source, sensitivity=SensitivityLevel(ns.sensitivity))
    payload = media_export(media, output_path=ns.output, export_format=ns.format)
    _json_print(payload)
    return 0 if payload.get("success") else 1


def _err(message: str) -> int:
    print(json.dumps({"success": False, "error": message}, indent=2))
    return 1


def build_parser(parent_subparsers: Any) -> argparse.ArgumentParser:
    parser = parent_subparsers.add_parser(
        "media",
        help="Multimodal perception, analysis, memory, and streaming.",
        description="Media subcommand group for ingesting, inspecting, OCR, transcription, analysis, embedding, search, conversion, streaming, and export.",
    )
    sub = parser.add_subparsers(dest="media_command", required=True)

    # ingest
    p_ingest = sub.add_parser("ingest", help="Normalize input to a MediaObject")
    p_ingest.add_argument("source", help="file path, URL, or base64 blob")
    p_ingest.add_argument("-t", "--type", choices=["image", "audio", "video", "document", "screen", "camera"], help="force media type")
    p_ingest.add_argument("-s", "--sensitivity", choices=["public", "private", "sensitive", "restricted"], default="private", help="data sensitivity")
    p_ingest.add_argument("-d", "--description", help="freeform description for metadata")
    p_ingest.set_defaults(func=cmd_ingest)

    # inspect
    p_inspect = sub.add_parser("inspect", help="Show metadata + privacy classification")
    p_inspect.add_argument("source", nargs="?", help="file path or URL")
    p_inspect.add_argument("--media-id", help="lookup by media ID (not implemented)")
    p_inspect.add_argument("-s", "--sensitivity", choices=["public", "private", "sensitive", "restricted"], default="private", help="assumed sensitivity if source needs routing")
    p_inspect.set_defaults(func=cmd_inspect)

    # ocr
    p_ocr = sub.add_parser("ocr", help="Run OCR on image/document/screen")
    p_ocr.add_argument("source", help="file path or URL")
    p_ocr.add_argument("-l", "--language", help="OCR language hint (e.g. eng, fra)")
    p_ocr.add_argument("--track", action="store_true", help="record provenance & confidence")
    p_ocr.set_defaults(func=cmd_ocr)

    # transcribe
    p_transcribe = sub.add_parser("transcribe", help="Transcribe audio/video")
    p_transcribe.add_argument("source", help="file path or URL")
    p_transcribe.add_argument("--track", action="store_true", help="record provenance & confidence")
    p_transcribe.set_defaults(func=cmd_transcribe)

    # analyze
    p_analyze = sub.add_parser("analyze", help="Describe image/video/document with a question")
    p_analyze.add_argument("source", help="file path or URL")
    p_analyze.add_argument("-q", "--question", default="Describe this content.", help="question to ask the model")
    p_analyze.add_argument("--track", action="store_true", help="record provenance & confidence")
    p_analyze.set_defaults(func=cmd_analyze)

    # embed
    p_embed = sub.add_parser("embed", help="Store media reference (+ optional embedding)")
    p_embed.add_argument("source", help="file path or URL")
    p_embed.add_argument("-m", "--model", default="text-embedding-3-small", help="embedding model name")
    p_embed.add_argument("--store", choices=["private", "shared"], default="private", help="where to store the reference")
    p_embed.set_defaults(func=cmd_embed)

    # search
    p_search = sub.add_parser("search", help="Retrieve by token overlap (light RAG)")
    p_search.add_argument("query", help="search text")
    p_search.add_argument("-l", "--limit", type=int, default=10, help="max results")
    p_search.add_argument("-k", "--kind", help="comma-separated kinds to filter (image,audio,video,document,text,fact)")
    p_search.set_defaults(func=cmd_search)

    # convert
    p_convert = sub.add_parser("convert", help="Resize/change image format")
    p_convert.add_argument("source", help="file path or URL")
    p_convert.add_argument("-f", "--format", choices=["png", "jpg", "jpeg", "webp", "bmp", "tiff"], default="png", help="target format")
    p_convert.add_argument("-o", "--output", help="output path (default: <source>.<format>)")
    p_convert.set_defaults(func=cmd_convert)

    # stream
    p_stream = sub.add_parser("stream", help="Push a frame into a bounded stream")
    p_stream.add_argument("source", help="file path, URL, or device index (e.g. 0 for webcam)")
    p_stream.add_argument("-k", "--kind", choices=["audio", "video", "screen"], default="audio", help="stream kind")
    p_stream.add_argument("--max-frames", type=int, default=500, help="maximum frames to retain")
    p_stream.set_defaults(func=cmd_stream)

    # export
    p_export = sub.add_parser("export", help="Dump media metadata to JSON")
    p_export.add_argument("source", help="file path or URL")
    p_export.add_argument("-o", "--output", required=True, help="output JSON path")
    p_export.add_argument("-f", "--format", choices=["json", "text"], default="json", help="export format")
    p_export.set_defaults(func=cmd_export)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    global logger
    import logging

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(prog="aetheros media", description="Media subcommand group")
    sub = parser.add_subparsers(dest="media_command", required=True)
    build_parser(sub)
    ns = parser.parse_args(argv)
    return ns.func(ns)  # type: ignore[attr-defined]


if __name__ == "__main__":
    sys.exit(main())
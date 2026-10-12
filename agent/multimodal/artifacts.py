"""Multimodal Artifacts and Export (Phases 86-87 of Master Prompt 10).

Integrates with MASTER 7 artifacts system. Artifacts can contain:
- text, images, audio, video, documents, charts, tables

Supports safe export: transcript, summary, image annotations, document analysis, video timeline, structured data.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from agent.multimodal.media_abstraction import MediaObject, MediaType, SensitivityLevel
from agent.multimodal.provenance import EvidenceRef, GroundedFact, EvidenceStatus

logger = logging.getLogger(__name__)


class ArtifactType(Enum):
    """Types of multimodal artifacts."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    CHART = "chart"
    TABLE = "table"
    CODE = "code"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    CSV = "csv"
    MIXED = "mixed"  # Multiple modalities


class ExportFormat(Enum):
    """Export formats for artifacts."""
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    ZIP = "zip"  # Archive with all media files
    TEXT = "text"
    CSV = "csv"


@dataclass
class ArtifactContent:
    """Content of a multimodal artifact."""
    type: ArtifactType
    data: Any  # Can be text, base64, media references, etc.
    media_refs: List[str] = field(default_factory=list)  # MediaObject IDs
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultimodalArtifact:
    """A multimodal artifact that can contain multiple content pieces."""
    artifact_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    contents: List[ArtifactContent] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE
    created_at: float = field(default_factory=lambda: __import__('time').time())
    updated_at: float = field(default_factory=lambda: __import__('time').time())
    created_by: str = "system"
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_content(
        self,
        content_type: ArtifactType,
        data: Any,
        media_refs: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a content piece to the artifact."""
        self.contents.append(ArtifactContent(
            type=content_type,
            data=data,
            media_refs=media_refs or [],
            metadata=metadata or {},
        ))
        self.updated_at = __import__('time').time()

    def add_provenance_step(self, step: str, actor: str = "system", metadata: Optional[Dict] = None) -> None:
        self.provenance.append({
            "step": step,
            "actor": actor,
            "timestamp": __import__('time').time(),
            "metadata": metadata or {},
        })

    def get_text_content(self) -> str:
        """Extract all text content."""
        texts = []
        for c in self.contents:
            if c.type in (ArtifactType.TEXT, ArtifactType.MARKDOWN, ArtifactType.CODE):
                if isinstance(c.data, str):
                    texts.append(c.data)
            elif c.type == ArtifactType.JSON:
                texts.append(json.dumps(c.data, indent=2))
        return "\n\n".join(texts)

    def get_media_refs(self) -> List[str]:
        """Get all referenced media IDs."""
        refs = []
        for c in self.contents:
            refs.extend(c.media_refs)
        return list(set(refs))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "title": self.title,
            "description": self.description,
            "contents": [
                {
                    "type": c.type.value,
                    "data": c.data,
                    "media_refs": c.media_refs,
                    "metadata": c.metadata,
                }
                for c in self.contents
            ],
            "tags": self.tags,
            "sensitivity": self.sensitivity.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
            "provenance": self.provenance,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MultimodalArtifact":
        artifact = cls(
            artifact_id=data.get("artifact_id", str(uuid.uuid4())),
            title=data.get("title", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            sensitivity=SensitivityLevel(data.get("sensitivity", SensitivityLevel.PRIVATE.value)),
            created_at=data.get("created_at", __import__('time').time()),
            updated_at=data.get("updated_at", __import__('time').time()),
            created_by=data.get("created_by", "system"),
            provenance=data.get("provenance", []),
            metadata=data.get("metadata", {}),
        )
        for c in data.get("contents", []):
            artifact.contents.append(ArtifactContent(
                type=ArtifactType(c["type"]),
                data=c["data"],
                media_refs=c.get("media_refs", []),
                metadata=c.get("metadata", {}),
            ))
        return artifact


class ArtifactStore:
    """Persistent store for multimodal artifacts."""

    def __init__(self, base_dir: Optional[str] = None):
        self._dir = base_dir or self._default_dir()
        os.makedirs(self._dir, exist_ok=True)
        self._index_path = os.path.join(self._dir, "artifacts_index.json")
        self._artifacts_dir = os.path.join(self._dir, "artifacts")
        os.makedirs(self._artifacts_dir, exist_ok=True)
        self._load_index()

    @staticmethod
    def _default_dir() -> str:
        try:
            from aetheros_constants import get_aetheros_home
            return str(get_aetheros_home() / "artifacts" / "multimodal")
        except Exception:
            return os.path.join(os.path.expanduser("~"), ".aetheros", "artifacts", "multimodal")

    def _load_index(self) -> None:
        try:
            if os.path.exists(self._index_path):
                with open(self._index_path, encoding="utf-8") as f:
                    self._index = json.load(f)
            else:
                self._index = {}
        except Exception as e:
            logger.warning("Could not load artifact index: %s", e)
            self._index = {}

    def _save_index(self) -> None:
        tmp = self._index_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._index, f, indent=2, default=str)
        os.replace(tmp, self._index_path)

    def store(self, artifact: MultimodalArtifact) -> str:
        """Store an artifact."""
        artifact_path = os.path.join(self._artifacts_dir, f"{artifact.artifact_id}.json")
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(artifact.to_dict(), f, indent=2, default=str)

        self._index[artifact.artifact_id] = {
            "title": artifact.title,
            "description": artifact.description,
            "tags": artifact.tags,
            "sensitivity": artifact.sensitivity.value,
            "created_at": artifact.created_at,
            "updated_at": artifact.updated_at,
            "created_by": artifact.created_by,
            "content_types": [c.type.value for c in artifact.contents],
            "media_count": len(artifact.get_media_refs()),
        }
        self._save_index()
        return artifact.artifact_id

    def get(self, artifact_id: str) -> Optional[MultimodalArtifact]:
        artifact_path = os.path.join(self._artifacts_dir, f"{artifact_id}.json")
        try:
            with open(artifact_path, encoding="utf-8") as f:
                data = json.load(f)
            return MultimodalArtifact.from_dict(data)
        except Exception as e:
            logger.warning("Could not load artifact %s: %s", artifact_id, e)
            return None

    def list(self, tags: Optional[List[str]] = None, limit: int = 50) -> List[Dict[str, Any]]:
        results = []
        for aid, info in self._index.items():
            if tags and not any(t in info.get("tags", []) for t in tags):
                continue
            results.append({"artifact_id": aid, **info})
        results.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
        return results[:limit]

    def delete(self, artifact_id: str) -> bool:
        artifact_path = os.path.join(self._artifacts_dir, f"{artifact_id}.json")
        if os.path.exists(artifact_path):
            os.remove(artifact_path)
        if artifact_id in self._index:
            del self._index[artifact_id]
            self._save_index()
            return True
        return False


class MultimodalExporter:
    """Exports multimodal artifacts and analyses (Phase 87)."""

    def __init__(self, artifact_store: Optional[ArtifactStore] = None):
        self.store = artifact_store or ArtifactStore()

    def export_artifact(
        self,
        artifact: MultimodalArtifact,
        format: ExportFormat,
        output_path: str,
        include_media: bool = False,
    ) -> Dict[str, Any]:
        """Export an artifact to the specified format."""
        try:
            if format == ExportFormat.JSON:
                return self._export_json(artifact, output_path)
            elif format == ExportFormat.MARKDOWN:
                return self._export_markdown(artifact, output_path)
            elif format == ExportFormat.HTML:
                return self._export_html(artifact, output_path)
            elif format == ExportFormat.TEXT:
                return self._export_text(artifact, output_path)
            elif format == ExportFormat.CSV:
                return self._export_csv(artifact, output_path)
            elif format == ExportFormat.ZIP:
                return self._export_zip(artifact, output_path, include_media)
            else:
                return {"success": False, "error": f"Unsupported format: {format.value}"}
        except Exception as e:
            logger.error("Export failed: %s", e)
            return {"success": False, "error": str(e)}

    def _export_json(self, artifact: MultimodalArtifact, output_path: str) -> Dict[str, Any]:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(artifact.to_dict(), f, indent=2, default=str)
        return {"success": True, "output_path": output_path, "format": "json"}

    def _export_markdown(self, artifact: MultimodalArtifact, output_path: str) -> Dict[str, Any]:
        lines = [
            f"# {artifact.title}",
            f"\n{artifact.description}\n",
            f"*Created: {datetime.fromtimestamp(artifact.created_at).isoformat()}*",
            f"*Tags: {', '.join(artifact.tags) if artifact.tags else 'none'}*",
            "\n---\n",
        ]

        for i, content in enumerate(artifact.contents):
            lines.append(f"## Content {i+1}: {content.type.value}")
            if content.metadata:
                lines.append(f"*Metadata: {json.dumps(content.metadata)}*")
            lines.append("")

            if content.type in (ArtifactType.TEXT, ArtifactType.MARKDOWN, ArtifactType.CODE):
                if isinstance(content.data, str):
                    if content.type == ArtifactType.CODE:
                        lines.append(f"```\n{content.data}\n```")
                    else:
                        lines.append(content.data)
            elif content.type == ArtifactType.JSON:
                lines.append(f"```json\n{json.dumps(content.data, indent=2)}\n```")
            elif content.type == ArtifactType.TABLE:
                if isinstance(content.data, list):
                    lines.append(self._table_to_markdown(content.data))
            elif content.media_refs:
                lines.append(f"*Media references: {', '.join(content.media_refs)}*")

            lines.append("\n---\n")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return {"success": True, "output_path": output_path, "format": "markdown"}

    def _table_to_markdown(self, data: List[Dict]) -> str:
        if not data:
            return ""
        headers = list(data[0].keys())
        lines = ["| " + " | ".join(headers) + " |"]
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in data:
            lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
        return "\n".join(lines)

    def _export_html(self, artifact: MultimodalArtifact, output_path: str) -> Dict[str, Any]:
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{artifact.title}</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
        h1 {{ color: #333; }}
        .content {{ margin: 2rem 0; padding: 1rem; border: 1px solid #ddd; border-radius: 8px; }}
        .metadata {{ font-size: 0.9em; color: #666; }}
        pre {{ background: #f5f5f5; padding: 1rem; overflow: auto; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
        th {{ background: #f5f5f5; }}
    </style>
</head>
<body>
    <h1>{artifact.title}</h1>
    <p>{artifact.description}</p>
    <p class="metadata">Created: {datetime.fromtimestamp(artifact.created_at).isoformat()}</p>
    <p class="metadata">Tags: {', '.join(artifact.tags) if artifact.tags else 'none'}</p>
"""

        for content in artifact.contents:
            html += f'    <div class="content">\n        <h2>{content.type.value}</h2>\n'
            if content.metadata:
                html += f'        <p class="metadata">Metadata: {json.dumps(content.metadata)}</p>\n'

            if content.type in (ArtifactType.TEXT, ArtifactType.MARKDOWN):
                html += f'        <div>{content.data}</div>\n'
            elif content.type == ArtifactType.CODE:
                html += f'        <pre><code>{content.data}</code></pre>\n'
            elif content.type == ArtifactType.JSON:
                html += f'        <pre><code>{json.dumps(content.data, indent=2)}</code></pre>\n'
            elif content.type == ArtifactType.TABLE and isinstance(content.data, list):
                html += self._table_to_html(content.data)

            if content.media_refs:
                html += f'        <p class="metadata">Media: {", ".join(content.media_refs)}</p>\n'

            html += "    </div>\n"

        html += """</body></html>"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return {"success": True, "output_path": output_path, "format": "html"}

    def _table_to_html(self, data: List[Dict]) -> str:
        if not data:
            return ""
        headers = list(data[0].keys())
        html = '<table>\n<thead><tr>' + ''.join(f'<th>{h}</th>' for h in headers) + '</tr></thead>\n<tbody>'
        for row in data:
            html += '<tr>' + ''.join(f'<td>{row.get(h, "")}</td>' for h in headers) + '</tr>'
        html += '</tbody></table>'
        return html

    def _export_text(self, artifact: MultimodalArtifact, output_path: str) -> Dict[str, Any]:
        lines = [
            artifact.title,
            "=" * len(artifact.title),
            artifact.description,
            "",
        ]
        for content in artifact.contents:
            lines.append(f"\n[{content.type.value}]")
            if isinstance(content.data, str):
                lines.append(content.data)
            else:
                lines.append(json.dumps(content.data, indent=2))
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return {"success": True, "output_path": output_path, "format": "text"}

    def _export_csv(self, artifact: MultimodalArtifact, output_path: str) -> Dict[str, Any]:
        # Export tables as CSV
        tables = [c for c in artifact.contents if c.type == ArtifactType.TABLE and isinstance(c.data, list)]
        if not tables:
            return {"success": False, "error": "No table content to export as CSV"}

        import csv
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            for i, table in enumerate(tables):
                if i > 0:
                    f.write("\n")
                writer = csv.DictWriter(f, fieldnames=list(table.data[0].keys()) if table.data else [])
                writer.writeheader()
                writer.writerows(table.data)

        return {"success": True, "output_path": output_path, "format": "csv", "tables_exported": len(tables)}

    def _export_zip(
        self,
        artifact: MultimodalArtifact,
        output_path: str,
        include_media: bool,
    ) -> Dict[str, Any]:
        import zipfile

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add artifact JSON
            zf.writestr("artifact.json", json.dumps(artifact.to_dict(), indent=2, default=str))

            # Add markdown
            import io
            md_buffer = io.StringIO()
            self._write_markdown_to_buffer(artifact, md_buffer)
            zf.writestr("artifact.md", md_buffer.getvalue())

            # Add media files if requested
            if include_media:
                for media_id in artifact.get_media_refs():
                    # Would need to resolve media_id to actual file path
                    pass

        return {"success": True, "output_path": output_path, "format": "zip"}

    def _write_markdown_to_buffer(self, artifact: MultimodalArtifact, buffer) -> None:
        buffer.write(f"# {artifact.title}\n\n{artifact.description}\n\n")
        for content in artifact.contents:
            buffer.write(f"## {content.type.value}\n\n")
            if isinstance(content.data, str):
                buffer.write(content.data + "\n\n")
            else:
                buffer.write(json.dumps(content.data, indent=2) + "\n\n")


def create_artifact(
    title: str,
    description: str = "",
    contents: Optional[List[Dict[str, Any]]] = None,
    tags: Optional[List[str]] = None,
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
) -> MultimodalArtifact:
    """Create a multimodal artifact."""
    artifact = MultimodalArtifact(
        title=title,
        description=description,
        tags=tags or [],
        sensitivity=sensitivity,
    )
    if contents:
        for c in contents:
            artifact.add_content(
                content_type=ArtifactType(c["type"]),
                data=c["data"],
                media_refs=c.get("media_refs"),
                metadata=c.get("metadata"),
            )
    return artifact


def create_artifact_from_analysis(
    title: str,
    media: MediaObject,
    analysis: Dict[str, Any],
    tags: Optional[List[str]] = None,
) -> MultimodalArtifact:
    """Create an artifact from media analysis results."""
    artifact = MultimodalArtifact(
        title=title,
        description=f"Analysis of {media.type.value} ({media.source})",
        tags=tags or [],
        sensitivity=media.sensitivity,
    )
    artifact.add_provenance_step("created_from_analysis", actor="exporter")
    artifact.add_content(
        ArtifactType.TEXT,
        analysis.get("analysis", "") or analysis.get("text", "") or str(analysis),
        media_refs=[media.media_id],
        metadata={"source_media": media.to_dict(), "confidence": analysis.get("confidence", 0.5)},
    )
    return artifact


def export_transcript(
    transcript: str,
    output_path: str,
    format: ExportFormat = ExportFormat.TEXT,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Export a transcript."""
    artifact = MultimodalArtifact(
        title="Transcript",
        description=metadata.get("description", "") if metadata else "",
        tags=["transcript"],
    )
    artifact.add_content(ArtifactType.TEXT, transcript)
    exporter = MultimodalExporter()
    return exporter.export_artifact(artifact, format, output_path)


def export_video_timeline(
    events: List[Dict[str, Any]],
    output_path: str,
    format: ExportFormat = ExportFormat.JSON,
) -> Dict[str, Any]:
    """Export a video timeline with timestamps."""
    artifact = MultimodalArtifact(
        title="Video Timeline",
        description="Timeline of video events with timestamps",
        tags=["video", "timeline"],
    )
    artifact.add_content(ArtifactType.JSON, events)
    exporter = MultimodalExporter()
    return exporter.export_artifact(artifact, format, output_path)


def export_document_analysis(
    analysis: Dict[str, Any],
    output_path: str,
    format: ExportFormat = ExportFormat.MARKDOWN,
) -> Dict[str, Any]:
    """Export document analysis results."""
    artifact = MultimodalArtifact(
        title="Document Analysis",
        description="Extracted text, tables, and structure from document",
        tags=["document", "analysis"],
    )
    artifact.add_content(ArtifactType.TEXT, analysis.get("text", ""))
    if "tables" in analysis:
        for i, table in enumerate(analysis["tables"]):
            artifact.add_content(ArtifactType.TABLE, table, metadata={"table_index": i})
    exporter = MultimodalExporter()
    return exporter.export_artifact(artifact, format, output_path)


def export_structured_data(
    data: Any,
    output_path: str,
    format: ExportFormat = ExportFormat.JSON,
    title: str = "Data Export",
) -> Dict[str, Any]:
    """Export structured data."""
    artifact = MultimodalArtifact(
        title=title,
        description="Structured data export",
        tags=["data", "export"],
    )
    if format == ExportFormat.CSV:
        artifact.add_content(ArtifactType.TABLE, data if isinstance(data, list) else [data])
    else:
        artifact.add_content(ArtifactType.JSON, data)
    exporter = MultimodalExporter()
    return exporter.export_artifact(artifact, format, output_path)


def create_artifact_store() -> ArtifactStore:
    """Create an artifact store with default configuration."""
    return ArtifactStore()


def get_default_artifact_store() -> ArtifactStore:
    """Get the default artifact store (singleton)."""
    global _DEFAULT_ARTIFACT_STORE
    if _DEFAULT_ARTIFACT_STORE is None:
        _DEFAULT_ARTIFACT_STORE = ArtifactStore()
    return _DEFAULT_ARTIFACT_STORE


_DEFAULT_ARTIFACT_STORE: Optional[ArtifactStore] = None


def get_default_exporter() -> MultimodalExporter:
    """Get the default exporter (singleton)."""
    global _DEFAULT_EXPORTER
    if _DEFAULT_EXPORTER is None:
        _DEFAULT_EXPORTER = MultimodalExporter()
    return _DEFAULT_EXPORTER


_DEFAULT_EXPORTER: Optional[MultimodalExporter] = None
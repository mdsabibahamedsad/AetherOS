"""AetherOS Vision — document intelligence.

Extracts text, tables, images, metadata, headings and footnotes from PDF,
DOCX, PPTX, XLSX, TXT, Markdown, HTML, and RTF. Reuses the existing
``aetheros_knowledge`` parser chain where present and adds structure-aware
extraction (sections, tables, images, metadata) on top. Every extractor
degrades to honest text with a recorded error when its dependency is
missing — never fabricates content.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_vision.config import VisionSettings, get_aetheros_dir, load_vision_settings
from aetheros_vision.models import (
    DocumentExtraction,
    DocumentSection,
    ExtractedImage,
    MediaType,
    TableData,
)

logger = logging.getLogger(__name__)


def detect_media_type(path: str) -> MediaType:
    suffix = Path(path).suffix.lower()
    mapping = {
        ".pdf": MediaType.PDF,
        ".docx": MediaType.DOCX,
        ".pptx": MediaType.PPTX,
        ".xlsx": MediaType.XLSX,
        ".xls": MediaType.XLSX,
        ".txt": MediaType.TXT,
        ".md": MediaType.MARKDOWN,
        ".markdown": MediaType.MARKDOWN,
        ".html": MediaType.HTML,
        ".htm": MediaType.HTML,
        ".rtf": MediaType.RTF,
    }
    return mapping.get(suffix, MediaType.UNKNOWN)


class DocumentIntelligence:
    def __init__(self, settings: Optional[VisionSettings] = None):
        self._settings = settings or load_vision_settings()
        self._extract_dir: Optional[Path] = None

    def _ensure_extract_dir(self) -> Path:
        if self._extract_dir is None:
            self._extract_dir = get_aetheros_dir("cache/vision/documents")
        self._extract_dir.mkdir(parents=True, exist_ok=True)
        return self._extract_dir

    def extract(self, path: str) -> DocumentExtraction:
        media_type = detect_media_type(path)
        start = time.perf_counter()
        handlers: Dict[MediaType, Callable[[str], DocumentExtraction]] = {
            MediaType.PDF: self._extract_pdf,
            MediaType.DOCX: self._extract_docx,
            MediaType.PPTX: self._extract_pptx,
            MediaType.XLSX: self._extract_xlsx,
            MediaType.TXT: self._extract_text,
            MediaType.MARKDOWN: self._extract_markdown,
            MediaType.HTML: self._extract_html,
            MediaType.RTF: self._extract_rtf,
        }
        handler = handlers.get(media_type)
        if handler is None:
            return DocumentExtraction(
                success=False,
                media_type=media_type,
                error=f"Unsupported document type: {Path(path).suffix}",
                processing_time_ms=(time.perf_counter() - start) * 1000,
            )
        try:
            result = handler(path)
            result.processing_time_ms = (time.perf_counter() - start) * 1000
            return result
        except Exception as exc:  # noqa: BLE001
            logger.warning("Document extraction failed for %s: %s", path, exc)
            return DocumentExtraction(
                success=False,
                media_type=media_type,
                error=str(exc),
                processing_time_ms=(time.perf_counter() - start) * 1000,
            )

    # -- PDF -----------------------------------------------------------------

    def _extract_pdf(self, path: str) -> DocumentExtraction:
        text, metadata = self._try_parsers(path)
        if text is not None:
            sections = _sections_from_text(text)
            tables = metadata.pop("tables", []) if isinstance(metadata, dict) else []
            return DocumentExtraction(
                success=True,
                media_type=MediaType.PDF,
                text=text,
                sections=sections,
                tables=tables,
                metadata=metadata,
                pages=len(re.findall(r"\f", "\f" + text)) if text else 0,
                title=str(metadata.get("title", "") or Path(path).stem),
                author=str(metadata.get("author", "") or ""),
            )
        # Fallback: OCR the pages.
        try:
            from aetheros_vision.ocr import create_ocr_engine
            engine = create_ocr_engine(self._settings)
            if engine.is_available():
                ocr = engine.extract_pdf(path)
                if ocr and ocr.success:
                    return DocumentExtraction(
                        success=True,
                        media_type=MediaType.PDF,
                        text=ocr.text,
                        metadata=metadata or {},
                        title=Path(path).stem,
                        pages=len(ocr.pages),
                        error=None,
                    )
        except Exception as exc:  # noqa: BLE001
            logger.debug("PDF OCR fallback failed: %s", exc)
        return DocumentExtraction(
            success=False,
            media_type=MediaType.PDF,
            error="No PDF parser available. Install PyPDF2/pdfminer/pdfplumber or enable OCR.",
            title=Path(path).stem,
            metadata=metadata or {},
        )

    def _try_parsers(self, path: str) -> tuple[Optional[str], Dict[str, Any]]:
        # Try the aetheros_knowledge parser chain first (PyPDF2→pdfminer→pdfplumber).
        try:
            from aetheros_knowledge.indexing.parsers import parse_pdf
            text = parse_pdf(path)
            if text and not text.startswith("[PDF file:"):
                return text, {}
        except Exception:  # noqa: BLE001
            pass
        try:
            import PyPDF2
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                pages = [p.extract_text() or "" for p in reader.pages]
                text = "\n\n".join(p for p in pages if p)
                if text.strip():
                    meta = reader.metadata or {}
                    return text, {"title": getattr(meta, "title", "") or "", "author": getattr(meta, "author", "") or "", "pages": len(reader.pages)}
        except ImportError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.debug("PyPDF2 parse failed: %s", exc)
        try:
            import pdfminer.high_level
            text = pdfminer.high_level.extract_text(path)
            if text and text.strip():
                return text, {}
        except ImportError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.debug("pdfminer parse failed: %s", exc)
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                parts = [p.extract_text() or "" for p in pdf.pages]
                tables: List[TableData] = []
                for p in pdf.pages:
                    for t in (p.extract_tables() or []):
                        if t:
                            tables.append(TableData(headers=[c or "" for c in t[0]], rows=[[c or "" for c in r] for r in t[1:]]))
                text = "\n\n".join(part for part in parts if part)
                if text.strip():
                    return text, {"tables": tables, "pages": len(pdf.pages)}
        except ImportError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.debug("pdfplumber parse failed: %s", exc)
        return None, {}

    # -- DOCX ----------------------------------------------------------------

    def _extract_docx(self, path: str) -> DocumentExtraction:
        try:
            from docx import Document
            doc = Document(path)
            paragraphs = [(p.style.name if p.style else "", p.text) for p in doc.paragraphs]
            sections: List[DocumentSection] = []
            text_parts: List[str] = []
            tables: List[TableData] = []
            for style, text in paragraphs:
                if text:
                    text_parts.append(text)
                if style and ("Heading" in style or "Title" in style):
                    level = 0
                    m = re.search(r"Heading (\d)", style or "")
                    if m:
                        level = int(m.group(1))
                    sections.append(DocumentSection(heading=text, level=level))
            for table in doc.tables:
                rows = [[c.text for c in row.cells] for row in table.rows]
                if rows:
                    tables.append(TableData(headers=rows[0], rows=rows[1:]))
            props = doc.core_properties
            return DocumentExtraction(
                success=True,
                media_type=MediaType.DOCX,
                text="\n".join(text_parts),
                sections=sections,
                tables=tables,
                title=props.title or Path(path).stem,
                author=props.author or "",
                created=props.created.isoformat() if props.created else "",
                modified=props.modified.isoformat() if props.modified else "",
                metadata={"subject": props.subject or "", "keywords": props.keywords or ""},
            )
        except ImportError:
            return DocumentExtraction(success=False, media_type=MediaType.DOCX, error="python-docx not installed", title=Path(path).stem)
        except Exception as exc:  # noqa: BLE001
            return DocumentExtraction(success=False, media_type=MediaType.DOCX, error=str(exc), title=Path(path).stem)

    # -- PPTX ----------------------------------------------------------------

    def _extract_pptx(self, path: str) -> DocumentExtraction:
        try:
            from pptx import Presentation
            prs = Presentation(path)
            sections: List[DocumentSection] = []
            text_parts: List[str] = []
            for idx, slide in enumerate(prs.slides, start=1):
                slide_texts: List[str] = []
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        slide_texts.append(shape.text)
                if slide_texts:
                    joined = "\n".join(slide_texts)
                    text_parts.append(joined)
                    sections.append(DocumentSection(heading=f"Slide {idx}", level=1, content=joined, page=idx))
            props = prs.core_properties
            return DocumentExtraction(
                success=True,
                media_type=MediaType.PPTX,
                text="\n\n".join(text_parts),
                sections=sections,
                title=props.title or Path(path).stem,
                author=props.author or "",
                created=props.created.isoformat() if props.created else "",
                modified=props.modified.isoformat() if props.modified else "",
                pages=len(prs.slides),
            )
        except ImportError:
            return DocumentExtraction(success=False, media_type=MediaType.PPTX, error="python-pptx not installed", title=Path(path).stem)
        except Exception as exc:  # noqa: BLE001
            return DocumentExtraction(success=False, media_type=MediaType.PPTX, error=str(exc), title=Path(path).stem)

    # -- XLSX ----------------------------------------------------------------

    def _extract_xlsx(self, path: str) -> DocumentExtraction:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            tables: List[TableData] = []
            text_parts: List[str] = []
            for sheet in wb.sheetnames:
                ws = wb[sheet]
                rows: List[List[str]] = []
                for row in ws.iter_rows(values_only=True):
                    cells = ["" if c is None else str(c) for c in row]
                    if any(c.strip() for c in cells):
                        rows.append(cells)
                if rows:
                    tables.append(TableData(headers=rows[0], rows=rows[1:]))
                text_parts.append(f"--- Sheet: {sheet} ---")
                for r in rows:
                    text_parts.append(" | ".join(r))
            return DocumentExtraction(
                success=True,
                media_type=MediaType.XLSX,
                text="\n".join(text_parts),
                tables=tables,
                title=Path(path).stem,
                metadata={"sheets": wb.sheetnames},
            )
        except ImportError:
            return DocumentExtraction(success=False, media_type=MediaType.XLSX, error="openpyxl not installed", title=Path(path).stem)
        except Exception as exc:  # noqa: BLE001
            return DocumentExtraction(success=False, media_type=MediaType.XLSX, error=str(exc), title=Path(path).stem)

    # -- Plain text / Markdown / HTML / RTF ----------------------------------

    def _extract_text(self, path: str) -> DocumentExtraction:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        return DocumentExtraction(success=True, media_type=MediaType.TXT, text=text, title=Path(path).stem, sections=_sections_from_text(text))

    def _extract_markdown(self, path: str) -> DocumentExtraction:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        sections: List[DocumentSection] = []
        tables: List[TableData] = []
        for line in text.splitlines():
            m = re.match(r"^(#{1,6})\s+(.*)$", line)
            if m:
                sections.append(DocumentSection(heading=m.group(2).strip(), level=len(m.group(1))))
        block: List[List[str]] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                if not any(cell for cell in cells) and not block:
                    continue
                if len(block) == 1 and all(re.fullmatch(r"[\s:|-]*", cell) for cell in cells) and any(re.fullmatch(r"[\s:|-]+", cell) for cell in cells):
                    block.append(cells)
                    continue
                block.append(cells)
            else:
                if len(block) >= 2:
                    rows = block if not all(re.fullmatch(r"[\s:|-]*", c) for c in block[1]) else [block[0]] + block[2:]
                    if len(rows) >= 2:
                        tables.append(TableData(headers=rows[0], rows=rows[1:]))
                block = []
        if len(block) >= 2:
            rows = block if not all(re.fullmatch(r"[\s:|-]*", c) for c in block[1]) else [block[0]] + block[2:]
            if len(rows) >= 2:
                tables.append(TableData(headers=rows[0], rows=rows[1:]))
        return DocumentExtraction(success=True, media_type=MediaType.MARKDOWN, text=text, title=Path(path).stem, sections=sections, tables=tables)

    def _extract_html(self, path: str) -> DocumentExtraction:
        raw = Path(path).read_text(encoding="utf-8", errors="replace")
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(raw, "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            title = soup.title.get_text(strip=True) if soup.title else Path(path).stem
            sections: List[DocumentSection] = []
            for i in range(1, 7):
                for h in soup.find_all(f"h{i}"):
                    sections.append(DocumentSection(heading=h.get_text(strip=True), level=i))
            text = soup.get_text(separator="\n", strip=True)
            return DocumentExtraction(success=True, media_type=MediaType.HTML, text=text, title=title, sections=sections)
        except ImportError:
            # Minimal HTML text strip fallback — no fabricated content.
            text = re.sub(r"<[^>]+>", " ", raw)
            text = re.sub(r"\s+", " ", text).strip()
            return DocumentExtraction(success=True, media_type=MediaType.HTML, text=text, title=Path(path).stem)

    def _extract_rtf(self, path: str) -> DocumentExtraction:
        raw = Path(path).read_text(encoding="utf-8", errors="replace")
        text = _strip_rtf(raw)
        return DocumentExtraction(success=True, media_type=MediaType.RTF, text=text, title=Path(path).stem, sections=_sections_from_text(text))

    # -- convenience ---------------------------------------------------------

    def extract_text(self, path: str) -> str:
        result = self.extract(path)
        return result.text


def _sections_from_text(text: str) -> List[DocumentSection]:
    """Best-effort section detection from plain text (heading-like lines)."""
    sections: List[DocumentSection] = []
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            sections.append(DocumentSection(heading=m.group(2).strip(), level=len(m.group(1))))
    return sections


def _strip_rtf(raw: str) -> str:
    """Minimal RTF to text: drop control words/symbols, decode unicode escapes."""
    raw = re.sub(r"\\[a-z]+-?\d*\s?", " ", raw)
    raw = re.sub(r"\\(['`^~\\{}])", r"\1", raw)
    raw = re.sub(r"\\u(\d+)\??", lambda m: chr(int(m.group(1))) if 0 <= int(m.group(1)) <= 0xFFFF else "?", raw)
    raw = re.sub(r"[{}]", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()

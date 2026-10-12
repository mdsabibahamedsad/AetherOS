"""Document ingestion into the evidence pipeline (P31-35).

Self-contained parser chain that PRESERVES PAGE NUMBERS for PDFs (the
known weakness of the legacy ``aetheros_vision`` path), extracts structured
tables where possible, and clearly marks OCR-derived pages.

All heavy libraries are optional; every failure degrades to a warning, not
an exception, so research tasks never die on a malformed document.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional
from xml.etree import ElementTree


@dataclass
class DocumentPage:
    number: int
    text: str
    ocr: bool = False


@dataclass
class DocumentTable:
    headers: List[str]
    rows: List[List[str]]
    page: Optional[int] = None
    origin: str = ""

    def to_markdown(self) -> str:
        headers = [h or "" for h in self.headers]
        out = ["| " + " | ".join(headers) + " |"]
        out.append("|" + "|".join(["---"] * len(headers)) + "|")
        for row in self.rows[:50]:
            cells = [(c if c is not None else "") for c in row]
            out.append("| " + " | ".join(str(c) for c in cells) + " |")
        return "\n".join(out)


@dataclass
class IngestedDocument:
    path: str
    kind: str
    title: str
    pages: List[DocumentPage] = field(default_factory=list)
    tables: List[DocumentTable] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    ocr_pages: int = 0
    warnings: List[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text)

    def page_of_offset(self, offset_chars: int) -> int:
        """Locate which page a character offset falls in (provenance)."""
        seen = 0
        for page in self.pages:
            end = seen + len(page.text) + 2
            if offset_chars < end:
                return page.number
            seen = end
        return self.pages[-1].number if self.pages else 0


_TEXT_KINDS = {
    ".txt": "text",
    ".md": "markdown",
    ".markdown": "markdown",
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".tsx": "code",
    ".go": "code",
    ".rs": "code",
    ".java": "code",
    ".c": "code",
    ".cpp": "code",
    ".sh": "code",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".csv": "csv",
    ".html": "html",
    ".htm": "html",
}


def _split_markdown_tables(text: str, page_number: int = 1) -> List[DocumentTable]:
    tables: List[DocumentTable] = []
    lines = text.splitlines()
    block: List[str] = []
    for line in lines + [""]:
        if re.match(r"^\s*\|.+\|\s*$", line):
            block.append(line.strip())
            continue
        if len(block) >= 2:
            header_cells = [c.strip() for c in block[0].strip("|").split("|")]
            body_rows = []
            start = 1
            if re.match(r"^\s*\|?[\s:\-|]+\|?\s*$", block[1]):
                start = 2
            for raw in block[start:]:
                cells = [c.strip() for c in raw.strip("|").split("|")]
                cells += [""] * (len(header_cells) - len(cells))
                body_rows.append(cells[: len(header_cells)])
            tables.append(
                DocumentTable(headers=header_cells, rows=body_rows, page=page_number,
                              origin="markdown")
            )
        block = []
    return tables


def _html_to_text(html: str) -> str:
    from html.parser import HTMLParser

    class Stripper(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts: List[str] = []
            self._skip = 0

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self._skip += 1
            if tag in ("p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4"):
                self.parts.append("\n")

        def handle_endtag(self, tag):
            if tag in ("script", "style") and self._skip:
                self._skip -= 1

        def handle_data(self, data):
            if not self._skip and data.strip():
                self.parts.append(data)

    s = Stripper()
    s.feed(html)
    return re.sub(r"\n{3,}", "\n\n", "".join(s.parts))


def _html_tables(html: str) -> List[DocumentTable]:
    tables: List[DocumentTable] = []
    for tbl_match in re.finditer(r"<table[^>]*>(.*?)</table>", html, re.S | re.I):
        body = tbl_match.group(1)
        rows: List[List[str]] = []
        for tr in re.finditer(r"<tr[^>]*>(.*?)</tr>", body, re.S | re.I):
            cells = [
                re.sub(r"<[^>]+>", "", c).strip()
                for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr.group(1), re.S | re.I)
            ]
            if cells:
                rows.append(cells)
        if len(rows) >= 2:
            tables.append(
                DocumentTable(headers=rows[0], rows=rows[1:], page=1, origin="html")
            )
    return tables


class DocumentIngestion:
    """Ingest authorized local/user-provided documents into research state."""

    def __init__(self, max_bytes: int = 20 * 1024 * 1024):
        self.max_bytes = max_bytes

    def ingest(self, path: str) -> IngestedDocument:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"document not found: {path}")
        size = p.stat().st_size
        if size > self.max_bytes:
            raise ValueError(f"document too large ({size} bytes > {self.max_bytes})")
        suffix = p.suffix.lower()
        if suffix == ".pdf":
            return self._ingest_pdf(p)
        if suffix == ".docx":
            return self._ingest_docx(p)
        if suffix == ".xlsx":
            return self._ingest_xlsx(p)
        if suffix == ".pptx":
            return self._ingest_pptx(p)
        if suffix in _TEXT_KINDS:
            return self._ingest_text(p, _TEXT_KINDS[suffix])
        raise ValueError(f"unsupported document type: {suffix}")

    # -- text family -------------------------------------------------------

    def _ingest_text(self, p: Path, kind: str) -> IngestedDocument:
        raw = p.read_text(encoding="utf-8", errors="replace")
        doc = IngestedDocument(
            path=str(p), kind=kind, title=p.stem, metadata={"size": str(p.stat().st_size)}
        )
        if kind == "html":
            text = _html_to_text(raw)
            doc.tables = _html_tables(raw)
        elif kind == "csv":
            rows = list(csv.reader(io.StringIO(raw)))
            if rows:
                doc.tables.append(
                    DocumentTable(headers=rows[0], rows=[[str(c) for c in r] for r in rows[1:]],
                                  page=1, origin="csv")
                )
            text = "\n".join(",".join(str(c) for c in r) for r in rows[:200])
        elif kind == "json":
            text = raw
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    doc.metadata["json_keys"] = ",".join(list(parsed)[:20])
            except json.JSONDecodeError:
                doc.warnings.append("malformed_json_treated_as_text")
        elif kind == "xml":
            text = raw
            try:
                ElementTree.fromstring(raw)
            except ElementTree.ParseError:
                doc.warnings.append("malformed_xml_treated_as_text")
        else:
            text = raw
        if kind == "markdown":
            doc.tables = _split_markdown_tables(text)
        doc.pages = [DocumentPage(number=1, text=text)]
        return doc

    # -- PDF -----------------------------------------------------------------

    def _ingest_pdf(self, p: Path) -> IngestedDocument:
        doc = IngestedDocument(path=str(p), kind="pdf", title=p.stem)
        for parser in (self._pdf_via_pdfplumber, self._pdf_via_pypdf,
                       self._pdf_via_pdfminer, self._pdf_via_ocr):
            if parser(p, doc):
                break
        if not doc.pages:
            doc.warnings.append(
                "no PDF library available; install pypdf or pdfplumber "
                "(or tesseract for OCR)"
            )
        doc.ocr_pages = sum(1 for pg in doc.pages if pg.ocr)
        if doc.ocr_pages:
            doc.metadata["ocr"] = f"{doc.ocr_pages}/{len(doc.pages)} pages"
        return doc

    def _pdf_via_pypdf(self, p: Path, doc: IngestedDocument) -> bool:
        try:
            try:
                from pypdf import PdfReader
            except ImportError:
                from PyPDF2 import PdfReader
        except ImportError:
            return False
        try:
            reader = PdfReader(str(p))
            try:
                for k, v in dict(reader.metadata or {}).items():
                    if v:
                        doc.metadata[str(k).strip("/").lower()] = str(v)[:200]
            except Exception:
                pass
            pages = []
            for i, page in enumerate(reader.pages, start=1):
                pages.append(DocumentPage(number=i, text=page.extract_text() or ""))
            if not pages:
                return False
            doc.pages = pages
            return True
        except Exception as exc:
            doc.warnings.append(f"pypdf_failed:{exc}")
            return False

    def _pdf_via_pdfplumber(self, p: Path, doc: IngestedDocument) -> bool:
        try:
            import pdfplumber
        except ImportError:
            return False
        pages: List[DocumentPage] = []
        tables: List[DocumentTable] = []
        try:
            with pdfplumber.open(str(p)) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    pages.append(DocumentPage(number=i, text=page.extract_text() or ""))
                    for t in page.extract_tables() or []:
                        if not t:
                            continue
                        header = [str(c or "") for c in t[0]]
                        rows = [[str(c or "") for c in r] for r in t[1:]]
                        tables.append(
                            DocumentTable(headers=header, rows=rows, page=i,
                                          origin="pdfplumber")
                        )
        except Exception as exc:
            doc.warnings.append(f"pdfplumber_failed:{exc}")
            return False
        if not pages:
            return False
        doc.pages = pages
        doc.tables = tables
        return True

    def _pdf_via_pdfminer(self, p: Path, doc: IngestedDocument) -> bool:
        try:
            from pdfminer.high_level import extract_pages
            from pdfminer.layout import LTTextContainer
        except ImportError:
            return False
        pages: List[DocumentPage] = []
        try:
            for i, layout in enumerate(extract_pages(str(p)), start=1):
                chunks = [
                    element.get_text()
                    for element in layout
                    if isinstance(element, LTTextContainer)
                ]
                pages.append(DocumentPage(number=i, text="".join(chunks)))
        except Exception:
            return False
        if not pages:
            return False
        doc.pages = pages
        return True

    def _pdf_via_ocr(self, p: Path, doc: IngestedDocument) -> bool:
        """Last-resort scanned-PDF OCR; pages are explicitly marked ocr=True."""
        try:
            from pdf2image import convert_from_path
            import pytesseract
        except ImportError:
            return False
        try:
            images = convert_from_path(str(p))
        except Exception as exc:
            doc.warnings.append(f"ocr_rasterize_failed:{exc}")
            return True
        pages: List[DocumentPage] = []
        for i, image in enumerate(images, start=1):
            try:
                text = pytesseract.image_to_string(image)
            except Exception:
                text = ""
            pages.append(DocumentPage(number=i, text=text, ocr=True))
        doc.pages = pages
        return True

    # -- office --------------------------------------------------------------

    def _ingest_docx(self, p: Path) -> IngestedDocument:
        doc = IngestedDocument(path=str(p), kind="docx", title=p.stem)
        try:
            import docx
        except ImportError:
            doc.warnings.append("python-docx not installed")
            return doc
        try:
            d = docx.Document(str(p))
            paras = [par.text for par in d.paragraphs if par.text.strip()]
            doc.pages = [DocumentPage(number=1, text="\n".join(paras))]
            for t in d.tables:
                rows = [[cell.text for cell in row.cells] for row in t.rows]
                if rows:
                    doc.tables.append(
                        DocumentTable(headers=rows[0], rows=rows[1:], page=1,
                                      origin="docx")
                    )
        except Exception as exc:
            doc.warnings.append(f"docx_parse_failed:{exc}")
        return doc

    def _ingest_xlsx(self, p: Path) -> IngestedDocument:
        doc = IngestedDocument(path=str(p), kind="xlsx", title=p.stem)
        try:
            import openpyxl
        except ImportError:
            doc.warnings.append("openpyxl not installed")
            return doc
        try:
            wb = openpyxl.load_workbook(str(p), read_only=True, data_only=True)
            for sheet in wb.worksheets:
                rows = [
                    [("" if c is None else str(c)) for c in row]
                    for row in sheet.iter_rows(values_only=True)
                    if any(c is not None and str(c).strip() for c in row)
                ]
                if not rows:
                    continue
                doc.pages.append(
                    DocumentPage(number=len(doc.pages) + 1,
                                 text=f"[sheet: {sheet.title}]")
                )
                doc.tables.append(
                    DocumentTable(headers=rows[0], rows=rows[1:],
                                  page=len(doc.pages), origin=f"xlsx:{sheet.title}")
                )
        except Exception as exc:
            doc.warnings.append(f"xlsx_parse_failed:{exc}")
        return doc

    def _ingest_pptx(self, p: Path) -> IngestedDocument:
        doc = IngestedDocument(path=str(p), kind="pptx", title=p.stem)
        try:
            from pptx import Presentation
        except ImportError:
            doc.warnings.append("python-pptx not installed")
            return doc
        try:
            prs = Presentation(str(p))
            for i, slide in enumerate(prs.slides, start=1):
                texts = []
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for para in shape.text_frame.paragraphs:
                            line = "".join(run.text for run in para.runs)
                            if line.strip():
                                texts.append(line)
                doc.pages.append(DocumentPage(number=i, text="\n".join(texts)))
        except Exception as exc:
            doc.warnings.append(f"pptx_parse_failed:{exc}")
        return doc

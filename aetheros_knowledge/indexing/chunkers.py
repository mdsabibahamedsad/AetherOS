"""Text chunking strategies."""

from __future__ import annotations

import re
from typing import Optional


def chunk_by_tokens(text: str, tokens: list[str],
                     chunk_size: int = 512,
                     overlap: int = 64) -> list[tuple[str, int, int]]:
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_text = " ".join(tokens[start:end])
        chunks.append((chunk_text, start, end))
        start += chunk_size - overlap
        if start >= len(tokens):
            break
    return chunks


def _chunk_by_markdown_headings(text: str, chunk_size: int,
                                 overlap: int) -> list[str]:
    """
    Structure-aware chunking for Markdown that preserves heading hierarchy.

    Each chunk includes its heading path (e.g., "## Section / ### Subsection")
    so retrieval context knows the document structure.
    """
    import re

    # Split on headings (ATX style # ## ### etc.)
    # Pattern: ^(#{1,6})\s+(.+)$ — captures level and title
    heading_re = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

    # Find all headings with positions
    headings = list(heading_re.finditer(text))
    if not headings:
        # No headings — fall back to paragraph chunking
        return _chunk_by_paragraph(text, chunk_size, overlap)

    chunks = []
    for i, h in enumerate(headings):
        level = len(h.group(1))
        title = h.group(2).strip()
        start = h.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        section_text = text[start:end].strip()

        # Build heading path from this and ancestor headings
        heading_path = []
        for h2 in headings[:i+1]:
            l = len(h2.group(1))
            t = h2.group(2).strip()
            if l >= level:
                break
            heading_path.append((l, t))
        heading_path.append((level, title))
        path_str = " / ".join(f"{'#'*l} {t}" for l, t in heading_path)

        if not section_text:
            continue

        # Chunk the section text with paragraph strategy, then prepend heading path
        section_chunks = _chunk_by_paragraph(section_text, chunk_size, overlap)
        for sc in section_chunks:
            if sc.strip():
                chunks.append(f"{path_str}\n\n{sc}")

    return chunks if chunks else _chunk_by_paragraph(text, chunk_size, overlap)


def chunk_text(text: str, chunk_size: int = 512,
               chunk_overlap: int = 64,
               strategy: str = "paragraph") -> list[str]:
    if strategy == "paragraph":
        return _chunk_by_paragraph(text, chunk_size, chunk_overlap)
    elif strategy == "sentence":
        return _chunk_by_sentence(text, chunk_size, chunk_overlap)
    elif strategy == "token":
        return _chunk_by_token(text, chunk_size, chunk_overlap)
    elif strategy == "fixed":
        return _chunk_fixed(text, chunk_size, chunk_overlap)
    elif strategy == "markdown":
        return _chunk_by_markdown_headings(text, chunk_size, chunk_overlap)
    else:
        return _chunk_by_paragraph(text, chunk_size, chunk_overlap)


def _chunk_by_paragraph(text: str, chunk_size: int,
                         overlap: int) -> list[str]:
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    chunks = []
    current = []
    current_len = 0
    for p in paragraphs:
        p_len = len(p.split())
        if current_len + p_len <= chunk_size:
            current.append(p)
            current_len += p_len
        else:
            if current:
                chunks.append("\n\n".join(current))
            if overlap > 0 and current:
                overlap_text = current[-min(len(current),
                                            max(1, overlap // 50)):]
                current = list(overlap_text)
                current_len = sum(len(t.split()) for t in current)
            else:
                current = []
                current_len = 0
            if p_len <= chunk_size:
                current.append(p)
                current_len = p_len
            else:
                sub_chunks = _chunk_fixed(p, chunk_size, overlap)
                chunks.extend(sub_chunks)
    if current:
        chunks.append("\n\n".join(current))
    return chunks if chunks else [text]


def _chunk_by_sentence(text: str, chunk_size: int,
                        overlap: int) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    chunks = []
    current = []
    current_len = 0
    for s in sentences:
        s_len = len(s.split())
        if current_len + s_len <= chunk_size:
            current.append(s)
            current_len += s_len
        else:
            if current:
                chunks.append(" ".join(current))
            if overlap > 0 and current:
                overlap_sentences = current[-min(len(current),
                                                  max(1, overlap // 20)):]
                current = list(overlap_sentences)
                current_len = sum(len(t.split()) for t in current)
            else:
                current = []
                current_len = 0
            if s_len <= chunk_size:
                current.append(s)
                current_len = s_len
            else:
                chunks.append(s)
    if current:
        chunks.append(" ".join(current))
    return chunks if chunks else [text]


def _chunk_by_token(text: str, chunk_size: int,
                     overlap: int) -> list[str]:
    tokens = text.split()
    chunks = []
    i = 0
    while i < len(tokens):
        end = min(i + chunk_size, len(tokens))
        chunk = " ".join(tokens[i:end])
        chunks.append(chunk)
        i += chunk_size - overlap
        if i >= len(tokens):
            break
    return chunks if chunks else [text]


def _chunk_fixed(text: str, chunk_size: int,
                  overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
        if start >= len(words):
            break
    return chunks or [text]


def chunk_by_tokens(text: str, tokens: list[str],
                     chunk_size: int = 512,
                     overlap: int = 64) -> list[tuple[str, int, int]]:
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_text = " ".join(tokens[start:end])
        chunks.append((chunk_text, start, end))
        start += chunk_size - overlap
        if start >= len(tokens):
            break
    return chunks

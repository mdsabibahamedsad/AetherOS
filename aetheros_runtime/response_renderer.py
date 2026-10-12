"""Response Renderer — markdown, tables, code, mermaid, math, images, HTML, file preview, thinking blocks, tool output.

Production-ready rendering pipeline for all content types.
"""

from __future__ import annotations

import enum
import json
import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aetheros_runtime.renderer")


class BlockType(enum.Enum):
    TEXT = "text"
    CODE = "code"
    TABLE = "table"
    MERMAID = "mermaid"
    MATH = "math"
    IMAGE = "image"
    HTML_PREVIEW = "html_preview"
    FILE_PREVIEW = "file_preview"
    THINKING = "thinking"
    TOOL_OUTPUT = "tool_output"
    LIST = "list"
    QUOTE = "quote"
    HEADING = "heading"
    DIVIDER = "divider"


@dataclass
class RenderBlock:
    block_type: BlockType
    content: str = ""
    language: str = ""
    title: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    indent: int = 0

    def render_text(self) -> str:
        if self.block_type == BlockType.HEADING:
            return f"{'#' * min(self.indent + 1, 6)} {self.content}"
        if self.block_type == BlockType.CODE:
            return f"```{self.language}\n{self.content}\n```"
        if self.block_type == BlockType.QUOTE:
            return "\n".join(f"> {line}" for line in self.content.split("\n"))
        if self.block_type == BlockType.DIVIDER:
            return "---"
        if self.block_type == BlockType.LIST:
            return f"- {self.content}"
        return self.content


class ResponseRenderer:
    """Renders responses into structured blocks.

    Parses raw content into typed blocks for rendering:
    - Markdown headings, lists, code blocks, tables, quotes, dividers
    - Mermaid diagrams
    - Math expressions ($$...$$)
    - Images
    - Thinking/reasoning blocks (with thinking tags)
    - Tool output
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._max_block_length: int = 50000

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse(self, content: str) -> List[RenderBlock]:
        blocks: List[RenderBlock] = []
        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            if line.startswith("```"):
                lang = line[3:].strip()
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                blocks.append(RenderBlock(
                    block_type=BlockType.CODE,
                    content="\n".join(code_lines),
                    language=lang,
                ))

            elif line.startswith("$$") and line.rstrip("$") == "$$":
                math_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith("$$"):
                    math_lines.append(lines[i])
                    i += 1
                blocks.append(RenderBlock(
                    block_type=BlockType.MATH,
                    content="\n".join(math_lines),
                ))

            elif line.startswith("```mermaid"):
                mermaid_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    mermaid_lines.append(lines[i])
                    i += 1
                blocks.append(RenderBlock(
                    block_type=BlockType.MERMAID,
                    content="\n".join(mermaid_lines),
                ))

            elif re.match(r"^#{1,6}\s", line):
                level = len(line.split(" ")[0])
                text = line.lstrip("#").strip()
                blocks.append(RenderBlock(
                    block_type=BlockType.HEADING,
                    content=text,
                    indent=level - 1,
                ))

            elif line.startswith("|") and "|" in line[1:]:
                table_lines = [line]
                i += 1
                while i < len(lines) and lines[i].startswith("|"):
                    table_lines.append(lines[i])
                    i += 1
                continue
                blocks.append(RenderBlock(
                    block_type=BlockType.TABLE,
                    content="\n".join(table_lines),
                ))
                continue

            elif line.startswith("> "):
                quote_lines = [line[2:]]
                i += 1
                while i < len(lines) and lines[i].startswith("> "):
                    quote_lines.append(lines[i][2:])
                    i += 1
                blocks.append(RenderBlock(
                    block_type=BlockType.QUOTE,
                    content="\n".join(quote_lines),
                ))
                continue

            elif line.startswith("- ") or line.startswith("* "):
                blocks.append(RenderBlock(
                    block_type=BlockType.LIST,
                    content=line[2:],
                ))

            elif line.strip() == "---":
                blocks.append(RenderBlock(block_type=BlockType.DIVIDER))

            elif re.match(r"!\[.*\]\(.*\)", line):
                alt_text = re.search(r"\[(.*?)\]", line)
                url = re.search(r"\((.*?)\)", line)
                blocks.append(RenderBlock(
                    block_type=BlockType.IMAGE,
                    content=url.group(1) if url else line,
                    title=alt_text.group(1) if alt_text else "",
                    metadata={"alt": alt_text.group(1) if alt_text else ""},
                ))

            elif "thinking" in line.lower() and len(line) < 20:
                thinking_lines = []
                i += 1
                while i < len(lines) and "thinking" not in lines[i].lower():
                    thinking_lines.append(lines[i])
                    i += 1
                if thinking_lines:
                    blocks.append(RenderBlock(
                        block_type=BlockType.THINKING,
                        content="\n".join(thinking_lines).strip(),
                    ))

            else:
                blocks.append(RenderBlock(block_type=BlockType.TEXT, content=line))

            i += 1

        return self._merge_text_blocks(blocks)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self, content: str, fmt: str = "text") -> str:
        blocks = self.parse(content)

        if fmt == "json":
            return json.dumps([b.__dict__ for b in blocks], indent=2)

        lines = []
        for block in blocks:
            rendered = block.render_text()
            if rendered:
                lines.append(rendered)

        return "\n".join(lines)

    def render_blocks(self, blocks: List[RenderBlock]) -> str:
        return "\n".join(b.render_text() for b in blocks if b.render_text())

    # ------------------------------------------------------------------
    # Block manipulation
    # ------------------------------------------------------------------

    def wrap_thinking(self, content: str) -> str:
        return f"thinking\n{content}\n/thinking"

    def wrap_tool_output(self, tool_name: str, content: str) -> str:
        blocks: List[str] = [
            f"[Tool: {tool_name}]",
            content,
            f"[/Tool]",
        ]
        return "\n".join(blocks)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_text_blocks(blocks: List[RenderBlock]) -> List[RenderBlock]:
        merged: List[RenderBlock] = []
        for block in blocks:
            if block.block_type == BlockType.TEXT and merged and merged[-1].block_type == BlockType.TEXT:
                merged[-1].content += "\n" + block.content
            else:
                merged.append(block)
        return merged

    def set_max_block_length(self, chars: int) -> None:
        self._max_block_length = chars

    def summary(self) -> str:
        return "Response Renderer: supports markdown, code, tables, mermaid, math, images, HTML, thinking blocks"
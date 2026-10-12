from __future__ import annotations

import logging
from typing import Any

from aetheros_automation.agents.registry import AgentRegistry, BaseAgent
from aetheros_automation.models.models import AgentRole, DocumentSpec, Task

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    @property
    def role(self) -> AgentRole:
        return AgentRole.WRITER

    async def execute(self, task: Task, context: dict | None = None) -> str:
        ctx = context or {}
        logger.info("Writer agent executing: %s", task.name)

        spec = task.metadata.get("spec")
        if isinstance(spec, dict):
            doc_spec = DocumentSpec(**spec)
        elif isinstance(spec, DocumentSpec):
            doc_spec = spec
        else:
            doc_spec = DocumentSpec(
                title=task.name,
                content=task.description,
                format=task.metadata.get("format", "markdown"),
                output_path=task.metadata.get("output_path", ""),
            )

        max_len = task.metadata.get("max_length", 500)
        text = task.metadata.get("text", task.description)

        if "summar" in task.description.lower():
            return await self.summarize(text, max_length=max_len)

        return await self.write_document(doc_spec)

    async def write_document(self, spec: DocumentSpec) -> str:
        logger.info("Writing document: %s (%s)", spec.title, spec.format)

        if spec.template:
            content = self._apply_template(spec.template, spec)
        elif spec.content:
            content = spec.content
        else:
            content = f"# {spec.title}\n\nContent for {spec.title}."

        full_doc = self._format_document(content, spec)
        logger.info("Document written: %d chars", len(full_doc))
        return full_doc

    async def summarize(self, text: str, max_length: int = 500) -> str:
        logger.info("Summarizing text (%d chars -> %d max)", len(text), max_length)

        if len(text) <= max_length:
            return text

        sentences = text.replace("\n", " ").split(". ")
        summary: list[str] = []
        current_len = 0

        first = sentences[0] if sentences else ""
        summary.append(first)
        current_len += len(first)

        for sentence in sentences[1:]:
            candidate = sentence.strip()
            if not candidate:
                continue
            if current_len + len(candidate) + 2 > max_length:
                break
            summary.append(candidate)
            current_len += len(candidate) + 2

        result = ". ".join(summary) + "."
        if len(result) > max_length:
            result = result[:max_length].rsplit(" ", 1)[0] + "..."

        return result

    def _apply_template(self, template: str, spec: DocumentSpec) -> str:
        import string
        tpl = string.Template(template)
        return tpl.safe_substitute(
            title=spec.title,
            content=spec.content,
            format=spec.format,
            output_path=spec.output_path,
        )

    def _format_document(self, content: str, spec: DocumentSpec) -> str:
        if spec.format == "html":
            return f"<!DOCTYPE html>\n<html><head><title>{spec.title}</title></head><body>\n{content}\n</body></html>"
        if spec.format in ("rst", "restructuredtext"):
            header = "=" * len(spec.title)
            return f"{header}\n{spec.title}\n{header}\n\n{content}"
        lines = [f"# {spec.title}", "", content]
        if spec.output_path:
            lines.append(f"\n---\nOutput: {spec.output_path}")
        return "\n".join(lines)


AgentRegistry.register(AgentRole.WRITER, WriterAgent)

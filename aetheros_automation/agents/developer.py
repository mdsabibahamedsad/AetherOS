from __future__ import annotations

import ast
import logging
import re
from typing import Any

from aetheros_automation.agents.registry import AgentRegistry, BaseAgent
from aetheros_automation.models.models import AgentRole, Task

logger = logging.getLogger(__name__)


class DeveloperAgent(BaseAgent):
    @property
    def role(self) -> AgentRole:
        return AgentRole.DEVELOPER

    async def execute(self, task: Task, context: dict | None = None) -> str:
        ctx = context or {}
        desc = task.description.lower()
        logger.info("Developer executing: %s", task.name)

        if "fix" in desc or "bug" in desc or "error" in desc:
            error = task.metadata.get("error", "")
            code = task.metadata.get("code", "")
            return await self.fix_bug(code, error)

        if "review" in desc:
            code = task.metadata.get("code", "")
            reviews = await self.review_code(code)
            return self._format_reviews(reviews)

        spec = task.metadata.get("spec", task.description)
        return await self.generate_code(spec)

    async def generate_code(self, spec: str) -> str:
        logger.info("Generating code from spec")
        lines = spec.strip().split("\n")
        func_name = self._infer_function_name(spec)
        imports: list[str] = []
        body_lines: list[str] = []

        for line in lines:
            stmt = line.strip()
            if stmt.startswith(("import ", "from ")):
                imports.append(stmt)
            else:
                body_lines.append(line)

        if not imports:
            imports = ["from __future__ import annotations"]

        code_parts = [*imports, "", f"def {func_name}(*args, **kwargs):"]
        if body_lines:
            for bl in body_lines:
                code_parts.append(f"    {bl}")
        else:
            code_parts.append('    """Auto-generated from spec."""')
            code_parts.append("    pass")

        code = "\n".join(code_parts)
        logger.info("Generated function: %s (%d lines)", func_name, len(code.splitlines()))
        return code

    async def fix_bug(self, code: str, error: str) -> str:
        logger.info("Fixing bug in code")
        if not code:
            return "No code provided to fix."

        lines = code.splitlines(keepends=True)
        error_lower = error.lower()

        if "nameerror" in error_lower or "is not defined" in error_lower:
            match = re.search(r"'(\w+)'", error)
            if match:
                missing = match.group(1)
                lines.insert(0, f"{missing} = None  # auto-fixed undefined name\n")

        if "indentation" in error_lower or "unexpected indent" in error_lower:
            lines = self._fix_indentation(lines)

        if "importerror" in error_lower or "module" in error_lower:
            match = re.search(r"'(.*?)'", error)
            if match:
                lines.insert(0, f"import {match.group(1)}  # auto-fixed missing import\n")

        if "typeerror" in error_lower:
            lines = self._add_type_guards(lines)

        fixed = "".join(lines)
        logger.info("Bug fix applied")
        return fixed

    async def review_code(self, code: str) -> list[dict]:
        logger.info("Reviewing code")
        issues: list[dict] = []

        if not code.strip():
            return issues

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            issues.append({
                "severity": "error",
                "line": e.lineno or 0,
                "message": f"Syntax error: {e.msg}",
            })
            return issues

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    issues.append({
                        "severity": "warning",
                        "line": node.lineno,
                        "message": f"Function '{node.name}' is empty (pass only)",
                    })
                if not node.name.islower() and not node.name.startswith("_"):
                    issues.append({
                        "severity": "style",
                        "line": node.lineno,
                        "message": f"Function '{node.name}' should use snake_case",
                    })
            if isinstance(node, ast.ClassDef):
                if not node.name[0].isupper():
                    issues.append({
                        "severity": "style",
                        "line": node.lineno,
                        "message": f"Class '{node.name}' should use PascalCase",
                    })
            if isinstance(node, ast.Try):
                if not any(h.type is None for h in node.handlers):
                    issues.append({
                        "severity": "warning",
                        "line": node.lineno,
                        "message": "Bare `except:` recommended as last handler",
                    })
            if isinstance(node, ast.Name) and node.id in ("print",):
                issues.append({
                    "severity": "info",
                    "line": node.lineno,
                    "message": "Avoid print() in production code; use logging",
                })

        for line_no, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()
            if len(line) > 120:
                issues.append({
                    "severity": "style",
                    "line": line_no,
                    "message": f"Line too long ({len(line)} > 120 chars)",
                })
            if stripped.startswith("# TODO"):
                issues.append({
                    "severity": "info",
                    "line": line_no,
                    "message": f"TODO comment: {stripped}",
                })

        return issues

    def _infer_function_name(self, spec: str) -> str:
        words = spec.strip().split()[:4]
        base = "_".join(w.lower().strip(",.!?") for w in words if w.isidentifier())
        if not base:
            base = "auto_generated"
        return base

    def _fix_indentation(self, lines: list[str]) -> list[str]:
        fixed: list[str] = []
        for line in lines:
            stripped = line.lstrip()
            if stripped and not line.startswith((" ", "\t")) and stripped not in ("\n", ""):
                if any(kw in stripped for kw in ("def ", "class ", "if ", "for ", "while ", "with ", "try:", "except", "finally", "async def")):
                    fixed.append(line)
                else:
                    fixed.append(f"    {line}")
            else:
                fixed.append(line)
        return fixed

    def _add_type_guards(self, lines: list[str]) -> list[str]:
        result: list[str] = []
        for line in lines:
            result.append(line)
            stripped = line.strip()
            if stripped.startswith("def ") and "):" in stripped:
                indent = " " * (len(line) - len(line.lstrip()))
                result.append(f"{indent}    # type guard placeholder\n")
        return result

    def _format_reviews(self, reviews: list[dict]) -> str:
        if not reviews:
            return "No issues found."
        lines = ["# Code Review"]
        for r in reviews:
            lines.append(f"\n- [{r['severity'].upper()}] Line {r['line']}: {r['message']}")
        return "\n".join(lines)


AgentRegistry.register(AgentRole.DEVELOPER, DeveloperAgent)

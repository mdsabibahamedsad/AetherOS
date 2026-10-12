from __future__ import annotations

import re
from aetheros_voice.models.models import DictationMode


class DictationModeHandler:
    def __init__(self):
        pass

    def apply(self, text: str, mode: DictationMode) -> str:
        if mode == DictationMode.PLAIN:
            return text
        elif mode == DictationMode.MARKDOWN:
            return self._to_markdown(text)
        elif mode == DictationMode.CODE:
            return self._to_code(text)
        elif mode == DictationMode.EMAIL:
            return self._to_email(text)
        return text

    def _to_markdown(self, text: str) -> str:
        lines = text.split(". ")
        result = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            words = line.split()
            if len(words) <= 3:
                result.append(f"## {line}")
            elif len(words) <= 8:
                result.append(f"### {line}")
            elif line.startswith("I") or line.startswith("We"):
                result.append(line)
            else:
                result.append(f"- {line}")
        return "\n\n".join(result)

    def _to_code(self, text: str) -> str:
        code_keywords = {
            "function": "def", "class": "class", "if": "if", "for": "for", "while": "while",
            "return": "return", "import": "import", "from": "from", "print": "print()",
        }
        lower = text.lower()
        for spoken, code_word in code_keywords.items():
            lower = lower.replace(spoken, code_word)
        return lower

    def _to_email(self, text: str) -> str:
        lines = text.split(". ")
        if len(lines) >= 2:
            greeting = f"Dear Team,\n\n"
            body = "\n".join(f"{line}." if not line.endswith(".") else line for line in lines[1:])
            closing = "\n\nBest regards,\n[Your Name]"
            return greeting + body + closing
        return text

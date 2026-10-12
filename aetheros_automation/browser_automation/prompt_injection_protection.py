from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

SUSPICIOUS_PATTERNS = [
    re.compile(r"ignore\s+all\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)\s+(above|previous)", re.IGNORECASE),
    re.compile(r"you\s+are\s+(now|not\s+an?\s+AI|actually)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(prior|previous|above)", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+are|though\s+you\s+are)", re.IGNORECASE),
    re.compile(r"new\s+instructions?:", re.IGNORECASE),
    re.compile(r"system\s+(prompt|instruction|command)", re.IGNORECASE),
    re.compile(r"overwrite|override", re.IGNORECASE),
    re.compile(r"you\s+must\s+(now|ignore)", re.IGNORECASE),
    re.compile(r"this\s+is\s+(an?\s+)?(important|critical)\s+(instruction|update)", re.IGNORECASE),
    re.compile(r"#\s*(system|instruction|command)", re.IGNORECASE),
    re.compile(r"\*\*(important|critical|warning|note)\*\*.*instruction", re.IGNORECASE),
    re.compile(r"do\s+not\s+(follow|obey|listen\s+to)", re.IGNORECASE),
    re.compile(r"pretend|imagine\s+you\s+are", re.IGNORECASE),
    re.compile(r"you\s+are\s+free|you\s+have\s+permission", re.IGNORECASE),
    re.compile(r"output\s+(only|just|exactly)", re.IGNORECASE),
    re.compile(r"respond\s+with\s+(\"|')(yes|no|ok)", re.IGNORECASE),
]


class PromptInjectionProtection:
    def __init__(self):
        self._detected_warnings: list[dict] = []

    def scan_page_content(self, html: str, text: str) -> list[dict]:
        warnings = []

        hidden_content = re.findall(
            r"<(div|span|p|font)[^>]*?(?:style|class)=[\"'][^\"']*?(?:display:\s*none|visibility:\s*hidden|opacity:\s*0)[^\"']*[\"'][^>]*>.*?</\1>",
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if hidden_content:
            warnings.append({
                "type": "hidden_content",
                "severity": "medium",
                "message": f"Found {len(hidden_content)} hidden elements that may contain concealed instructions.",
                "count": len(hidden_content),
            })

        for pattern in SUSPICIOUS_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                warnings.append({
                    "type": "suspicious_instruction",
                    "severity": "high",
                    "pattern": pattern.pattern[:80],
                    "message": f"Detected potential prompt injection pattern: '{matches[0][:100]}'",
                    "matches": len(matches),
                })
                if len(warnings) >= 5:
                    break

        base64_patterns = re.findall(
            r"[A-Za-z0-9+/]{40,}(?:=|= {0,10}=)?", text
        )
        if len(base64_patterns) > 3:
            warnings.append({
                "type": "encoded_content",
                "severity": "medium",
                "message": "Large amount of encoded content detected, may contain hidden instructions.",
                "count": len(base64_patterns),
            })

        script_injection = re.findall(
            r"<script[^>]*>[^<]*(?:eval|atob|document\.write|innerHTML)[^<]*</script>",
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if script_injection:
            warnings.append({
                "type": "script_injection",
                "severity": "high",
                "message": f"Found {len(script_injection)} script elements with dynamic code execution.",
                "count": len(script_injection),
            })

        if warnings:
            self._detected_warnings.extend(warnings)
            logger.warning("Prompt injection scan found %d warnings", len(warnings))

        return warnings

    def is_content_safe(self, html: str, text: str) -> tuple[bool, list[dict]]:
        warnings = self.scan_page_content(html, text)
        high_severity = [w for w in warnings if w.get("severity") == "high"]
        if high_severity:
            return False, high_severity
        return True, warnings

    def sanitize_user_instruction(self, instruction: str, page_text: str) -> tuple[str, bool]:
        for pattern in SUSPICIOUS_PATTERNS:
            if pattern.search(page_text):
                logger.warning("Suspicious pattern blocked: %s", pattern.pattern[:60])
                return instruction, True
        return instruction, False

    def get_warnings(self) -> list[dict]:
        return list(self._detected_warnings)

    def clear_warnings(self):
        self._detected_warnings.clear()

    def get_security_context(self, url: str) -> dict[str, Any]:
        return {
            "url": url,
            "page_is_untrusted": True,
            "user_instructions_override_page": True,
            "never_execute_page_instructions": True,
            "warnings": self._detected_warnings[-10:],
        }

    @staticmethod
    def is_sensitive_domain(url: str) -> bool:
        sensitive = [
            "bank", "pay", "login", "signin", "account", "password",
            "secure", "wallet", "crypto", "trade", "invest",
            "admin", "dashboard", "billing", "payment",
        ]
        url_lower = url.lower()
        return any(s in url_lower for s in sensitive)

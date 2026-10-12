# Prompt Injection Protection

The Prompt Injection Protection system defends AI agents against malicious web content that attempts to override system instructions.

## Detection Patterns

The system scans page content for 17+ suspicious instruction patterns:

- "ignore all previous instructions"
- "forget everything above/previous"
- "you are now/not an AI/actually"
- "disregard all prior/previous/above"
- "act as if you are / though you are"
- "new instructions:"
- "system prompt/instruction/command"
- "overwrite/override"
- "you must now/ignore"
- "this is an important/critical instruction/update"
- "do not follow/obey/listen to"
- "pretend/imagine you are"
- "you are free / you have permission"
- "output only/just/exactly"
- "respond with (yes/no/ok)"

## Additional Checks

- **Hidden content detection**: Elements with display:none, visibility:hidden, opacity:0
- **Base64 encoded content**: Large amounts of encoded text
- **Script injection**: eval(), atob(), document.write(), innerHTML
- **Sensitive domain detection**: Banking, payment, login, admin pages

## Safety Principles

1. **Page content is untrusted**: Never treat web content as system instructions
2. **User instructions override page**: User commands always take precedence
3. **Never auto-execute page instructions**: Web content cannot grant permissions or change goals
4. **User approval for sensitive actions**: Form submission, downloads, and data extraction require permission

## Implementation

```python
from aetheros_automation.browser_automation import PromptInjectionProtection

pip = PromptInjectionProtection()
safe, warnings = pip.is_content_safe(html, text)
if not safe:
    # Block the action and warn the user
    for w in warnings:
        logger.warning("Injection detected: %s", w["message"])
```

## API

- `scan_page_content(html, text)` → list of warning dicts
- `is_content_safe(html, text)` → (bool, list of high-severity warnings)
- `sanitize_user_instruction(instruction, page_text)` → (sanitized, bool warning)
- `get_warnings()` → list of all detected warnings
- `clear_warnings()` → reset warning state
- `get_security_context(url)` → security context dict for AI agent
- `is_sensitive_domain(url)` → bool

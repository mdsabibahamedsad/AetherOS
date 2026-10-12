"""
Starter Templates
=================

Provides ready-to-use starter templates for all supported plugin types.
Each template includes the minimal files needed to build, package, and
publish an Aetheros extension.

Template types:
    - ``tool`` — Tool Plugin
    - ``agent`` — Agent Plugin
    - ``workflow`` — Workflow Plugin
    - ``memory`` — Memory Plugin
    - ``model`` — Model Provider
    - ``voice`` — Voice Provider
    - ``desktop`` — Desktop Adapter
    - ``engineering`` — Engineering Extension
    - ``notification`` — Notification Adapter
    - ``enterprise`` — Enterprise Integration
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# Mapping of template type to its file contents.
# Each template is a dict of ``{relative_path: content}``.
_TEMPLATES: Dict[str, Dict[str, str]] = {}


def _register_template(template_type: str, files: Dict[str, str]) -> None:
    """Register a template."""
    _TEMPLATES[template_type] = files


def list_templates() -> List[str]:
    """Return sorted list of available template names."""
    return sorted(_TEMPLATES.keys())


def get_template(template_type: str) -> Optional[Dict[str, str]]:
    """Get a template by type. Returns {filename: content} or None."""
    return _TEMPLATES.get(template_type)


def scaffold_plugin(
    template_type: str,
    target_dir: Path,
    name: str,
    **kwargs,
) -> List[Path]:
    """Scaffold a new plugin from a template.

    Args:
        template_type: One of the registered template types.
        target_dir: Directory to create the plugin in.
        name: Plugin name (becomes the directory and package name).
        **kwargs: Template variables (description, author, etc.).

    Returns:
        List of created file paths.

    Raises:
        ValueError: If the template type is unknown.
    """
    template = _TEMPLATES.get(template_type)
    if template is None:
        raise ValueError(
            f"Unknown template type: '{template_type}'. "
            f"Available: {', '.join(list_templates())}"
        )

    target = Path(target_dir).resolve() / name
    target.mkdir(parents=True, exist_ok=True)

    created: List[Path] = []
    variables = {"name": name, "Name": name.title(), "name_upper": name.upper(),
                 "description": kwargs.get("description", ""),
                 "author": kwargs.get("author", ""), **kwargs}

    for rel_path, content in template.items():
        file_path = target / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Simple variable substitution
        rendered = content
        for key, value in variables.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value))

        file_path.write_text(rendered, encoding="utf-8")
        created.append(file_path)

    logger.info("Scaffolded %s plugin at %s (%d files)", template_type, target, len(created))
    return created


# ===========================================================================
# Template definitions
# ===========================================================================

_register_template("tool", {
    "manifest.yaml": """name: {{name}}
version: 1.0.0
description: {{description}}
author: {{author}}
kind: standalone

sdk_version: ">=1.0.0"
aetheros_version: ">=0.1.0"

permissions:
  - filesystem:read
  - workspace:read
""",
    "__init__.py": '''"""
{{name}} — {{description}}
"""

import logging
from sdk import ExtensionContext

logger = logging.getLogger(__name__)


def register(ctx: ExtensionContext) -> None:
    """Register the plugin with the Aetheros runtime."""
    logger.info("Registering plugin: %s", ctx.name)

    # Register a tool
    ctx.tools.register_tool(
        name="{{name}}_hello",
        description="Say hello from the {{name}} plugin",
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name to greet",
                }
            },
            "required": ["name"],
        },
        handler=hello_handler,
    )


def hello_handler(args: dict, **kwargs) -> str:
    """Handle the {{name}}_hello tool call."""
    import json
    name = args.get("name", "World")
    return json.dumps({"greeting": f"Hello, {name}! From {{name}}."})
''',
})

_register_template("agent", {
    "manifest.yaml": """name: {{name}}
version: 1.0.0
description: {{description}}
author: {{author}}
kind: standalone

sdk_version: ">=1.0.0"
aetheros_version: ">=0.1.0"

dependencies: []
""",
    "__init__.py": '''"""
{{name}} — {{description}}
Agent extension that hooks into the agent lifecycle.
"""

import logging
from sdk import ExtensionContext

logger = logging.getLogger(__name__)


def register(ctx: ExtensionContext) -> None:
    """Register agent lifecycle hooks."""
    logger.info("Registering agent extension: %s", ctx.name)

    # Subscribe to session lifecycle events
    ctx.events.on("session:start")(on_session_start)
    ctx.events.on("session:end")(on_session_end)


def on_session_start(event) -> None:
    """Handle session start."""
    logger.info("Session started: %s", event.data.get("session_id"))


def on_session_end(event) -> None:
    """Handle session end."""
    logger.info("Session ended: %s", event.data.get("session_id"))
''',
})

_register_template("workflow", {
    "manifest.yaml": """name: {{name}}
version: 1.0.0
description: {{description}}
author: {{author}}
kind: standalone

sdk_version: ">=1.0.0"
aetheros_version: ">=0.1.0"
""",
    "__init__.py": '''"""
{{name}} — {{description}}
Workflow plugin with composable steps.
"""

import logging
from sdk import ExtensionContext, WorkflowDef, WorkflowStep

logger = logging.getLogger(__name__)


def register(ctx: ExtensionContext) -> None:
    """Register workflows."""
    logger.info("Registering workflow: %s", ctx.name)

    # Define a workflow
    wf = ctx.workflows.define_workflow(
        "{{name}}_pipeline",
        description="Multi-step pipeline for {{description}}",
    )
    wf.steps.append(WorkflowStep(
        id="step1",
        action="{{name}}_prepare",
        params={"input": "default"},
    ))
    wf.steps.append(WorkflowStep(
        id="step2",
        action="{{name}}_process",
        params={"mode": "auto"},
        depends_on=["step1"],
    ))
    wf.steps.append(WorkflowStep(
        id="step3",
        action="{{name}}_finalize",
        params={"output": "result"},
        depends_on=["step2"],
    ))
    ctx.workflows.register_workflow(wf)
''',
})

_register_template("memory", {
    "manifest.yaml": """name: {{name}}
version: 1.0.0
description: {{description}}
author: {{author}}
kind: exclusive

sdk_version: ">=1.0.0"
aetheros_version: ">=0.1.0"
""",
    "__init__.py": '''"""
{{name}} — {{description}}
Memory provider plugin.

Implements the MemoryProvider ABC from agent/memory_provider.py.
Activated via the `memory.provider` config key.
"""

import logging
from typing import Any, Dict, List, Optional

from sdk import ExtensionContext

logger = logging.getLogger(__name__)


def register(ctx: ExtensionContext) -> None:
    """Register the memory provider."""
    logger.info("Registering memory provider: %s", ctx.name)

    from agent.memory_provider import MemoryProvider, register_memory_provider

    class {{Name}}MemoryProvider(MemoryProvider):
        """Memory provider implementation."""

        @property
        def name(self) -> str:
            return "{{name}}"

        def setup(self, **kwargs) -> None:
            logger.info("Setting up {{name}} memory provider")

        def store(self, key: str, data: Dict[str, Any]) -> None:
            logger.debug("Storing: %s", key)

        def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
            logger.debug("Searching: %s", query)
            return []

        def shutdown(self) -> None:
            logger.info("Shutting down {{name}} memory provider")

        def sync_turn(self, turn_messages: List[Dict[str, Any]]) -> None:
            """Sync a conversation turn."""

    provider = {{Name}}MemoryProvider()
    register_memory_provider(provider)
''',
})

_register_template("model", {
    "manifest.yaml": """name: {{name}}
version: 1.0.0
description: {{description}}
author: {{author}}
kind: model-provider

sdk_version: ">=1.0.0"
aetheros_version: ">=0.1.0"
""",
    "__init__.py": '''"""
{{name}} — {{description}}
Model provider plugin.

Registers a ProviderProfile with the Aetheros provider registry.
"""

import logging
from sdk import ExtensionContext

logger = logging.getLogger(__name__)


def register(ctx: ExtensionContext) -> None:
    """Register the model provider."""
    logger.info("Registering model provider: %s", ctx.name)

    from providers import register_provider
    from providers.base import ProviderProfile, OMIT_TEMPERATURE

    profile = ProviderProfile(
        name="{{name}}",
        description="{{description}}",
        api_mode="chat_completions",
        base_url="https://api.{{name}}.com/v1",
        api_key_env_var="{{name_upper}}_API_KEY",
        models=[
            "{{name}}-default",
        ],
        extra_headers={},
        features={},
    )
    register_provider(profile)
''',
})

_register_template("voice", {
    "manifest.yaml": """name: {{name}}
version: 1.0.0
description: {{description}}
author: {{author}}
kind: backend

sdk_version: ">=1.0.0"
aetheros_version: ">=0.1.0"
""",
    "__init__.py": '''"""
{{name}} — {{description}}
Voice/TTS provider plugin.
"""

import logging
from sdk import ExtensionContext

logger = logging.getLogger(__name__)


def register(ctx: ExtensionContext) -> None:
    """Register the voice/TTS provider."""
    logger.info("Registering voice provider: %s", ctx.name)

    ctx.register_tts_provider({{Name}}TTSProvider())


class {{Name}}TTSProvider:
    """Text-to-speech provider."""

    @property
    def name(self) -> str:
        return "{{name}}"

    def synthesize(self, text: str, **kwargs) -> bytes:
        """Synthesize text to speech audio bytes."""
        logger.debug("Synthesizing: %s", text[:50])
        raise NotImplementedError("Implement me!")
''',
})

_register_template("notification", {
    "manifest.yaml": """name: {{name}}
version: 1.0.0
description: {{description}}
author: {{author}}
kind: backend

sdk_version: ">=1.0.0"
aetheros_version: ">=0.1.0"
""",
    "__init__.py": '''"""
{{name}} — {{description}}
Notification adapter plugin.
"""

import logging
from sdk import ExtensionContext

logger = logging.getLogger(__name__)


def register(ctx: ExtensionContext) -> None:
    """Register the notification adapter."""
    logger.info("Registering notification adapter: %s", ctx.name)

    ctx.tools.register_tool(
        name="{{name}}_notify",
        description="Send a notification via {{name}}",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Notification title"},
                "message": {"type": "string", "description": "Notification body"},
            },
            "required": ["message"],
        },
        handler=send_notification,
    )


def send_notification(args: dict, **kwargs) -> str:
    """Send a notification."""
    import json
    title = args.get("title", "Aetheros Notification")
    message = args.get("message", "")
    logger.info("Notification: [%s] %s", title, message)
    return json.dumps({"success": True, "sent_to": "{{name}}"})
''',
})

_register_template("enterprise", {
    "manifest.yaml": """name: {{name}}
version: 1.0.0
description: {{description}}
author: {{author}}
kind: standalone

sdk_version: ">=1.0.0"
aetheros_version: ">=0.1.0"

permissions:
  - filesystem:read
  - filesystem:write
  - network:connect
  - workspace:read
""",
    "__init__.py": '''"""
{{name}} — {{description}}
Enterprise integration plugin.

For integrating with enterprise systems (SSO, audit logging, compliance).
"""

import logging
from sdk import ExtensionContext

logger = logging.getLogger(__name__)


def register(ctx: ExtensionContext) -> None:
    """Register the enterprise integration."""
    logger.info("Registering enterprise integration: %s", ctx.name)

    # Register lifecycle hooks for compliance
    ctx.events.on("user:login")(on_user_login)
    ctx.events.on("tool:executed")(on_tool_executed)

    # Register enterprise tools
    ctx.tools.register_tool(
        name="{{name}}_audit_log",
        description="Write to the enterprise audit log",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action being audited"},
                "details": {"type": "object", "description": "Audit details"},
            },
            "required": ["action"],
        },
        handler=audit_log_handler,
    )


def on_user_login(event) -> None:
    """Log user login events."""
    logger.info("Enterprise audit: user login %s", event.data)


def on_tool_executed(event) -> None:
    """Log tool execution events."""
    logger.info("Enterprise audit: tool executed %s", event.data)


def audit_log_handler(args: dict, **kwargs) -> str:
    """Write to the audit log."""
    import json
    action = args.get("action", "")
    details = args.get("details", {})
    logger.info("AUDIT: %s %s", action, details)
    return json.dumps({"logged": True, "action": action})
''',
})

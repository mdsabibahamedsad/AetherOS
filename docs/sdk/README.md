# AetherOS SDK Guide

## Overview

The AetherOS Developer SDK provides a stable, versioned API for building extensions to the Aetheros platform. The SDK is the **narrow waist** between external code and the Aetheros core — every public API is versioned, documented, and guaranteed backward-compatible within the same major version.

## Quick Start

Scaffold a new plugin:

```bash
aetheros sdk init my-plugin --type tool --description "My awesome plugin" --author "Me"
```

Build and package:

```bash
cd my-plugin
aetheros sdk build
```

Validate your manifest:

```bash
aetheros sdk validate
```

## SDK Components

### API Facades (`sdk.api`)

| API | Purpose |
|-----|---------|
| `PluginAPI` | Query plugin registry and metadata |
| `ToolAPI` | Register and query tools |
| `EventAPI` | Publish and subscribe to events |
| `WorkflowAPI` | Define and execute workflows |
| `AgentAPI` | Interact with the running agent |
| `MemoryAPI` | Access the memory system |
| `InteractionAPI` | Respond to user interactions |
| `EngineeringAPI` | Code analysis and engineering tools |
| `ClusterAPI` | Distributed agent coordination |

### Extension Context (`sdk.context`)

`ExtensionContext` is the runtime facade given to every extension. It provides stable access to all API facades, permissions, logging, and sandboxed file/HTTP access.

```python
def register(ctx):
    ctx.tools.register_tool(name="my_tool", ...)
    ctx.events.publish("my:event", {"key": "value"})
    ctx.log_info("Plugin registered successfully")
```

### Lifecycle (`sdk.lifecycle`)

Extensions transition through well-defined states:

- `INSTALLED` → `DISABLED` → `ENABLED` → `RUNNING`

Transitions are validated, audited, and reversible.

### Permissions (`sdk.permissions`)

Extensions declare required permissions. Users grant or deny them at install time.

Supported permission categories:
- `filesystem:read/write`
- `network:connect`
- `clipboard:read/write`
- `microphone:access`
- `camera:access`
- `notifications:send`
- `workspace:read`

### Versioning (`sdk.versioning`)

SemVer 2.0 parsing, comparison, range matching, and breaking change tracking.

### Compatibility (`sdk.compatibility`)

Check Aetheros version, SDK version, platform, runtime requirements, and dependencies.

### Validation (`sdk.validator`)

Validate plugin manifests against the SDK schema.

### Packaging (`sdk.packaging`)

Package plugins into `.aep` (Aetheros Extension Package) files.

### Signing (`sdk.signing`)

Cryptographic signing and verification using Ed25519 or HMAC-SHA256.

### Templates (`sdk.templates`)

Starter templates for all plugin types. Scafold with:

```bash
aetheros sdk init my-plugin --type workflow
```

## Plugin Types

| Type | Description |
|------|-------------|
| `tool` | Register new tools the agent can call |
| `agent` | Hook into agent lifecycle events |
| `workflow` | Compose multi-step workflows |
| `memory` | Pluggable memory backend |
| `model` | Register inference providers |
| `voice` | Text-to-speech provider |
| `notification` | Send alerts and notifications |
| `enterprise` | SSO, audit, compliance integrations |

## CLI Commands

```
aetheros sdk init       Scaffold a new plugin
aetheros sdk build      Package a plugin into .aep
aetheros sdk validate   Validate a plugin manifest
aetheros sdk sign       Sign a package
aetheros sdk verify     Verify a package signature
aetheros sdk templates  List available templates
aetheros sdk publish    Publish to marketplace
```

## Enterprise Registry

### Private Registries

Configure private registries for enterprise use:

```yaml
# ~/.aetheros/config.yaml
marketplace:
  registries:
    - name: Enterprise Registry
      url: https://registry.mycorp.com/api/v1
      api_key: ${INTERNAL_REGISTRY_KEY}
```

### Offline Installation

```bash
aetheros sdk build --output my-plugin.aep
# Transfer my-plugin.aep to offline machine
aetheros marketplace install my-plugin.aep
```

## Migration Guide

### Upgrading from Plugin API v0.x

The 1.0 SDK introduces:
- Stable, versioned API facades
- Permission model with user consent
- Extension sandboxing
- Plugin signing and verification
- Marketplace publishing

Key changes:
- `ctx.register_tool(...)` still works (backward compatible)
- New: `ctx.tools.register_tool(...)` (preferred)
- New: `ctx.events` for event-driven architecture
- New: `ctx.permissions` for access control

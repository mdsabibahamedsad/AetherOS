# AetherOS Permissions System

**Version:** 0.24.0  
**Last Updated:** July 21, 2026

---

## 1. Overview

AetherOS implements a granular, Zero Trust permission system. Every AI Agent, Tool, Plugin, MCP Server, Automation, Provider, and Remote Instance operates under explicit permissions. By default, all actions are denied unless explicitly granted.

### Principles

- **Secure by default** — No implicit trust. Every capability must be granted.
- **User-controlled** — The user has final authority over all permission decisions.
- **Granular** — Permissions are scoped to specific actions, not broad categories.
- **Transparent** — All permission checks are visible in the audit log.
- **Auditable** — Every grant, denial, and approval is recorded.

---

## 2. Permission Categories & Actions

### Filesystem

| Permission | ID | Risk | Default |
|-----------|-----|------|---------|
| Read Files | `fs-read` | Low | Allow |
| Write Files | `fs-write` | Medium | Ask Every Time |
| Delete Files | `fs-delete` | Critical | Deny |
| Move Files | `fs-move` | Medium | Ask Every Time |
| Create Directories | `fs-create-dir` | Low | Allow |

### Network

| Permission | ID | Risk | Default |
|-----------|-----|------|---------|
| Internet Access | `net-internet` | Medium | Ask Every Time |
| Specific Domains | `net-domains` | Low | Allow |
| Specific Ports | `net-ports` | Low | Allow |
| Local Network | `net-local` | Medium | Deny |

### Browser

| Permission | ID | Risk | Default |
|-----------|-----|------|---------|
| Open Pages | `browser-open` | Medium | Ask Every Time |
| Download Files | `browser-download` | High | Ask Every Time |
| Upload Files | `browser-upload` | High | Deny |
| Cookies | `browser-cookies` | Critical | Deny |

### Clipboard

| Permission | ID | Risk | Default |
|-----------|-----|------|---------|
| Read Clipboard | `clipboard-read` | High | Deny |
| Write Clipboard | `clipboard-write` | Medium | Ask Every Time |

### Terminal

| Permission | ID | Risk | Default |
|-----------|-----|------|---------|
| Command Execution | `term-execute` | High | Ask Every Time |
| Shell Access | `term-shell` | High | Deny |
| Process Management | `term-process` | Critical | Deny |

### Docker

| Permission | ID | Risk | Default |
|-----------|-----|------|---------|
| Container Creation | `docker-create` | Critical | Deny |
| Container Execution | `docker-exec` | High | Deny |
| Container Network | `docker-net` | Critical | Deny |

### Python

| Permission | ID | Risk | Default |
|-----------|-----|------|---------|
| Code Execution | `py-exec` | High | Deny |
| Package Installation | `py-pkg` | High | Deny |

### Database

| Permission | ID | Risk | Default |
|-----------|-----|------|---------|
| Database Read | `db-read` | Medium | Ask Every Time |
| Database Write | `db-write` | High | Deny |
| Database Delete | `db-delete` | Critical | Deny |

### Cloud Services

| Permission | ID | Risk | Default |
|-----------|-----|------|---------|
| Email | `cloud-email` | High | Deny |
| Messaging | `cloud-messaging` | High | Deny |
| Calendar | `cloud-calendar` | Medium | Deny |
| GitHub | `cloud-github` | High | Deny |
| Storage | `cloud-storage` | High | Deny |

---

## 3. Permission Policy

Each grant has one of four policies:

| Policy | Behavior |
|--------|----------|
| **Allow** | The action is permitted without user interaction |
| **Deny** | The action is blocked immediately |
| **Ask Every Time** | User is prompted for approval each time |
| **Ask Once** | User is prompted once; choice remembered for the session |

### Duration Types

| Duration | Behavior |
|----------|----------|
| Ask Every Time | Prompt on every use |
| Ask Once | Prompt once per session |
| Temporary | Expires after a set time period (configurable) |
| Session | Valid for the current session only |
| Permanent | Stored indefinitely |

---

## 4. Per-Agent Permissions

Each agent, plugin, MCP server, automation, and tool has its own permission profile. The profile defines:

- Which permissions are granted (with policy and duration)
- Sandbox mode for execution
- Filesystem access boundaries (allowed/blocked/read-only folders)
- Network access boundaries (domain allowlist/blocklist)
- Execution timeouts and resource limits

### Default Profiles

| Grantee Type | Default Sandbox | Default Policy |
|-------------|----------------|----------------|
| Built-in Agent | Standard | Ask Every Time for medium-risk actions |
| Third-party Plugin | Restricted | Deny for all high/critical risk actions |
| MCP Server | Standard | Allow for declared permissions |
| Automation Workflow | Trusted | Inherits from component tools |

---

## 5. Approval System

When an agent requests a dangerous action, the approval system displays a dialog with:

- Agent name and ID
- Requested action description
- Reason provided by the agent
- Target resource or destination
- Risk level (Low/Medium/High/Critical)
- Affected files (if applicable)
- Command to be executed (if applicable)
- Network destination (if applicable)

### User Options

| Option | Behavior |
|--------|----------|
| Allow Once | The specific action is permitted one time |
| Allow Session | All similar actions permitted for the session duration |
| Always Allow | A permanent permission grant is created |
| Deny | The action is blocked and logged |

---

## 6. Plugin Security

Every Plugin must declare its required permissions in its manifest. The system:

1. Reads the plugin manifest to discover requested permissions
2. Compares against the user's pre-configured grants
3. Displays any new or escalated permissions before activation
4. Enforces the permission profile during execution

Plugin manifest permissions include:
- Publisher identity and signature verification
- Requested permission IDs with justifications
- Risk level self-assessment
- Dependency chain permissions

---

## 7. MCP Security

Every MCP Server has its own security profile:

- **Permission Profile** — Which tools and resources the server can access
- **Tool Allowlist** — Specific MCP tools that are permitted
- **Resource Allowlist** — Specific resources that can be accessed
- **Network Rules** — Domain/IP/port restrictions for the server connection
- **Filesystem Rules** — Directory access boundaries
- **Approval Rules** — Which operations require user approval

---

## 8. Automation Security

Every workflow has:

- **Permission Scope** — The set of permissions available to the workflow
- **Execution Limits** — Max runtime, retries, resource consumption
- **Allowed Tools** — Only explicitly listed tools can be used
- **Allowed Agents** — Only explicitly listed agents can participate

---

## 9. Audit Logging

All permission events are logged to the tamper-evident audit log:

- **Permission Granted** — When a grant is created or updated
- **Permission Denied** — When an action is blocked by policy
- **Permission Approved** — When a user approves a pending request
- **Escalation Attempt** — When an entity attempts an action it doesn't have permission for

---

## 10. Security Best Practices

1. **Principle of Least Privilege** — Grant only the minimum permissions needed
2. **Regular Audits** — Review active grants periodically
3. **Prefer Ask Every Time** — For medium-risk actions, use ask-every-time rather than permanent allow
4. **Deny by Default** — Start with deny for all critical-risk actions
5. **Review Plugin Permissions** — Always review permission requests before activating plugins
6. **Use Sandboxes** — Enable sandbox mode for third-party code execution
7. **Monitor Audit Log** — Check the audit log regularly for unexpected permission usage

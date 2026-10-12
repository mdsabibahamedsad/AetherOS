# AetherOS Sandbox System

**Version:** 0.24.0  
**Last Updated:** July 21, 2026

---

## 1. Overview

The AetherOS Sandbox System provides isolated execution environments for agents, plugins, MCP servers, Python code, shell commands, browser tasks, and automation workflows. Sandboxes enforce security boundaries, resource limits, and access controls to prevent malicious or unintended damage to the host system.

---

## 2. Sandbox Modes

| Mode | Description | Filesystem | Network | Execution |
|------|-------------|------------|---------|-----------|
| **Read Only** | No write access to any filesystem | Read-only everywhere | Blocked | No execution |
| **Restricted** | Limited write access to temp directories | Temp + specific folders | Domain allowlist only | Scoped to specific binaries |
| **Standard** | Balanced isolation for trusted code | Workspace + temp | Internet + specific ports | Controlled execution |
| **Trusted** | Full access for verified first-party code | Full workspace | Full internet | Full execution |
| **Custom** | User-defined rules | Configurable | Configurable | Configurable |

---

## 3. Filesystem Sandbox

The filesystem sandbox enforces workspace-scoped access with fine-grained controls:

### Controls

| Setting | Description |
|---------|-------------|
| **Allowed Folders** | Directories the sandbox can read and write |
| **Blocked Folders** | Directories the sandbox CANNOT access (overrides allow) |
| **Read-Only Folders** | Directories accessible for reading only |
| **Temporary Folders** | Scratch space that is cleaned up on sandbox exit |
| **Project Workspace** | The primary project directory for the sandbox |

### Path Resolution

Path access is resolved using the most restrictive rule:
1. If the path is in a **blocked folder**, access is denied
2. If the path is in a **read-only folder**, write operations are denied
3. If the path is in an **allowed folder** (or temp folder), access is permitted
4. If the path is outside all configured folders, access is denied (unless in trusted mode)

---

## 4. Network Security

### Controls

| Setting | Description |
|---------|-------------|
| **Domain Allowlist** | Only connections to these domains are permitted |
| **Domain Blocklist** | Connections to these domains are always blocked |
| **IP Restrictions** | Network access limited to specific IP ranges (CIDR notation) |
| **Port Restrictions** | Only connections on specified ports are permitted |
| **Offline Mode** | All network access is blocked |

### Resolution Order
1. If **offline mode** is active, all network is blocked
2. If the destination matches the **blocklist**, access is denied
3. If the destination matches the **allowlist**, access is permitted
4. If **IP restrictions** are set and the destination does not match, access is denied
5. If **port restrictions** are set and the port is not in the list, access is denied

---

## 5. Cross-Platform Sandboxing

AetherOS uses platform-appropriate sandboxing mechanisms:

| Platform | Mechanism | Notes |
|----------|-----------|-------|
| **Windows** | Windows Job Objects + Integrity Levels + AppContainer (where available) | Process isolation with resource limits |
| **Linux** | Linux namespaces + cgroups + seccomp-bpf + Landlock | Full kernel-level isolation |
| **macOS** | macOS sandbox profiles + seatbelt + app sandbox | Apple's sandbox framework |

### Fallback
When native sandboxing is unavailable, AetherOS falls back to:
- Python `restricted` module execution for code
- Subprocess with reduced privileges for commands
- Docker/podman containers when available

---

## 6. Resource Limits

Each sandbox enforces configurable resource limits:

| Resource | Default | Description |
|----------|---------|-------------|
| Memory | 1024 MB | Maximum memory the sandbox can consume |
| CPU | 50% | Maximum CPU utilization |
| Timeout | 300s | Maximum execution time before forced termination |
| File Size | 100 MB | Maximum file that can be created |
| Process Count | 50 | Maximum number of child processes |
| Network Connections | 10 | Maximum concurrent outbound connections |

---

## 7. Sandbox Types

| Type | Use Case | Default Mode |
|------|----------|-------------|
| **Agent** | AI agent execution | Standard |
| **Plugin** | Third-party plugin isolation | Restricted |
| **MCP Server** | MCP server process | Standard |
| **Python** | Python code execution | Read Only |
| **Shell** | Shell command execution | Standard |
| **Browser** | Browser automation | Standard |
| **Automation** | Workflow execution | Trusted |

---

## 8. Sandbox Lifecycle

```
Created ─► Creating ─► Running ─► Stopped
               │          │
               │          ├──► Error
               │          │
               │          └──► Violation (security boundary crossed)
               │
               └──► Failed (creation error)
```

### Events
- **Sandbox Created** — A new sandbox instance is configured
- **Sandbox Started** — The sandbox begins execution
- **Sandbox Violation** — A security boundary was crossed (logged and terminated)
- **Sandbox Stopped** — Normal termination (timeout, completion, or user request)
- **Sandbox Destroyed** — Resources cleaned up

---

## 9. Platform-Specific Notes

### Windows
- Windows Sandbox (for full isolation) requires Windows 10 Pro/Enterprise
- Job Objects provide lightweight process management
- Integrity Levels (Low/Medium/High) provide mandatory access control

### Linux
- User namespaces for UID/GID mapping
- Mount namespaces for filesystem isolation
- Network namespaces for network isolation
- PID namespaces for process visibility
- cgroup v2 for resource limits
- seccomp-bpf for syscall filtering

### macOS
- App Sandbox with entitlements
- Seatbelt profiles for filesystem and network
- Hardened Runtime for code signing enforcement

---

## 10. Best Practices

1. **Use the most restrictive mode** that still allows the task to work
2. **Enable offline mode** for tasks that don't need network access
3. **Set appropriate timeouts** to prevent runaway processes
4. **Review blocked folders** — block system directories unless explicitly needed
5. **Use read-only mode** for analysis and inspection tasks
6. **Monitor sandbox violations** in the audit log and security alerts
7. **Regularly clean up** stopped sandbox resources

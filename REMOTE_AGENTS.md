# AetherOS Remote Agent Platform

**Version:** 0.23.0  
**Last Updated:** July 21, 2026

---

## 1. Overview

The Remote Agent Platform extends AetherOS beyond a single machine, enabling agents to be deployed, monitored, and controlled across multiple remote instances. It provides secure remote access to agent runtimes, workspace files, and real-time monitoring — turning any AetherOS instance into a distributed agent network.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     REMOTE AGENT PLATFORM                                │
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │
│  │  Local        │    │  Remote Node │    │  Remote Node │             │
│  │  Controller   │    │    Alpha     │    │    Beta      │             │
│  │               │    │              │    │              │             │
│  │  ┌────────┐   │    │  ┌────────┐  │    │  ┌────────┐  │             │
│  │  │ Agent  │   │    │  │ Agent  │  │    │  │ Agent  │  │             │
│  │  │ Control│───┼────┼─►│ Runtime│  │    │  │ Runtime│  │             │
│  │  └────────┘   │    │  └────────┘  │    │  └────────┘  │             │
│  │               │    │              │    │              │             │
│  │  ┌────────┐   │    │  ┌────────┐  │    │  ┌────────┐  │             │
│  │  │ Monitor│───┼────┼─►│  Logs & │  │    │  │  Logs &│  │             │
│  │  │  Feed  │◄──┼────┼──┤ Metrics │  │◄──┼──┤ Metrics │  │             │
│  │  └────────┘   │    │  └────────┘  │    │  └────────┘  │             │
│  │               │    │              │    │              │             │
│  │  ┌────────┐   │    │  ┌────────┐  │    │  ┌────────┐  │             │
│  │  │ Worksp. │───┼────┼─►│ Shared  │  │    │  │ Shared  │  │             │
│  │  │ Access  │◄──┼────┼──┤ Storage │  │◄──┼──┤ Storage │  │             │
│  │  └────────┘   │    │  └────────┘  │    │  └────────┘  │             │
│  └──────┬────────┘    └──────┬───────┘    └──────┬───────┘             │
│         │                    │                    │                    │
│  ┌──────┴────────────────────┴────────────────────┴──────────────────┐ │
│  │                    CONNECTION LAYER                                 │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐  │ │
│  │  │  Mutual  │ │  Token   │ │  Rate    │ │  Auto-Reconnect      │  │ │
│  │  │   TLS   │ │   Auth   │ │ Limiting │ │  (Exponential Backoff)│  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   CONTROLLER (Local Instance)                  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │               Remote Agent Manager                       │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │ Instance │ │ Connect  │ │  Monitor │ │ Health   │  │  │
│  │  │ Registry │ │ Manager  │ │  Engine  │ │ Checker  │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐               │  │
│  │  │ Workspace│ │  Audit   │ │  Latency │               │  │
│  │  │  Bridge  │ │  Logger  │ │  Tracker │               │  │
│  │  └──────────┘ └──────────┘ └──────────┘               │  │
│  └────────────────────────────────────────────────────────┘  │
│                              │                                 │
│  ┌───────────────────────────▼────────────────────────────┐  │
│  │               Connection Multiplexer                    │  │
│  │        (mTLS / Token Auth / Rate Limiting)               │  │
│  └───────────────────────────┬────────────────────────────┘  │
└──────────────────────────────┼───────────────────────────────┘
                               │
                  ═════════════╪══════════════════ Network
                               │
┌──────────────────────────────┼───────────────────────────────┐
│                   NODE (Remote Instance)                       │
│                              │                                 │
│  ┌───────────────────────────▼────────────────────────────┐  │
│  │               Remote Agent Server                       │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │  Auth    │ │  Session │ │  Command │ │  Stream  │  │  │
│  │  │  Gateway │ │  Manager │ │  Handler │ │  Manager │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  └───────────────────────────┬────────────────────────────┘  │
│                              │                                 │
│  ┌───────────────────────────▼────────────────────────────┐  │
│  │               Local Agent Runtime                      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │ AIAgent  │ │  Tools   │ │  Memory  │ │  Skills  │  │  │
│  │  │  Core    │ │  System  │ │  Manager │ │  System  │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Remote Instance Management

### Instance Registry

Each remote instance is registered with a unique identifier and metadata:

```json
{
  "instance_id": "node-alpha-001",
  "name": "Home Server Alpha",
  "host": "192.168.1.100:8443",
  "status": "connected",
  "version": "0.23.0",
  "capabilities": ["agent", "workspace", "monitoring"],
  "device_id": "dev-abc123",
  "registered_at": "2026-07-21T08:00:00Z",
  "last_seen": "2026-07-21T10:30:00Z",
  "latency_ms": 12,
  "uptime_seconds": 86400
}
```

### Authentication & Registration

1. Remote node generates RSA-4096 key pair.
2. Public key is registered with the controller (out-of-band or via pairing code).
3. Controller issues a signed certificate for mTLS.
4. Node presents certificate on each connection.

### Remote Node Configuration (`config.yaml`)

```yaml
remote:
  mode: node  # "controller" | "node"
  
  # Controller mode
  instances:
    - name: "Home Server"
      host: "192.168.1.100:8443"
      token: "${REMOTE_NODE_TOKEN}"
      auto_reconnect: true
      health_check_interval: 30
      
  # Node mode
  server:
    host: "0.0.0.0"
    port: 8443
    tls_cert: "/path/to/cert.pem"
    tls_key: "/path/to/key.pem"
    allowed_controllers:
      - "controller-device-id"
    rate_limit:
      requests_per_minute: 60
      burst: 10
    audit_log: true
```

---

## 4. Connection Lifecycle

```
DISCONNECTED
    │
    ├─► connect()
    │       │
    │       ├─► mTLS handshake
    │       ├─► Token authentication
    │       ├─► Capability negotiation
    │       └─► Session established
    │               │
    │          ┌────▼────┐
    │          │ HEALTHY │
    │          └────┬────┘
    │               │
    │          ┌────▼────┐
    │          │ ACTIVE  │◄────────── Command/Stream/Workspace ops
    │          └────┬────┘
    │               │
    │          ┌────▼────┐
    │          │ STALE   │──► Health check timeout
    │          └────┬────┘
    │               │
    ├─► disconnect()
    │       │
    │       ├─► Graceful shutdown
    │       ├─► Session cleanup
    │       └─► DISCONNECTED
    │
    └─► Connection lost
            │
            ├─► Auto-reconnect (backoff)
            ├─► Backoff: 1s → 2s → 4s → 8s → 16s → 30s (cap)
            └─► Or manual reconnect
```

### connect()

Establishes a secure connection to a remote node:

1. **mTLS handshake**: Both sides present certificates. Mutual verification.
2. **Token authentication**: Short-lived bearer token for session auth.
3. **Capability negotiation**: Exchange supported features (agent control, workspace access, monitoring, etc.).
4. **Session establishment**: Create bidirectional session with stream multiplexing.

### disconnect()

Gracefully tears down the connection:

1. Send `disconnect` message with reason.
2. Wait for in-flight operations to complete (timeout: 5s).
3. Close session streams.
4. Clean up session state.
5. Emit `instance.disconnected` event.

### reconnect()

Automatic reconnection with exponential backoff:

| Attempt | Backoff |
|---------|---------|
| 1 | 1s |
| 2 | 2s |
| 3 | 4s |
| 4 | 8s |
| 5 | 16s |
| 6+ | 30s (cap) |

- Jitter: ±25% random to prevent thundering herd.
- Total attempts: unlimited (configurable max).
- Reset on successful connection or manual reconnect.

### health_check()

Periodic health probe (default: 30s interval):

```json
{
  "status": "healthy",
  "uptime": 86400,
  "cpu_percent": 23.5,
  "memory_percent": 45.2,
  "agent_running": true,
  "last_error": null,
  "latency_ms": 12
}
```

Health states:
- `healthy`: All systems normal.
- `degraded`: High resource usage or minor errors.
- `unhealthy`: Critical errors or agent unresponsive.

---

## 5. Agent Control

### Control Commands

| Command | Description | Payload |
|---------|-------------|---------|
| `start` | Start agent instance | `{ agent_id, config_overrides }` |
| `stop` | Stop agent instance | `{ agent_id, force: bool }` |
| `pause` | Pause agent execution | `{ agent_id }` |
| `resume` | Resume paused agent | `{ agent_id }` |
| `restart` | Restart agent process | `{ agent_id, config_overrides }` |

### Command Flow

```
Controller                    Node
    │                          │
    ├─── agent.control ───────►│
    │     { command: "start",  │
    │       agent_id: "...",   │
    │       config: {...} }    │
    │                          ├─── Validate request
    │                          ├─── Spawn agent process
    │                          ├─── Attach to session
    │                          ├─── Emit agent.started
    │◄─────────────────────── ─┤
    │  { status: "ok",        │
    │    agent_id: "...",     │
    │    pid: 12345,          │
    │    session_id: "..." }  │
    │                          │
    ├─── agent.control ───────►│
    │     { command: "stop",   │
    │       agent_id: "..." }  │
    │                          ├─── Send SIGTERM
    │                          ├─── Wait (timeout: 10s)
    │                          ├─── Send SIGKILL if needed
    │                          ├─── Emit agent.stopped
    │◄─────────────────────────┤
    │  { status: "ok",        │
    │    agent_id: "...",     │
    │    exit_code: 0 }       │
```

---

## 6. Remote Monitoring

### Log Streaming

Real-time log streaming with level filtering:

```python
# Subscribe to remote agent logs
remote.subscribe_logs(agent_id="agent-001", level="INFO")

# Received events:
{
  "event": "agent.log",
  "agent_id": "agent-001",
  "timestamp": "2026-07-21T10:30:00.123Z",
  "level": "INFO",
  "message": "Tool call: terminal ls -la",
  "metadata": {
    "source": "run_agent.py:245",
    "session_id": "sess-abc"
  }
}
```

### Task Monitoring

Track running tasks, completion status, and resource usage:

```json
{
  "event": "agent.tasks",
  "agent_id": "agent-001",
  "tasks": {
    "running": 2,
    "queued": 3,
    "completed_today": 47,
    "failed_today": 1,
    "active": [
      {
        "task_id": "task-001",
        "type": "research",
        "started_at": "...",
        "elapsed_seconds": 45,
        "tokens_used": 1234
      }
    ]
  }
}
```

### Memory & Resource Monitoring

```json
{
  "event": "agent.resources",
  "agent_id": "agent-001",
  "memory": {
    "rss_mb": 256,
    "vms_mb": 1024,
    "percent": 12.5
  },
  "cpu": {
    "percent": 23.5,
    "user_time_s": 120,
    "sys_time_s": 15
  },
  "disk": {
    "agent_home_mb": 450,
    "available_mb": 50000
  }
}
```

### Usage Statistics

```json
{
  "event": "agent.usage",
  "agent_id": "agent-001",
  "period": "24h",
  "tokens_in": 150000,
  "tokens_out": 45000,
  "api_calls": 320,
  "tool_calls": 180,
  "errors": 3
}
```

### Error Monitoring

```json
{
  "event": "agent.errors",
  "agent_id": "agent-001",
  "errors": [
    {
      "timestamp": "...",
      "type": "APIError",
      "message": "Rate limit exceeded",
      "traceback": "...",
      "recovered": true
    }
  ]
}
```

---

## 7. Remote Workspace Access

### Supported Resources

| Resource | Operations | Description |
|----------|------------|-------------|
| Files | List, read, write, delete, search | Remote file system access |
| Projects | List, create, open, close | Project management |
| Agents | List, inspect, control | Agent configuration and lifecycle |
| Automations | List, enable, disable, trigger | Automation rule management |
| Knowledge | Search, query, index | Remote knowledge base access |

### File Operations

```python
# List remote directory
files = remote.list_files(path="/home/user/projects", recursive=False)

# Read file content
content = remote.read_file(path="/home/user/projects/notes.md")

# Write file
result = remote.write_file(path="/home/user/projects/notes.md", 
                           content="Updated content", 
                           mode="overwrite")

# Search files
results = remote.search_files(pattern="*.py", root="/home/user/projects")
```

### Project Operations

```python
# List remote projects
projects = remote.list_projects()

# Create project
project = remote.create_project(name="New Project", template="python")

# Open project in remote editor
session = remote.open_project(project_id="proj-001")
```

### Knowledge Operations

```python
# Search remote knowledge base
results = remote.search_knowledge(query="machine learning", limit=10)

# Index new documents
job = remote.index_documents(paths=["/remote/path/doc.pdf"])
```

---

## 8. Security

### Mutual TLS (mTLS)

All connections between controllers and nodes use mutual TLS:

- **Controller certificate**: Identifies the controlling instance.
- **Node certificate**: Identifies the remote node.
- **CA**: Self-signed or enterprise CA.
- **Cipher suites**: TLS_AES_256_GCM_SHA_SHA384 (TLS 1.3).

### Token Authentication

In addition to mTLS, each session uses short-lived bearer tokens:

- **Issued**: On successful mTLS handshake.
- **TTL**: 1 hour.
- **Refresh**: Automatic, 5 minutes before expiry.
- **Scoped**: Token includes allowed capabilities.

### Rate Limiting

| Limit | Scope | Behavior |
|-------|-------|----------|
| 60 req/min | Per connection | 429 Too Many Requests |
| 10 burst | Per connection | Token bucket |
| 1000 req/min | Per node | Connection-level throttle |

### Audit Logging

All remote operations are logged:

| Event | Description |
|-------|-------------|
| `remote.connect` | Connection established |
| `remote.disconnect` | Connection closed |
| `remote.auth.success` | Authentication succeeded |
| `remote.auth.failure` | Authentication failed |
| `remote.agent.start` | Remote agent started |
| `remote.agent.stop` | Remote agent stopped |
| `remote.agent.error` | Remote agent error |
| `remote.file.read` | Remote file read |
| `remote.file.write` | Remote file written |
| `remote.file.delete` | Remote file deleted |
| `remote.rate_limit.hit` | Rate limit exceeded |

---

## 9. Auto-Reconnect with Exponential Backoff

The connection manager implements robust reconnection with configurable backoff.

### Backoff Sequence

```
Attempt 1:  sleep(1s)
Attempt 2:  sleep(2s)
Attempt 3:  sleep(4s)
Attempt 4:  sleep(8s)
Attempt 5:  sleep(16s)
Attempt 6:  sleep(30s)  ← cap
...
Attempt N:  sleep(30s)  ← stays at cap
```

### Jitter

Random ±25% jitter applied to each backoff interval to prevent synchronized reconnection storms:

```python
jitter = random.uniform(0.75, 1.25)
delay = min(base_delay * (2 ** attempt), max_delay) * jitter
```

### Reset Conditions

- Backoff resets to 1s on successful connection.
- Backoff resets to 1s on manual reconnect trigger.
- Counter resets after 10 minutes of stable connection.

---

## 10. Latency Tracking & Health Monitoring

### Latency Measurement

Round-trip time measured via periodic ping/pong messages:

```
Controller                    Node
    │                          │
    ├─── ping ───────────────►│  (timestamp: T1)
    │                          │
    │◄─────────────────────── ─┤  (timestamp: T2)
    │                          │
    RTT = (T2 - T1)
```

### Health Check Aggregation

```json
{
  "instance_id": "node-alpha-001",
  "status": "healthy",
  "latency_ms": 12,
  "uptime_hours": 48,
  "last_health_check": "2026-07-21T10:30:00Z",
  "checks": {
    "agent_running": true,
    "disk_space": { "status": "ok", "available_gb": 50 },
    "memory": { "status": "ok", "percent": 45 },
    "cpu": { "status": "ok", "percent": 23 },
    "network": { "status": "ok", "latency_ms": 12 }
  }
}
```

---

## 11. Collaboration Architecture (Future)

### Team Workspaces

Multi-user workspaces where multiple controllers can manage shared agent instances:

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│  User A  │  │  User B  │  │  User C  │
│(Operator)│  │(Operator)│  │(Operator)│
└─────┬────┘  └─────┬────┘  └─────┬────┘
      │              │              │
┌─────┴──────────────┴──────────────┴────┐
│           Team Workspace                │
│  ┌──────────┐  ┌──────────┐           │
│  │ Shared   │  │ Shared   │           │
│  │ Agents   │  │ Knowledge│           │
│  └──────────┘  └──────────┘           │
│  ┌──────────┐  ┌──────────┐           │
│  │ Shared   │  │ Role     │           │
│  │ Automat. │  │ Manager  │           │
│  └──────────┘  └──────────┘           │
└────────────────────────────────────────┘
```

### Shared Agents

Agents that can be controlled by multiple authorized users within a workspace. Enables collaborative agent development, shared automation, and delegation workflows.

### Shared Knowledge

Knowledge bases accessible across the team. Searchable by all members with role-based access controls.

### Role-Based Access

| Role | Agent Control | Workspace Access | User Management |
|------|--------------|------------------|-----------------|
| Admin | Full | Full | Full |
| Operator | Start/Stop/View | Read/Write | None |
| Viewer | View only | Read only | None |

---

## 12. Error Handling

| Error | Code | Recovery |
|-------|------|----------|
| Connection refused | ECONNREFUSED | Retry with backoff |
| TLS handshake failed | ETLSFAIL | Verify certificates |
| Authentication failed | EAUTHFAIL | Refresh token or re-register |
| Session expired | ESESSIONEXP | Re-authenticate |
| Rate limited | ERATELIMIT | Wait and retry |
| Agent not found | EAGENTNOTFOUND | Verify agent_id |
| Command timeout | ETIMEOUT | Retry command |
| Workspace unavailable | EWORKSPACE | Check node status |

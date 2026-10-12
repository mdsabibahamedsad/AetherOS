# AetherOS Multi-Agent System

## Overview

The Multi-Agent System enables multiple AI agents to collaborate on complex
tasks. Agents can communicate, share results, spawn sub-agents, and work
together in coordinated workflows.

## Agent Collaboration

### AgentCollaborationManager (`aetheros_automation/multi_agent/collaboration.py`)

Manages collaborative agent conversations:
- `start_collaboration()` — Begin multi-agent session
- `send_message()` — Send message between agents
- `broadcast()` — Send to all participants
- `share_result()` — Share structured data
- `get_shared_result()` — Retrieve shared data
- `end_collaboration()` — End session

### Collaboration Flow
```
1. Coordinator starts collaboration
2. Coordinator sends task description
3. Research agent gathers data
4. Research agent shares findings
5. Developer agent implements solution
6. Review agent validates
7. Collaboration ends
```

## Agent Messaging

### AgentMessaging (`aetheros_automation/multi_agent/messaging.py`)

Structured messaging between agents:
- `send()` — Send message asynchronously
- `receive()` — Wait for incoming message
- `send_and_wait()` — Send and wait for response
- `get_messages()` — Browse message history
- `get_conversation()` — Get full conversation

### Message Types
- `text` — Text messages
- `result` — Task results
- `file` — File references
- `structured_data` — JSON data
- `task_status` — Status updates
- `error` — Error reports
- `recommendation` — Agent recommendations

## Sub-Agent System

### SubAgentManager (`aetheros_automation/multi_agent/sub_agent_manager.py`)

Manages creation and lifecycle of sub-agents:
- `create_sub_agent()` — Spawn child agent with limited scope
- `terminate_sub_agent()` — Destroy sub-agent
- `terminate_all_sub_agents()` — Clean up all children
- `get_sub_agents()` — List active sub-agents

### Sub-Agent Properties
- Limited scope and permissions
- Clear parent ownership
- Execution limits (max_steps, max_time)
- Automatically terminated when finished
- Cannot create further sub-agents (leaf role)

### Hierarchy Example
```
Main Agent
├── Research Agent (sub)
├── Browser Agent (sub)
├── Data Agent (sub)
└── Review Agent (sub)
```

## Specialized Agents

| Agent | Role | Description |
|-------|------|-------------|
| CoordinatorAgent | coordinator | Orchestrates workflow, delegates tasks |
| PlannerAgent | planner | Strategic decomposition and planning |
| DeveloperAgent | developer | Code generation and implementation |
| ResearchAgent | research | Information gathering and analysis |
| WriterAgent | writer | Content and document creation |
| BrowserAgent | browser | Web navigation and data extraction |
| QAAgent | qa | Testing and quality assurance |
| DeploymentAgent | deployment | Release and deployment management |
| SecurityAgent | security | Security analysis and auditing |
| MemoryAgent | memory | Memory and knowledge management |
| **CreativeAgent** | creative | Creative design and content generation |
| **DataAgent** | data | Data analysis and visualization |
| **CommunicationAgent** | communication | Email and message composition |
| **ReviewAgent** | review | Code, document, and security review |

## Agent Assignment

Each agent receives:
- Model and provider (routed by ModelRouter)
- Required toolset
- Permission set based on role
- Task-specific instructions
- Execution limits
- Memory and knowledge scope

## Security

- Sub-agents inherit limited permissions
- Parent is responsible for child's actions
- Communication is structured and audited
- No uncontrolled infinite conversations
- All agent actions are permission-checked

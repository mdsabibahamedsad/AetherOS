## 11. Integration Points

The Computer Agent should integrate with the existing Aetheros framework at the following points:

### 11.1 Agent Framework Integration
- **Agent Instantiation**: The Computer Agent should be instantiable as an AIAgent with appropriate pre-enabled toolsets and skills.
- **Toolset Configuration**: Should use or extend the computer_use toolset and potentially create a new computer_agent toolset that includes:
  * computer_use
  * terminal, process, read_terminal
  * file tools (read_file, write_file, etc.)
  * browser tools (if web interaction is needed)
  * skills_tool
  * memory_tool
  * delegate_tool
  * clarify_tool, approval_tool
  * relevant MCP servers
- **Skill Integration**: Should automatically load relevant skills based on context (e.g., load coding-related skills when in a code workspace, load github skills when interacting with GitHub).
- **LSP Integration**: Should leverage the existing LSP service for language intelligence when performing coding-related computer tasks.
- **Coding Posture Detection**: Should respect and enhance the coding posture detection to automatically activate computer agent capabilities when in a code workspace.
- **Memory System**: Should use the existing memory system for persistent context across computer agent sessions.
- **Delegation System**: Should leverage the delegation system to spawn subagents for subtasks (e.g., delegate coding tasks to a coding subagent while the computer agent handles browser interaction).
- **Cron System**: Should be able to schedule computer agent tasks using the existing cron system.
- **MCP System**: Should integrate with the MCP system to allow extending computer agent capabilities with external MCP servers.

### 11.2 Configuration Points
- New config section computer_agent: in config.yaml:
  - enabled: true/false
  - uto_activate: true/false (automatically activate in contexts that benefit from computer automation)
  - preferred_backend: [local, browserbase, browser_use, camofox] (for browser tools)
  - desktop_backend: [cua-driver] (for computer_use tool, though this is likely fixed)
  - enabled_capabilities: [window_management, application_launch, clipboard, notifications, etc.]
  - 	ool_overrides: {} (custom tool parameters)
  - skill_overrides: {} (custom skill parameters)
  - domain_policy: {} (domain-based permissions for websites and applications)
  - sensitivity_rules: {} (rules for when to require human approval for specific actions)

### 11.3 UI Integration
- Should integrate with existing Aetheros interfaces:
  * CLI: Add /computer command group with subcommands for common computer tasks.
  * TUI: Integrate with the existing TUI to show computer agent status, screenshots, and controls.
  * Desktop App: Ensure the computer agent works seamlessly in the Electron desktop application.
  * Web Dashboard: Integrate with the web dashboard to show computer agent status and allow monitoring.

### 11.4 Data Flow Integration
- **Context Sharing**: Should share context with other agents (e.g., coding agent) through the memory system and delegation mechanism.
- **Event System**: Should leverage existing event systems (if any) for inter-component communication.
- **Approval Flow**: Should use the existing approval and clarify tools for requesting user consent when needed.

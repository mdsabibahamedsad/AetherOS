# AETHEROS COMPUTER AGENT AUDIT
## 1. Existing Browser System

Aetheros provides a comprehensive browser automation system through the following tools:

- **browser_tool.py**: The main browser automation tool that supports multiple backends:
  * Local mode: headless Chromium via agent-browser CLI (zero-cost, works on Linux servers without display)
  * Cloud mode: Browserbase or Browser Use cloud execution when configured
  * Features: navigation, snapshots, accessibility tree (ariaSnapshot) for text-based page representation, element interaction via ref selectors (@e1, @e2, etc.), task-aware content extraction using LLM summarization, automatic cleanup of browser sessions.
  * Supported actions: browser_navigate, browser_snapshot, browser_click, browser_type, browser_scroll, browser_back, browser_press, browser_get_images, browser_vision, browser_console, browser_cdp, browser_dialog.

- **browser_cdp_tool.py**: Raw Chrome DevTools Protocol (CDP) passthrough tool for sending arbitrary CDP commands to the browser's DevTools WebSocket endpoint. Works when a CDP URL is configured (via /browser connect or rowser.cdp_url in config.yaml) or when a CDP-backed cloud provider session is active.

- **browser_supervisor.py**: Persistent CDP supervisor that runs per task_id with a reachable CDP endpoint. It holds a single persistent WebSocket to the backend, subscribes to Page/Runtime/Target events, and surfaces observable state (pending dialogs and frame tree) through a thread-safe snapshot object. Its output is merged into browser_snapshot and used by browser_dialog tool.

- **browser_dialog_tool.py**: Agent-facing tool to respond to native JavaScript dialogs (alert/confirm/prompt/beforeunload) captured by the CDP supervisor. The agent first reads pending_dialogs from browser_snapshot output, then calls this tool to accept or dismiss.

- **browser_camofox.py**: Camofox browser backend - a local anti-detection browser via REST API. Uses Camoufox (Firefox fork with C++ fingerprint spoofing) exposed via a REST API. When CAMOFOX_URL is set, the browser tools route through this module instead of the agent-browser CLI.

All browser tools integrate with the existing tool system and are gated by appropriate check_fn functions (e.g., browser tools require a reachable CDP endpoint or configured cloud credentials).
## 2. Existing Desktop System

Aetheros provides desktop automation capabilities primarily through the **computer_use tool** and the **terminal environment**:

- **computer_use tool** (tools/computer_use_tool.py and tools/computer_use/): 
  * Provides universal background desktop control via cua-driver (works with any tool-capable model).
  * Capabilities: screenshots, mouse movement, clicks (left/right/double), drag, scrolling, keyboard input (including key combinations like cmd+c), and launching/focusing applications.
  * Does NOT steal the user's cursor or keyboard focus, allowing concurrent user and agent interaction.
  * Backends exist for Linux (linux_backend.py), Windows (win32_backend.py), and macOS (implied by the description and cua-driver).
  * Includes permission checking to ensure safe operation.

- **Terminal access via local environment** (tools/environments/local.py):
  * Spawn-per-call local execution environment with session snapshot.
  * Allows running shell commands and managing processes on the host machine.
  * Integrated via the 	erminal tool and process tool (in _AETHEROS_CORE_TOOLS).
  * Provides traditional command-line desktop automation.

- **Embedded terminal pane reading** (read_terminal tool in _AETHEROS_CORE_TOOLS):
  * Reads the desktop GUI's embedded terminal pane (gated on HERMES_DESKTOP via check_fn in tools/read_terminal_tool.py).
  * Allows interaction with terminal panes inside GUI applications (e.g., IDE terminals, VS Code integrated terminal).

No separate window management tools are explicitly defined, but window operations (focus, move, resize, etc.) can be achieved through the computer_use tool's mouse and keyboard capabilities combined with application-specific shortcuts.
## 3. Existing Computer Tools

The **computer_use tool** serves as the primary computer automation tool, providing:
- Desktop automation (mouse, keyboard, etc.) as described above.
- Screenshot capture for visual understanding.
- Application control via launching, focusing, and interacting with GUI elements.
- The tool is already included in the _AETHEROS_CORE_TOOLS list, making it available by default in most agent configurations.

Note that the desktop system and computer tools are largely unified through the computer_use tool, which provides both desktop automation and general computer control capabilities.
## 4. Existing Security Controls

Aetheros implements multiple layers of security controls:

- **Tool Guardrails** (agent/tool_guardrails.py): 
  * Provides ToolCallGuardrailConfig and ToolGuardrailController to evaluate and block tool calls based on risk.
  * Integrates with the agent's tool execution pipeline to prevent unsafe actions.

- **Approval System**:
  * **clarify_tool.py**: For asking clarifying questions (multiple-choice or open-ended) before proceeding with sensitive actions.
  * **approval.py**: Handles approval workflows for tool calls that require explicit user consent.
  * These tools allow the agent to request approval before executing potentially risky actions.

- **Computer Use Permissions** (tools/computer_use/permissions.py):
  * The computer_use tool includes a permissions module that likely checks whether desktop automation actions are allowed based on user policy.
  * Integrates with the tool's check_fn mechanism to gate availability.

- **Toolset-based gating**: 
  * Many tools are gated by check_fn functions that verify requirements (e.g., browser tools require a CDP endpoint, computer_use requires cua-driver installation).
  * The agent's toolset configuration (enabled/disabled toolsets) controls which tools are available.

- **Credential and Secret Management**:
  * Uses agent/secret_sources.py for accessing API keys and secrets securely.
  * Secrets are never exposed to the model unnecessarily.
## 5. Existing Permissions

Specific permission systems include:

- **computer_use tool permissions**: 
  * Located in tools/computer_use/permissions.py.
  * Likely provides functions to check whether the user has granted permission for desktop automation actions.
  * Integrated via the tool's check_fn to determine availability.

- **Browser tool permissions**: 
  * Browser tools are gated by the availability of a CDP endpoint or configured cloud credentials (checked via _browser_cdp_check in tools/browser_tool.py).
  * The browser_supervisor and related tools only function when a CDP-capable backend is attached.

- **Terminal environment permissions**: 
  * The local environment (tools/environments/local.py) inherits general OS-level permissions for process execution.
  * No additional Aetheros-specific permission layer beyond standard OS user privileges.

- **Tool guardrails**: 
  * Agent/tool_guardrails.py provides a flexible system to allow, deny, or require approval for specific tool actions based on configuration.
  * Integrates with the model_tools.py tool execution pipeline.
## 6. Existing UI

Aetheros provides multiple user interfaces for interacting with the agent:

- **Command Line Interface (CLI)**: 
  * Implemented in aetheros_cli/cli.py and related modules.
  * Features rich text output, autocomplete, skinning, and interactive input via prompt_toolkit.
  * Accessible via etheros command in terminal.

- **Terminal User Interface (TUI)**:
  * Located in ui-tui/ directory (Ink-based React frontend) and tui_gateway/ (Python JSON-RPC backend).
  * Activated via etheros --tui or HERMES_TUI=1.
  * Provides a modern, responsive interface with live transcripts, composer, and activity feed.

- **Desktop Application**:
  * Located in apps/desktop/ (Electron + React + nanostore renderer).
  * Provides a standalone desktop chat surface with its own composer, transcript, and slash-command pipeline.
  * Communicates with a tui_gateway backend over JSON-RPC.

- **Web Dashboard**:
  * Located in website/ (Docusaurus) and web/ (the actual dashboard implementation).
  * Provides a browser-based interface for monitoring and interacting with Aetheros instances.
  * Includes features like the embedded TUI via /chat endpoint (using aetheros_cli/pty_bridge.py and aetheros_cli/web_server.py).

All interfaces share the same underlying agent core and tool system, ensuring consistent capabilities across platforms.
## 8. Existing Tests

Aetheros maintains a comprehensive test suite:

- **tests/ directory**: Contains ~17k tests across ~900 files (as of May 26, 2026).
- **test structure**: 
  * Unit tests for individual modules (e.g., tests/tools/, tests/agent/, tests/aetheros_cli/).
  * Integration tests for workflows and cross-component interactions.
  * Specialized tests for skills (tests/skills/), gateway (tests/gateway/), and automation (tests/cron/).
- **Testing infrastructure**:
  * Uses scripts/run_tests.sh to enforce hermetic environment parity with CI (unsets credential vars, TZ=UTC, LANG=C.UTF-8, etc.).
  * Employs subprocess-per-test isolation via in-tree plugin to prevent state leakage.
  * Test timeout of 30 seconds per test to prevent hangs.
- **Test categories** relevant to computer agent:
  * Browser tool tests (tests/tools/test_browser_tool.py, etc.)
  * Computer use tool tests (tests/tools/test_computer_use_tool.py, etc.)
  * Terminal and file operation tests
  * Skill tests (tests/skills/*)
  * Delegation and cron tests
## 10. Duplicate Capabilities

After reviewing the existing codebase, the following potential duplicates were identified:

### 10.1 Terminal Access
- **Duplicate**: Both the 	erminal tool (from tools/terminal_tool.py) and the process tool (also from tools/terminal_tool.py) provide process execution capabilities.
- **Assessment**: These are complementary rather than duplicate - 	erminal provides interactive terminal sessions, while process provides spawn-per-call process execution. Both are needed for different use cases.

### 10.2 File Operations
- **Duplicate**: Multiple tools for file operations exist (ead_file, write_file, patch, search_files in tools/file_tools.py) but they serve distinct purposes (read, write, patch, search).
- **Assessment**: These are not duplicates but rather a complete set of file manipulation tools.

### 10.3 Screenshot Capabilities
- **Potential Duplicate**: Both the computer_use tool (via screenshots) and rowser_tool (via browser_snapshot) can capture screenshots.
- **Assessment**: These serve different purposes - computer_use screenshots the entire desktop or active window, while browser_snapshot captures browser page content via accessibility tree (not a visual screenshot). The browser_tool does not currently provide visual screenshots (only accessibility tree snapshots). However, the computer_use tool can capture screenshots of the browser window if needed. True duplicate would require both providing the same type of screenshot (visual pixels) for the same context.

### 10.4 Keyboard Input
- **Potential Duplicate**: Both computer_use tool (keyboard input) and rowser_tool (browser_type) can send keyboard input.
- **Assessment**: These serve different contexts - computer_use for desktop applications, browser_type for browser pages. Not true duplicates.

Overall, the existing toolset appears to be well-designed with complementary rather than duplicate capabilities. Each tool serves a specific context or provides a distinct level of abstraction.
## 9. Missing Capabilities

Based on the Master Prompt 3 requirements for a unified Computer Agent, the following capabilities are missing or need enhancement:

### 9.1 Unified Computer Agent Interface
- **Gap**: No single agent interface specifically optimized for computer automation tasks that seamlessly integrates browser and desktop capabilities.
- **Opportunity**: Create a specialized computer agent that automatically enables relevant toolsets (computer_use, terminal, file, browser, etc.) and skills when activated.

### 9.2 Advanced Window Management
- **Gap**: While computer_use tool provides mouse and keyboard capabilities, explicit window management operations (list windows, focus window, minimize/maximize/restore/resize/move/close windows) are not exposed as dedicated tools.
- **Opportunity**: 
  * Create window management tools that leverage the computer_use tool's capabilities or platform-specific APIs.
  * For example, use computer_use to send window manager shortcuts (Alt+Tab, Win+Arrow, etc.) or interact with window management APIs via available backends.

### 9.3 Application Launching and Management
- **Gap**: No dedicated tools for launching applications, checking if applications are running, or managing application lifecycle beyond what can be achieved via terminal commands or computer_use shortcuts.
- **Opportunity**: 
  * Create application launch tools that use platform-specific mechanisms (Start menu on Windows, Launch Services on macOS, .desktop files on Linux).
  * Integrate with the terminal tool for CLI-based launching and the computer_use tool for GUI-based launching.

### 9.4 Clipboard Support
- **Gap**: No dedicated tools for clipboard operations (copy, paste, read clipboard) beyond what might be achievable via computer_use keyboard shortcuts (Ctrl+C, Ctrl+V).
- **Opportunity**: 
  * Create clipboard tools that use the computer_use tool to send clipboard shortcuts and potentially access clipboard content through available APIs.
  * Ensure sensitive data in clipboard is handled appropriately (not unnecessarily logged or exposed).

### 9.5 Notification Handling
- **Gap**: No tools for reading or interacting with system notifications (toast notifications, banner alerts, etc.).
- **Opportunity**: 
  * Create notification tools that use platform-specific APIs to read and dismiss notifications.
  * Integrate with computer_use to interact with notification UI elements when needed.

### 9.6 Robust File Upload/Download Handling in Browser Context
- **Gap**: While file tools exist for general file operations, browser-specific upload/download handling could be enhanced.
- **Opportunity**: 
  * Enhance browser tools with dedicated upload/download actions that provide better feedback and error handling.
  * Integrate with file tools for secure storage and validation of downloaded files.
  * Add pre-upload verification (target website, file validation, destination verification, user authorization).

### 9.7 Domain Policy and Access Controls
- **Gap**: While the agent has general security controls, more granular domain-based permissions for browser and computer use actions would be beneficial.
- **Opportunity**: 
  * Implement domain policies (ALLOW/DENY/ASK/TEMPORARY ALLOW) for websites and applications.
  * Integrate with the existing permission system to require appropriate approval for sensitive domains.
  * Support global, workspace, and task-level policies.

### 9.8 Authentication Handling
- **Gap**: No specialized tools for handling authentication pages beyond what can be achieved through general browser interaction.
- **Opportunity**: 
  * Create tools that detect authentication pages and assist with secure credential filling.
  * Integrate with secret_sources to securely retrieve credentials without exposing them to the model.
  * Ensure credentials are never logged or exposed in model-visible output.

### 9.9 Sensitive Data Protection
- **Gap**: While there are some protections, more systematic detection and masking of sensitive data (passwords, API keys, tokens, credit card info, etc.) in model-visible output would be beneficial.
- **Opportunity**: 
  * Enhance the system to automatically detect and mask sensitive data in screenshots, page text, and other outputs.
  * Integrate with existing secret detection mechanisms where possible.

### 9.10 Human Approval for Sensitive Actions
- **Gap**: While approval and clarify tools exist, more granular control over when to require human approval for specific computer actions would be beneficial.
- **Opportunity**: 
  * Define sensitivity levels for computer actions (e.g., deleting files vs. reading files, submitting financial forms vs. browsing news).
  * Integrate with the approval system to require appropriate confirmation for irreversible or sensitive actions.
  * Ensure the agent distinguishes between \"I can prepare this\" and \"I am authorized to submit this.\"

### 9.11 Visual Understanding Enhancement
- **Gap**: While computer_use provides screenshots and browser tools provide accessibility trees, more sophisticated visual understanding could be beneficial.
- **Opportunity**: 
  * Enhance integration between computer_use screenshots, browser accessibility trees, and LSP-like visual analysis.
  * Consider adding OCR capabilities for extracting text from images where accessibility tree is insufficient.
  * Use multiple signals (DOM, accessibility tree, screenshot, OCR) for increased confidence in element identification.

### 9.12 Loop Detection and Prevention
- **Gap**: While the agent has general loop detection in the conversation loop, more specific computer action loop detection would be beneficial.
- **Opportunity**: 
  * Implement computer action loop detection that monitors for repetitive actions without progress (e.g., clicking the same button repeatedly).
  * Set bounded retries and automatic replanning when no progress is detected.
  * Ensure the agent can recover from stale states (changed page, window, or screen).

### 9.13 Action Verification System
- **Gap**: While the agent observes after actions, a more systematic computer action verification system would be beneficial.
- **Opportunity": 
  * Implement the OBSERVE ? PLAN ? ACTION ? OBSERVE ? VERIFY cycle for important computer actions.
  * For example, after a click, observe the response and verify the expected state change occurred.
  * Never assume an action worked without verification.
## 10. Duplicate Capabilities

After reviewing the existing codebase, the following potential duplicates were identified:

### 10.1 Terminal Access
- **Duplicate**: Both the 	erminal tool (from tools/terminal_tool.py) and the process tool (also from tools/terminal_tool.py) provide process execution capabilities.
- **Assessment**: These are complementary rather than duplicate - 	erminal provides interactive terminal sessions, while process provides spawn-per-call process execution. Both are needed for different use cases.

### 10.2 File Operations
- **Duplicate**: Multiple tools for file operations exist (
ead_file, write_file, patch, search_files in tools/file_tools.py) but they serve distinct purposes (read, write, patch, search).
- **Assessment**: These are not duplicates but rather a complete set of file manipulation tools.

### 10.3 Screenshot Capabilities
- **Potential Duplicate**: Both the computer_use tool (via screenshots) and rowser_tool (via browser_snapshot) can capture screenshots.
- **Assessment**: These serve different purposes - computer_use screenshots the entire desktop or active window, while browser_snapshot captures browser page content via accessibility tree (not a visual screenshot). The browser_tool does not currently provide visual screenshots (only accessibility tree snapshots). However, the computer_use tool can capture screenshots of the browser window if needed. True duplicate would require both providing the same type of screenshot (visual pixels) for the same context.

### 10.4 Keyboard Input
- **Potential Duplicate**: Both computer_use tool (keyboard input) and rowser_tool (browser_type) can send keyboard input.
- **Assessment**: These serve different contexts - computer_use for desktop applications, browser_type for browser pages. Not true duplicates.

Overall, the existing toolset appears to be well-designed with complementary rather than duplicate capabilities. Each tool serves a specific context or provides a distinct level of abstraction.
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

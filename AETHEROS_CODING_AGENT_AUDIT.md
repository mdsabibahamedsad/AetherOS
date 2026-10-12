# AetherOS Coding Agent Audit

## Overview
This document audits the existing coding-related functionality in the AetherOS codebase to inform the implementation of a Coding Super Agent.

## Existing Coding-Related Skills

### Software Development Skills
- aetheros-agent-skill-authoring: For creating skills
- node-inspect-debugger: For debugging Node.js applications
- plan: For planning coding tasks
- python-debugpy: For debugging Python code
- requesting-code-review: For pre-commit code review (security scan, quality gates, auto-fix)
- simplify-code: For code simplification
- spike: For exploratory coding
- systematic-debugging: For systematic debugging approaches
- test-driven-development: For TDD (RED-GREEN-REFACTOR)

### GitHub Skills
- codebase-inspection: For inspecting codebase on GitHub
- github-auth: For GitHub authentication
- github-code-review: For reviewing PRs (diffs, inline comments)
- github-issues: For managing GitHub issues
- github-pr-workflow: For GitHub PR workflow
- github-repo-management: For managing GitHub repositories

## Existing Coding-Related Tools
- code_execution_tool.py: Executes code in sandboxed environments (local or remote) via Programmatic Tool Calling (PTC)
- terminal_tool.py: Provides terminal interaction capabilities (shell command execution)
- file_tools.py & file_operations.py: Handle file operations (read, write, edit, delete, etc.)
- delegate_tool.py: Enables task delegation to subagents (important for multi-agent coding workflows)
- memory_tool.py: Manages agent memory (storage and recall of code context)
- skills_tool.py: Manages skill lifecycle (loading, unloading, invoking skills)
- kanban_tools.py: Provides task management capabilities (could be used for coding task tracking)
- cronjob_tools.py: Enables scheduling of tasks (could be used for automated coding tasks)
- checkpoint_manager.py: Manages checkpoints (could be used to save coding session state)
- clarify_tool.py: Facilitates asking clarifying questions (important for understanding coding requirements)
- approval.py: Handles approval workflows (could be used for code approval processes)
- patch_parser.py: Parses patch files (possibly from code reviews or version control)
- browser_tool.py: Enables web interaction (could be used for GitHub, GitLab, documentation lookup)
- vision_tool.py: Provides image analysis capabilities (could be used for UI testing, diagram analysis)
- mcp_tool.py: Implements Model Context Protocol for extending capabilities with external tools
- computer_use_tool.py: Provides low-level computer interaction (mouse, keyboard) - potentially for IDE interaction
- Environment tools (local.py, docker.py, ssh.py, etc.): Provide isolated execution environments for code execution

## Existing LSP and Language Intelligence
- agent/lsp/client.py: Async LSP client over stdin/stdout for language server communication
- agent/lsp/manager.py: LSP service that runs an event loop in a background thread
- agent/lsp/workspace.py: Manages workspace folders and file operations for LSP
- agent/lsp/protocol.py: Implements LSP protocol structures and constants
- agent/lsp/servers.py: Manages language server installation and lifecycle
- Provides language intelligence features (diagnostics, completions, hover, definition, etc.) for multiple languages
- Integrates with file_operations layer to touch files and trigger diagnostics

## Coding Posture Detection
- agent/coding_context.py: Detects when Aetheros is inside a code workspace and shifts into a **coding posture**
- The posture is modelled as a frozen :class:`RuntimeMode` selected from a small :class:`ContextProfile` registry (today: ``coding`` and ``general``)
- Under coding posture:
  * System prompt includes live git/workspace snapshot
  * Toolset collapses to the ``coding`` toolset plus user's enabled MCP servers
  * Delegation propagates the coding posture to subagents
  * Model, memory, and compression settings are declared on the profile
- This ensures that when the user runs Aetheros in a code workspace (CLI, TUI, desktop app, or editor over ACP), the agent automatically adapts to assist with coding tasks.

## Other Relevant Components
- agent/secret_sources.py: For accessing API keys and secrets (needed for GitHub, etc.)
- agent/transports.py: For various transports (maybe for remote execution)
- agent/model_tools.py: For tool discovery and execution (core of tool system)
- agent/conversation_loop.py: Main agent loop (where the coding agent would integrate)
- agent/agent_init.py: Agent initialization (where the AIAgent is set up)
- aetheros_cli/: CLI interface (where coding agent commands would be exposed)
- aetheros_automation/: Task orchestration system (could be reused for coding workflows)
- cron/: Scheduling system (for automated coding tasks)
- tests/: Existing test structure to understand validation approaches
- agent/lsp/: Language Server Protocol implementation (already covered)
- agent/coding_context.py: Coding posture detection (already covered)

## Gaps and Opportunities for Coding Super Agent
While Aetheros already provides a strong foundation for coding assistance, there are several opportunities to enhance its capabilities into a true Coding Super Agent:

### 1. Unified Coding Agent Interface
- **Gap**: No single agent interface specifically optimized for coding tasks
- **Opportunity**: Create a specialized coding agent that leverages the coding posture and automatically enables relevant toolsets (coding, terminal, file, etc.) and skills

### 2. Enhanced Code Generation and Editing
- **Gap**: File editing relies on basic file tools; no specialized diff/patch application tools for sophisticated code changes
- **Opportunity**: 
  - Develop higher-level code generation tools that understand language syntax and semantics
  - Create tools for applying code modifications using AST-based approaches
  - Enhance existing file tools with intelligent code insertion/update capabilities

### 3. Integrated Testing Workflow
- **Gap**: Testing relies on skills and manual execution via code_execution_tool/terminal_tool
- **Opportunity**:
  - Create dedicated testing tools that understand test frameworks (pytest, Jest, etc.) and can run tests in appropriate environments
  - Integrate with LSP to provide test navigation and quick-fix suggestions
  - Develop tools for generating unit tests from code snippets

### 4. Advanced Debugging Capabilities
- **Gap**: Debugging is handled via skills (python-debugpy, node-inspect-debugger) but lacks integrated debugging tool
- **Opportunity**:
  - Create a debugging tool that provides breakpoints, step-through, variable inspection, and stack trace visualization
  - Integrate with LSP for debug information and breakpoint management
  - Support multiple languages through adapters

### 5. Comprehensive Code Review Assistant
- **Gap**: Code review is handled via skills but could be more integrated and proactive
- **Opportunity**:
  - Create tools for automated code review (linting, formatting, security scanning) that provide real-time feedback
  - Integrate with GitHub skills for seamless PR review workflow
  - Develop tools for suggesting code improvements and refactorings

### 6. Dependency Management and Project Understanding
- **Gap**: No dedicated tools for dependency management (pip, npm, Cargo, etc.) or project structure understanding
- **Opportunity**:
  - Create tools for managing dependencies across different ecosystems
  - Develop project understanding tools that can explain project structure, build systems, and configurations
  - Integrate with LSP to provide dependency-aware completions and navigation

### 7. CI/CD Integration
- **Gap**: No direct integration with CI/CD systems (GitHub Actions, GitLab CI, etc.)
- **Opportunity**:
  - Create tools for triggering, monitoring, and retrieving results from CI/CD pipelines
  - Develop skills for analyzing build failures and suggesting fixes

### 8. Refactoring Assistance
- **Gap**: No dedicated refactoring tools beyond basic file manipulation
- **Opportunity**:
  - Create tools for common refactorings (extract method, rename variable, etc.) using LSP or language-specific parsers
  - Integrate with LSP to provide refactoring previews and apply changes safely

### 9. Documentation Generation
- **Gap**: No tools for generating code documentation
- **Opportunity**:
  - Create tools for generating documentation from code comments and annotations
  - Support multiple documentation formats (Javadoc, Sphinx, Markdown, etc.)

### 10. Collaborative Coding Features
- **Gap**: Limited built-in support for real-time collaborative coding (though delegation exists)
- **Opportunity**:
  - Enhance delegation capabilities for pair programming scenarios
  - Create tools for sharing coding sessions and coordinating with other agents or humans

### Implementation Approach
The Coding Super Agent should:
1. Leverage existing coding posture detection to automatically activate when in a code workspace
2. Utilize and extend existing tools rather than reimplementing where possible
3. Integrate with the LSP for deep language understanding
4. Leverage existing skills for specialized workflows (testing, debugging, code review)
5. Provide a unified interface through the existing agent framework
6. Maintain backward compatibility with all existing functionality

## Integration Points
The Coding Super Agent should integrate with the existing agent framework by:
* Being instantiable as an AIAgent with appropriate toolsets and skills pre-enabled
* Leveraging the existing conversation loop and tool execution system
* Using the existing skill system to load coding-relevant skills on demand
* Integrating with the LSP service for language intelligence
* Respecting the coding posture detection to automatically adapt to coding contexts

Configuration points:
* Can be enabled/disabled via configuration
* Can be customized to enable/disable specific capabilities (testing, debugging, etc.)
* Can integrate with existing MCP servers for extended capabilities

## Conclusion
Aetheros already provides a robust foundation for coding assistance through its skills, tools, LSP implementation, and coding posture detection. The Coding Super Agent would not need to replace these components but rather orchestrate them into a unified, proactive coding assistant. By leveraging the existing architecture and filling the identified gaps, the Coding Super Agent can provide a seamless coding experience that enhances developer productivity while maintaining full compatibility with the existing system.
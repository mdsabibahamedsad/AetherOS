# AetherOS Coding Super Agent Design

## Overview
This document outlines the design for the Coding Super Agent, a specialized AI agent within Aetheros optimized for software development tasks. The design leverages existing Aetheros architecture and fills identified gaps from the audit.

## Core Principles
1. **Leverage Existing Infrastructure**: Use existing tools, skills, LSP, and coding posture detection rather than reimplementing.
2. **Unified Interface**: Provide a cohesive agent experience for coding tasks.
3. **Proactive Assistance**: Anticipate developer needs and offer context-aware help.
4. **Backward Compatibility**: Ensure no disruption to existing Aetheros functionality.
5. **Modular Extensibility**: Allow enabling/disabling specific capabilities via configuration.

## Architecture

### Agent Specialization
The Coding Super Agent will be an instance of `AIAgent` with:
- Pre-enabled toolsets: `coding`, `terminal`, `file`, `memory`, `skills`, `lsp` (if available), and relevant MCP servers
- Pre-loaded skills: `test-driven-development`, `requesting-code-review`, `python-debugpy` (or language-specific), `plan`, `systematic-debugging`, `github-code-review`, `github-pr-workflow` (as appropriate)
- Custom system prompt enhancements for coding contexts
- Integration with LSP for language intelligence

### Key Components

#### 1. Coding Agent Factory
A factory function or class that creates a pre-configured `AIAgent` instance optimized for coding.
- Located in `agent/coding_agent.py` or similar
- Handles toolset selection, skill loading, and prompt customization

#### 2. Enhanced Toolset: `coding`
Define a new toolset `coding` that includes:
- Existing tools: `code_execution_tool`, `terminal_tool`, `file_tools`, `file_operations`, `delegate_tool`, `memory_tool`, `skills_tool`, `clarify_tool`, `approval_tool`, `patch_parser`
- Potential new tools (to be implemented in Phase 2 if needed):
  - `testing_tool`: For running tests in various frameworks
  - `debugging_tool`: For breakpoint management and debugging
  - `refactoring_tool`: For common refactorings
  - `dependency_tool`: For managing dependencies
  - `ci_cd_tool`: For CI/CD integration
  - `documentation_tool`: For generating documentation

#### 3. Skill Integration
- Automatically load relevant skills based on project context (detected via file extensions, package.json, etc.)
- Allow manual skill loading/unloading via `/skills` commands
- Create a meta-skill for the Coding Super Agent that orchestrates other skills

#### 4. LSP Integration
- Use existing LSP service for diagnostics, completions, hover, definition, etc.
- Enhance with coding-agent-specific features:
  - Test navigation (find related tests)
  - Error explanation and quick fixes
  - Code generation suggestions

#### 5. Context Awareness
- Leverage `coding_context.py` to detect coding workspaces
- Enhance context with:
  - Project type detection (web, mobile, backend, etc.)
  - Framework detection (React, Django, Spring, etc.)
  - Recent changes and git status
  - Active files and open editors (if available via TUI/desktop)

#### 6. Interaction Model
- Standard agent conversation loop with tool usage
- Specialized slash commands for coding tasks:
  - `/code generate <description>`: Generate code from description
  - `/code edit <instructions>`: Edit existing code
  - `/code explain`: Explain selected code or current file
  - `/code test`: Generate or run tests
  - `/code debug`: Start debugging session
  - `/code review`: Request code review
  - `/code refactor <type>`: Apply refactoring
  - `/code doc`: Generate documentation
  - `/code deps <action>`: Manage dependencies
  - `/code ci <action>`: Interact with CI/CD

#### 7. Configuration
- New config section `coding_agent:` in `config.yaml`
  - `enabled: true/false`
  - `auto_activate: true/false` (automatically activate in coding workspaces)
  - `preferred_languages: [list]` 
  - `enabled_capabilities: [testing, debugging, refactoring, etc.]`
  - `tool_overrides: {}` (custom tool parameters)
  - `skill_overrides: {}` (custom skill parameters)

## Implementation Plan

### Phase 1: Foundation (Current Phase)
- Create `agent/coding_agent.py` with factory function
- Define `coding` toolset in `toolsets.py` (aggregating existing tools)
- Update `aetheros_cli/commands.py` to add `/code` command group
- Implement basic `/code` subcommands that delegate to existing tools/skills
- Add configuration schema

### Phase 2: Enhanced Capabilities
- Implement new tools as needed (testing, debugging, refactoring, etc.)
- Enhance LSP integration with coding-specific features
- Improve context awareness with project/framework detection
- Create meta-skill for orchestrating coding workflows

### Phase 3: Polish and Integration
- Refine user experience and error handling
- Add comprehensive documentation and examples
- Ensure seamless integration with all Aetheros interfaces (CLI, TUI, desktop, gateway)
- Performance optimization and testing

## Integration Points

### With Existing Agent Framework
- The Coding Super Agent uses the standard `AIAgent` class, so it inherits all standard features (conversation loop, tool execution, memory, etc.)
- It registers with the CLI via the standard slash command mechanism
- It can be instantiated directly or via a `/coding agent` command

### With Skills
- Uses existing skills where possible
- Provides a meta-skill that can recommend and load appropriate coding skills
- Skills can be triggered automatically based on context (e.g., load `test-driven-development` when test files are present)

### With LSP
- Consumes the existing LSP service for language intelligence
- Adds coding-agent-specific LSP requests (if needed) or uses existing ones in novel ways

### With Coding Posture
- Automatically activates when `coding_context.py` detects a coding workspace
- Can be manually overridden via configuration or command

### With MCP
- Includes any enabled MCP servers in the `coding` toolset
- Can recommend relevant MCP servers for coding tasks (e.g., a code search MCP server)

## Potential New Tools (for Phase 2)

### Testing Tool
- Parameters: `framework` (auto-detect or specify), `test_path`, `args`
- Functionality: Discover and run tests, parse results, provide feedback
- Integrates with: `code_execution_tool` or `terminal_tool` for execution, LSP for test navigation

### Debugging Tool
- Parameters: `action` (start, stop, breakpoints, step, etc.), `location`, `condition`
- Functionality: Manage debugging sessions, set breakpoints, inspect state
- Integrates with: LSP for breakpoint resolution, `terminal_tool` for debugger backend

### Refactoring Tool
- Parameters: `type` (rename, extract method, etc.), `target`, `options`
- Functionality: Apply refactorings using LSP or language-specific parsers
- Integrates with: Lsp for refactoring capabilities, `file_tools` for applying changes

### Dependency Tool
- Parameters: `ecosystem` (pip, npm, cargo, etc.), `action` (add, remove, update, list), `package`, `version`
- Functionality: Manage project dependencies
- Integrates with: `terminal_tool` to run package manager commands

### CI/CD Tool
- Parameters: `system` (github, gitlab, jenkins, etc.), `action` (trigger, status, logs, etc.), `workflow`, `ref`
- Functionality: Interact with CI/CD systems
- Integrates with: `browser_tool` or `mcp_tool` for API interactions, `secret_sources` for authentication

### Documentation Tool
- Parameters: `format` (javadoc, sphinx, markdown, etc.), `target`, `options`
- Functionality: Generate documentation from code comments and annotations
- Integrates with: LSP for symbol information, `file_tools` for writing output

## Conclusion
The Coding Super Agent will enhance Aetheros by providing a unified, proactive coding assistant that leverages the platform's existing strengths. By following this design, we ensure compatibility, extensibility, and a seamless user experience that boosts developer productivity.

Next steps: Begin implementation of Phase 1 foundation components.
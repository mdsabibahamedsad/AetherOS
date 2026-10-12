## 10. Existing Migrations

- Aetheros has a migration system for configuration and schema changes, managed via `aetheros_cli/config.py` and the `_config_version` mechanism.
- Memory system migrations would need to be handled carefully to avoid data loss.
- Existing memory-related files that may require migration considerations:
  * `agent/memory_manager.py`
  * `agent/memory_provider.py`
  * `agent/memory_lifecycle.py`
  * `agent/metadata.md` (user's personal notes file)
  * `agent/metadata/` (if any)
  * `tools/memory_tool.py`
  * Skills that interact with memory (e.g., in `skills/` directory)
- The system uses a versioning mechanism in `DEFAULT_CONFIG` in `aetheros_cli/config.py` to trigger migrations when the config version is bumped.
- For memory data, a similar approach could be used with a memory schema version.
## 11. Missing Capabilities

Based on the Master Prompt 5 requirements, the following capabilities are missing or need enhancement in the current memory system:

- **Unified memory layers**: While there is a memory system, it does not explicitly separate working memory, conversation memory, session memory, episodic memory, semantic memory, procedural memory, project memory, user memory, agent memory, and organizational memory as distinct layers with appropriate scoping and lifetimes.
- **Memory scoping and isolation**: The current memory system does not enforce strict isolation by user, project, workspace, agent, etc. Memories are not scoped by these dimensions by default.
- **Provenance tracking**: Memories do not consistently track their source (USER, ASSISTANT, PROJECT_FILE, DOCUMENT, RESEARCH, WEB_SOURCE, CODE, TOOL, TASK_RESULT, SYSTEM_CONFIGURATION).
- **Memory confidence and importance**: Memories lack confidence levels (EXPLICIT_USER, AUTHORITATIVE_SOURCE, VERIFIED, OBSERVED, INFERRED, MODEL_INFERRED, UNKNOWN) and importance levels (CRITICAL, HIGH, MEDIUM, LOW, TEMPORARY).
- **Temporal memory**: Memories do not have valid_from and valid_until fields to support temporal reasoning.
- **Memory versioning**: Important memories do not support version history.
- **Memory expiration and forgetting**: There is no systematic policy for expiring temporary memories or forgetting low-value memories.
- **Memory update and conflict resolution**: There is no mechanism for updating memories with versioning and resolving conflicts (e.g., when a fact changes).
- **Memory deduplication**: There is no system to detect and merge duplicate or near-duplicate memories.
- **Memory inspection and controls**: There is no way for users to inspect memories, forget specific memories, or control what is remembered.
- **Memory search and retrieval**: While there is some retrieval capability, there is no unified interface for semantic search, keyword search, metadata filtering, temporal filtering, scope filtering, entity filtering, hybrid retrieval, reranking, and graph retrieval.
- **Knowledge base and knowledge graph**: There is no unified knowledge abstraction that combines documents, repositories, web research, project files, manual notes, research reports, and verified memories into a searchable knowledge base with entity and relationship tracking.
- **Document indexing and chunking**: There is no system for indexing documents (PDF, DOCX, TXT, MD, HTML, CSV, JSON, source code, configuration) with intelligent chunking and metadata storage.
- **Codebase knowledge**: There is no system to index the codebase (files, symbols, functions, classes, imports, dependencies, tests, architecture) for code-aware retrieval.
- **Memory explanation and auditing**: There is no way to explain why a memory was used in a context or to audit memory operations (created, retrieved, updated, deleted, expired, conflict, verified, denied).
- **Memory + research integration**: Research results are not automatically turned into memory when appropriate (verified findings, important sources, research decisions, project-specific discoveries).
- **Memory + coding integration**: The Coding Agent does not retrieve or store reusable project knowledge (architecture decisions, coding conventions, test commands, known bugs, previous fixes, dependency decisions).
- **Memory + computer agent integration**: The Computer Agent does not retrieve or store approved workflows, application state, project environment, known UI behavior, test procedures.
- **Memory access control**: There is no fine-grained access control for memory retrieval based on user, organization, workspace, project, agent, session.
- **Encryption and secret exclusion**: There is no mechanism to encrypt sensitive memories or to ensure that secrets (passwords, API keys, private keys, authentication tokens, session cookies, credential material) are not stored in long-term memory.
- **Privacy classification**: There is no support for PUBLIC, INTERNAL, PRIVATE, SENSITIVE, RESTRICTED classifications for memories.
- **Memory drift detection and reality verification**: There is no system to detect when project reality changes (e.g., memory says API endpoint = /v1/chat but code uses /v2/chat) and trigger verification.
- **Failure and success memory**: There is no system to store useful recurring failures or successful procedures with verification against current project state.
- **Decision memory**: There is no system to store architecture decisions with structure (decision, reason, alternatives, date, scope, owner/source, status, superseded_by).
- **User-provided memory**: There is no mechanism for explicit user instructions to remember or forget something.
- **Memory query API**: There is no stable API conceptually equivalent to memory.add(), memory.search(), memory.get(), memory.update(), memory.delete(), memory.forget(), memory.verify(), memory.explain(), memory.list(), memory.consolidate().
- **RAG API**: There is no API for knowledge.index(), knowledge.search(), knowledge.retrieve(), knowledge.delete(), knowledge.reindex(), knowledge.sources(), knowledge.explain().
- **Context API**: There is no API for context.build(), context.retrieve(), context.rank(), context.compress(), context.validate().
## 12. Duplicate Capabilities

After reviewing the existing codebase, the following potential duplicates were identified:

- **Memory system and llm-wiki skill**: The llm-wiki skill in skills/research/llm-wiki provides a knowledge base functionality that overlaps with the proposed unified knowledge base. However, llm-wiki is markdown-file based and lacks the advanced features of a full knowledge graph and entity resolution.
- **Memory system and memory_lifecycle.py**: The agent/memory_lifecycle.py already handles conflict detection for facts (attribute contradictions, polarity conflicts) and memory decay, which are part of the proposed memory lifecycle.
- **Memory system and skills/tool.py**: The skills tool already provides a mechanism to load and manage skills, which can be considered a form of procedural memory.
- **These are not exact duplicates but rather complementary or partial implementations. The proposed memory engine would unify and enhance these existing capabilities.
## 13. Data-loss risks

- **Migration risks**: Changing the memory schema or storage format without proper migration could corrupt or lose existing memories (e.g., user's personal notes in agent/metadata.md, skill knowledge, etc.).
- **Incorrect deletion**: Bugs in memory deletion or forgetting mechanisms could inadvertently remove important memories.
- **Storage corruption**: Disk failures or improper handling of memory files could lead to data loss.
- **Overwriting memories**: Updates to memories without versioning could overwrite valuable historical information.
- **Conflicting writes**: Concurrent modifications to the same memory by multiple agents or processes could lead to lost updates.
- **Improper scoping**: Memories stored with incorrect scope could be inaccessible or appear as lost data.
- **Encryption issues**: If encryption is used, loss of encryption keys could render memories inaccessible.
- **These risks must be mitigated through backups, versioning, atomic operations, and thorough testing.
## 14. Security risks

- **Secret leakage**: Storing secrets (passwords, API keys, private keys, etc.) in long-term memory could lead to exposure if memory is accessed or leaked.
- **Inference attacks**: An attacker could infer sensitive information by querying the memory system for related facts.
- **Memory injection**: Malicious input could lead to the storage of false or harmful memories that could influence future behavior.
- **Scope bypass**: Failure to properly enforce memory scopes could allow one user to access another user's memories.
- **These risks must be addressed through secret exclusion, input validation, strict scoping, and encryption where appropriate.
## 15. Integration points

- **Agent system**: The memory engine should be integrated into the agent's core loop so that memories can be retrieved and stored during agent operation.
- **Coding Agent**: The Coding Agent should retrieve relevant project memories (architecture decisions, coding conventions, etc.) and store reusable knowledge after successful work.
- **Computer Agent**: The Computer Agent should retrieve approved workflows and project environment information, and store test procedures and known UI behavior.
- **Research Agent**: The Research Agent should store verified research findings and important sources as memories, and retrieve relevant background knowledge.
- **Skill system**: Skills should be able to store and retrieve procedural knowledge as memories.
- **MCP system**: External MCP servers could expose memory-like functionality that should be integrated into the unified memory engine.
- **LSP system**: The LSP system could benefit from semantic memory for code intelligence (e.g., recalling similar code patterns).
- **Automation system**: The aetheros_automation/ system could use memory to store and retrieve workflow templates and execution history.
- **Cron system**: Scheduled tasks could store execution results as memories and retrieve previous runs for comparison.
- **These integration points ensure that memory is a cross-cutting concern that enhances all aspects of Aetheros.
## 16. Files to modify and Files that must remain untouched

### Files to modify (potentially, for integration):
- `agent/memory_manager.py`: To enhance with memory layers, scoping, provenance, etc.
- `agent/memory_provider.py`: To abstract different memory backends.
- `agent/memory_lifecycle.py`: To implement memory lifecycle features (expiration, forgetting, versioning, conflict resolution).
- `agent/metadata.md`: To potentially migrate to a structured memory format.
- `tools/memory_tool.py`: To expose memory operations as a tool.
- `agent/agent_init.py`: To initialize the memory engine.
- `agent/model_tools.py`: To integrate memory retrieval into the agent's tool execution.
- `agent/conversation_loop.py`: To integrate memory context building.
- `aetheros_cli/config.py`: To add a memory configuration section.
- `aetheros_cli/commands.py`: To add memory-related slash commands (e.g., `/memory`).
- `skills/ directory`: To update skills to use the new memory engine for procedural knowledge.
- `tools/skills_tool.py`: To integrate memory storage for skills.
- `tools/mcp_tool.py`: To integrate external MCP servers as memory sources.
- `agent/lsp/`: To potentially use semantic memory for code intelligence.
- `aetheros_automation/`: To integrate memory for workflow automation.
- `cron/`: To integrate memory for scheduled task history.

### Files that must remain untouched (unless absolutely necessary):
- `run_agent.py`: Core agent runner.
- `agent/agent_init.py`: (Already listed for modification, but changes should be minimal and backward compatible).
- `agent/model_tools.py`: (Already listed for modification, but the core tool execution logic should be preserved).
- `agent/conversation_loop.py`: (Already listed for modification, but the conversation loop structure should be preserved).
- `tools/registry.py`: Central tool registry (auto-discovery and registration).
- `tools/toolsets.py`: Toolset definitions and _AETHEROS_CORE_TOOLS.
- `tools/\*.py`: Individual tool implementations (modifying these could break tool contracts).
- `tools/skills_tool.py`: Skill lifecycle management (already listed for modification, but caution advised).
- `skills/ directory`: Skill documents (modifying skill documents is allowed and encouraged, but the skill system framework should not be changed).
- `aetheros_cli/config.py`: Configuration management (already listed for modification, but schema changes should be backward compatible).
- `agent/secret_sources.py`: Secure secret access.
- `agent/tool_guardrails.py`: Tool call guardrails (critical for security).
- `aetheros_cli/cli.py`: Main CLI implementation.
- `ui-tui/` and `tui_gateway/`: TUI implementation.
- `apps/desktop/`: Desktop application.
- `scripts/run_tests.sh`: Test execution script.
- The test isolation plugin.
- `AGENTS.md`: This file itself (defines project contribution guidelines).
- Master Prompts 1-5 (defines the architectural vision).

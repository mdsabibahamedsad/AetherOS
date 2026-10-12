#!/usr/bin/env python3
"""
Capability Registry — Central Capability Discovery and Registration

Maps user goals to executable capabilities by maintaining a registry of
CapabilitySpec entries that link to tools, models, MCP servers, plugins,
and skills. Provides dynamic discovery, health tracking, and availability
checking.
"""

from __future__ import annotations

import importlib
import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .models import (
    CapabilityCategory,
    CapabilityEntry,
    CapabilityProvider,
    CapabilitySpec,
    ModelReference,
    RiskLevel,
    ToolReference,
    VerificationStrategy,
    RecoveryStrategy,
    to_json_serializable,
)

logger = logging.getLogger(__name__)


# Default capability specifications for built-in AetherOS capabilities
BUILTIN_CAPABILITIES: Dict[str, CapabilitySpec] = {
    # Computer Control
    "computer_control": CapabilitySpec(
        id="computer_control",
        name="Computer Control",
        description="Full desktop automation: screenshot, click, type, scroll, window management",
        category=CapabilityCategory.COMPUTER_CONTROL,
        tools=[
            ToolReference(
                name="computer_use",
                toolset="computer_use",
                schema={"name": "computer_use", "description": "Control macOS desktop via cua-driver"},
                handler="tools.computer_use_tool.computer_use",
                risk_level=RiskLevel.HIGH,
                permissions=["desktop_automation"],
                confirmation_required=True,
                supports_background_execution=True,
            ),
        ],
        models=[
            ModelReference(
                name="cua-model",
                provider="local",
                capabilities=["vision", "tool_use"],
                supports_vision=True,
            ),
        ],
        risk_level=RiskLevel.HIGH,
        confirmation_required=True,
        timeout_seconds=600,
        tags=["desktop", "automation", "macos"],
    ),
    
    # Web Browser
    "web_browser": CapabilitySpec(
        id="web_browser",
        name="Web Browser",
        description="Full browser automation: navigate, click, type, extract, forms, downloads",
        category=CapabilityCategory.WEB_BROWSER,
        tools=[
            ToolReference(name="browser_navigate", toolset="browser", schema={}, handler="tools.browser_tool.browser_navigate"),
            ToolReference(name="browser_click", toolset="browser", schema={}, handler="tools.browser_tool.browser_click"),
            ToolReference(name="browser_type", toolset="browser", schema={}, handler="tools.browser_tool.browser_type"),
            ToolReference(name="browser_snapshot", toolset="browser", schema={}, handler="tools.browser_tool.browser_snapshot"),
            ToolReference(name="browser_scroll", toolset="browser", schema={}, handler="tools.browser_tool.browser_scroll"),
            ToolReference(name="browser_back", toolset="browser", schema={}, handler="tools.browser_tool.browser_back"),
            ToolReference(name="browser_press", toolset="browser", schema={}, handler="tools.browser_tool.browser_press"),
            ToolReference(name="browser_get_images", toolset="browser", schema={}, handler="tools.browser_tool.browser_get_images"),
            ToolReference(name="browser_vision", toolset="browser", schema={}, handler="tools.browser_tool.browser_vision"),
            ToolReference(name="browser_console", toolset="browser", schema={}, handler="tools.browser_tool.browser_console"),
            ToolReference(name="browser_cdp", toolset="browser", schema={}, handler="tools.browser_tool.browser_cdp"),
            ToolReference(name="browser_dialog", toolset="browser", schema={}, handler="tools.browser_tool.browser_dialog"),
            ToolReference(name="browser_download", toolset="browser", schema={}, handler="tools.browser_tool.browser_download"),
            ToolReference(name="browser_upload", toolset="browser", schema={}, handler="tools.browser_tool.browser_upload"),
            ToolReference(name="browser_tab", toolset="browser", schema={}, handler="tools.browser_tool.browser_tab"),
            ToolReference(name="browser_form_fill", toolset="browser", schema={}, handler="tools.browser_tool.browser_form_fill"),
            ToolReference(name="browser_submit", toolset="browser", schema={}, handler="tools.browser_tool.browser_submit"),
        ],
        risk_level=RiskLevel.MEDIUM,
        timeout_seconds=300,
        tags=["web", "browser", "automation"],
    ),
    
    # Web Search
    "web_search": CapabilitySpec(
        id="web_search",
        name="Web Search",
        description="Search the web and extract content from pages",
        category=CapabilityCategory.WEB_BROWSER,
        tools=[
            ToolReference(name="web_search", toolset="web", schema={}, handler="tools.web_tools.web_search"),
            ToolReference(name="web_extract", toolset="web", schema={}, handler="tools.web_tools.web_extract"),
        ],
        risk_level=RiskLevel.LOW,
        timeout_seconds=120,
        tags=["web", "search", "research"],
    ),
    
    # File System
    "file_system": CapabilitySpec(
        id="file_system",
        name="File System",
        description="Read, write, search, patch, and organize files",
        category=CapabilityCategory.FILE_SYSTEM,
        tools=[
            ToolReference(name="read_file", toolset="file", schema={}, handler="tools.file_tools.read_file"),
            ToolReference(name="write_file", toolset="file", schema={}, handler="tools.file_tools.write_file"),
            ToolReference(name="patch", toolset="file", schema={}, handler="tools.file_tools.patch"),
            ToolReference(name="search_files", toolset="file", schema={}, handler="tools.file_tools.search_files"),
        ],
        risk_level=RiskLevel.MEDIUM,
        timeout_seconds=120,
        tags=["files", "read", "write", "search"],
    ),
    
    # Terminal
    "terminal": CapabilitySpec(
        id="terminal",
        name="Terminal",
        description="Execute commands, manage processes, run scripts",
        category=CapabilityCategory.TERMINAL,
        tools=[
            ToolReference(name="terminal", toolset="terminal", schema={}, handler="tools.terminal_tool.terminal", risk_level=RiskLevel.HIGH, permissions=["shell_exec"], confirmation_required=True),
            ToolReference(name="process", toolset="terminal", schema={}, handler="tools.terminal_tool.process"),
            ToolReference(name="read_terminal", toolset="terminal", schema={}, handler="tools.read_terminal_tool.read_terminal"),
        ],
        risk_level=RiskLevel.HIGH,
        confirmation_required=True,
        timeout_seconds=600,
        tags=["shell", "command", "process"],
    ),
    
    # Coding
    "coding": CapabilitySpec(
        id="coding",
        name="Coding Agent",
        description="Understand, edit, test, and debug code repositories",
        category=CapabilityCategory.CODING,
        tools=[
            ToolReference(name="execute_code", toolset="code_execution", schema={}, handler="tools.code_execution_tool.execute_code"),
            ToolReference(name="delegate_task", toolset="delegation", schema={}, handler="tools.delegate_tool.delegate_task"),
        ],
        models=[
            ModelReference(name="coding-model", provider="cloud", capabilities=["coding", "reasoning", "tool_use"], supports_tools=True, supports_reasoning=True),
        ],
        risk_level=RiskLevel.MEDIUM,
        timeout_seconds=600,
        tags=["coding", "development", "debugging"],
    ),
    
    # Research
    "research": CapabilitySpec(
        id="research",
        name="Deep Research",
        description="Multi-source research with citation tracking and synthesis",
        category=CapabilityCategory.RESEARCH,
        tools=[
            ToolReference(name="web_search", toolset="web", schema={}, handler="tools.web_tools.web_search"),
            ToolReference(name="web_extract", toolset="web", schema={}, handler="tools.web_tools.web_extract"),
            ToolReference(name="session_search", toolset="session_search", schema={}, handler="tools.session_search_tool.session_search"),
        ],
        models=[
            ModelReference(name="research-model", provider="cloud", capabilities=["reasoning", "long_context"], supports_reasoning=True),
        ],
        risk_level=RiskLevel.LOW,
        timeout_seconds=900,
        tags=["research", "synthesis", "citations"],
    ),
    
    # Knowledge
    "knowledge": CapabilitySpec(
        id="knowledge",
        name="Knowledge Engine",
        description="Semantic search, RAG, document indexing, and knowledge retrieval",
        category=CapabilityCategory.KNOWLEDGE,
        tools=[],
        models=[
            ModelReference(name="embedding-model", provider="local", capabilities=["embedding"]),
            ModelReference(name="reranker", provider="local", capabilities=["reranking"]),
        ],
        risk_level=RiskLevel.LOW,
        timeout_seconds=120,
        tags=["knowledge", "rag", "search", "documents"],
    ),
    
    # Memory
    "memory": CapabilitySpec(
        id="memory",
        name="Memory System",
        description="Persistent memory across sessions: notes, preferences, knowledge graph",
        category=CapabilityCategory.MEMORY,
        tools=[
            ToolReference(name="memory", toolset="memory", schema={}, handler="tools.memory_tool.memory"),
            ToolReference(name="memory2_search", toolset="memory", schema={}, handler="tools.memory2_tool.memory2_search"),
            ToolReference(name="memory2_get", toolset="memory", schema={}, handler="tools.memory2_tool.memory2_get"),
            ToolReference(name="memory2_create", toolset="memory", schema={}, handler="tools.memory2_tool.memory2_create"),
            ToolReference(name="memory2_explain", toolset="memory", schema={}, handler="tools.memory2_tool.memory2_explain"),
            ToolReference(name="memory2_forget", toolset="memory", schema={}, handler="tools.memory2_tool.memory2_forget"),
            ToolReference(name="memory2_project", toolset="memory", schema={}, handler="tools.memory2_tool.memory2_project"),
            ToolReference(name="memory2_graph", toolset="memory", schema={}, handler="tools.memory2_tool.memory2_graph"),
            ToolReference(name="memory2_conflicts", toolset="memory", schema={}, handler="tools.memory2_tool.memory2_conflicts"),
        ],
        risk_level=RiskLevel.LOW,
        timeout_seconds=120,
        tags=["memory", "persistence", "knowledge_graph"],
    ),
    
    # Communication
    "communication": CapabilitySpec(
        id="communication",
        name="Communication",
        description="Send messages across platforms: Telegram, Discord, Slack, Email, SMS",
        category=CapabilityCategory.COMMUNICATION,
        tools=[
            ToolReference(name="send_message", toolset="messaging", schema={}, handler="tools.send_message_tool.send_message", risk_level=RiskLevel.HIGH, permissions=["messaging"], confirmation_required=True),
        ],
        risk_level=RiskLevel.HIGH,
        confirmation_required=True,
        timeout_seconds=60,
        tags=["messaging", "telegram", "discord", "slack", "email"],
    ),
    
    # Calendar
    "calendar": CapabilitySpec(
        id="calendar",
        name="Calendar",
        description="Manage calendar events, schedule meetings, detect conflicts",
        category=CapabilityCategory.CALENDAR,
        tools=[],
        risk_level=RiskLevel.MEDIUM,
        timeout_seconds=60,
        tags=["calendar", "scheduling", "events"],
    ),
    
    # Automation
    "automation": CapabilitySpec(
        id="automation",
        name="Automation Engine",
        description="Create, schedule, and manage automated workflows",
        category=CapabilityCategory.AUTOMATION,
        tools=[
            ToolReference(name="automation_create", toolset="automation", schema={}, handler="tools.automation_tool.automation_create"),
            ToolReference(name="automation_preview", toolset="automation", schema={}, handler="tools.automation_tool.automation_preview"),
            ToolReference(name="automation_enable", toolset="automation", schema={}, handler="tools.automation_tool.automation_enable"),
            ToolReference(name="automation_disable", toolset="automation", schema={}, handler="tools.automation_tool.automation_disable"),
            ToolReference(name="automation_delete", toolset="automation", schema={}, handler="tools.automation_tool.automation_delete"),
            ToolReference(name="automation_run", toolset="automation", schema={}, handler="tools.automation_tool.automation_run"),
            ToolReference(name="automation_runs", toolset="automation", schema={}, handler="tools.automation_tool.automation_runs"),
            ToolReference(name="automation_search", toolset="automation", schema={}, handler="tools.automation_tool.automation_search"),
            ToolReference(name="automation_build", toolset="automation", schema={}, handler="tools.automation_tool.automation_build"),
            ToolReference(name="automation_template", toolset="automation", schema={}, handler="tools.automation_tool.automation_template"),
            ToolReference(name="automation_health", toolset="automation", schema={}, handler="tools.automation_tool.automation_health"),
            ToolReference(name="automation_stop_all", toolset="automation", schema={}, handler="tools.automation_tool.automation_stop_all"),
        ],
        risk_level=RiskLevel.MEDIUM,
        timeout_seconds=300,
        tags=["automation", "workflow", "scheduling"],
    ),
    
    # Multi-Agent
    "multi_agent": CapabilitySpec(
        id="multi_agent",
        name="Multi-Agent Orchestration",
        description="Spawn and coordinate specialist subagents for complex tasks",
        category=CapabilityCategory.MULTI_AGENT,
        tools=[
            ToolReference(name="delegate_task", toolset="delegation", schema={}, handler="tools.delegate_tool.delegate_task"),
            ToolReference(name="swarm_start", toolset="swarm", schema={}, handler="tools.swarm_tool.swarm_start"),
            ToolReference(name="swarm_status", toolset="swarm", schema={}, handler="tools.swarm_tool.swarm_status"),
            ToolReference(name="swarm_stop", toolset="swarm", schema={}, handler="tools.swarm_tool.swarm_stop"),
            ToolReference(name="swarm_pause", toolset="swarm", schema={}, handler="tools.swarm_tool.swarm_pause"),
            ToolReference(name="swarm_resume", toolset="swarm", schema={}, handler="tools.swarm_tool.swarm_resume"),
            ToolReference(name="swarm_approve", toolset="swarm", schema={}, handler="tools.swarm_tool.swarm_approve"),
            ToolReference(name="swarm_events", toolset="swarm", schema={}, handler="tools.swarm_tool.swarm_events"),
            ToolReference(name="swarm_trace", toolset="swarm", schema={}, handler="tools.swarm_tool.swarm_trace"),
        ],
        risk_level=RiskLevel.MEDIUM,
        timeout_seconds=1800,
        tags=["orchestration", "subagents", "swarm"],
    ),
    
    # Model Orchestration
    "model_orchestration": CapabilitySpec(
        id="model_orchestration",
        name="Model Orchestration",
        description="Route tasks to optimal models based on capability, cost, latency, privacy",
        category=CapabilityCategory.MODEL_ORCHESTRATION,
        tools=[],
        models=[
            ModelReference(name="fast-model", provider="cloud", capabilities=["fast"], latency_class="fast", cost_class="low"),
            ModelReference(name="reasoning-model", provider="cloud", capabilities=["reasoning"], supports_reasoning=True, latency_class="slow", cost_class="high"),
            ModelReference(name="coding-model", provider="cloud", capabilities=["coding"], supports_tools=True),
            ModelReference(name="vision-model", provider="cloud", capabilities=["vision"], supports_vision=True),
            ModelReference(name="local-model", provider="local", capabilities=["local"], privacy_level="local"),
        ],
        risk_level=RiskLevel.LOW,
        tags=["model", "routing", "optimization"],
    ),
    
    # Vision
    "vision": CapabilitySpec(
        id="vision",
        name="Vision Analysis",
        description="Analyze images, screenshots, documents, UI elements",
        category=CapabilityCategory.MULTIMODAL,
        tools=[
            ToolReference(name="vision_analyze", toolset="vision", schema={}, handler="tools.vision_tools.vision_analyze"),
            ToolReference(name="image_ocr", toolset="vision", schema={}, handler="tools.vision_tools.image_ocr"),
            ToolReference(name="document_extract", toolset="vision", schema={}, handler="tools.vision_tools.document_extract"),
            ToolReference(name="screen_capture", toolset="vision", schema={}, handler="tools.vision_tools.screen_capture"),
            ToolReference(name="screen_understand", toolset="vision", schema={}, handler="tools.vision_tools.screen_understand"),
        ],
        models=[
            ModelReference(name="vision-model", provider="cloud", capabilities=["vision"], supports_vision=True),
        ],
        risk_level=RiskLevel.LOW,
        timeout_seconds=120,
        tags=["vision", "image", "ocr", "document"],
    ),
    
    # Voice
    "voice": CapabilitySpec(
        id="voice",
        name="Voice Assistant",
        description="Speech-to-text, text-to-speech, realtime conversation",
        category=CapabilityCategory.VOICE,
        tools=[
            ToolReference(name="text_to_speech", toolset="tts", schema={}, handler="tools.tts_tool.text_to_speech"),
            ToolReference(name="transcription", toolset="transcription", schema={}, handler="tools.transcription_tools.transcribe"),
        ],
        models=[
            ModelReference(name="stt-model", provider="cloud", capabilities=["speech_to_text"]),
            ModelReference(name="tts-model", provider="cloud", capabilities=["text_to_speech"]),
        ],
        risk_level=RiskLevel.LOW,
        timeout_seconds=300,
        tags=["voice", "speech", "tts", "stt"],
    ),
    
    # Creative
    "creative": CapabilitySpec(
        id="creative",
        name="Creative Generation",
        description="Generate images, videos, documents, presentations",
        category=CapabilityCategory.CREATIVE,
        tools=[
            ToolReference(name="image_generate", toolset="image_gen", schema={}, handler="tools.image_generation_tool.image_generate"),
            ToolReference(name="video_generate", toolset="video_gen", schema={}, handler="tools.video_generation_tool.video_generate"),
        ],
        models=[
            ModelReference(name="image-gen-model", provider="cloud", capabilities=["image_generation"]),
            ModelReference(name="video-gen-model", provider="cloud", capabilities=["video_generation"]),
        ],
        risk_level=RiskLevel.LOW,
        timeout_seconds=300,
        tags=["creative", "image", "video", "generation"],
    ),
    
    # Data Analysis
    "data_analysis": CapabilitySpec(
        id="data_analysis",
        name="Data Analysis",
        description="Analyze CSV, JSON, spreadsheets, databases; generate charts and reports",
        category=CapabilityCategory.DATA_ANALYSIS,
        tools=[
            ToolReference(name="execute_code", toolset="code_execution", schema={}, handler="tools.code_execution_tool.execute_code"),
        ],
        models=[
            ModelReference(name="analysis-model", provider="cloud", capabilities=["data_analysis", "reasoning"]),
        ],
        risk_level=RiskLevel.LOW,
        timeout_seconds=600,
        tags=["data", "analysis", "charts", "statistics"],
    ),
    
    # Skills
    "skills": CapabilitySpec(
        id="skills",
        name="Skills System",
        description="Load, create, and manage specialized instruction sets",
        category=CapabilityCategory.MCP_PLUGIN,
        tools=[
            ToolReference(name="skills_list", toolset="skills", schema={}, handler="tools.skills_tool.skills_list"),
            ToolReference(name="skill_view", toolset="skills", schema={}, handler="tools.skills_tool.skill_view"),
            ToolReference(name="skill_manage", toolset="skills", schema={}, handler="tools.skills_tool.skill_manage"),
        ],
        risk_level=RiskLevel.LOW,
        timeout_seconds=60,
        tags=["skills", "instructions", "workflows"],
    ),
    
    # Session Search
    "session_search": CapabilitySpec(
        id="session_search",
        name="Session Search",
        description="Search and recall past conversations with summarization",
        category=CapabilityCategory.KNOWLEDGE,
        tools=[
            ToolReference(name="session_search", toolset="session_search", schema={}, handler="tools.session_search_tool.session_search"),
        ],
        risk_level=RiskLevel.LOW,
        timeout_seconds=60,
        tags=["history", "search", "conversations"],
    ),
    
    # Cron Jobs
    "cron_jobs": CapabilitySpec(
        id="cron_jobs",
        name="Cron Jobs",
        description="Schedule and manage recurring tasks",
        category=CapabilityCategory.AUTOMATION,
        tools=[
            ToolReference(name="cronjob", toolset="cronjob", schema={}, handler="tools.cronjob_tools.cronjob"),
        ],
        risk_level=RiskLevel.MEDIUM,
        timeout_seconds=60,
        tags=["cron", "scheduling", "recurring"],
    ),
    
    # Home Assistant
    "home_assistant": CapabilitySpec(
        id="home_assistant",
        name="Home Assistant",
        description="Control and monitor smart home devices",
        category=CapabilityCategory.SYSTEM_INTEGRATION,
        tools=[
            ToolReference(name="ha_list_entities", toolset="homeassistant", schema={}, handler="tools.homeassistant_tool.ha_list_entities"),
            ToolReference(name="ha_get_state", toolset="homeassistant", schema={}, handler="tools.homeassistant_tool.ha_get_state"),
            ToolReference(name="ha_list_services", toolset="homeassistant", schema={}, handler="tools.homeassistant_tool.ha_list_services"),
            ToolReference(name="ha_call_service", toolset="homeassistant", schema={}, handler="tools.homeassistant_tool.ha_call_service"),
        ],
        risk_level=RiskLevel.MEDIUM,
        timeout_seconds=60,
        tags=["home_assistant", "smart_home", "iot"],
    ),
    
    # Kanban
    "kanban": CapabilitySpec(
        id="kanban",
        name="Kanban Coordination",
        description="Multi-agent task coordination via kanban board",
        category=CapabilityCategory.MULTI_AGENT,
        tools=[
            ToolReference(name="kanban_show", toolset="kanban", schema={}, handler="tools.kanban_tools.kanban_show"),
            ToolReference(name="kanban_list", toolset="kanban", schema={}, handler="tools.kanban_tools.kanban_list"),
            ToolReference(name="kanban_complete", toolset="kanban", schema={}, handler="tools.kanban_tools.kanban_complete"),
            ToolReference(name="kanban_block", toolset="kanban", schema={}, handler="tools.kanban_tools.kanban_block"),
            ToolReference(name="kanban_heartbeat", toolset="kanban", schema={}, handler="tools.kanban_tools.kanban_heartbeat"),
            ToolReference(name="kanban_comment", toolset="kanban", schema={}, handler="tools.kanban_tools.kanban_comment"),
            ToolReference(name="kanban_create", toolset="kanban", schema={}, handler="tools.kanban_tools.kanban_create"),
            ToolReference(name="kanban_link", toolset="kanban", schema={}, handler="tools.kanban_tools.kanban_link"),
            ToolReference(name="kanban_unblock", toolset="kanban", schema={}, handler="tools.kanban_tools.kanban_unblock"),
        ],
        risk_level=RiskLevel.LOW,
        timeout_seconds=120,
        tags=["kanban", "coordination", "tasks"],
    ),
    
    # Planning
    "planning": CapabilitySpec(
        id="planning",
        name="Task Planning",
        description="Create and manage multi-step task plans with todo tracking",
        category=CapabilityCategory.PERSONAL_ASSISTANT,
        tools=[
            ToolReference(name="todo", toolset="todo", schema={}, handler="tools.todo_tool.todo"),
        ],
        risk_level=RiskLevel.LOW,
        timeout_seconds=60,
        tags=["planning", "todo", "tasks"],
    ),
    
    # Clarification
    "clarification": CapabilitySpec(
        id="clarification",
        name="User Clarification",
        description="Ask clarifying questions to disambiguate user intent",
        category=CapabilityCategory.PERSONAL_ASSISTANT,
        tools=[
            ToolReference(name="clarify", toolset="clarify", schema={}, handler="tools.clarify_tool.clarify"),
        ],
        risk_level=RiskLevel.NONE,
        timeout_seconds=300,
        tags=["clarification", "questions", "disambiguation"],
    ),
}


@dataclass
class CapabilityRegistry:
    """Central registry for all AetherOS capabilities."""
    
    _capabilities: Dict[str, CapabilityEntry] = field(default_factory=dict)
    _category_index: Dict[CapabilityCategory, Set[str]] = field(default_factory=lambda: defaultdict(set))
    _tag_index: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    _tool_to_capability: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    _model_to_capability: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    _providers: Dict[str, CapabilityProvider] = field(default_factory=dict)
    _verification_strategies: Dict[str, VerificationStrategy] = field(default_factory=dict)
    _recovery_strategies: Dict[str, RecoveryStrategy] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _generation: int = 0
    _config: Dict[str, Any] = field(default_factory=dict)
    _initialized: bool = False

    def __init__(self, config: Dict[str, Any] | None = None):
        self._config = config or {}
        self._capabilities = {}
        self._category_index = defaultdict(set)
        self._tag_index = defaultdict(set)
        self._tool_to_capability = defaultdict(set)
        self._model_to_capability = defaultdict(set)
        self._providers = {}
        self._verification_strategies = {}
        self._recovery_strategies = {}
        self._lock = threading.RLock()
        self._generation = 0
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the registry with built-in capabilities."""
        with self._lock:
            if self._initialized:
                return
            for spec in BUILTIN_CAPABILITIES.values():
                self._register_capability_internal(spec)
            self._initialized = True
            logger.info(f"Capability registry initialized with {len(self._capabilities)} capabilities")

    def _register_capability_internal(self, spec: CapabilitySpec) -> None:
        """Internal registration without locking (caller must hold lock)."""
        entry = CapabilityEntry(spec=spec)
        self._capabilities[spec.id] = entry
        self._category_index[spec.category].add(spec.id)
        for tag in spec.tags:
            self._tag_index[tag].add(spec.id)
        for tool in spec.tools:
            self._tool_to_capability[tool.name].add(spec.id)
        for model in spec.models:
            self._model_to_capability[model.name].add(spec.id)
        for provider in spec.providers:
            self._providers[provider.id] = provider
        self._generation += 1

    def register_capability(self, spec: CapabilitySpec) -> bool:
        """Register a new capability."""
        with self._lock:
            if spec.id in self._capabilities:
                logger.warning(f"Capability {spec.id} already registered, overwriting")
            self._register_capability_internal(spec)
            logger.info(f"Registered capability: {spec.id} ({spec.category.value})")
            return True

    def unregister_capability(self, capability_id: str) -> bool:
        """Unregister a capability."""
        with self._lock:
            entry = self._capabilities.pop(capability_id, None)
            if not entry:
                return False
            spec = entry.spec
            self._category_index[spec.category].discard(capability_id)
            for tag in spec.tags:
                self._tag_index[tag].discard(capability_id)
            for tool in spec.tools:
                self._tool_to_capability[tool.name].discard(capability_id)
            for model in spec.models:
                self._model_to_capability[model.name].discard(capability_id)
            self._generation += 1
            logger.info(f"Unregistered capability: {capability_id}")
            return True

    def get_capability(self, capability_id: str) -> Optional[CapabilityEntry]:
        """Get a capability by ID."""
        with self._lock:
            return self._capabilities.get(capability_id)

    def get_capability_spec(self, capability_id: str) -> Optional[CapabilitySpec]:
        """Get just the spec (no runtime data)."""
        entry = self.get_capability(capability_id)
        return entry.spec if entry else None

    def list_capabilities(
        self,
        category: CapabilityCategory | None = None,
        tag: str | None = None,
        available_only: bool = True,
    ) -> List[CapabilitySpec]:
        """List capabilities with optional filters."""
        with self._lock:
            if category:
                ids = self._category_index.get(category, set())
            elif tag:
                ids = self._tag_index.get(tag, set())
            else:
                ids = set(self._capabilities.keys())
            
            result = []
            for cap_id in ids:
                entry = self._capabilities.get(cap_id)
                if entry and (not available_only or entry.spec.available):
                    result.append(entry.spec)
            return result

    def get_capabilities_for_tool(self, tool_name: str) -> List[CapabilitySpec]:
        """Get all capabilities that use a specific tool."""
        with self._lock:
            cap_ids = self._tool_to_capability.get(tool_name, set())
            return [self._capabilities[cid].spec for cid in cap_ids if cid in self._capabilities]

    def get_capabilities_for_model(self, model_name: str) -> List[CapabilitySpec]:
        """Get all capabilities that use a specific model."""
        with self._lock:
            cap_ids = self._model_to_capability.get(model_name, set())
            return [self._capabilities[cid].spec for cid in cap_ids if cid in self._capabilities]

    def discover_and_register_capabilities(self) -> int:
        """Discover capabilities from the existing tool registry and other sources."""
        count = 0
        
        # Discover from tool registry
        try:
            from tools.registry import registry as tool_registry
            tool_entries = tool_registry._snapshot_entries()
            for entry in tool_entries:
                # Create or update capability for each tool
                cap_id = f"tool:{entry.toolset}:{entry.name}"
                if cap_id not in self._capabilities:
                    spec = CapabilitySpec(
                        id=cap_id,
                        name=entry.name.replace("_", " ").title(),
                        description=entry.description or entry.schema.get("description", ""),
                        category=self._infer_category(entry.toolset),
                        tools=[ToolReference(
                            name=entry.name,
                            toolset=entry.toolset,
                            schema=entry.schema,
                            handler=f"tools.{entry.toolset}_tool.{entry.name}",
                            check_fn=entry.check_fn.__name__ if entry.check_fn else None,
                            requires_env=entry.requires_env,
                            is_async=entry.is_async,
                            risk_level=self._infer_risk_level(entry.toolset),
                            description=entry.description or entry.schema.get("description", ""),
                        )],
                        risk_level=self._infer_risk_level(entry.toolset),
                        tags=[entry.toolset],
                    )
                    self.register_capability(spec)
                    count += 1
        except Exception as e:
            logger.warning(f"Could not discover tools from registry: {e}")
        
        # Discover from MCP servers
        try:
            from tools.mcp_tool import get_mcp_tool_registry
            mcp_registry = get_mcp_tool_registry()
            for server_name, server_info in mcp_registry.get_all_servers().items():
                cap_id = f"mcp:{server_name}"
                if cap_id not in self._capabilities:
                    spec = CapabilitySpec(
                        id=cap_id,
                        name=f"MCP: {server_name}",
                        description=f"MCP server {server_name} tools",
                        category=CapabilityCategory.MCP_PLUGIN,
                        providers=[CapabilityProvider(
                            id=f"mcp:{server_name}",
                            name=server_name,
                            type="mcp",
                        )],
                        risk_level=RiskLevel.LOW,
                        tags=["mcp", server_name],
                    )
                    self.register_capability(spec)
                    count += 1
        except Exception as e:
            logger.debug(f"Could not discover MCP servers: {e}")
        
        # Discover from skills
        try:
            from tools.skills_hub import get_skills_hub
            skills_hub = get_skills_hub()
            for skill_name, skill_info in skills_hub.list_skills().items():
                cap_id = f"skill:{skill_name}"
                if cap_id not in self._capabilities:
                    spec = CapabilitySpec(
                        id=cap_id,
                        name=f"Skill: {skill_name}",
                        description=skill_info.get("description", ""),
                        category=CapabilityCategory.MCP_PLUGIN,
                        providers=[CapabilityProvider(
                            id=f"skill:{skill_name}",
                            name=skill_name,
                            type="skill",
                        )],
                        risk_level=RiskLevel.LOW,
                        tags=["skill", skill_name],
                    )
                    self.register_capability(spec)
                    count += 1
        except Exception as e:
            logger.debug(f"Could not discover skills: {e}")

        logger.info(f"Discovered and registered {count} new capabilities")
        return count

    def _infer_category(self, toolset: str) -> CapabilityCategory:
        """Infer capability category from toolset name."""
        mapping = {
            "computer_use": CapabilityCategory.COMPUTER_CONTROL,
            "browser": CapabilityCategory.WEB_BROWSER,
            "web": CapabilityCategory.WEB_BROWSER,
            "file": CapabilityCategory.FILE_SYSTEM,
            "terminal": CapabilityCategory.TERMINAL,
            "code_execution": CapabilityCategory.CODING,
            "delegation": CapabilityCategory.MULTI_AGENT,
            "swarm": CapabilityCategory.MULTI_AGENT,
            "memory": CapabilityCategory.MEMORY,
            "session_search": CapabilityCategory.KNOWLEDGE,
            "messaging": CapabilityCategory.COMMUNICATION,
            "automation": CapabilityCategory.AUTOMATION,
            "cronjob": CapabilityCategory.AUTOMATION,
            "vision": CapabilityCategory.MULTIMODAL,
            "image_gen": CapabilityCategory.CREATIVE,
            "video_gen": CapabilityCategory.CREATIVE,
            "tts": CapabilityCategory.VOICE,
            "transcription": CapabilityCategory.VOICE,
            "skills": CapabilityCategory.MCP_PLUGIN,
            "kanban": CapabilityCategory.MULTI_AGENT,
            "todo": CapabilityCategory.PERSONAL_ASSISTANT,
            "clarify": CapabilityCategory.PERSONAL_ASSISTANT,
            "homeassistant": CapabilityCategory.SYSTEM_INTEGRATION,
        }
        return mapping.get(toolset, CapabilityCategory.SYSTEM_INTEGRATION)

    def _infer_risk_level(self, toolset: str) -> RiskLevel:
        """Infer risk level from toolset."""
        high_risk = {"terminal", "computer_use", "messaging", "delegation", "swarm"}
        medium_risk = {"browser", "file", "automation", "cronjob", "code_execution", "homeassistant"}
        if toolset in high_risk:
            return RiskLevel.HIGH
        if toolset in medium_risk:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def register_verification_strategy(self, strategy: VerificationStrategy) -> None:
        """Register a verification strategy."""
        with self._lock:
            self._verification_strategies[strategy.name] = strategy
            logger.debug(f"Registered verification strategy: {strategy.name}")

    def register_recovery_strategy(self, strategy: RecoveryStrategy) -> None:
        """Register a recovery strategy."""
        with self._lock:
            self._recovery_strategies[strategy.name] = strategy
            logger.debug(f"Registered recovery strategy: {strategy.name}")

    def get_verification_strategy(self, name: str) -> Optional[VerificationStrategy]:
        """Get a verification strategy by name."""
        with self._lock:
            return self._verification_strategies.get(name)

    def get_recovery_strategy(self, name: str) -> Optional[RecoveryStrategy]:
        """Get a recovery strategy by name."""
        with self._lock:
            return self._recovery_strategies.get(name)

    def list_verification_strategies(self) -> List[VerificationStrategy]:
        """List all verification strategies."""
        with self._lock:
            return list(self._verification_strategies.values())

    def list_recovery_strategies(self) -> List[RecoveryStrategy]:
        """List all recovery strategies."""
        with self._lock:
            return list(self._recovery_strategies.values())

    def get_generation(self) -> int:
        """Get current registry generation for cache invalidation."""
        with self._lock:
            return self._generation

    def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Run health checks on all capabilities."""
        results = {}
        with self._lock:
            for cap_id, entry in self._capabilities.items():
                results[cap_id] = self._health_check_entry(entry)
        return results

    def _health_check_entry(self, entry: CapabilityEntry) -> Dict[str, Any]:
        """Run health check on a single capability entry."""
        spec = entry.spec
        checks = []
        
        # Check availability
        if spec.availability_check:
            try:
                check_fn = self._import_callable(spec.availability_check)
                if check_fn:
                    available = check_fn()
                    checks.append(("availability", available))
                    entry.spec.available = available
            except Exception as e:
                checks.append(("availability", False, str(e)))
        
        # Check tool availability
        for tool in spec.tools:
            if tool.check_fn:
                try:
                    check_fn = self._import_callable(tool.check_fn)
                    if check_fn:
                        available = check_fn()
                        checks.append((f"tool:{tool.name}", available))
                except Exception as e:
                    checks.append((f"tool:{tool.name}", False, str(e)))
        
        # Determine overall health
        all_passed = all(c[1] for c in checks) if checks else True
        entry._health_status = "healthy" if all_passed else "degraded"
        entry._last_health_check = time.time()
        
        return {
            "status": entry._health_status,
            "checks": [{"name": c[0], "passed": c[1], "error": c[2] if len(c) > 2 else None} for c in checks],
            "last_check": entry._last_health_check,
        }

    def _import_callable(self, dotted_path: str) -> Optional[Callable]:
        """Import a callable from a dotted path."""
        try:
            module_path, func_name = dotted_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, func_name)
        except Exception as e:
            logger.debug(f"Could not import {dotted_path}: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            return {
                "total_capabilities": len(self._capabilities),
                "by_category": {cat.value: len(ids) for cat, ids in self._category_index.items()},
                "by_tag": {tag: len(ids) for tag, ids in self._tag_index.items()},
                "total_tools": len(self._tool_to_capability),
                "total_models": len(self._model_to_capability),
                "total_providers": len(self._providers),
                "verification_strategies": len(self._verification_strategies),
                "recovery_strategies": len(self._recovery_strategies),
                "generation": self._generation,
            }


# Module-level instance
registry = CapabilityRegistry()


def get_capability_registry() -> CapabilityRegistry:
    """Get the global capability registry."""
    return registry
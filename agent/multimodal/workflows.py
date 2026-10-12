"""Multimodal Workflows, Tool Routing, and Agent Handoff (Phases 82-85 of Master Prompt 10).

Implements:
- Phase 82: Multimodal Workflows - Skills can accept multimodal inputs
- Phase 83: Multimodal Tool Routing - Select tools based on modality
- Phase 84: Multimodal Agent Handoff - Specialized agents (Vision, Audio, Document, Video, Research, Computer)
- Phase 85: Cross-Modal Agent Handoff - Preserve provenance across handoffs
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from agent.multimodal.media_abstraction import MediaObject, MediaType, SensitivityLevel
from agent.multimodal.perception import perceive, analyze_image, transcribe_audio, extract_document, analyze_video, understand_screen
from agent.multimodal.provenance import ProvenanceTracker, ConfidenceTracker, EvidenceRef, GroundedFact, EvidenceStatus
from agent.multimodal.memory import MultimodalMemoryStore, default_store

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Categories of multimodal tools."""
    VISION = "vision"
    OCR = "ocr"
    STT = "stt"
    TTS = "tts"
    DOCUMENT = "document"
    VIDEO = "video"
    SCREEN = "screen"
    CAMERA = "camera"
    MEMORY = "memory"
    SEARCH = "search"
    ANALYSIS = "analysis"


@dataclass
class ToolRoute:
    """A tool routing decision."""
    tool_name: str
    category: ToolCategory
    reason: str
    confidence: float
    modality: MediaType
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowStep:
    """A step in a multimodal workflow."""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    tool_route: Optional[ToolRoute] = None
    input_media: List[str] = field(default_factory=list)  # media_ids
    output_media: List[str] = field(default_factory=list)  # media_ids
    condition: Optional[str] = None  # Python expression for conditional execution
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultimodalWorkflow:
    """A workflow that processes multimodal inputs through a sequence of tools."""
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    input_media: List[str] = field(default_factory=list)  # Expected input media types
    output_media: List[str] = field(default_factory=list)  # Expected output media types
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultimodalToolRouter:
    """Routes multimodal inputs to appropriate tools (Phase 83)."""

    def __init__(self):
        self._tool_registry: Dict[str, Dict[str, Any]] = {}
        self._modality_to_tools: Dict[MediaType, List[str]] = {
            MediaType.IMAGE: ["vision_analyze", "image_ocr", "screen_understand"],
            MediaType.VIDEO: ["video_analyze", "extract_video_frames"],
            MediaType.AUDIO: ["transcribe_audio"],
            MediaType.DOCUMENT: ["document_extract", "image_ocr"],
            MediaType.SCREEN: ["screen_capture", "screen_understand", "image_ocr"],
            MediaType.CAMERA: ["vision_analyze"],
            MediaType.TEXT: ["memory_search", "web_search"],
            MediaType.STRUCTURED_DATA: ["memory_search"],
        }
        self._tool_capabilities: Dict[str, Dict[str, Any]] = {}

    def register_tool(
        self,
        name: str,
        category: ToolCategory,
        modalities: List[MediaType],
        description: str = "",
        handler: Optional[Callable] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a tool for routing."""
        self._tool_registry[name] = {
            "name": name,
            "category": category,
            "modalities": modalities,
            "description": description,
            "handler": handler,
            "parameters": parameters or {},
        }
        for modality in modalities:
            if modality not in self._modality_to_tools:
                self._modality_to_tools[modality] = []
            if name not in self._modality_to_tools[modality]:
                self._modality_to_tools[modality].append(name)

    def route(
        self,
        media: MediaObject,
        task: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ToolRoute]:
        """Determine which tools to use for the given media and task."""
        routes = []
        available_tools = self._modality_to_tools.get(media.type, [])

        for tool_name in available_tools:
            tool_info = self._tool_registry.get(tool_name, {})
            confidence = self._calculate_confidence(tool_name, media, task, context)
            if confidence > 0.3:
                routes.append(ToolRoute(
                    tool_name=tool_name,
                    category=tool_info.get("category", ToolCategory.ANALYSIS),
                    reason=f"Modality {media.type.value} matches tool capability",
                    confidence=confidence,
                    modality=media.type,
                    parameters=tool_info.get("parameters", {}),
                ))

        # Sort by confidence descending
        routes.sort(key=lambda r: r.confidence, reverse=True)
        return routes

    def _calculate_confidence(
        self,
        tool_name: str,
        media: MediaObject,
        task: str,
        context: Optional[Dict[str, Any]],
    ) -> float:
        """Calculate routing confidence."""
        confidence = 0.5  # Base confidence for modality match

        tool_info = self._tool_registry.get(tool_name, {})
        task_lower = task.lower()

        # Boost confidence based on task keywords
        if "describe" in task_lower or "analyze" in task_lower:
            if "vision" in tool_name or "analyze" in tool_name:
                confidence += 0.3
        if "transcribe" in task_lower or "speech" in task_lower:
            if "transcribe" in tool_name or "stt" in tool_name:
                confidence += 0.3
        if "ocr" in task_lower or "text" in task_lower or "read" in task_lower:
            if "ocr" in tool_name or "extract" in tool_name:
                confidence += 0.3
        if "document" in task_lower or "pdf" in task_lower:
            if "document" in tool_name:
                confidence += 0.3
        if "screen" in task_lower or "ui" in task_lower:
            if "screen" in tool_name:
                confidence += 0.3

        return min(confidence, 1.0)


class AgentRole(Enum):
    """Specialized agent roles for multimodal handoff (Phase 84)."""
    VISION = "vision"
    AUDIO = "audio"
    DOCUMENT = "document"
    VIDEO = "video"
    RESEARCH = "research"
    COMPUTER = "computer"
    COORDINATOR = "coordinator"


@dataclass
class AgentHandoff:
    """Represents a handoff between agents (Phase 84-85)."""
    handoff_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: AgentRole = AgentRole.COORDINATOR
    to_agent: AgentRole = AgentRole.VISION
    task: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    media_ids: List[str] = field(default_factory=list)
    provenance_refs: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=lambda: __import__('time').time())


class MultimodalAgentCoordinator:
    """Coordinates multimodal agent handoffs (Phases 84-85)."""

    def __init__(
        self,
        tool_router: Optional[MultimodalToolRouter] = None,
        memory: Optional[MultimodalMemoryStore] = None,
    ):
        self.tool_router = tool_router or MultimodalToolRouter()
        self.memory = memory or default_store()
        self._provenance = ProvenanceTracker()
        self._confidence = ConfidenceTracker()
        self._agents: Dict[AgentRole, Callable] = {}
        self._handoffs: Dict[str, AgentHandoff] = {}
        self._register_default_agents()

    def _register_default_agents(self) -> None:
        """Register default agent handlers."""
        self._agents = {
            AgentRole.VISION: self._vision_agent,
            AgentRole.AUDIO: self._audio_agent,
            AgentRole.DOCUMENT: self._document_agent,
            AgentRole.VIDEO: self._video_agent,
            AgentRole.RESEARCH: self._research_agent,
            AgentRole.COMPUTER: self._computer_agent,
            AgentRole.COORDINATOR: self._coordinator_agent,
        }

    def register_agent(self, role: AgentRole, handler: Callable) -> None:
        """Register a custom agent handler."""
        self._agents[role] = handler

    def handoff(
        self,
        from_agent: AgentRole,
        to_agent: AgentRole,
        task: str,
        media: List[MediaObject],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentHandoff:
        """Execute a handoff between agents with provenance tracking."""
        media_ids = [m.media_id for m in media]

        handoff = AgentHandoff(
            from_agent=from_agent,
            to_agent=to_agent,
            task=task,
            context=context or {},
            media_ids=media_ids,
        )
        self._handoffs[handoff.handoff_id] = handoff

        logger.info("Handoff %s: %s -> %s for task: %s", handoff.handoff_id, from_agent.value, to_agent.value, task)

        # Execute target agent
        handler = self._agents.get(to_agent)
        if not handler:
            handoff.status = "failed"
            handoff.result = {"error": f"No handler for agent role: {to_agent.value}"}
            return handoff

        try:
            handoff.status = "in_progress"
            result = handler(task, media, context or {})
            handoff.status = "completed"
            handoff.result = result

            # Record provenance
            for media_obj in media:
                self._provenance.record(
                    claim=f"Handoff from {from_agent.value} to {to_agent.value}: {task}",
                    media=media_obj,
                    processor=f"agent:{to_agent.value}",
                    confidence=0.8,
                )

            self._emit_handoff_event(handoff)
        except Exception as e:
            logger.error("Handoff %s failed: %s", handoff.handoff_id, e)
            handoff.status = "failed"
            handoff.result = {"error": str(e)}

        return handoff

    def _emit_handoff_event(self, handoff: AgentHandoff) -> None:
        """Emit handoff event for monitoring."""
        logger.debug("Handoff event: %s", handoff.handoff_id)

    # --- Default agent implementations ---

    def _vision_agent(self, task: str, media: List[MediaObject], context: Dict[str, Any]) -> Dict[str, Any]:
        """Vision agent: image understanding, object detection, scene analysis."""
        results = []
        for m in media:
            if m.type in (MediaType.IMAGE, MediaType.SCREEN, MediaType.CAMERA):
                result = analyze_image(m, task)
                results.append({"media_id": m.media_id, "result": result})
            elif m.type == MediaType.VIDEO:
                result = analyze_video(m, task)
                results.append({"media_id": m.media_id, "result": result})
        return {"agent": "vision", "results": results}

    def _audio_agent(self, task: str, media: List[MediaObject], context: Dict[str, Any]) -> Dict[str, Any]:
        """Audio agent: transcription, speaker diarization, audio analysis."""
        results = []
        for m in media:
            if m.type == MediaType.AUDIO:
                result = transcribe_audio(m)
                results.append({"media_id": m.media_id, "result": result})
        return {"agent": "audio", "results": results}

    def _document_agent(self, task: str, media: List[MediaObject], context: Dict[str, Any]) -> Dict[str, Any]:
        """Document agent: extraction, OCR, layout analysis."""
        results = []
        for m in media:
            if m.type == MediaType.DOCUMENT:
                result = extract_document(m)
                results.append({"media_id": m.media_id, "result": result})
            elif m.type in (MediaType.IMAGE, MediaType.SCREEN):
                result = ocr_media(m)
                results.append({"media_id": m.media_id, "result": result})
        return {"agent": "document", "results": results}

    def _video_agent(self, task: str, media: List[MediaObject], context: Dict[str, Any]) -> Dict[str, Any]:
        """Video agent: frame extraction, temporal analysis, action recognition."""
        results = []
        for m in media:
            if m.type == MediaType.VIDEO:
                frames_result = extract_video_frames(m)
                analysis_result = analyze_video(m, task)
                results.append({
                    "media_id": m.media_id,
                    "frames": frames_result,
                    "analysis": analysis_result,
                })
        return {"agent": "video", "results": results}

    def _research_agent(self, task: str, media: List[MediaObject], context: Dict[str, Any]) -> Dict[str, Any]:
        """Research agent: cross-modal synthesis, fact extraction, citation."""
        # This would integrate with MASTER 4 research architecture
        findings = []
        for m in media:
            if m.type == MediaType.DOCUMENT:
                result = extract_document(m)
                if result.get("success"):
                    findings.append({"source": m.media_id, "type": "document", "content": result.get("text", "")})
            elif m.type == MediaType.IMAGE:
                result = analyze_image(m, f"Research task: {task}")
                if result.get("success"):
                    findings.append({"source": m.media_id, "type": "image", "content": result.get("analysis", "")})
        return {"agent": "research", "findings": findings, "task": task}

    def _computer_agent(self, task: str, media: List[MediaObject], context: Dict[str, Any]) -> Dict[str, Any]:
        """Computer agent: screen understanding, UI automation, code analysis."""
        results = []
        for m in media:
            if m.type == MediaType.SCREEN:
                result = understand_screen(m, task)
                results.append({"media_id": m.media_id, "result": result})
        return {"agent": "computer", "results": results}

    def _coordinator_agent(self, task: str, media: List[MediaObject], context: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinator agent: routes to appropriate specialists."""
        # Analyze task and media to determine routing
        routes = []
        for m in media:
            tool_routes = self.tool_router.route(m, task, context)
            routes.extend(tool_routes)

        # Deduplicate and execute top routes
        seen = set()
        unique_routes = []
        for r in routes:
            if r.tool_name not in seen:
                seen.add(r.tool_name)
                unique_routes.append(r)

        return {"agent": "coordinator", "routes": [r.tool_name for r in unique_routes[:5]], "task": task}


class CrossModalHandoffManager:
    """Manages cross-modal agent handoffs with provenance preservation (Phase 85)."""

    def __init__(self, coordinator: Optional[MultimodalAgentCoordinator] = None):
        self.coordinator = coordinator or MultimodalAgentCoordinator()
        self._pipeline: List[AgentHandoff] = []

    def create_pipeline(
        self,
        steps: List[Dict[str, Any]],
        initial_media: List[MediaObject],
        initial_task: str,
    ) -> List[AgentHandoff]:
        """Create a multi-agent pipeline (e.g., Vision -> Research -> Data -> Writer)."""
        handoffs = []
        current_media = initial_media
        current_task = initial_task
        context = {}

        for i, step in enumerate(steps):
            from_agent = step.get("from", AgentRole.COORDINATOR)
            to_agent = step.get("to", AgentRole.VISION)
            task = step.get("task", current_task)

            handoff = self.coordinator.handoff(
                from_agent=from_agent,
                to_agent=to_agent,
                task=task,
                media=current_media,
                context=context,
            )
            handoffs.append(handoff)

            # Update context with results for next agent
            if handoff.result:
                context[f"step_{i}_{to_agent.value}"] = handoff.result
                # Extract new media from results
                current_media = self._extract_media_from_result(handoff.result)
                current_task = f"Continue from {to_agent.value}: {task}"

        self._pipeline.extend(handoffs)
        return handoffs

    def _extract_media_from_result(self, result: Dict[str, Any]) -> List[MediaObject]:
        """Extract media references from agent result."""
        # This would create new MediaObjects from agent outputs
        # For now, return empty - would be implemented with actual media generation
        return []

    def get_pipeline_status(self) -> List[Dict[str, Any]]:
        """Get status of all handoffs in the pipeline."""
        return [
            {
                "handoff_id": h.handoff_id,
                "from": h.from_agent.value,
                "to": h.to_agent.value,
                "task": h.task,
                "status": h.status,
                "created_at": h.created_at,
            }
            for h in self._pipeline
        ]


# --- Workflow execution ---

@dataclass
class WorkflowExecution:
    """Tracks execution of a multimodal workflow."""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow: Optional[MultimodalWorkflow] = None
    input_media: List[MediaObject] = field(default_factory=list)
    step_results: Dict[str, Any] = field(default_factory=dict)
    current_step: int = 0
    status: str = "pending"  # pending, running, completed, failed
    created_at: float = field(default_factory=lambda: __import__('time').time())
    completed_at: Optional[float] = None


class MultimodalWorkflowEngine:
    """Executes multimodal workflows (Phase 82)."""

    def __init__(
        self,
        tool_router: Optional[MultimodalToolRouter] = None,
        coordinator: Optional[MultimodalAgentCoordinator] = None,
    ):
        self.tool_router = tool_router or MultimodalToolRouter()
        self.coordinator = coordinator or MultimodalAgentCoordinator(tool_router)
        self._executions: Dict[str, WorkflowExecution] = {}

    def create_workflow(
        self,
        name: str,
        steps: List[Dict[str, Any]],
        description: str = "",
    ) -> MultimodalWorkflow:
        """Create a workflow from step definitions."""
        workflow = MultimodalWorkflow(name=name, description=description)
        for i, step_def in enumerate(steps):
            step = WorkflowStep(
                name=step_def.get("name", f"step_{i}"),
                condition=step_def.get("condition"),
                metadata=step_def.get("metadata", {}),
            )
            if "tool" in step_def:
                step.tool_route = ToolRoute(
                    tool_name=step_def["tool"],
                    category=ToolCategory(step_def.get("category", "analysis")),
                    reason=step_def.get("reason", ""),
                    confidence=1.0,
                    modality=MediaType(step_def.get("modality", "image")),
                )
            workflow.steps.append(step)
        return workflow

    def execute(
        self,
        workflow: MultimodalWorkflow,
        input_media: List[MediaObject],
    ) -> WorkflowExecution:
        """Execute a workflow with the given input media."""
        execution = WorkflowExecution(
            workflow=workflow,
            input_media=input_media,
            status="running",
        )
        self._executions[execution.execution_id] = execution

        try:
            current_media = input_media
            for i, step in enumerate(workflow.steps):
                execution.current_step = i

                # Check condition
                if step.condition:
                    if not self._evaluate_condition(step.condition, execution):
                        logger.info("Step %s skipped due to condition", step.name)
                        continue

                # Execute step
                if step.tool_route:
                    result = self._execute_tool_step(step.tool_route, current_media)
                else:
                    # Use coordinator for agent handoff
                    result = self.coordinator._coordinator_agent(
                        step.name, current_media, execution.step_results
                    )

                execution.step_results[step.step_id] = result

                # Extract output media for next step
                current_media = self._extract_media_from_result(result)

            execution.status = "completed"
            execution.completed_at = __import__('time').time()

        except Exception as e:
            logger.error("Workflow execution failed: %s", e)
            execution.status = "failed"
            execution.step_results["error"] = str(e)

        return execution

    def _evaluate_condition(self, condition: str, execution: WorkflowExecution) -> bool:
        """Evaluate a workflow step condition."""
        # Simple eval with limited scope - in production use a safe evaluator
        try:
            return bool(eval(condition, {"results": execution.step_results}))
        except Exception:
            return True

    def _execute_tool_step(self, route: ToolRoute, media: List[MediaObject]) -> Dict[str, Any]:
        """Execute a tool route."""
        # This would call the actual tool handler
        # For now, use perceive as a general processor
        results = []
        for m in media:
            result = perceive(m)
            results.append({"media_id": m.media_id, "result": result})
        return {"tool": route.tool_name, "results": results}

    def _extract_media_from_result(self, result: Dict[str, Any]) -> List[MediaObject]:
        """Extract media objects from tool/agent result."""
        # Placeholder - would create new MediaObjects from outputs
        return []

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        return self._executions.get(execution_id)

    def list_executions(self) -> List[WorkflowExecution]:
        return list(self._executions.values())


# --- Convenience functions ---

def route_tool(media: MediaObject, task: str = "") -> List[ToolRoute]:
    """Route media to appropriate tools."""
    router = MultimodalToolRouter()
    return router.route(media, task)


def create_workflow(name: str, steps: List[Dict[str, Any]]) -> MultimodalWorkflow:
    """Create a multimodal workflow."""
    engine = MultimodalWorkflowEngine()
    return engine.create_workflow(name, steps)


def execute_workflow(workflow: MultimodalWorkflow, input_media: List[MediaObject]) -> WorkflowExecution:
    """Execute a multimodal workflow."""
    engine = MultimodalWorkflowEngine()
    return engine.execute(workflow, input_media)


def handoff_agents(
    from_agent: AgentRole,
    to_agent: AgentRole,
    task: str,
    media: List[MediaObject],
) -> AgentHandoff:
    """Execute a single agent handoff."""
    coordinator = MultimodalAgentCoordinator()
    return coordinator.handoff(from_agent, to_agent, task, media)


def create_cross_modal_pipeline(
    steps: List[Dict[str, Any]],
    initial_media: List[MediaObject],
    initial_task: str,
) -> List[AgentHandoff]:
    """Create a cross-modal agent pipeline."""
    manager = CrossModalHandoffManager()
    return manager.create_pipeline(steps, initial_media, initial_task)


# --- Example workflows ---

EXAMPLE_WORKFLOWS = {
    "document_analysis": {
        "name": "Document Analysis",
        "description": "Extract text, tables, and charts from a document",
        "steps": [
            {"name": "extract_document", "tool": "document_extract", "modality": "document"},
            {"name": "ocr_pages", "tool": "image_ocr", "modality": "image"},
            {"name": "analyze_charts", "tool": "vision_analyze", "modality": "image", "condition": "results.get('step_0', {}).get('has_charts')"},
        ],
    },
    "video_understanding": {
        "name": "Video Understanding",
        "description": "Extract frames, transcribe audio, analyze content",
        "steps": [
            {"name": "extract_frames", "tool": "extract_video_frames", "modality": "video"},
            {"name": "transcribe_audio", "tool": "transcribe_audio", "modality": "video"},
            {"name": "analyze_content", "tool": "video_analyze", "modality": "video"},
        ],
    },
    "screen_debugging": {
        "name": "Screen Debugging",
        "description": "Capture screen, understand UI, find errors",
        "steps": [
            {"name": "capture_screen", "tool": "screen_capture", "modality": "screen"},
            {"name": "understand_ui", "tool": "screen_understand", "modality": "screen"},
            {"name": "analyze_errors", "tool": "vision_analyze", "modality": "screen"},
        ],
    },
    "research_pipeline": {
        "name": "Visual Research Pipeline",
        "description": "Vision -> Research -> Data extraction -> Report",
        "steps": [
            {"from": "coordinator", "to": "vision", "task": "Analyze all visual sources"},
            {"from": "vision", "to": "research", "task": "Synthesize findings and find supporting sources"},
            {"from": "research", "to": "data", "task": "Extract exact numbers and data points"},
            {"from": "data", "to": "writer", "task": "Generate structured report with citations"},
        ],
    },
}
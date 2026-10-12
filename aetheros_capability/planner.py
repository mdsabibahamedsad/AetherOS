#!/usr/bin/env python3
"""
Planning & Parameterization Layer — Intent to Tool Parameters

This module bridges the gap between user intent and tool execution by:
1. Taking a user intent and selected capability/tool
2. Using an LLM to generate appropriate tool parameters from the tool schema
3. Handling multi-step planning for complex tasks
4. Managing parameter validation and refinement
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from .models import (
    CapabilitySpec,
    Task,
    TaskRequest,
    TaskStep,
    ToolReference,
    RoutingDecision,
)

logger = logging.getLogger(__name__)

# Try to import LLM client
try:
    from model_tools import handle_function_call
    from agent.auxiliary_client import get_auxiliary_client
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logger.warning("LLM client not available for planning")


@dataclass
class ParameterizationResult:
    """Result of parameterizing a tool call."""
    tool_name: str
    parameters: Dict[str, Any]
    confidence: float
    reasoning: str
    missing_required: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class PlanStep:
    """A single step in a plan."""
    id: str
    name: str
    description: str
    capability_id: str
    tool_name: str
    input_template: Dict[str, Any]  # Template with placeholders
    dependencies: List[str] = field(default_factory=list)
    expected_output: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    """A multi-step execution plan."""
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class Parameterizer:
    """
    Converts user intent + tool schema into tool parameters using LLM.
    """
    
    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        self._parameterization_cache: Dict[str, ParameterizationResult] = {}
        self._cache_ttl_seconds = 300
    
    def parameterize(self, 
                    intent: str, 
                    tool: ToolReference, 
                    context: Dict[str, Any] | None = None,
                    previous_results: Dict[str, Any] | None = None) -> ParameterizationResult:
        """
        Generate tool parameters from intent using tool schema.
        """
        context = context or {}
        previous_results = previous_results or {}
        
        # Check cache
        # Convert enums to strings for JSON serialization
        serializable_context = {}
        for k, v in context.items():
            if hasattr(v, 'value'):  # Enum
                serializable_context[k] = v.value
            else:
                serializable_context[k] = v
        
        cache_key = f"{intent}|{tool.name}|{json.dumps(serializable_context, sort_keys=True)}"
        if cache_key in self._parameterization_cache:
            return self._parameterization_cache[cache_key]
        
        # Build prompt for LLM
        prompt = self._build_parameterization_prompt(intent, tool, context, previous_results)
        
        # Call LLM
        if LLM_AVAILABLE:
            try:
                result = self._call_llm_for_parameters(prompt, tool)
            except Exception as e:
                logger.warning(f"LLM parameterization failed: {e}")
                result = self._fallback_parameterization(intent, tool, context)
        else:
            result = self._fallback_parameterization(intent, tool, context)
        
        # Cache result
        self._parameterization_cache[cache_key] = result
        return result
    
    def _build_parameterization_prompt(self, intent: str, tool: ToolReference, 
                                      context: Dict[str, Any], 
                                      previous_results: Dict[str, Any]) -> str:
        """Build the prompt for LLM parameterization."""
        schema = tool.schema
        properties = schema.get("parameters", {}).get("properties", {})
        required = schema.get("parameters", {}).get("required", [])
        
        # Format schema for prompt
        param_desc = []
        for param_name, param_info in properties.items():
            param_type = param_info.get("type", "any")
            param_desc_text = param_info.get("description", "")
            is_required = param_name in required
            param_desc.append(f"  - {param_name} ({param_type}){' [REQUIRED]' if is_required else ''}: {param_desc_text}")
        
        param_text = "\n".join(param_desc) if param_desc else "  (no parameters)"
        
        context_text = ""
        if context:
            # Convert enums to strings for JSON serialization
            serializable_context = {}
            for k, v in context.items():
                if hasattr(v, 'value'):  # Enum
                    serializable_context[k] = v.value
                else:
                    serializable_context[k] = v
            context_text = f"\nContext: {json.dumps(serializable_context, indent=2)}"
        
        prev_text = ""
        if previous_results:
            prev_text = f"\nPrevious step results: {json.dumps(previous_results, indent=2)}"
        
        tool_description = getattr(tool, 'description', '') or tool.schema.get('description', '')
        prompt = f"""You are an expert at converting user intent into precise tool parameters.

User Intent: {intent}

Tool: {tool.name}
Description: {tool_description}
Parameters:
{param_text}

{context_text}
{prev_text}

Generate the JSON parameters for this tool call. Only output valid JSON matching the schema.
For required parameters not inferable from intent, use reasonable defaults or mark as missing.
"""
        return prompt
    
    def _call_llm_for_parameters(self, prompt: str, tool: ToolReference) -> ParameterizationResult:
        """Call LLM to generate parameters."""
        # Use the auxiliary client for parameterization
        try:
            client = get_auxiliary_client()
            response = client.complete(
                prompt=prompt,
                model="parameterizer",
                temperature=0.1,
                max_tokens=1000,
            )
            text = response.text if hasattr(response, 'text') else str(response)
        except Exception:
            # Fallback to direct model call
            from model_tools import _run_async
            from openai import OpenAI
            client = OpenAI()
            response = _run_async(client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000,
            ))
            text = response.choices[0].message.content
        
        # Parse JSON from response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                params = json.loads(json_match.group())
            else:
                params = json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM parameters: {text[:200]}")
            return self._fallback_parameterization("", None, {})
        
        # Validate against schema
        missing_required = []
        properties = tool.schema.get("parameters", {}).get("properties", {})
        required = tool.schema.get("parameters", {}).get("required", [])
        
        for req in required:
            if req not in params:
                missing_required.append(req)
        
        return ParameterizationResult(
            tool_name=tool.name,
            parameters=params,
            confidence=0.8 if not missing_required else 0.5,
            reasoning="Generated by LLM from intent and tool schema",
            missing_required=missing_required,
        )
    
    def _fallback_parameterization(self, intent: str, tool: ToolReference, 
                                  context: Dict[str, Any]) -> ParameterizationResult:
        """Fallback parameterization using simple heuristics."""
        params = {}
        properties = tool.schema.get("parameters", {}).get("properties", {})
        required = tool.schema.get("parameters", {}).get("required", [])
        
        # Simple heuristic mapping for common tools
        intent_lower = intent.lower()
        
        # Web search
        if tool.name == "web_search":
            # Extract search query from intent
            query = intent
            # Try to extract a cleaner query
            queries = re.findall(r'search (?:for |)["\']([^"\']+)["\']', intent)
            if not queries:
                queries = re.findall(r'(?:search|find|look up) (?:for |)(.+)', intent)
            if queries:
                params["query"] = queries[0]
            else:
                params["query"] = intent[:200]
        
        # Terminal
        elif tool.name == "terminal":
            cmd_match = re.search(r'(?:run|execute|command) ["\']([^"\']+)["\']', intent)
            if cmd_match:
                params["command"] = cmd_match.group(1)
            else:
                params["command"] = intent[:200]
        
        # File operations
        elif tool.name in ("read_file", "write_file", "patch"):
            path_match = re.search(r'(?:file|path) ["\']([^"\']+)["\']', intent)
            if path_match:
                params["path"] = path_match.group(1)
        
        # Browser
        elif tool.name == "browser_navigate":
            url_match = re.search(r'(?:open|go to|navigate to) ["\']([^"\']+)["\']', intent)
            if url_match:
                params["url"] = url_match.group(1)
            else:
                # Try to extract URL from intent
                urls = re.findall(r'https?://[^\s]+', intent)
                if urls:
                    params["url"] = urls[0]
        
        # For other tools, try to extract key-value pairs from intent
        for param_name, param_info in properties.items():
            if param_name in required and param_name not in params:
                # Try to find value in context or intent
                if param_name in context:
                    params[param_name] = context[param_name]
                elif param_name.replace("_", " ") in intent_lower:
                    # Very rough extraction
                    pass
        
        missing_required = [r for r in required if r not in params]
        
        return ParameterizationResult(
            tool_name=tool.name,
            parameters=params,
            confidence=0.3,
            reasoning="Fallback heuristic parameterization",
            missing_required=missing_required,
            warnings=["Used fallback parameterization - results may be inaccurate"],
        )


class Planner:
    """
    Creates multi-step plans for complex goals.
    """
    
    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        self._router = None
        self._parameterizer = Parameterizer(config)
    
    @property
    def router(self):
        if self._router is None:
            from .capability_router import get_capability_router
            self._router = get_capability_router()
        return self._router
    
    def create_plan(self, request: "AssistantRequest") -> Plan:
        """
        Create an execution plan from a task request.
        """
        goal = request.user_input
        
        # Route to primary capability
        routing = self.router.route(goal, request.context)
        
        # For simple goals, create single-step plan
        if self._is_simple_goal(goal):
            return self._create_simple_plan(goal, routing, request)
        
        # For complex goals, use LLM to decompose
        if LLM_AVAILABLE:
            return self._create_llm_plan(goal, routing, request)
        
        # Fallback: create simple plan
        return self._create_simple_plan(goal, routing, request)
    
    def _is_simple_goal(self, goal: str) -> bool:
        """Heuristic to determine if goal is simple (single tool)."""
        simple_indicators = [
            "search", "find", "look up", "open", "run", "execute",
            "read", "write", "create", "delete", "list", "show"
        ]
        goal_lower = goal.lower()
        return any(ind in goal_lower for ind in simple_indicators) and len(goal.split()) < 20
    
    def _create_simple_plan(self, goal: str, routing: RoutingDecision, 
                           request: "AssistantRequest") -> Plan:
        """Create a single-step plan."""
        from .models import PlanStep
        import uuid
        
        step = PlanStep(
            id=str(uuid.uuid4()),
            name="Execute capability",
            description=f"Execute {routing.capability_id}",
            capability_id=routing.capability_id,
            tool_name=routing.tool_name or "",
            input_template=self._create_input_template(goal, routing, request),
            expected_output={},
        )
        
        return Plan(
            goal=goal,
            steps=[step],
            metadata={"routing": routing.__dict__},
        )
    
    def _create_llm_plan(self, goal: str, routing: RoutingDecision,
                        request: "AssistantRequest") -> Plan:
        """Use LLM to create a multi-step plan."""
        # Build prompt for plan decomposition
        prompt = f"""Decompose this goal into executable steps using available capabilities.

Goal: {goal}
Primary capability: {routing.capability_id}
Available tools: {[t.name for t in get_capability_registry().get_capability(routing.capability_id).spec.tools]}

Create a JSON plan with steps. Each step should have:
- id: unique identifier
- name: short name
- description: what this step does
- capability_id: which capability to use
- tool_name: specific tool to use
- input_template: JSON with parameters (use {{placeholder}} for values from previous steps)
- dependencies: list of step IDs this depends on
- expected_output: expected output format

Output ONLY valid JSON array of steps.
"""
        try:
            client = get_auxiliary_client()
            response = client.complete(
                prompt=prompt,
                model="planner",
                temperature=0.2,
                max_tokens=2000,
            )
            text = response.text if hasattr(response, 'text') else str(response)
            
            # Parse plan
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                steps_data = json.loads(json_match.group())
            else:
                steps_data = json.loads(text)
            
            steps = []
            for step_data in steps_data:
                step = PlanStep(
                    id=step_data.get("id", str(uuid.uuid4())),
                    name=step_data.get("name", "Step"),
                    description=step_data.get("description", ""),
                    capability_id=step_data.get("capability_id", ""),
                    tool_name=step_data.get("tool_name", ""),
                    input_template=step_data.get("input_template", {}),
                    dependencies=step_data.get("dependencies", []),
                    expected_output=step_data.get("expected_output", {}),
                )
                steps.append(step)
            
            return Plan(goal=goal, steps=steps, metadata={"generated_by": "llm"})
        except Exception as e:
            logger.warning(f"LLM planning failed: {e}")
            return self._create_simple_plan(goal, routing, request)
    
    def _create_input_template(self, goal: str, routing: RoutingDecision, 
                               request: "AssistantRequest") -> Dict[str, Any]:
        """Create input template for a step."""
        # For now, just pass the goal and context
        return {
            "intent": goal,
            "context": request.context,
        }


# Module-level instances
_parameterizer_instance: Optional[Parameterizer] = None
_planner_instance: Optional[Planner] = None


def get_parameterizer(config: Dict[str, Any] | None = None) -> Parameterizer:
    global _parameterizer_instance
    if _parameterizer_instance is None:
        _parameterizer_instance = Parameterizer(config)
    return _parameterizer_instance


def get_planner(config: Dict[str, Any] | None = None) -> Planner:
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = Planner(config)
    return _planner_instance
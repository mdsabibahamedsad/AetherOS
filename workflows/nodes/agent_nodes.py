"""Agent nodes — integrate multi-agents for autonomous execution and delegation."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from workflows.nodes.base import BaseNode, NodeRegistry, NodeResult
from workflows.models import WorkflowNode, WorkflowConfig

logger = logging.getLogger(__name__)


class DelegateTaskNode(BaseNode):
    type = "agent.delegate"
    category = "agent"
    label = "Delegate Task"
    description = "Delegate a task to another agent"
    default_config = {"agent_name": "", "goal": "", "toolsets": []}
    outputs = [{"id": "output", "label": "Result", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        agent_name = node.config.get("agent_name", "")
        if not agent_name and engine and hasattr(engine, "get_agent_by_role"):
            agent_name = engine.get_agent_by_role(workflow.owner)
        if agent_name:
            try:
                from agents.runtime import AgentRuntime
                rt = AgentRuntime()
                result = await rt.run_agent(agent_name, node.config.get("goal", str(context.get("input", ""))))
                return NodeResult(success=result.get("success", True), output=result)
            except Exception as e:
                return NodeResult(success=False, output={"error": str(e)}, error=str(e))
        else:
            try:
                from tools.delegate_tool import delegate_task
                result = delegate_task(goal=node.config.get("goal", str(context.get("input", ""))),
                                       toolsets=node.config.get("toolsets", []))
                return NodeResult(success=True, output=str(result))
            except Exception as e:
                return NodeResult(success=False, output={"error": str(e)}, error=str(e))


class RunAgentNode(BaseNode):
    type = "agent.run"
    category = "agent"
    label = "Run Agent"
    description = "Run a registered multi-agent"
    default_config = {"agent_id": "", "prompt": ""}
    outputs = [{"id": "output", "label": "Response", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        agent_id = node.config.get("agent_id", "")
        prompt = node.config.get("prompt", "") or str(context.get("input", ""))
        try:
            from agents.runtime import AgentRuntime
            rt = AgentRuntime()
            if agent_id:
                result = await rt.run_agent(agent_id, prompt)
                return NodeResult(success=result.get("success", True), output=result)
            return NodeResult(success=False, output={"error": "No agent_id"})
        except Exception as e:
            return NodeResult(success=False, output={"error": str(e)}, error=str(e))


class AgentPipelineNode(BaseNode):
    type = "agent.pipeline"
    category = "agent"
    label = "Agent Pipeline"
    description = "Chain multiple agents in a sequence pipeline"
    default_config = {"agents": [], "mode": "sequential"}
    outputs = [{"id": "output", "label": "Results", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        agents = node.config.get("agents", [])
        mode = node.config.get("mode", "sequential")
        results = []
        try:
            from agents.runtime import AgentRuntime
            rt = AgentRuntime()
            input_data = context.get("input", "")
            for agent_ref in agents:
                if isinstance(agent_ref, dict):
                    name = agent_ref.get("name", "")
                    prompt = agent_ref.get("prompt", "").replace("{input}", str(input_data))
                    result = await rt.run_agent(name, prompt)
                    results.append({name: result})
                    input_data = result.get("output", result)
                else:
                    prompt = f"Process: {input_data}"
                    result = await rt.run_agent(str(agent_ref), prompt)
                    results.append({str(agent_ref): result})
                    input_data = result.get("output", result)
            return NodeResult(success=True, output=results,
                              logs=[{"message": f"Pipeline: {len(results)} agents"}])
        except Exception as e:
            return NodeResult(success=False, output={"error": str(e)}, error=str(e))


class AgentReviewNode(BaseNode):
    type = "agent.review"
    category = "agent"
    label = "Agent Review"
    description = "Request a review from another agent"
    default_config = {"reviewer_id": "", "criteria": "quality"}
    outputs = [{"id": "output", "label": "Review", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        reviewer = node.config.get("reviewer_id", "")
        criteria = node.config.get("criteria", "quality")
        work = context.get("input", "")
        try:
            from agents.collaboration import CollaborationEngine
            ce = CollaborationEngine()
            review = await ce.request_review(reviewer, work, criteria)
            return NodeResult(success=True, output=review,
                              logs=[{"message": f"Review requested from {reviewer}"}])
        except Exception as e:
            from run_agent import AIAgent
            agent = AIAgent(max_iterations=3, quiet_mode=True)
            result = agent.run_conversation(
                f"Review the following work for {criteria}. Be constructive:\n\n{work}")
            return NodeResult(success=True,
                              output=result.get("final_response", "Review unavailable"),
                              logs=[{"message": "Fallback review via AIAgent"}])


def register():
    NodeRegistry.register(DelegateTaskNode)
    NodeRegistry.register(RunAgentNode)
    NodeRegistry.register(AgentPipelineNode)
    NodeRegistry.register(AgentReviewNode)


register()

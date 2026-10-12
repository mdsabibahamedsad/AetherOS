"""AI nodes — execute LLM operations through the AetherOS agent runtime."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from workflows.nodes.base import BaseNode, NodeRegistry, NodeResult
from workflows.models import WorkflowNode, WorkflowConfig

logger = logging.getLogger(__name__)


async def _run_llm(prompt: str, system: str = "", model: str = "",
                   provider: str = "", temperature: float = 0.7) -> dict:
    """Execute an LLM call via Hermes AIAgent."""
    try:
        from run_agent import AIAgent
        agent = AIAgent(
            model=model or "",
            provider=provider or "",
            temperature=temperature,
            max_iterations=5,
            quiet_mode=True,
        )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        result = agent.run_conversation(prompt, conversation_history=messages or None)
        return {
            "response": result.get("final_response", ""),
            "tokens": result.get("tokens_used", 0),
            "messages": result.get("messages", []),
        }
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return {"response": "", "tokens": 0, "error": str(e)}


class ChatNode(BaseNode):
    type = "ai.chat"
    category = "ai"
    label = "Chat"
    description = "Freeform conversation with an AI model"
    default_config = {"system_prompt": "", "model": "", "temperature": 0.7}
    outputs = [{"id": "output", "label": "Response", "type": "string"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        prompt = node.config.get("prompt", "")
        if not prompt:
            prompt = str(context.get("input", ""))
        system = node.config.get("system_prompt", "")
        result = await _run_llm(prompt, system,
                                node.config.get("model", ""),
                                temperature=node.config.get("temperature", 0.7))
        return NodeResult(success=not result.get("error"), output=result.get("response", ""),
                          logs=[{"message": f"Chat: {len(result.get('response', ''))} chars"}])


class ReasoningNode(BaseNode):
    type = "ai.reasoning"
    category = "ai"
    label = "Reasoning"
    description = "Deep reasoning and analysis"
    default_config = {"model": "", "temperature": 0.5}
    outputs = [{"id": "output", "label": "Analysis", "type": "string"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        prompt = context.get("input", "")
        if not isinstance(prompt, str):
            prompt = json.dumps(prompt)
        result = await _run_llm(
            f"Analyze the following carefully. Think step by step.\n\n{prompt}",
            model=node.config.get("model", ""),
            temperature=node.config.get("temperature", 0.5),
        )
        return NodeResult(success=not result.get("error"), output=result.get("response", ""))


class SummarizeNode(BaseNode):
    type = "ai.summarize"
    category = "ai"
    label = "Summarize"
    description = "Summarize input text"
    default_config = {"max_length": 500, "model": ""}
    outputs = [{"id": "output", "label": "Summary", "type": "string"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        text = context.get("input", "")
        max_len = node.config.get("max_length", 500)
        result = await _run_llm(
            f"Summarize the following text in {max_len} words or fewer:\n\n{text}",
            system="You are a precise summarizer. Capture key points concisely.",
        )
        return NodeResult(success=not result.get("error"), output=result.get("response", ""))


class TranslateNode(BaseNode):
    type = "ai.translate"
    category = "ai"
    label = "Translate"
    description = "Translate text between languages"
    default_config = {"target_language": "Spanish", "source_language": ""}
    outputs = [{"id": "output", "label": "Translation", "type": "string"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        text = context.get("input", "")
        target = node.config.get("target_language", "Spanish")
        source = node.config.get("source_language", "")
        src_prefix = f" from {source}" if source else ""
        result = await _run_llm(
            f"Translate the following text{src_prefix} to {target}. Return only the translation:\n\n{text}",
        )
        return NodeResult(success=not result.get("error"), output=result.get("response", ""))


class CodeGenerationNode(BaseNode):
    type = "ai.code_generation"
    category = "ai"
    label = "Generate Code"
    description = "Generate code from a description"
    default_config = {"language": "python", "framework": ""}
    outputs = [{"id": "output", "label": "Code", "type": "string"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        desc = context.get("input", "")
        lang = node.config.get("language", "python")
        framework = node.config.get("framework", "")
        fw_hint = f" using {framework}" if framework else ""
        result = await _run_llm(
            f"Write {lang} code{fw_hint} for the following. Return only the code:\n\n{desc}",
            system="You are a code generation expert. Produce clean, working code.",
        )
        return NodeResult(success=not result.get("error"), output=result.get("response", ""))


class CodeReviewNode(BaseNode):
    type = "ai.review_code"
    category = "ai"
    label = "Review Code"
    description = "Review code for bugs, security, and best practices"
    default_config = {"language": ""}
    outputs = [{"id": "output", "label": "Review", "type": "string"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        code = context.get("input", "")
        result = await _run_llm(
            f"Review the following code for bugs, security vulnerabilities, "
            f"performance issues, and adherence to best practices:\n\n{code}",
            system="You are a senior code reviewer. Be thorough but constructive.",
        )
        return NodeResult(success=not result.get("error"), output=result.get("response", ""))


class ResearchNode(BaseNode):
    type = "ai.research"
    category = "ai"
    label = "Research"
    description = "Research a topic using web search and synthesis"
    default_config = {"depth": "balanced"}
    outputs = [{"id": "output", "label": "Research", "type": "string"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        topic = context.get("input", "")
        result = await _run_llm(
            f"Research the following topic thoroughly. Use web search, synthesize findings, "
            f"and produce a well-structured report with citations:\n\n{topic}",
            system="You are a research assistant. Find accurate information and cite sources.",
            temperature=0.3,
        )
        return NodeResult(success=not result.get("error"), output=result.get("response", ""))


class MemorySearchNode(BaseNode):
    type = "ai.memory_search"
    category = "ai"
    label = "Memory Search"
    description = "Search agent memory for relevant context"
    default_config = {"limit": 5}
    outputs = [{"id": "output", "label": "Memories", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        query = context.get("input", "")
        try:
            from agent.memory_manager import get_memory
            mem = get_memory()
            results = mem.search(query, limit=node.config.get("limit", 5))
            return NodeResult(success=True, output=results)
        except Exception as e:
            return NodeResult(success=False, output=str(e), error=str(e))


class VisionNode(BaseNode):
    type = "ai.vision"
    category = "ai"
    label = "Vision Analysis"
    description = "Analyze images using vision-capable models"
    default_config = {"model": ""}
    outputs = [{"id": "output", "label": "Analysis", "type": "string"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        image_url = context.get("input", "")
        try:
            from tools.vision_tool import vision_analyze
            result = vision_analyze(image=image_url)
            return NodeResult(success=True, output=result)
        except Exception as e:
            return NodeResult(success=False, output=str(e), error=str(e))


def register():
    NodeRegistry.register(ChatNode)
    NodeRegistry.register(ReasoningNode)
    NodeRegistry.register(SummarizeNode)
    NodeRegistry.register(TranslateNode)
    NodeRegistry.register(CodeGenerationNode)
    NodeRegistry.register(CodeReviewNode)
    NodeRegistry.register(ResearchNode)
    NodeRegistry.register(MemorySearchNode)
    NodeRegistry.register(VisionNode)


register()

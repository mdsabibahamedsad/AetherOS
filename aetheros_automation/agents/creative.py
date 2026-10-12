from __future__ import annotations

import json
import logging
import random
from typing import Any

from aetheros_automation.agents.registry import AgentRegistry, BaseAgent
from aetheros_automation.models.models import AgentRole, Task

logger = logging.getLogger(__name__)


class CreativeAgent(BaseAgent):
    @property
    def role(self) -> AgentRole:
        return AgentRole.CREATIVE

    async def execute(self, task: Task, context: dict | None = None) -> str:
        ctx = context or {}
        brief = task.metadata.get("brief", task.description)
        logger.info("Creative agent working on: %s", brief[:80])

        content_type = ctx.get("content_type", "creative")
        if "image" in brief.lower() or "visual" in brief.lower():
            return await self.generate_visual_concept(brief)
        if "design" in brief.lower() or "layout" in brief.lower():
            return await self.generate_design(brief)
        if "story" in brief.lower() or "narrative" in brief.lower():
            return await self.generate_story(brief)
        if "idea" in brief.lower() or "brainstorm" in brief.lower():
            return await self.brainstorm_ideas(brief)

        return await self.generate_creative_content(brief, content_type)

    async def generate_visual_concept(self, brief: str) -> str:
        concepts = [
            f"Visual concept for '{brief}':\n",
            "- Color palette inspired by natural elements\n",
            "- Asymmetric composition drawing focus to the center\n",
            "- Layered depth with foreground, midground, and background elements\n",
            "- Textural contrast between smooth and rough surfaces\n",
        ]
        return "".join(concepts)

    async def generate_design(self, brief: str) -> str:
        design = {
            "concept": f"Design for {brief}",
            "layout": "Asymmetric grid with focal point at upper-left",
            "typography": "Sans-serif for headers, serif for body",
            "color_scheme": ["#2C3E50", "#E74C3C", "#ECF0F1", "#3498DB"],
            "spacing": "Generous whitespace with 8px grid system",
            "style_notes": "Minimalist with bold accent elements",
        }
        return json.dumps(design, indent=2)

    async def generate_story(self, brief: str) -> str:
        return (
            f"Story outline for '{brief}':\n\n"
            "1. Opening hook that establishes the central conflict\n"
            "2. Rising action with three key turning points\n"
            "3. Climax where the protagonist faces their greatest challenge\n"
            "4. Falling action resolving subplots\n"
            "5. Satisfying conclusion with thematic resonance\n"
        )

    async def brainstorm_ideas(self, brief: str) -> str:
        ideas: list[dict] = []
        for i in range(5):
            ideas.append({
                "id": i + 1,
                "title": f"Concept {i + 1}: {brief}",
                "approach": random.choice([
                    "Minimalist", "Bold", "Experimental", "Classic", "Futuristic",
                ]),
                "estimated_effort": random.choice(["Low", "Medium", "High"]),
            })
        return json.dumps(ideas, indent=2)

    async def generate_creative_content(self, brief: str, content_type: str) -> str:
        return (
            f"Creative content generated for '{brief}':\n\n"
            f"Type: {content_type}\n"
            "- Original concept developed\n"
            "- Creative direction established\n"
            "- Production-ready output\n"
        )


AgentRegistry.register(AgentRole.CREATIVE, CreativeAgent)

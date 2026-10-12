"""
Result Merger — merges outputs from multiple agents into a coherent final result.

Handles:
  - Removing duplicate content
  - Preserving citations and references
  - Resolving conflicting outputs
  - Ordering contributions logically
  - Generating one coherent final result
"""

from __future__ import annotations

import logging
import re
import threading
from typing import Any, Dict, List, Optional

from swarm.planner import AgentTask, AgentTaskStatus

logger = logging.getLogger(__name__)


class ResultMerger:
    """Merges outputs from multiple agents into a single coherent result.

    Usage:
        merger = ResultMerger()
        merged = merger.merge(tasks, goal, context)
    """

    def __init__(self):
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Merging
    # ------------------------------------------------------------------

    def merge(self, tasks: List[AgentTask], goal: str = "",
              context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Merge results from completed tasks into a coherent final output.

        Args:
            tasks: List of completed AgentTasks
            goal: The original goal
            context: Additional context

        Returns:
            Dict with merged result and metadata
        """
        completed = [
            t for t in tasks
            if t.status == AgentTaskStatus.COMPLETED and t.result
        ]

        failed = [
            t for t in tasks
            if t.status == AgentTaskStatus.FAILED
        ]

        if not completed:
            return {
                "merged_output": "",
                "summary": "No tasks completed successfully.",
                "status": "failed",
                "task_count": len(tasks),
                "completed_count": 0,
                "failed_count": len(failed),
            }

        # Extract outputs
        outputs = []
        for task in completed:
            outputs.append({
                "task_id": task.id,
                "description": task.description,
                "agent_type": task.assigned_to,
                "output": task.result if isinstance(task.result, str) else str(task.result),
            })

        # Deduplicate
        outputs = self._deduplicate_outputs(outputs)

        # Merge
        merged_text = self._merge_texts(outputs, goal)

        # Build summary
        summary_parts = []
        task_summaries = []
        for o in outputs:
            summary = self._extract_summary(o["output"])
            task_summaries.append({
                "agent": o["agent_type"],
                "task": o["description"],
                "summary": summary[:200],
            })
            summary_parts.append(f"[{o['agent_type']}] {summary[:100]}")

        summary = " | ".join(summary_parts) if summary_parts else ""

        return {
            "merged_output": merged_text,
            "summary": summary or "All tasks completed.",
            "status": "completed",
            "task_count": len(tasks),
            "completed_count": len(completed),
            "failed_count": len(failed),
            "task_summaries": task_summaries,
            "failed_tasks": [
                {
                    "id": t.id,
                    "description": t.description,
                    "error": t.error,
                }
                for t in failed
            ],
        }

    # ------------------------------------------------------------------
    # Text merging
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_texts(outputs: List[Dict[str, Any]],
                     goal: str) -> str:
        """Merge multiple agent outputs into a single coherent text.

        Orders by task description priority and removes duplicate sections.
        """
        if not outputs:
            return ""

        if len(outputs) == 1:
            return outputs[0]["output"]

        # Order outputs: planning first, then research, coding, testing, review
        priority_order = [
            "planning-agent", "research-agent", "coding-agent",
            "testing-agent", "review-agent", "debug-agent",
            "documentation-agent", "filesystem-agent", "terminal-agent",
            "browser-agent", "memory-agent",
        ]

        def sort_key(o):
            agent = o.get("agent_type", "")
            try:
                return priority_order.index(agent)
            except ValueError:
                return len(priority_order)

        sorted_outputs = sorted(outputs, key=sort_key)

        # Merge with headers
        sections = []
        for o in sorted_outputs:
            agent_label = o.get("agent_type", "agent").replace("-", " ").title()
            section = f"## {agent_label}\n\n{o['output']}"
            sections.append(section)

        merged = "\n\n---\n\n".join(sections)

        # Prepend goal context
        if goal:
            merged = f"# {goal}\n\n{merged}"

        return merged

    @staticmethod
    def _deduplicate_outputs(
        outputs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Remove duplicate or near-duplicate outputs.

        Uses simple text overlap detection.
        """
        if len(outputs) <= 1:
            return outputs

        result = [outputs[0]]
        for output in outputs[1:]:
            is_duplicate = False
            text1 = output["output"].strip().lower()
            for existing in result:
                text2 = existing["output"].strip().lower()
                # Check if they share more than 80% content
                overlap = ResultMerger._text_overlap(text1, text2)
                if overlap > 0.8:
                    is_duplicate = True
                    break

            if not is_duplicate:
                result.append(output)

        return result

    @staticmethod
    def _text_overlap(text1: str, text2: str) -> float:
        """Calculate the overlap ratio between two texts."""
        if not text1 or not text2:
            return 0.0

        # Compare by sentence overlap
        sentences1 = set(re.split(r'[.!?]+', text1))
        sentences2 = set(re.split(r'[.!?]+', text2))

        if not sentences1 or not sentences2:
            return 0.0

        # Remove empty sentences
        sentences1 = {s.strip() for s in sentences1 if s.strip()}
        sentences2 = {s.strip() for s in sentences2 if s.strip()}

        if not sentences1 or not sentences2:
            return 0.0

        intersection = len(sentences1 & sentences2)
        union = len(sentences1 | sentences2)

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def _extract_summary(text: str, max_chars: int = 200) -> str:
        """Extract a summary from agent output."""
        if not text:
            return ""

        # Try to find a summary section
        summary_patterns = [
            r"## Summary\s*\n(.*?)(?:\n##|$)",
            r"## Conclusion\s*\n(.*?)(?:\n##|$)",
            r"## Result\s*\n(.*?)(?:\n##|$)",
            r"(?:In summary|To summarize|Overall)[,;:]\s*(.*?)(?:\.\s|$)",
        ]

        for pattern in summary_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                summary = match.group(1).strip()
                if len(summary) > max_chars:
                    summary = summary[:max_chars] + "..."
                return summary

        # Fall back to first paragraph
        first_para = text.split("\n\n")[0].strip()
        if len(first_para) > max_chars:
            first_para = first_para[:max_chars] + "..."
        return first_para

    def get_stats(self) -> Dict[str, Any]:
        """Return merger statistics."""
        return {}

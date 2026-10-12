"""
Workflow AI for AetherOS Intelligence Engine.

Automatically:
    - Optimizes workflows by removing duplicate steps
    - Suggests shortcuts for common patterns
    - Recommends automations for repetitive tasks
    - Analyzes workflow efficiency

Works with the AetherOS automation engine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    name: str = ""
    description: str = ""
    duration_ms: float = 0.0
    frequency: int = 1
    is_automated: bool = False
    category: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowSuggestion:
    title: str
    description: str
    type: str
    effort: str
    impact: str
    confidence: float = 0.5


class WorkflowAI:
    """AI-powered workflow optimization engine.

    Analyzes execution patterns, identifies inefficiencies,
    and suggests optimizations, shortcuts, and automations.

    Usage::

        wf = WorkflowAI()
        # Record step execution
        wf.record_step("build", duration_ms=12000)
        # Get optimization suggestions
        suggestions = wf.get_suggestions()
    """

    def __init__(self) -> None:
        self._steps: List[WorkflowStep] = []
        self._workflows: Dict[str, List[WorkflowStep]] = {}

    # ------------------------------------------------------------------
    # Step recording
    # ------------------------------------------------------------------

    def record_step(self, name: str, description: str = "",
                    duration_ms: float = 0.0,
                    category: str = "",
                    workflow: str = "") -> None:
        """Record a workflow step execution."""
        step = WorkflowStep(
            name=name,
            description=description,
            duration_ms=duration_ms,
            category=category,
        )
        self._steps.append(step)

        if workflow:
            if workflow not in self._workflows:
                self._workflows[workflow] = []
            self._workflows[workflow].append(step)

        logger.debug("Recorded workflow step: %s (%sms)", name, duration_ms)

    def record_workflow(self, name: str, steps: List[Dict[str, Any]]) -> str:
        """Record a complete workflow with steps."""
        workflow_steps = []
        for s in steps:
            step = WorkflowStep(
                name=s.get("name", "step"),
                description=s.get("description", ""),
                duration_ms=s.get("duration_ms", 0.0),
                category=s.get("category", ""),
            )
            workflow_steps.append(step)
            self._steps.append(step)

        self._workflows[name] = workflow_steps
        return name

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze_efficiency(self) -> Dict[str, Any]:
        """Analyze overall workflow efficiency."""
        if not self._steps:
            return {"message": "No workflow data recorded yet"}

        total_steps = len(self._steps)
        total_duration = sum(s.duration_ms for s in self._steps)
        avg_duration = total_duration / total_steps if total_steps > 0 else 0

        categories = {}
        for s in self._steps:
            cat = s.category or "uncategorized"
            categories.setdefault(cat, {"count": 0, "total_duration_ms": 0.0})
            categories[cat]["count"] += 1
            categories[cat]["total_duration_ms"] += s.duration_ms

        return {
            "total_steps": total_steps,
            "total_duration_ms": total_duration,
            "avg_duration_ms": round(avg_duration, 1),
            "categories": categories,
            "workflow_count": len(self._workflows),
        }

    # ------------------------------------------------------------------
    # Optimization suggestions
    # ------------------------------------------------------------------

    def get_suggestions(self) -> List[Dict[str, Any]]:
        """Get workflow optimization suggestions."""
        suggestions = []

        if len(self._steps) < 3:
            return [{
                "title": "Not enough data",
                "description": "Record more workflow steps for personalized suggestions",
                "type": "info",
                "effort": "none",
                "impact": "none",
            }]

        duplicate_suggestion = self._find_duplicate_steps()
        if duplicate_suggestion:
            suggestions.append(duplicate_suggestion)

        slow_steps = self._find_slow_steps()
        suggestions.extend(slow_steps)

        automation_opportunities = self._find_automation_opportunities()
        suggestions.extend(automation_opportunities)

        shortcut_suggestion = self._find_shortcuts()
        if shortcut_suggestion:
            suggestions.append(shortcut_suggestion)

        return suggestions

    def _find_duplicate_steps(self) -> Optional[Dict[str, Any]]:
        """Find steps that appear frequently and could be optimized."""
        from collections import Counter

        step_names = [s.name for s in self._steps]
        counter = Counter(step_names)
        duplicates = {name: count for name, count in counter.items()
                      if count > 2}

        if duplicates:
            most_common = max(duplicates, key=duplicates.get)
            return {
                "title": f"Frequent step: '{most_common}'",
                "description": f"Executed {duplicates[most_common]} times. "
                               f"Consider caching or batching.",
                "type": "optimization",
                "effort": "low",
                "impact": "medium",
                "confidence": 0.7,
            }
        return None

    def _find_slow_steps(self) -> List[Dict[str, Any]]:
        """Find steps that take disproportionately long."""
        suggestions = []
        if not self._steps:
            return suggestions

        avg_duration = sum(s.duration_ms for s in self._steps) / len(self._steps)
        threshold = avg_duration * 3

        slow_steps = [s for s in self._steps if s.duration_ms > threshold]
        for s in slow_steps[:3]:
            suggestions.append({
                "title": f"Slow step: '{s.name}'",
                "description": f"Took {s.duration_ms:.0f}ms "
                               f"({(s.duration_ms / avg_duration):.1f}x average)",
                "type": "performance",
                "effort": "medium",
                "impact": "high",
                "confidence": 0.75,
            })

        return suggestions

    def _find_automation_opportunities(self) -> List[Dict[str, Any]]:
        """Find steps that are good automation candidates."""
        suggestions = []
        from collections import Counter

        step_names = [s.name for s in self._steps if not s.is_automated]
        counter = Counter(step_names)
        automation_candidates = {name: count for name, count in counter.items()
                                  if count > 2}

        for name, count in automation_candidates.items():
            suggestions.append({
                "title": f"Automate: '{name}'",
                "description": f"Performed {count} times manually. "
                               f"Automation could save significant time.",
                "type": "automation",
                "effort": "medium",
                "impact": "high",
                "confidence": 0.8,
            })

        return suggestions[:3]

    def _find_shortcuts(self) -> Optional[Dict[str, Any]]:
        """Identify potential shortcuts in common sequences."""
        if len(self._steps) < 4:
            return None

        sequences = []
        for i in range(len(self._steps) - 2):
            seq = (self._steps[i].name, self._steps[i + 1].name)
            sequences.append(seq)

        from collections import Counter
        counter = Counter(sequences)
        common_sequence = counter.most_common(1)
        if common_sequence and common_sequence[0][1] > 1:
            seq, count = common_sequence[0]
            return {
                "title": f"Common sequence: '{seq[0]}' -> '{seq[1]}'",
                "description": f"Occurred {count} times. Consider creating "
                               f"a combined operation or script.",
                "type": "shortcut",
                "effort": "low",
                "impact": "medium",
                "confidence": 0.65,
            }
        return None

    # ------------------------------------------------------------------
    # Workflow analysis
    # ------------------------------------------------------------------

    def get_workflow_report(self, workflow_name: str = "") -> Dict[str, Any]:
        """Get a detailed report on workflows."""
        if workflow_name:
            steps = self._workflows.get(workflow_name, [])
            if not steps:
                return {"error": f"Workflow '{workflow_name}' not found"}
            return {
                "name": workflow_name,
                "steps": [
                    {"name": s.name, "duration_ms": s.duration_ms,
                     "category": s.category}
                    for s in steps
                ],
                "total_steps": len(steps),
                "total_duration_ms": sum(s.duration_ms for s in steps),
            }

        return {
            "workflows": {
                name: {
                    "step_count": len(steps),
                    "total_duration_ms": sum(s.duration_ms for s in steps),
                }
                for name, steps in self._workflows.items()
            },
            "total_workflows": len(self._workflows),
            "suggestions_count": len(self._find_automation_opportunities()),
        }

    def clear_history(self) -> None:
        self._steps.clear()
        self._workflows.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_steps_recorded": len(self._steps),
            "total_workflows_recorded": len(self._workflows),
            "available_suggestions": len(self.get_suggestions()),
        }

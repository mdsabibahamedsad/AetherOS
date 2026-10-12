"""
Reflection Engine — post-execution analysis, learning, and improvement.

After each mission or execution phase, the Reflection Engine:
  1. Analyzes execution results vs intended goals
  2. Identifies what went well and what went wrong
  3. Extracts lessons and improvement suggestions
  4. Updates planning strategies for future missions
  5. Stores lessons in a persistent lesson store

This creates a continuous improvement loop where the system
learns from every execution.
"""

from __future__ import annotations

import enum
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class LessonCategory(enum.Enum):
    PLANNING = "planning"
    EXECUTION = "execution"
    COORDINATION = "coordination"
    COMMUNICATION = "communication"
    RESOURCE_MANAGEMENT = "resource_management"
    ERROR_HANDLING = "error_handling"
    QUALITY = "quality"
    SECURITY = "security"
    PERFORMANCE = "performance"


class LessonSeverity(enum.IntEnum):
    SUGGESTION = 0
    IMPORTANT = 1
    CRITICAL = 2


@dataclass
class Lesson:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    category: LessonCategory = LessonCategory.PLANNING
    severity: LessonSeverity = LessonSeverity.IMPORTANT
    title: str = ""
    description: str = ""
    context: str = ""
    recommendation: str = ""
    source_plan_id: str = ""
    source_agent_id: str = ""
    created_at: float = field(default_factory=time.time)
    applied: bool = False
    applied_at: Optional[float] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class ReflectionResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    plan_id: str = ""
    plan_goal: str = ""
    success: bool = False
    duration_seconds: float = 0.0
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    lessons: List[Lesson] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    improvement_suggestions: List[str] = field(default_factory=list)


class ReflectionEngine:
    """Post-execution analysis engine that learns from every mission.

    Analyzes execution results, extracts lessons, and improves
    future planning and execution strategies.

    Usage:
        engine = ReflectionEngine(event_bus)
        result = engine.analyze_execution(plan_id, plan_data, execution_data)
        lessons = engine.get_lessons(category=LessonCategory.PLANNING)
        suggestions = engine.get_improvement_suggestions()
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._reflections: Dict[str, ReflectionResult] = {}
        self._lessons: Dict[str, Lesson] = {}
        self._strategy_adjustments: Dict[str, float] = {}
        self._execution_history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Execution analysis
    # ------------------------------------------------------------------

    def analyze_execution(self, plan_id: str, goal: str,
                          plan_data: Dict[str, Any],
                          execution_data: Dict[str, Any],
                          steps: List[Dict[str, Any]] = None) -> ReflectionResult:
        start = time.time()
        steps = steps or plan_data.get("steps", []) or []

        total = len(steps)
        completed = sum(1 for s in steps if s.get("status") in ("completed", "success"))
        failed = sum(1 for s in steps if s.get("status") in ("failed", "error"))
        success = failed == 0 and completed > 0
        duration = execution_data.get("duration_seconds", 0.0)

        lessons: List[Lesson] = []

        lessons.extend(self._analyze_plan_quality(plan_data, goal))
        lessons.extend(self._analyze_execution_quality(execution_data, steps))
        lessons.extend(self._analyze_coordination(execution_data))
        lessons.extend(self._analyze_errors(execution_data))
        lessons.extend(self._analyze_performance(execution_data))

        improvement_suggestions = self._generate_suggestions(lessons)

        summary_parts = []
        if success:
            summary_parts.append(f"Mission completed successfully ({completed}/{total} steps)")
        else:
            summary_parts.append(f"Mission had {failed} failures ({completed}/{total} steps)")

        metrics = {
            "success_rate": (completed / total * 100) if total > 0 else 0,
            "failure_rate": (failed / total * 100) if total > 0 else 0,
            "total_steps": total,
            "completed_steps": completed,
            "failed_steps": failed,
            "duration_seconds": duration,
            "lessons_extracted": len(lessons),
        }

        result = ReflectionResult(
            plan_id=plan_id,
            plan_goal=goal,
            success=success,
            duration_seconds=duration,
            total_steps=total,
            completed_steps=completed,
            failed_steps=failed,
            lessons=lessons,
            metrics=metrics,
            summary=" | ".join(summary_parts),
            improvement_suggestions=improvement_suggestions,
        )

        with self._lock:
            self._reflections[result.id] = result
            for lesson in lessons:
                self._lessons[lesson.id] = lesson
            self._execution_history.append({
                "plan_id": plan_id,
                "goal": goal[:80],
                "success": success,
                "duration": duration,
                "completed": completed,
                "failed": failed,
                "timestamp": time.time(),
            })
            if len(self._execution_history) > 1000:
                self._execution_history = self._execution_history[-500:]

        if self._event_bus:
            self._event_bus.emit_async("reflection.completed", {
                "result_id": result.id,
                "plan_id": plan_id,
                "success": success,
                "lessons_count": len(lessons),
            })

        logger.info("ReflectionEngine: analyzed plan %s: %s",
                     plan_id, summary_parts[0] if summary_parts else "done")
        return result

    # ------------------------------------------------------------------
    # Analysis methods
    # ------------------------------------------------------------------

    def _analyze_plan_quality(self, plan_data: Dict[str, Any],
                              goal: str) -> List[Lesson]:
        lessons: List[Lesson] = []
        steps = plan_data.get("steps", []) or []

        if not steps:
            lessons.append(Lesson(
                category=LessonCategory.PLANNING,
                severity=LessonSeverity.CRITICAL,
                title="Empty plan",
                description="Plan had no defined steps",
                recommendation="Always break goals into concrete, actionable steps",
                tags=["planning", "completeness"],
            ))

        if len(steps) == 1:
            lessons.append(Lesson(
                category=LessonCategory.PLANNING,
                severity=LessonSeverity.SUGGESTION,
                title="Single-step plan",
                description=f"Plan had only 1 step for goal: {goal[:60]}",
                recommendation="Complex goals benefit from more granular step decomposition",
                tags=["planning", "granularity"],
            ))

        has_deps = any(s.get("dependencies") for s in steps if isinstance(s, dict))
        if len(steps) > 1 and not has_deps:
            lessons.append(Lesson(
                category=LessonCategory.PLANNING,
                severity=LessonSeverity.IMPORTANT,
                title="Missing dependencies",
                description=f"Plan has {len(steps)} steps but no dependency relationships",
                recommendation="Define dependencies between steps for better parallelism and ordering",
                tags=["planning", "dependencies"],
            ))

        return lessons

    def _analyze_execution_quality(self, execution_data: Dict[str, Any],
                                   steps: List[Dict[str, Any]]) -> List[Lesson]:
        lessons: List[Lesson] = []
        errors = execution_data.get("errors", []) or []
        retries = execution_data.get("retries", 0) or 0

        if retries > 3:
            lessons.append(Lesson(
                category=LessonCategory.ERROR_HANDLING,
                severity=LessonSeverity.IMPORTANT,
                title="Excessive retries",
                description=f"Execution required {retries} retries",
                recommendation="Investigate root cause instead of relying on retries",
                tags=["execution", "error-handling"],
            ))

        if errors:
            lessons.append(Lesson(
                category=LessonCategory.ERROR_HANDLING,
                severity=LessonSeverity.IMPORTANT,
                title=f"{len(errors)} execution errors",
                description=f"Errors encountered: {errors[:3]}",
                recommendation="Add better error handling and preconditions",
                tags=["execution", "errors"],
            ))

        return lessons

    def _analyze_coordination(self, execution_data: Dict[str, Any]) -> List[Lesson]:
        lessons: List[Lesson] = []
        handoffs = execution_data.get("handoffs", []) or []
        conflicts = execution_data.get("conflicts", []) or []

        if conflicts:
            lessons.append(Lesson(
                category=LessonCategory.COORDINATION,
                severity=LessonSeverity.CRITICAL,
                title=f"{len(conflicts)} inter-agent conflicts",
                description="Agents had conflicts that required resolution",
                recommendation="Define clearer responsibility boundaries between agents",
                tags=["coordination", "conflicts"],
            ))

        if not handoffs:
            lessons.append(Lesson(
                category=LessonCategory.COORDINATION,
                severity=LessonSeverity.SUGGESTION,
                title="No agent handoffs",
                description="No task handoffs occurred between agents",
                recommendation="Consider distributing work across specialized agents",
                tags=["coordination", "delegation"],
            ))

        return lessons

    def _analyze_errors(self, execution_data: Dict[str, Any]) -> List[Lesson]:
        lessons: List[Lesson] = []
        error_types = execution_data.get("error_types", {}) or {}

        for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
            if count >= 2:
                lessons.append(Lesson(
                    category=LessonCategory.QUALITY,
                    severity=LessonSeverity.IMPORTANT,
                    title=f"Recurring error: {error_type}",
                    description=f"Error '{error_type}' occurred {count} times",
                    recommendation=f"Address root cause of recurring '{error_type}' errors",
                    tags=["quality", "errors", error_type],
                ))

        return lessons

    def _analyze_performance(self, execution_data: Dict[str, Any]) -> List[Lesson]:
        lessons: List[Lesson] = []
        duration = execution_data.get("duration_seconds", 0.0)

        if duration > 600:
            lessons.append(Lesson(
                category=LessonCategory.PERFORMANCE,
                severity=LessonSeverity.IMPORTANT,
                title=f"Long execution time ({duration:.0f}s)",
                description=f"Execution took {duration:.0f}s",
                recommendation="Consider parallelizing independent tasks for faster execution",
                tags=["performance", "duration"],
            ))

        memory_peak = execution_data.get("memory_peak_mb", 0.0)
        if memory_peak > 1024:
            lessons.append(Lesson(
                category=LessonCategory.PERFORMANCE,
                severity=LessonSeverity.IMPORTANT,
                title=f"High memory usage ({memory_peak:.0f}MB)",
                description=f"Peak memory usage was {memory_peak:.0f}MB",
                recommendation="Optimize memory usage, consider streaming for large artifacts",
                tags=["performance", "memory"],
            ))

        return lessons

    # ------------------------------------------------------------------
    # Improvement suggestions
    # ------------------------------------------------------------------

    def _generate_suggestions(self, lessons: List[Lesson]) -> List[str]:
        suggestions: Set[str] = set()
        for lesson in lessons:
            if lesson.severity >= LessonSeverity.IMPORTANT:
                suggestions.add(lesson.recommendation)
        return list(suggestions)[:10]

    # ------------------------------------------------------------------
    # Lesson management
    # ------------------------------------------------------------------

    def get_lessons(self, category: LessonCategory = None,
                    severity: LessonSeverity = None,
                    limit: int = 100) -> List[Lesson]:
        with self._lock:
            lessons = list(self._lessons.values())
        if category:
            lessons = [l for l in lessons if l.category == category]
        if severity:
            lessons = [l for l in lessons if l.severity >= severity]
        lessons.sort(key=lambda l: (l.severity, l.created_at), reverse=True)
        return lessons[:limit]

    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        with self._lock:
            return self._lessons.get(lesson_id)

    def mark_lesson_applied(self, lesson_id: str) -> bool:
        with self._lock:
            lesson = self._lessons.get(lesson_id)
            if lesson is None or lesson.applied:
                return False
            lesson.applied = True
            lesson.applied_at = time.time()
        return True

    # ------------------------------------------------------------------
    # Strategy adjustments
    # ------------------------------------------------------------------

    def record_strategy_adjustment(self, strategy: str,
                                   adjustment: float) -> None:
        with self._lock:
            current = self._strategy_adjustments.get(strategy, 0.0)
            self._strategy_adjustments[strategy] = current + adjustment

    def get_strategy_adjustments(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._strategy_adjustments)

    # ------------------------------------------------------------------
    # History and stats
    # ------------------------------------------------------------------

    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._execution_history[-limit:])

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            reflections = list(self._reflections.values())
            total = len(reflections)
            successful = sum(1 for r in reflections if r.success)
            total_lessons = len(self._lessons)
            applied_lessons = sum(1 for l in self._lessons.values() if l.applied)
        return {
            "total_analyses": total,
            "successful_missions": successful,
            "failed_missions": total - successful,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "total_lessons": total_lessons,
            "applied_lessons": applied_lessons,
            "strategy_adjustments": len(self._strategy_adjustments),
        }
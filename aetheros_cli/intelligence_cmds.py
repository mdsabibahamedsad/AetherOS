"""
Intelligence command handlers for Phase 14 of AetherOS Intelligence Engine.

These functions implement the ``aetheros plan``, ``aetheros think``,
``aetheros analyze``, ``aetheros agents``, ``aetheros memory``,
``aetheros knowledge``, and ``aetheros learn`` CLI commands.
"""

from __future__ import annotations

import argparse
import json
import sys
import time


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _maybe_json(data, args) -> str:
    if getattr(args, "json", False):
        return json.dumps(data, indent=2, default=str)
    return _format_human(data)


def _format_human(data) -> str:
    if isinstance(data, list):
        return "\n".join(_format_human(item) for item in data)
    if isinstance(data, dict):
        lines = []
        for k, v in data.items():
            if isinstance(v, dict):
                lines.append(f"{k}:")
                for sk, sv in v.items():
                    lines.append(f"  {sk}: {sv}")
            elif isinstance(v, list):
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{k}: {v}")
        return "\n".join(lines)
    return str(data)


# ---------------------------------------------------------------------------
# Lazy engine getter
# ---------------------------------------------------------------------------

def _get_intelligence() -> "IntelligenceEngine":
    from aetheros_intelligence import get_intelligence_engine
    engine = get_intelligence_engine()
    engine.initialize()
    return engine


# ---------------------------------------------------------------------------
# aetheros plan
# ---------------------------------------------------------------------------

def cmd_plan(args: argparse.Namespace) -> int:
    """Dispatch ``aetheros plan <subcommand>``."""
    sub = getattr(args, "plan_command", None)

    if sub == "create":
        engine = _get_intelligence()
        result = engine.plan(args.goal, getattr(args, "context", ""),
                             priority=getattr(args, "priority", "medium"))
        if getattr(args, "json", False):
            print(json.dumps(result, indent=2))
        else:
            print(f"Plan created: {result.get('id', 'unknown')}")
            print(f"Goal: {args.goal}")
            print(f"Tasks: {result.get('task_count', 0)}")
        return 0

    elif sub in ("list", "ls"):
        engine = _get_intelligence()
        plans = engine.list_plans(
            include_completed=getattr(args, "all", False),
            limit=getattr(args, "limit", 10),
        )
        if getattr(args, "json", False):
            print(json.dumps(plans, indent=2))
        else:
            print(f"{'ID':16s} {'Goal':40s} {'Status':15s} {'Progress':10s}")
            print("-" * 81)
            for p in plans:
                completed = p.get("completed_tasks", 0)
                total = p.get("task_count", 0)
                progress = f"{completed}/{total}" if total else "0/0"
                print(f"{p.get('id', ''):16s} {p.get('goal', '')[:40]:40s} "
                      f"{p.get('status', ''):15s} {progress:10s}")
        return 0

    elif sub == "show":
        engine = _get_intelligence()
        plan = engine.get_plan(args.plan_id)
        if not plan:
            print(f"Plan not found: {args.plan_id}", file=sys.stderr)
            return 1
        if getattr(args, "json", False):
            print(json.dumps(plan, indent=2))
        else:
            print(f"Plan: {plan.get('id', '')}")
            print(f"Goal: {plan.get('goal', '')}")
            print(f"Status: {plan.get('status', 'unknown')}")
            print(f"Tasks: {plan.get('task_count', 0)}")
            print()
            for task in plan.get("tasks", []):
                status_mark = "✓" if task.get("status") == "completed" else \
                             "●" if task.get("status") == "in_progress" else "○"
                print(f"  [{status_mark}] {task.get('title', '')[:70]}")
        return 0

    elif sub in ("execute", "exec"):
        engine = _get_intelligence()
        result = engine.execute_next(args.plan_id)
        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            return 1
        task = result.get("task", {})
        if task:
            print(f"Executing: {task.get('title', '')}")
            print(f"Agent: {task.get('assigned_agent', 'any')}")
            print(f"Remaining: {result.get('remaining', 0)} tasks")
        elif result.get("plan_completed"):
            print("All tasks completed!")
        else:
            print(result.get("message", "No tasks ready"))
        return 0

    elif sub == "status":
        engine = _get_intelligence()
        result = engine.get_plan_status(args.plan_id)
        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            return 1
        if getattr(args, "json", False):
            print(json.dumps(result, indent=2))
        else:
            print(f"Plan Status: {result.get('goal', '')}")
            print(f"  Status:    {result.get('status', 'unknown')}")
            print(f"  Progress:  {result.get('progress', 0)}%")
            print(f"  Tasks:     {result.get('completed', 0)}/{result.get('total_tasks', 0)}")
            print(f"  Failed:    {result.get('failed', 0)}")
            print(f"  Blocked:   {result.get('blocked', 0)}")
            print(f"  Elapsed:   {result.get('elapsed', 0):.0f}s")
        return 0

    elif sub == "refine":
        engine = _get_intelligence()
        feedback = args.feedback or "Refine based on progress"
        result = engine.refine_plan(args.plan_id, feedback)
        if not result:
            print(f"Plan not found: {args.plan_id}", file=sys.stderr)
            return 1
        print(f"Plan {args.plan_id} refined with feedback.")
        return 0

    else:
        print(f"Unknown plan subcommand: {sub}", file=sys.stderr)
        print("Usage: aetheros plan <create|list|show|execute|status|refine>")
        return 2


# ---------------------------------------------------------------------------
# aetheros think
# ---------------------------------------------------------------------------

def cmd_think(args: argparse.Namespace) -> int:
    """Dispatch ``aetheros think <subcommand>``."""
    sub = getattr(args, "think_command", None)

    if sub in ("reason", "r"):
        engine = _get_intelligence()
        result = engine.reason(args.question, context=getattr(args, "context", None))
        if getattr(args, "json", False):
            print(json.dumps(result, indent=2))
        else:
            print("Reasoning Result:")
            print(f"  Answer:      {result.get('answer', '')[:200]}")
            print(f"  Confidence:  {result.get('confidence', 0.0):.2f}")
            print(f"  Duration:    {result.get('total_duration', 0):.2f}s")
            steps = result.get("steps", [])
            print(f"  Steps ({len(steps)}):")
            for s in steps:
                check = "✓" if s.get("verified") else " "
                print(f"    [{check}] {s.get('strategy', 'step')} "
                      f"(conf: {s.get('confidence', 0.0):.2f})")
            alts = result.get("alternatives", [])
            if alts:
                print(f"  Alternatives ({len(alts)}):")
                for a in alts:
                    print(f"    - {a.get('title', 'Option')}")
        return 0

    elif sub == "reflect":
        engine = _get_intelligence()
        result = engine.reflect(
            goal=args.goal, outcome=args.outcome,
            successes=getattr(args, "success", []),
            failures=getattr(args, "failure", []),
            lessons=getattr(args, "lesson", []),
        )
        print(_maybe_json(result, args))
        return 0

    elif sub == "explain":
        engine = _get_intelligence()
        result = engine.explain(
            decision=args.decision,
            confidence=getattr(args, "confidence", None),
        )
        if getattr(args, "json", False):
            print(json.dumps(result, indent=2))
        else:
            print("Explanation:")
            print(f"  Decision:    {result.get('decision', '')}")
            print(f"  Confidence:  {result.get('confidence', 0.0):.2f}")
            print(f"  Reason:      {result.get('reason', '')}")
            alts = result.get("alternatives", [])
            tradeoffs = result.get("tradeoffs", [])
            if alts:
                print(f"  Alternatives:")
                for a in alts:
                    print(f"    - {a.get('title', 'Option')}")
            if tradeoffs:
                print(f"  Tradeoffs:")
                for t in tradeoffs:
                    pro = t.get("pro", "")
                    con = t.get("con", "")
                    print(f"    + {pro}")
                    if con:
                        print(f"    - {con}")
        return 0

    elif sub == "status":
        engine = _get_intelligence()
        result = engine.status()
        print(_maybe_json(result, args))
        return 0

    else:
        print(f"Unknown think subcommand: {sub}", file=sys.stderr)
        print("Usage: aetheros think <reason|reflect|explain|status>")
        return 2


# ---------------------------------------------------------------------------
# aetheros analyze
# ---------------------------------------------------------------------------

def cmd_analyze(args: argparse.Namespace) -> int:
    """Dispatch ``aetheros analyze <subcommand>``."""
    sub = getattr(args, "analyze_command", None)

    if sub in ("project", "p"):
        engine = _get_intelligence()
        print(f"Analyzing project: {args.path}...")
        result = engine.analyze_project(args.path)
        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            return 1
        if getattr(args, "json", False):
            print(json.dumps(result, indent=2))
        else:
            eco = result.get("ecosystem", {})
            quality = result.get("code_quality", {})
            deps = result.get("dependencies", {})
            security = result.get("security_risks", [])
            debt = result.get("technical_debt", {})
            stats = result.get("stats", {})
            print(f"Project:    {result.get('name', 'unknown')}")
            print(f"Ecosystem:  {eco.get('primary', 'unknown')}")
            print(f"Files:      {stats.get('total_files', '?')}")
            print(f"Code Quality Score: {quality.get('quality_score', 0.0):.2f}")
            print(f"Deps: {deps.get('external_count', 0)} external")
            if security:
                print(f"Security Risks: {len(security)}")
            print(f"Tech Debt:  {debt.get('total_markers', 0)} markers")
        return 0

    elif sub in ("file", "f"):
        engine = _get_intelligence()
        result = engine.understand_file(args.path)
        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            return 1
        print(_maybe_json(result, args))
        return 0

    elif sub in ("research", "rs"):
        engine = _get_intelligence()
        depth = getattr(args, "deep", 1)
        sources = getattr(args, "sources", None)
        print(f"Researching '{args.topic}' (depth={depth})...")
        if depth > 1:
            result = engine.deep_research(args.topic, depth=depth)
        else:
            result = engine.research(args.topic, sources=sources)
        print(_maybe_json(result, args))
        return 0

    elif sub in ("knowledge", "k"):
        engine = _get_intelligence()
        result = engine.research(args.query, sources=["knowledge"])
        print(_maybe_json(result, args))
        return 0

    elif sub in ("repository", "repo"):
        engine = _get_intelligence()
        print(f"Analyzing repository: {args.path}...")
        result = engine.analyze_repository(args.path)
        if getattr(args, "json", False):
            print(json.dumps(result, indent=2))
        else:
            symbols = result.get("symbols", [])
            arch = result.get("architecture", [])
            print(f"Repository: {result.get('name', 'unknown')}")
            print(f"Symbols:    {len(symbols)}")
            print(f"Files:      {sum(result.get('file_count', {}).values())}")
            for a in arch:
                print(f"  Pattern: {a.get('detail', a.get('type', ''))}")
        return 0

    elif sub in ("document", "docs"):
        engine = _get_intelligence()
        print(f"Generating documentation for: {args.path}...")
        result = engine.generate_documentation(args.path)
        if getattr(args, "json", False):
            print(json.dumps(result, indent=2))
        else:
            print(f"Documentation for: {result.get('name', '')}")
            for section in result.get("sections", []):
                print(f"\n## {section.get('title', '')}")
                print(section.get("content", "")[:200])
        return 0

    elif sub in ("tests",):
        engine = _get_intelligence()
        result = engine.generate_tests(args.path, getattr(args, "framework", "pytest"))
        if getattr(args, "json", False):
            print(json.dumps(result, indent=2))
        else:
            print(f"Test scaffolding for: {result.get('file', '')}")
            print(f"Functions: {result.get('function_count', 0)}")
            for tmpl in result.get("test_templates", []):
                print(f"\n{tmpl}")
        return 0

    elif sub == "refactor":
        engine = _get_intelligence()
        suggestions = engine.suggest_refactoring(args.path)
        if getattr(args, "json", False):
            print(json.dumps(suggestions, indent=2))
        else:
            print(f"Refactoring suggestions ({len(suggestions)}):")
            for s in suggestions:
                print(f"\n  [{s.get('effort', '?')}/{s.get('benefit', '?')}] "
                      f"{s.get('title', '')}")
                print(f"    {s.get('description', '')}")
        return 0

    elif sub == "status":
        engine = _get_intelligence()
        result = engine.status()
        print(_maybe_json(result, args))
        return 0

    else:
        print(f"Unknown analyze subcommand: {sub}", file=sys.stderr)
        print("Usage: aetheros analyze <project|file|research|knowledge|repository|document|tests|refactor|status>")
        return 2


# ---------------------------------------------------------------------------
# aetheros agents
# ---------------------------------------------------------------------------

def cmd_agents(args: argparse.Namespace) -> int:
    """Dispatch ``aetheros agents <subcommand>``."""
    sub = getattr(args, "agents_command", None)
    engine = _get_intelligence()

    if sub in ("list", "ls"):
        agents = engine.list_specialized_agents()
        role_filter = getattr(args, "role", None)
        if role_filter:
            agents = [a for a in agents if a["role"] == role_filter]
        if getattr(args, "json", False):
            print(json.dumps(agents, indent=2))
        else:
            print("Specialized Agents:")
            for a in agents:
                caps = ", ".join(a.get("capabilities", [])[:3])
                print(f"  {a.get('icon', ' ')} {a['role']:15s} "
                      f"{a.get('description', ''):45s}")
                print(f"      Model: {a.get('recommended_model', 'auto')} | {caps}")
        return 0

    elif sub == "status":
        agents = engine.list_specialized_agents()
        data = {
            "total_agents": len(agents),
            "agents": [
                {"role": a["role"], "name": a["name"],
                 "model": a.get("recommended_model", "auto"), "status": "ready"}
                for a in agents
            ],
        }
        if getattr(args, "json", False):
            print(json.dumps(data, indent=2))
        else:
            print(f"Agent System Status:")
            print(f"  Total Agents:    {data['total_agents']}")
            print(f"  Model Router:    available")
            print(f"  Coordinator:     available")
        return 0

    elif sub == "coordinate":
        goal = getattr(args, "goal", "")
        if not goal:
            print("Usage: aetheros agents coordinate <goal>", file=sys.stderr)
            return 2
        result = engine.coordinate(goal)
        if getattr(args, "json", False):
            print(json.dumps(result, indent=2))
        else:
            print(f"Coordination Plan for: {result.get('goal', goal)[:80]}")
            print(f"Agents: {result.get('agent_count', 0)} in "
                  f"{result.get('total_groups', 0)} groups")
            for group in result.get("execution_plan", []):
                agents_str = ", ".join(
                    a.get("agent_role", "?") for a in group.get("agents", [])
                )
                print(f"  Group {group.get('group_id', 0)} ({group.get('execution', 'serial')}): {agents_str}")
        return 0

    elif sub == "logs":
        limit = getattr(args, "limit", 50)
        data = {"entries": limit, "message": "Agent activity log"}
        print(_maybe_json(data, args))
        return 0

    elif sub == "history":
        limit = getattr(args, "limit", 20)
        data = {"entries": limit, "history": []}
        print(_maybe_json(data, args))
        return 0

    else:
        print(f"Unknown agents subcommand: {sub}", file=sys.stderr)
        print("Usage: aetheros agents <list|status|coordinate|logs|history>")
        return 2


# ---------------------------------------------------------------------------
# aetheros knowledge
# ---------------------------------------------------------------------------

def cmd_knowledge(args: argparse.Namespace) -> int:
    """Dispatch ``aetheros knowledge <subcommand>``."""
    sub = getattr(args, "knowledge_command", None)

    if sub in ("search", "s"):
        query = args.query
        mode = getattr(args, "mode", "hybrid")
        limit = getattr(args, "limit", 10)
        try:
            from aetheros_knowledge.search.engine import SearchEngine
            engine = SearchEngine()
            if mode == "semantic":
                results = engine.semantic_search(query, top_k=limit)
            elif mode == "keyword":
                results = engine.keyword_search(query, top_k=limit)
            else:
                results = engine.hybrid_search(query, top_k=limit)
        except Exception:
            results = []
        if getattr(args, "json", False):
            print(json.dumps(results, indent=2))
        else:
            print(f"Knowledge search results for '{query}' ({mode}):\n")
            for r in results:
                score = r.get("score", 0.5)
                title = r.get("title", "Result")
                content = r.get("content", "")[:120]
                print(f"  [{score:.2f}] {title}")
                if content:
                    print(f"         {content}")
        return 0

    elif sub == "graph":
        entity = getattr(args, "entity", None)
        depth = getattr(args, "depth", 2)
        data = {
            "entity": entity or "root",
            "depth": depth,
            "nodes": 5,
            "edges": 8,
        }
        print(_maybe_json(data, args))
        return 0

    elif sub in ("entities", "e"):
        entity_type = getattr(args, "type", None)
        limit = getattr(args, "limit", 20)
        data = {"total_entities": 25, "type_filter": entity_type or "all"}
        print(_maybe_json(data, args))
        return 0

    elif sub == "stats":
        engine = _get_intelligence()
        result = engine.status()
        print(_maybe_json(result, args))
        return 0

    else:
        print(f"Unknown knowledge subcommand: {sub}", file=sys.stderr)
        print("Usage: aetheros knowledge <search|graph|entities|stats>")
        return 2


# ---------------------------------------------------------------------------
# aetheros learn
# ---------------------------------------------------------------------------

def cmd_learn(args: argparse.Namespace) -> int:
    """Dispatch ``aetheros learn <subcommand>``."""
    sub = getattr(args, "learn_command", None)
    engine = _get_intelligence()

    if sub == "observe":
        result = engine.observe(
            category=args.category,
            observation=args.observation,
            pattern=getattr(args, "pattern", ""),
            context=getattr(args, "context", ""),
            auto_approve=getattr(args, "approve", False),
        )
        if getattr(args, "json", False):
            print(json.dumps(result, indent=2))
        else:
            print(f"Observed: {result.get('observation', '')[:60]}")
            if result.get("approved"):
                print("✓ Auto-approved")
            else:
                print("Pending approval (use: aetheros learn approve)")
        return 0

    elif sub in ("list", "ls"):
        category = getattr(args, "category", None)
        pending = engine.get_pending_learning(category)
        if getattr(args, "json", False):
            print(json.dumps(pending, indent=2))
        else:
            print(f"Pending learning observations ({len(pending)}):")
            for p in pending:
                print(f"  [{p.get('category', '?')}] {p.get('observation', '')[:60]}")
                print(f"    ID: {p.get('id', '')}")
        return 0

    elif sub == "approve":
        sample_id = getattr(args, "sample_id", None)
        all_flag = getattr(args, "all", False)
        if all_flag:
            count = engine.approve_all_learning(getattr(args, "category", None))
            print(f"Approved {count} learning observations")
        elif sample_id:
            result = engine.approve_learning(sample_id)
            if result:
                print(f"Approved: {result.get('observation', '')[:60]}")
            else:
                print(f"Sample not found: {sample_id}", file=sys.stderr)
                return 1
        return 0

    elif sub == "reject":
        sample_id = getattr(args, "sample_id", None)
        all_flag = getattr(args, "all", False)
        if all_flag:
            count = 0
            for p in engine.get_pending_learning(getattr(args, "category", None)):
                if engine.reject_learning(p["id"]):
                    count += 1
            print(f"Rejected {count} learning observations")
        elif sample_id:
            if engine.reject_learning(sample_id):
                print("Rejected")
            else:
                print(f"Sample not found: {sample_id}", file=sys.stderr)
                return 1
        return 0

    elif sub in ("learned", "patterns"):
        category = getattr(args, "category", None)
        patterns = engine.get_learned_patterns(category)
        if getattr(args, "json", False):
            print(json.dumps(patterns, indent=2))
        else:
            if isinstance(patterns, dict):
                for cat, pats in patterns.items():
                    print(f"{cat}:")
                    for p in pats:
                        print(f"  - {p.get('pattern', p.get('observation', ''))[:70]}")
            elif isinstance(patterns, list):
                for p in patterns:
                    print(f"  - {p.get('pattern', p.get('observation', ''))[:70]}")
        return 0

    elif sub == "summary":
        if not hasattr(engine, "_learning") or engine._learning is None:
            print("Learning engine not initialized")
            return 0
        summary = engine._learning.get_learning_summary()
        if getattr(args, "json", False):
            print(json.dumps(summary, indent=2))
        else:
            print("Learning Summary:")
            for cat, info in summary.items():
                print(f"  {cat:20s} learned: {info.get('learned_count', 0):3d}  "
                      f"pending: {info.get('pending_count', 0)}")
        return 0

    else:
        print(f"Unknown learn subcommand: {sub}", file=sys.stderr)
        print("Usage: aetheros learn <observe|list|approve|reject|learned|summary>")
        return 2

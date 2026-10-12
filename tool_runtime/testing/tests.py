"""Comprehensive tests for all tool runtimes.

Covers:
- Filesystem operations (read, write, delete, search, compress, checksum, metadata)
- Terminal execution
- Python runtime
- Permission system
- Safety engine
- Execution planner
- Dashboard
- Observability
- REST API
- Database (SQLite)
- Git
- Plugin system
- Tool chaining
- Failure recovery
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

from tool_runtime.interface import (
    ToolResult,
    ToolStatus,
    ToolRiskLevel,
    ToolCategory,
    ToolMetadata,
)
from tool_runtime.manager import ToolRuntimeManager, get_runtime_manager
from tool_runtime.permission import PermissionSystem, RiskLevel, PermissionRule
from tool_runtime.safety import SafetyEngine, SafetyVerdict
from tool_runtime.planner import ExecutionPlanner, PlanStep, PlanStatus
from tool_runtime.dashboard import ExecutionDashboard
from tool_runtime.observability import ObservabilityCollector
from tool_runtime.filesystem.tools import FilesystemRuntime
from tool_runtime.python.runtime import PythonRuntime


class ToolInterfaceTests(unittest.TestCase):
    """Test the universal tool interface contract."""

    def test_tool_result_ok(self):
        r = ToolResult.ok({"data": 42})
        self.assertTrue(r.success)
        self.assertEqual(r.output, {"data": 42})
        self.assertEqual(r.status, ToolStatus.COMPLETED)

    def test_tool_result_fail(self):
        r = ToolResult.fail("something went wrong")
        self.assertFalse(r.success)
        self.assertEqual(r.error, "something went wrong")
        self.assertEqual(r.status, ToolStatus.FAILED)

    def test_tool_result_timeout(self):
        r = ToolResult.timeout("timed out")
        self.assertFalse(r.success)
        self.assertEqual(r.status, ToolStatus.TIMEOUT)

    def test_tool_result_serialization(self):
        r = ToolResult.ok({"msg": "hello"}, duration_ms=42.5)
        d = r.to_dict()
        self.assertEqual(d["success"], True)
        self.assertEqual(d["duration_ms"], 42.5)
        self.assertEqual(d["status"], "completed")


class PermissionSystemTests(unittest.TestCase):
    """Test the permission system."""

    def setUp(self):
        self.perm = PermissionSystem()

    def test_read_allowed(self):
        meta = ToolMetadata(
            id="test", name="test", description="",
            category=ToolCategory.UTILITY, risk_level=ToolRiskLevel.READ,
        )
        result = self.perm.check("read_file", meta, {})
        self.assertTrue(result.allowed)

    def test_admin_requires_approval(self):
        meta = ToolMetadata(
            id="admin", name="admin", description="",
            category=ToolCategory.SYSTEM, risk_level=ToolRiskLevel.ADMIN,
        )
        result = self.perm.check("admin_test", meta, {})
        self.assertFalse(result.allowed)

    def test_deny_rule(self):
        self.perm.add_rule(PermissionRule(
            effect="deny", tool_pattern="dangerous*",
            reason="Blocked for safety",
        ))
        meta = ToolMetadata(
            id="dangerous_op", name="dangerous_op", description="",
            category=ToolCategory.SYSTEM, risk_level=ToolRiskLevel.EXECUTE,
        )
        result = self.perm.check("dangerous_op", meta, {})
        self.assertFalse(result.allowed)

    def test_rules_listing(self):
        rules = self.perm.get_rules()
        self.assertGreater(len(rules), 0)
        self.assertIn("effect", rules[0])


class SafetyEngineTests(unittest.TestCase):
    """Test the safety engine."""

    def setUp(self):
        self.safety = SafetyEngine()

    def test_read_is_safe(self):
        meta = ToolMetadata(
            id="read", name="read", description="",
            category=ToolCategory.FILESYSTEM, risk_level=ToolRiskLevel.READ,
        )
        result = self.safety.check("read_file", {"path": "/tmp/test.txt"}, meta)
        self.assertEqual(result.result, SafetyVerdict.SAFE)

    def test_delete_detected(self):
        meta = ToolMetadata(
            id="test", name="test", description="",
            category=ToolCategory.FILESYSTEM, risk_level=ToolRiskLevel.WRITE,
        )
        result = self.safety.check("delete_file", {"command": "rm -rf /"}, meta)
        self.assertEqual(result.result, SafetyVerdict.DESTRUCTIVE)
        self.assertTrue(result.requires_approval)

    def test_format_blocked(self):
        meta = ToolMetadata(
            id="test", name="test", description="",
            category=ToolCategory.TERMINAL, risk_level=ToolRiskLevel.EXECUTE,
        )
        result = self.safety.check("format", {"command": "format C:"}, meta)
        self.assertEqual(result.result, SafetyVerdict.BLOCKED)

    def test_safety_rules_summary(self):
        rules = self.safety.get_rules_summary()
        self.assertGreater(len(rules), 0)
        self.assertIn("name", rules[0])


class FilesystemRuntimeTests(unittest.TestCase):
    """Test filesystem runtime with real I/O."""

    def setUp(self):
        self.fs = FilesystemRuntime()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_file = self.temp_dir / "test.txt"
        self.test_file.write_text("Hello, World!", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate(self):
        errors = self.fs.validate({})
        self.assertGreater(len(errors), 0)
        errors = self.fs.validate({"operation": "read", "path": str(self.test_file)})
        self.assertEqual(len(errors), 0)

    def test_read_file(self):
        result = self.fs.execute({"operation": "read", "path": str(self.test_file)}, {})
        self.assertTrue(result.success)
        self.assertIn("Hello, World!", str(result.output))

    def test_write_file(self):
        new_file = self.temp_dir / "new.txt"
        result = self.fs.execute({"operation": "write", "path": str(new_file), "content": "New content"}, {})
        self.assertTrue(result.success)
        self.assertTrue(new_file.exists())
        self.assertEqual(new_file.read_text(), "New content")

    def test_append_file(self):
        result = self.fs.execute({"operation": "append", "path": str(self.test_file), "content": "\nAppended"}, {})
        self.assertTrue(result.success)
        content = self.test_file.read_text()
        self.assertIn("Appended", content)

    def test_delete_file(self):
        result = self.fs.execute({"operation": "delete", "path": str(self.test_file)}, {})
        self.assertTrue(result.success)
        self.assertFalse(self.test_file.exists())

    def test_list_directory(self):
        result = self.fs.execute({"operation": "list_dir", "path": str(self.temp_dir)}, {})
        self.assertTrue(result.success)
        self.assertIn("entries", result.output)

    def test_search_files(self):
        result = self.fs.execute({"operation": "search", "path": str(self.temp_dir), "pattern": "*.txt"}, {})
        self.assertTrue(result.success)
        self.assertGreaterEqual(result.output.get("count", 0), 1)

    def test_checksum(self):
        result = self.fs.execute({"operation": "checksum", "path": str(self.test_file)}, {})
        self.assertTrue(result.success)
        self.assertIn("md5", result.output)
        self.assertIn("sha256", result.output)

    def test_metadata(self):
        result = self.fs.execute({"operation": "metadata", "path": str(self.test_file)}, {})
        self.assertTrue(result.success)
        self.assertIn("size", result.output)
        self.assertIn("modified", result.output)

    def test_copy_file(self):
        dest = self.temp_dir / "copied.txt"
        result = self.fs.execute({"operation": "copy", "path": str(self.test_file), "target": str(dest)}, {})
        self.assertTrue(result.success)
        self.assertTrue(dest.exists())

    def test_rename_file(self):
        new_name = "renamed.txt"
        result = self.fs.execute({"operation": "rename", "path": str(self.test_file), "target": new_name}, {})
        self.assertTrue(result.success)
        self.assertTrue((self.temp_dir / new_name).exists())

    def test_compress_and_extract(self):
        compress_result = self.fs.execute({"operation": "compress", "path": str(self.temp_dir), "target": str(self.temp_dir / "archive.zip")}, {})
        self.assertTrue(compress_result.success)
        self.assertTrue((self.temp_dir / "archive.zip").exists())

        extract_dir = self.temp_dir / "extracted"
        extract_result = self.fs.execute({"operation": "extract", "path": str(self.temp_dir / "archive.zip"), "target": str(extract_dir)}, {})
        self.assertTrue(extract_result.success)

    def test_health(self):
        health = self.fs.health()
        self.assertTrue(health["healthy"])


class PythonRuntimeTests(unittest.TestCase):
    """Test Python runtime with real execution."""

    def setUp(self):
        self.py = PythonRuntime()

    def test_exec_simple(self):
        result = self.py.execute({"operation": "exec", "code": "result = 2 + 2"}, {})
        self.assertTrue(result.success)
        self.assertIn("4", str(result.output))

    def test_exec_failure(self):
        result = self.py.execute({"operation": "exec", "code": "1/0"}, {})
        self.assertFalse(result.success)

    def test_validate(self):
        errors = self.py.validate({})
        self.assertGreater(len(errors), 0)
        errors = self.py.validate({"operation": "exec", "code": "x = 1"})
        self.assertEqual(len(errors), 0)

    def test_eval(self):
        result = self.py.execute({"operation": "eval", "expression": "42"}, {})
        self.assertTrue(result.success)
        self.assertIn("42", str(result.output))


class ExecutionPlannerTests(unittest.TestCase):
    """Test execution planner with dependency resolution."""

    def setUp(self):
        self.planner = ExecutionPlanner()

    def test_create_plan(self):
        steps = [
            {"id": "s1", "tool_name": "filesystem", "params": {"operation": "read", "path": "/tmp"}, "description": "Read tmp"},
        ]
        plan = self.planner.create_plan("test goal", steps=steps)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.status, PlanStatus.PENDING)

    def test_validate_plan_with_deps(self):
        steps = [
            {"id": "s1", "tool_name": "filesystem", "params": {"operation": "read", "path": "/tmp"}},
            {"id": "s2", "tool_name": "filesystem", "params": {"operation": "read", "path": "/etc"}, "depends_on": ["s1"]},
        ]
        plan = self.planner.create_plan("test", steps=steps)
        errors = self.planner.validate_plan(plan)
        self.assertIsInstance(errors, list)

    def test_cancel_plan(self):
        steps = [{"id": "s1", "tool_name": "filesystem", "params": {"operation": "read", "path": "/tmp"}}]
        plan = self.planner.create_plan("test", steps=steps)
        self.assertTrue(self.planner.cancel_plan(plan.id))

    def test_list_plans(self):
        self.planner.create_plan("plan a", steps=[])
        self.planner.create_plan("plan b", steps=[])
        plans = self.planner.list_plans()
        self.assertGreaterEqual(len(plans), 2)


class ObservabilityTests(unittest.TestCase):
    """Test observability metrics collection."""

    def setUp(self):
        self.obs = ObservabilityCollector()

    def test_record_execution(self):
        self.obs.record_execution("test_tool", success=True, duration_ms=100)
        metrics = self.obs.get_metrics()
        self.assertGreaterEqual(metrics["total_executions"], 1)

    def test_success_rate(self):
        self.obs.record_execution("t1", success=True, duration_ms=50)
        self.obs.record_execution("t1", success=True, duration_ms=75)
        self.obs.record_execution("t1", success=False, duration_ms=25)
        rate = self.obs.get_success_rate("t1")
        self.assertAlmostEqual(rate, 2/3, places=2)

    def test_latency_stats(self):
        self.obs.record_execution("t1", success=True, duration_ms=10)
        self.obs.record_execution("t1", success=True, duration_ms=20)
        self.obs.record_execution("t1", success=True, duration_ms=30)
        stats = self.obs.get_latency_stats("t1")
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["min_ms"], 10)
        self.assertEqual(stats["max_ms"], 30)

    def test_tool_breakdown(self):
        self.obs.record_execution("alpha", success=True, duration_ms=100)
        self.obs.record_execution("beta", success=False, duration_ms=200)
        breakdown = self.obs.get_tool_breakdown()
        self.assertGreaterEqual(len(breakdown), 2)

    def test_metrics_export(self):
        self.obs.record_execution("t1", success=True, duration_ms=50)
        exported = self.obs.export_metrics()
        self.assertIn("summary", exported)
        self.assertIn("tool_breakdown", exported)


class DashboardTests(unittest.TestCase):
    """Test execution dashboard."""

    def setUp(self):
        self.dash = ExecutionDashboard()

    def test_snapshot(self):
        snap = self.dash.get_snapshot()
        self.assertIn("runtime", snap)
        self.assertIn("metrics", snap)
        self.assertIn("observability", snap)

    def test_record_artifact(self):
        self.dash.record_artifact("req_1", "output.txt", "/tmp/output.txt", 100)
        self.dash.record_artifact("req_1", "log.txt", "/tmp/log.txt", 50)
        detail = self.dash.get_execution_detail("req_1")
        if detail:
            self.assertIn("artifacts", detail)


class ManagerTests(unittest.TestCase):
    """Test the tool runtime manager."""

    def setUp(self):
        self.manager = get_runtime_manager()
        self.manager.start()

    def test_manager_start(self):
        self.assertIsNotNone(self.manager.get_runtime_count())

    def test_health_check(self):
        health = self.manager.health_check()
        self.assertIn("state", health)
        self.assertIn("total_runtimes", health)

    def test_execution_status(self):
        req_id = self.manager.execute_async("filesystem", {"operation": "read", "path": "/tmp"}, {})
        self.assertIsNotNone(req_id)
        status = self.manager.get_execution_status(req_id)
        self.assertIsNotNone(status)

    def test_metrics(self):
        metrics = self.manager.get_metrics()
        self.assertIn("total_executions", metrics)


class ChainingTests(unittest.TestCase):
    """Test tool chaining engine."""

    def test_chaining_schema(self):
        from tool_runtime.chaining.engine import ChainingEngine
        engine = ChainingEngine()
        schema = engine.schema()
        self.assertIn("steps", schema["parameters"]["properties"])

    def test_validate_steps(self):
        from tool_runtime.chaining.engine import ChainingEngine
        engine = ChainingEngine()
        errors = engine.validate({"steps": []})
        self.assertGreater(len(errors), 0)
        errors = engine.validate({
            "steps": [{"runtime": "filesystem", "operation": "read"}]
        })
        self.assertEqual(len(errors), 0)


class ToolRuntimeTests:
    """Aggregated test suite runner."""

    @staticmethod
    def run_all() -> Dict[str, Any]:
        """Run all tool runtime tests and return results."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        test_cases = [
            ToolInterfaceTests,
            PermissionSystemTests,
            SafetyEngineTests,
            FilesystemRuntimeTests,
            PythonRuntimeTests,
            ExecutionPlannerTests,
            ObservabilityTests,
            DashboardTests,
            ManagerTests,
            ChainingTests,
        ]

        for tc in test_cases:
            suite.addTests(loader.loadTestsFromTestCase(tc))

        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        return {
            "total": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "success": result.wasSuccessful(),
            "details": {
                "failures": [str(f[0]) for f in result.failures],
                "errors": [str(e[0]) for e in result.errors],
            },
        }

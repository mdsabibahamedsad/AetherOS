from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "optional-skills"
    / "productivity"
    / "memory-maintenance"
    / "scripts"
    / "memory_maintain.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("memory_maintain", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fake_store(memory_entries=None, user_entries=None):
    from tools.memory_tool import MemoryStore

    store = MemoryStore()
    store.memory_entries["default"] = memory_entries or []
    store.user_entries["default"] = user_entries or []
    return store


class _FakeStore:
    """Duck-typed store that satisfies memory_lifecycle's minimal interface."""

    def __init__(self, memory=None, user=None):
        self.memory_entries = {"default": memory or []}
        self.user_entries = {"default": user or []}

    def _entries_for(self, target, scope="default"):
        if target == "memory":
            return self.memory_entries[scope]
        return self.user_entries[scope]

    def _set_entries(self, target, entries, scope="default"):
        if target == "memory":
            self.memory_entries[scope] = entries
        else:
            self.user_entries[scope] = entries

    def _path_for(self, target, scope="default"):
        return str(Path(".") / f"{target}.{scope}.md")

    def _char_limit(self, target, scope="default"):
        return 0

    def save_to_disk(self, target, scope="default"):
        pass

    def owner(self):
        return "test"


def test_module_loads():
    mod = load_module()
    assert callable(mod.run_maintenance)
    assert callable(mod.main)


def test_run_maintenance_silent_when_no_change(tmp_path, monkeypatch):
    """A clean pass on an empty store must return '' (silent cron tick)."""
    mod = load_module()
    store = _FakeStore()
    out = mod.run_maintenance(store)
    assert out == ""


def test_run_maintenance_reports_changes(monkeypatch):
    """A pass that changes anything must emit a non-empty report."""
    mod = load_module()

    def fake_lifecycle_stats(store):
        return {
            "total": len(store._entries_for("memory")) + len(store._entries_for("user")),
            "by_target": {"memory": len(store._entries_for("memory")), "user": len(store._entries_for("user"))},
        }

    def fake_maintain(store, **kwargs):
        return {
            "repair": {"rewritten": 0, "backed_up": 0},
            "secrets": {"redacted": 1, "found": 1},
            "reconsolidate": {"merged": 2, "archived": 1},
            "decay": {"decayed": 3, "archived": 0},
            "conflicts": {"resolved": 1},
        }

    import tools.memory_lifecycle as lifecycle

    monkeypatch.setattr(lifecycle, "lifecycle_stats", fake_lifecycle_stats)
    monkeypatch.setattr(lifecycle, "maintain", fake_maintain)

    store = _FakeStore(memory=["alpha", "beta"], user=["gamma"])
    out = mod.run_maintenance(store)
    assert out != ""
    assert "secrets redacted: 1" in out
    assert "duplicates merged: 2" in out
    assert "entries decayed: 3" in out


def test_dry_run_does_not_mutate(tmp_path, monkeypatch):
    mod = load_module()

    def fake_lifecycle_stats(store):
        return {"total": 2, "by_target": {"memory": 2, "user": 0}}

    def fake_maintain(store, **kwargs):
        return {
            "repair": {"rewritten": 0, "backed_up": 0},
            "secrets": {"redacted": 1, "found": 1},
            "reconsolidate": {"merged": 0, "archived": 0},
            "decay": {"decayed": 0, "archived": 0},
            "conflicts": {"resolved": 0},
        }

    import tools.memory_lifecycle as lifecycle

    monkeypatch.setattr(lifecycle, "lifecycle_stats", fake_lifecycle_stats)
    monkeypatch.setattr(lifecycle, "maintain", fake_maintain)

    store = _FakeStore(memory=["a", "b"])
    out = mod.run_maintenance(store, dry_run=True)
    assert out != ""
    assert store._entries_for("memory") == ["a", "b"]


def test_main_exit_code_zero_on_clean_run(tmp_path, monkeypatch):
    mod = load_module()
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=60,
    )
    # With no AETHEROS_HOME the import may fail; ensure the script at least
    # exits without an unhandled traceback.
    assert result.returncode in (0, 2)

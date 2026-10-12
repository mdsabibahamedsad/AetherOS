"""Master-13 slice 2: filesystem watcher — detection, debounce, fail-closed roots."""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.events import reset_bus


@pytest.fixture(autouse=True)
def fresh_bus():
    reset_bus()
    yield
    reset_bus()


def _settings(root: Path, **overrides):
    base = {
        "allowed_roots": [str(root)],
        "poll_interval_seconds": 1.0,
        "debounce_seconds": 0.0,
        "max_files_per_root": 1000,
        "max_events_per_cycle": 50,
    }
    base.update(overrides)
    return base


class TestRootValidation:
    def test_outside_allowed_roots_rejected(self, tmp_path):
        from automation.file_watcher import FileWatcher

        other = tmp_path / "elsewhere"
        other.mkdir()
        watcher = FileWatcher([str(other)], settings=_settings(tmp_path / "data"))
        assert watcher.roots == []

    def test_inside_root_accepted(self, tmp_path):
        from automation.file_watcher import FileWatcher

        data = tmp_path / "data"
        data.mkdir()
        watcher = FileWatcher([str(data)], settings=_settings(data))
        assert len(watcher.roots) == 1
        assert Path(watcher.roots[0]).resolve() == data.resolve()

    def test_missing_root_rejected(self, tmp_path):
        from automation.file_watcher import FileWatcher

        ghost = tmp_path / "does-not-exist"
        watcher = FileWatcher([str(ghost)], settings=_settings(ghost))
        assert watcher.roots == []


class TestDetection:
    def test_baseline_then_created_modified_deleted(self, tmp_path):
        from automation.file_watcher import FileWatcher

        root = tmp_path / "watch"
        root.mkdir()
        target = root / "a.txt"

        watcher = FileWatcher([str(root)], settings=_settings(root))
        assert watcher.poll() == []          # baseline pass emits nothing

        target.write_text("hello")
        changes = watcher.poll()
        assert [(c["event"], c["path"]) for c in changes] == [("created", str(target))]

        target.write_text("hello!")
        changes = watcher.poll()
        assert [c["event"] for c in changes] == ["modified"]

        target.unlink()
        changes = watcher.poll()
        assert [c["event"] for c in changes] == ["deleted"]

    def test_debounce_coalesces_storm(self, tmp_path):
        from automation.file_watcher import FileWatcher

        root = tmp_path / "watch"
        root.mkdir()
        target = root / "b.csv"

        watcher = FileWatcher(
            [str(root)], settings=_settings(root, debounce_seconds=60.0)
        )
        watcher.poll()                        # baseline

        target.write_text("v1")
        watcher.poll()                        # created observed → pending
        target.write_text("v2")
        watcher.poll()                        # modify coalesces into same entry

        ready = watcher.flush_ready()
        assert ready == []                    # quiet period not elapsed yet

        # Age the pending entry past the debounce window.
        for entry in watcher._pending.values():
            entry["first_seen"] -= 61.0
        ready = watcher.flush_ready()
        assert len(ready) == 1                # one event for the whole storm

    def test_emit_changes_publishes_normalized_events(self, tmp_path):
        from automation.events import get_bus
        from automation.file_watcher import FileWatcher, emit_changes

        root = tmp_path / "watch"
        root.mkdir()

        watcher = FileWatcher([str(root)], settings=_settings(root))
        watcher.poll()
        (root / "c.log").write_text("x")
        watcher.poll()
        count = emit_changes(watcher.flush_ready())

        assert count == 1
        recent = get_bus().recent(limit=5)
        assert recent[0]["event_type"] == "file.created"
        assert recent[0]["trust"] == "external"
        assert recent[0]["payload"]["path"].endswith("c.log")

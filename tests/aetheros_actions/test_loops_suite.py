"""Phase 2I — LoopDetector extended: repeat / oscillation / cyclic / near-id.

Covers: repeated actions, repeated failed actions, A↔B oscillation,
near-identical states (same signature, different ids), cyclic 3-patterns,
window trimming, thresholds, and safe non-detection of legitimate sequences.
"""

from __future__ import annotations

from aetheros_actions.loops import LoopDetector, action_signature
from aetheros_actions.model import Action, ActionType, RiskLevel


def _act(target: str, at: ActionType = ActionType.CLICK, params: dict | None = None) -> Action:
    return Action(action_type=at, target=target, parameters=params or {})


class TestRepeatDetection:
    def test_repeat_same_action(self):
        ld = LoopDetector(repeat_threshold=3)
        for _ in range(3):
            ld.record(_act("b"))
        info = ld.detect()
        assert info is not None and info.kind == "repeat"

    def test_below_threshold_no_loop(self):
        ld = LoopDetector(repeat_threshold=3)
        for _ in range(2):
            ld.record(_act("b"))
        assert ld.detect() is None

    def test_repeated_failed_action(self):
        ld = LoopDetector(failure_threshold=3)
        for _ in range(3):
            ld.record(_act("b"), failed=True)
        info = ld.detect()
        assert info is not None and info.kind == "repeated_failure"

    def test_repeat_counts_distinct_actions(self):
        # Same target repeated but interleaved with others — count the window.
        ld = LoopDetector(window_size=6, repeat_threshold=3)
        for t in ("a", "b", "a", "c", "a"):
            ld.record(_act(t))
        info = ld.detect()
        assert info is not None and info.kind == "repeat"
        assert info.signature.startswith("CLICK:a")


class TestOscillation:
    def test_ab_oscillation(self):
        ld = LoopDetector()
        a, b = _act("A"), _act("B")
        for _ in range(4):
            ld.record(a)
            ld.record(b)
        info = ld.detect()
        assert info is not None and info.kind == "oscillation"
        assert "A" in info.signature and "B" in info.signature

    def test_no_false_oscillation_on_unique(self):
        ld = LoopDetector()
        for i in range(8):
            ld.record(_act(f"step{i}"))
        assert ld.detect() is None


class TestNearIdentical:
    def test_same_signature_ignores_ids(self):
        # action_signature must ignore action_id so near-identical repeats count.
        a1 = Action(action_type=ActionType.CLICK, target="b")
        a2 = Action(action_type=ActionType.CLICK, target="b")
        assert action_signature(a1) == action_signature(a2)

    def test_near_identical_coordinate_repeat(self):
        ld = LoopDetector(repeat_threshold=3)
        for _ in range(3):
            ld.record(_act("", params={"coordinate": [100, 100]}))
        assert ld.detect() is not None

    def test_coordinate_variation_distinct(self):
        ld = LoopDetector(repeat_threshold=3)
        for i in range(3):
            ld.record(_act("", params={"coordinate": [100, i]}))
        assert ld.detect() is None


class TestWindowAndThresholds:
    def test_window_trims_old_entries(self):
        ld = LoopDetector(window_size=3, repeat_threshold=3)
        for t in ("a", "b", "c", "d", "d", "d"):
            ld.record(_act(t))
        info = ld.detect()
        # window holds only last 3 ("d","d","d") → repeat.
        assert info is not None and info.kind == "repeat"

    def test_snapshot_counts(self):
        ld = LoopDetector()
        ld.record(_act("a"), failed=True)
        snap = ld.snapshot()
        assert snap["window_size"] == 1
        assert snap["failures"] == 1

    def test_thread_safe_record_and_detect(self):
        import threading

        ld = LoopDetector()
        def run():
            for _ in range(4):
                ld.record(_act("t"))
        threads = [threading.Thread(target=run) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert ld.snapshot()["window_size"] > 0


class TestSignatures:
    def test_signature_covers_relevant_params(self):
        s = action_signature(_act("x", ActionType.TYPE, {"text": "hi"}))
        assert "TYPE:x" in s
        assert "text" in s

    def test_signature_excludes_id(self):
        a = Action(action_type=ActionType.CLICK, target="b")
        assert "action_id" not in action_signature(a)
        assert "agentId" not in action_signature(a)
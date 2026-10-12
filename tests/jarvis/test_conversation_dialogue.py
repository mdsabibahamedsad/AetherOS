"""Tests for conversation modes and dialogue (aetheros_jarvis)."""

from aetheros_jarvis.conversation import ConversationManager
from aetheros_jarvis.dialogue import DialogueManager
from aetheros_jarvis.models import ConversationMode, Utterance


class TestConversationManager:
    def test_default_mode_is_mixed(self):
        cm = ConversationManager()
        assert cm.mode == ConversationMode.MIXED

    def test_text_only_never_listens_or_speaks(self):
        cm = ConversationManager(ConversationMode.TEXT_ONLY)
        assert cm.should_listen() is False
        assert cm.should_speak() is False

    def test_off_mode(self):
        cm = ConversationManager(ConversationMode.OFF)
        assert cm.should_listen() is False
        assert cm.should_speak() is False

    def test_push_to_talk_does_not_listen_by_default(self):
        cm = ConversationManager(ConversationMode.PUSH_TO_TALK)
        assert cm.should_listen() is False
        assert cm.should_speak() is True

    def test_hands_free_keeps_channel_open(self):
        cm = ConversationManager(ConversationMode.HANDS_FREE)
        assert cm.hands_free()
        assert cm.listens_for_follow_up()
        assert cm.can_interrupt()
        assert cm.should_listen() is True

    def test_continuous_mode(self):
        cm = ConversationManager(ConversationMode.CONTINUOUS)
        assert cm.continuous()
        assert cm.listens_for_follow_up()

    def test_turn_lifecycle(self):
        cm = ConversationManager()
        cm.start_turn(Utterance(text="hello", source="text"))
        assert cm.turn_count == 1
        assert cm.should_listen() is True
        cm.finish_turn()
        assert cm.turn_count == 1
        assert cm.should_listen() is True  # mixed mode re-listens after turn

    def test_speaking_stops_listening(self):
        cm = ConversationManager()
        cm.mark_speaking(True)
        assert cm.should_listen() is False
        cm.mark_listening(True)
        assert cm.should_listen() is True

    def test_set_mode(self):
        cm = ConversationManager()
        cm.set_mode(ConversationMode.VOICE_ONLY)
        assert cm.mode == ConversationMode.VOICE_ONLY
        assert cm.should_listen() is True
        assert cm.should_speak() is True

    def test_snapshot(self):
        cm = ConversationManager(ConversationMode.CONTINUOUS)
        snap = cm.snapshot()
        assert snap["mode"] == "continuous"
        assert snap["turn_count"] == 0


class TestDialogueManager:
    def test_add_turns_and_recent(self):
        dm = DialogueManager(max_turns=3)
        dm.user("first")
        dm.assistant("reply")
        dm.user("second")
        dm.user("third")
        turns = dm.recent()
        assert [t.text for t in turns] == ["reply", "second", "third"]

    def test_bounded_buffer(self):
        dm = DialogueManager(max_turns=2)
        for i in range(5):
            dm.user(f"msg {i}")
        assert len(dm.recent(10)) == 2

    def test_last_user_text_and_topic(self):
        dm = DialogueManager()
        dm.user("What is the status of project X?")
        dm.assistant("Checking.")
        dm.user("And the tests?")
        assert dm.last_user_text() == "And the tests?"
        assert dm.last_topic() == "And the tests?"

    def test_follow_up_heuristic(self):
        dm = DialogueManager()
        assert dm.is_follow_up("and the second one?")
        assert dm.is_follow_up("what about the rest?")
        assert not dm.is_follow_up("please summarize the entire project history for me now")
        assert not dm.is_follow_up("")

    def test_clarification_cycle(self):
        dm = DialogueManager()
        assert dm.pending_clarification is None
        dm.request_clarification("Which repository do you mean?")
        assert dm.pending_clarification == "Which repository do you mean?"
        dm.resolve_clarification()
        assert dm.pending_clarification is None

    def test_corrections_recorded_and_bounded(self):
        dm = DialogueManager()
        for i in range(15):
            dm.record_correction(f"old{i}", f"new{i}")
        assert len(dm.corrections) == 10

    def test_needs_clarification(self):
        dm = DialogueManager()
        assert dm.needs_clarification("it")
        assert dm.needs_clarification("yes")
        assert dm.needs_clarification("")
        assert not dm.needs_clarification("the second test file please")

    def test_snapshot(self):
        dm = DialogueManager()
        dm.user("hello")
        snap = dm.snapshot()
        assert snap["turn_count"] == 1
        assert snap["last_topic"] == "hello"

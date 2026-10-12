from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

import json
from datetime import datetime, timedelta

import pytest

from aetheros_automation.communications import (
    ProviderManager, ProviderConnection, ConnectionStatus, ProviderType, AuthMethod, ProviderCapabilities,
    AuthManager, OAuthFlow, OAuthToken, TokenStatus,
    UnifiedInbox, UnifiedMessage, InboxFilter, MessageType, MessagePriority,
    ContactManager, UnifiedContact, ContactLink,
    MessageScheduler, ScheduledMessage, ScheduleRecurrence, ScheduledMessageStatus,
    CommsAIAssistant, ReplyStyle, DraftResult, AssistantContext,
    MessageAutomationEngine, AutomationTrigger, AutomationAction, AutomationRule,
    NotificationManager, NotificationRule as NotifRule, NotificationCategory, NotificationPriority,
    PrivacyManager, PrivacySettings, ProcessingScope, DataRetentionPolicy,
)


@pytest.fixture
def tmp_storage():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestProviderManager:
    def test_register_and_list(self, tmp_storage):
        pm = ProviderManager(tmp_storage)
        conn = ProviderConnection(id="tg1", provider=ProviderType.TELEGRAM, label="My Telegram", auth_method=AuthMethod.BOT_TOKEN)
        pm.register_connection(conn)
        assert len(pm.list_connections()) == 1
        assert pm.get_connection("tg1") is not None

    def test_get_active_connections(self, tmp_storage):
        pm = ProviderManager(tmp_storage)
        pm.register_connection(ProviderConnection(id="a", provider=ProviderType.TELEGRAM, label="A", auth_method=AuthMethod.OAUTH, status=ConnectionStatus.CONNECTED))
        pm.register_connection(ProviderConnection(id="b", provider=ProviderType.DISCORD, label="B", auth_method=AuthMethod.BOT_TOKEN, status=ConnectionStatus.DISCONNECTED))
        active = pm.get_active_connections()
        assert len(active) == 1
        assert active[0].id == "a"

    def test_set_status(self, tmp_storage):
        pm = ProviderManager(tmp_storage)
        pm.register_connection(ProviderConnection(id="t1", provider=ProviderType.TELEGRAM, label="T", auth_method=AuthMethod.BOT_TOKEN))
        pm.set_connection_status("t1", ConnectionStatus.CONNECTED)
        assert pm.get_connection("t1").status == ConnectionStatus.CONNECTED

    def test_remove_connection(self, tmp_storage):
        pm = ProviderManager(tmp_storage)
        pm.register_connection(ProviderConnection(id="x", provider=ProviderType.TELEGRAM, label="X", auth_method=AuthMethod.OAUTH))
        assert pm.remove_connection("x") is True
        assert pm.get_connection("x") is None

    def test_provider_capabilities(self, tmp_storage):
        pm = ProviderManager(tmp_storage)
        tg_caps = pm.get_provider_capabilities(ProviderType.TELEGRAM)
        assert tg_caps.send_files is True
        assert tg_caps.send_images is True
        sms_caps = pm.get_provider_capabilities(ProviderType.SMS)
        assert sms_caps.send_files is False


class TestAuthManager:
    def test_register_auth_config(self, tmp_storage):
        am = AuthManager(tmp_storage)
        cid = am.register_auth_config(am.get_provider_auth_config("telegram"))
        assert cid is not None
        assert am.get_auth_config(cid) is not None

    def test_store_and_get_token(self, tmp_storage):
        am = AuthManager(tmp_storage)
        token = OAuthToken(access_token="abc123", provider="telegram", account_id="acc1")
        tid = am.store_token(token)
        retrieved = am.get_token(tid)
        assert retrieved is not None
        assert retrieved.access_token == "abc123"

    def test_revoke_token(self, tmp_storage):
        am = AuthManager(tmp_storage)
        tid = am.store_token(OAuthToken(access_token="tok", provider="discord", account_id="acc2"))
        assert am.revoke_token(tid) is True
        assert am.get_token(tid).status == TokenStatus.REVOKED

    def test_clear_account_tokens(self, tmp_storage):
        am = AuthManager(tmp_storage)
        am.store_token(OAuthToken(access_token="a", provider="telegram", account_id="acc1"))
        am.store_token(OAuthToken(access_token="b", provider="telegram", account_id="acc1"))
        am.store_token(OAuthToken(access_token="c", provider="discord", account_id="acc2"))
        assert am.clear_account_tokens("acc1") == 2
        assert len(am.get_tokens_for_account("acc1")) == 0

    def test_get_provider_auth_config(self, tmp_storage):
        am = AuthManager(tmp_storage)
        cfg = am.get_provider_auth_config("gmail")
        assert cfg.provider == "gmail"
        assert "gmail.modify" in " ".join(cfg.scopes)


class TestUnifiedInbox:
    def test_add_message(self, tmp_storage):
        inbox = UnifiedInbox(tmp_storage)
        msg = UnifiedMessage(id="m1", provider="telegram", account_id="a1", conversation_id="c1", sender_id="s1", sender_name="Alice", content="Hello", timestamp=datetime.now(), direction="incoming", status="sent")
        inbox.add_message(msg)
        assert len(inbox.get_conversation_messages("c1")) == 1
        assert inbox.unread_count() == 1

    def _now(self):
        from datetime import datetime
        return datetime.now()

    def test_mark_read(self, tmp_storage):
        inbox = UnifiedInbox(tmp_storage)
        msg = UnifiedMessage(id="m1", provider="telegram", account_id="a1", conversation_id="c1", sender_id="s1", sender_name="Alice", content="Hello", timestamp=datetime.now(), direction="incoming", status="sent")
        inbox.add_message(msg)
        inbox.add_message(UnifiedMessage(id="m2", provider="telegram", account_id="a1", conversation_id="c1", sender_id="s2", sender_name="Bob", content="Hi", timestamp=datetime.now(), direction="incoming", status="sent"))
        assert inbox.unread_count() == 2
        inbox.mark_conversation_read("c1")
        assert inbox.unread_count() == 0

    def test_filter_unread(self, tmp_storage):
        inbox = UnifiedInbox(tmp_storage)
        inbox.add_message(UnifiedMessage(id="m1", provider="telegram", account_id="a1", conversation_id="c1", sender_id="s1", sender_name="A", content="Read", timestamp=datetime.now(), direction="incoming", status="sent", read=True))
        inbox.add_message(UnifiedMessage(id="m2", provider="telegram", account_id="a1", conversation_id="c1", sender_id="s2", sender_name="B", content="Unread", timestamp=datetime.now(), direction="incoming", status="sent"))
        msgs = inbox.filter_messages(InboxFilter.UNREAD)
        assert len(msgs) == 1
        assert msgs[0].content == "Unread"

    def test_filter_by_provider(self, tmp_storage):
        inbox = UnifiedInbox(tmp_storage)
        inbox.add_message(UnifiedMessage(id="m1", provider="telegram", account_id="a1", conversation_id="c1", sender_id="s1", sender_name="A", content="TG msg", timestamp=datetime.now(), direction="incoming", status="sent"))
        inbox.add_message(UnifiedMessage(id="m2", provider="gmail", account_id="a1", conversation_id="c2", sender_id="s2", sender_name="B", content="Email msg", timestamp=datetime.now(), direction="incoming", status="sent"))
        msgs = inbox.filter_messages(InboxFilter.EMAIL)
        assert len(msgs) == 1
        assert msgs[0].provider == "gmail"

    def test_search(self, tmp_storage):
        inbox = UnifiedInbox(tmp_storage)
        inbox.add_message(UnifiedMessage(id="m1", provider="telegram", account_id="a1", conversation_id="c1", sender_id="s1", sender_name="Alice", content="Project meeting tomorrow", timestamp=datetime.now(), direction="incoming", status="sent"))
        inbox.add_message(UnifiedMessage(id="m2", provider="telegram", account_id="a1", conversation_id="c1", sender_id="s2", sender_name="Bob", content="Lunch plans", timestamp=datetime.now(), direction="incoming", status="sent"))
        msgs = inbox.search_messages("meeting")
        assert len(msgs) == 1

    def test_toggle_important(self, tmp_storage):
        inbox = UnifiedInbox(tmp_storage)
        inbox.add_message(UnifiedMessage(id="m1", provider="telegram", account_id="a1", conversation_id="c1", sender_id="s1", sender_name="A", content="Important!", timestamp=datetime.now(), direction="incoming", status="sent"))
        inbox.toggle_important("m1")
        assert inbox.filter_messages(InboxFilter.IMPORTANT)[0].id == "m1"


class TestContactManager:
    def test_add_and_list(self, tmp_storage):
        cm = ContactManager(tmp_storage)
        contact = UnifiedContact(id="c1", name="John Doe", email="john@example.com")
        cm.add_contact(contact)
        assert len(cm.list_contacts()) == 1

    def test_search(self, tmp_storage):
        cm = ContactManager(tmp_storage)
        cm.add_contact(UnifiedContact(id="c1", name="Alice", email="alice@test.com"))
        cm.add_contact(UnifiedContact(id="c2", name="Bob", email="bob@test.com"))
        results = cm.search_contacts("alice")
        assert len(results) == 1

    def test_add_link(self, tmp_storage):
        cm = ContactManager(tmp_storage)
        cm.add_contact(UnifiedContact(id="c1", name="Multi"))
        link = ContactLink(provider="telegram", account_id="tg_1", username="@multi")
        assert cm.add_link_to_contact("c1", link) is True
        assert len(cm.get_contact("c1").links) == 1

    def test_merge_contacts(self, tmp_storage):
        cm = ContactManager(tmp_storage)
        cm.add_contact(UnifiedContact(id="p", name="Primary", email="p@test.com", phone="+111", tags=["work"]))
        cm.add_contact(UnifiedContact(id="s", name="Secondary", phone="+222", tags=["friend"]))
        merged = cm.merge_contacts("p", "s")
        assert merged is not None
        assert merged.name == "Primary"
        assert merged.phone == "+111"
        assert set(merged.tags) == {"work", "friend"}
        assert len(cm.list_contacts()) == 1

    def test_find_by_provider_account(self, tmp_storage):
        cm = ContactManager(tmp_storage)
        cm.add_contact(UnifiedContact(id="c1", name="Test", links=[ContactLink(provider="slack", account_id="sl1", username="@test")]))
        found = cm.find_by_provider_account("slack", "sl1")
        assert found is not None
        assert found.name == "Test"


class TestMessageScheduler:
    def test_schedule_and_list(self, tmp_storage):
        sched = MessageScheduler(tmp_storage)
        msg = ScheduledMessage(id="s1", provider="telegram", account_id="a1", recipient_id="@j", recipient_name="John", content="Hello!", scheduled_at=datetime.now())
        sched.schedule(msg)
        assert len(sched.list_scheduled()) == 1

    def _now(self):
        from datetime import datetime, timedelta
        return datetime.now() + timedelta(hours=1)

    def test_cancel(self, tmp_storage):
        sched = MessageScheduler(tmp_storage)
        msg = ScheduledMessage(id="s1", provider="telegram", account_id="a1", recipient_id="@j", recipient_name="John", content="Hi", scheduled_at=datetime.now(), status=ScheduledMessageStatus.SCHEDULED)
        sched.schedule(msg)
        assert sched.cancel("s1") is True
        assert sched.list_scheduled() == []

    def test_pause_resume(self, tmp_storage):
        sched = MessageScheduler(tmp_storage)
        msg = ScheduledMessage(id="s1", provider="telegram", account_id="a1", recipient_id="@j", recipient_name="John", content="Hi", scheduled_at=datetime.now(), status=ScheduledMessageStatus.SCHEDULED)
        sched.schedule(msg)
        sched.pause("s1")
        assert sched.list_scheduled()[0].status == ScheduledMessageStatus.PAUSED
        sched.resume("s1")
        assert sched.list_scheduled()[0].status == ScheduledMessageStatus.SCHEDULED

    def test_reschedule(self, tmp_storage):
        sched = MessageScheduler(tmp_storage)
        from datetime import datetime, timedelta
        original = datetime.now() + timedelta(hours=2)
        new_time = datetime.now() + timedelta(days=1)
        msg = ScheduledMessage(id="s1", provider="telegram", account_id="a1", recipient_id="@j", recipient_name="John", content="Hi", scheduled_at=original, status=ScheduledMessageStatus.SCHEDULED)
        sched.schedule(msg)
        sched.reschedule("s1", new_time)
        assert sched.list_scheduled()[0].scheduled_at == new_time

    def test_mark_sent(self, tmp_storage):
        sched = MessageScheduler(tmp_storage)
        msg = ScheduledMessage(id="s1", provider="telegram", account_id="a1", recipient_id="@j", recipient_name="John", content="Hi", scheduled_at=datetime.now(), status=ScheduledMessageStatus.SCHEDULED)
        sched.schedule(msg)
        sched.mark_sent("s1")
        assert sched.list_scheduled() == []

    def test_approve(self, tmp_storage):
        sched = MessageScheduler(tmp_storage)
        msg = ScheduledMessage(id="s1", provider="telegram", account_id="a1", recipient_id="@j", recipient_name="John", content="Hi", scheduled_at=datetime.now(), status=ScheduledMessageStatus.SCHEDULED, require_approval=True)
        sched.schedule(msg)
        assert sched.approve("s1") is True


class TestCommsAIAssistant:
    def setup_method(self):
        self.ai = CommsAIAssistant()

    def test_generate_draft_professional(self):
        context = AssistantContext(provider="telegram", conversation_id="c1", messages=[{"content": "Can you help?", "sender_name": "Alice"}], contact_name="Alice")
        result = self.ai.generate_draft(context, ReplyStyle.PROFESSIONAL)
        assert "Dear Alice" in result.content
        assert result.requires_approval is True

    def test_generate_draft_casual(self):
        context = AssistantContext(provider="telegram", conversation_id="c1", messages=[{"content": "See you later!", "sender_name": "Bob"}], contact_name="Bob")
        result = self.ai.generate_draft(context, ReplyStyle.CASUAL)
        assert "Hey Bob" in result.content

    def test_generate_draft_short(self):
        context = AssistantContext(provider="telegram", conversation_id="c1", messages=[{"content": "Urgent question?", "sender_name": "Charlie"}], contact_name="Charlie")
        result = self.ai.generate_draft(context, ReplyStyle.SHORT)
        assert len(result.content) < 200

    def test_summarize_conversation(self):
        messages = [
            {"content": "Hello everyone", "sender_name": "Alice"},
            {"content": "Hi Alice, important update on the project", "sender_name": "Bob"},
            {"content": "Thanks Bob, I will review it tonight", "sender_name": "Alice"},
        ]
        summary = self.ai.summarize_conversation(messages, "c1")
        assert summary.message_count == 3
        assert "Alice" in summary.participants
        assert "Bob" in summary.participants

    def test_extract_tasks(self):
        messages = [
            {"content": "I will submit the report by Friday", "sender_name": "Alice", "id": "m1"},
            {"content": "Please review my code changes", "sender_name": "Bob", "id": "m2"},
        ]
        tasks = self.ai.extract_tasks(messages)
        assert len(tasks) >= 2

    def test_detect_urgent(self):
        messages = [
            {"content": "This is urgent, please respond ASAP", "sender_name": "Alice"},
            {"content": "Just checking in", "sender_name": "Bob"},
        ]
        urgent = self.ai.detect_urgent_messages(messages)
        assert len(urgent) == 1

    def test_find_pending_requests(self):
        messages = [
            {"content": "Can you send me the file?", "sender_name": "Alice", "id": "m1"},
            {"content": "Please update the documentation", "sender_name": "Bob", "id": "m2"},
        ]
        pending = self.ai.find_pending_requests(messages)
        assert len(pending) >= 2

    def test_classify_priority(self):
        messages = [
            {"content": "URGENT: Server is down!"},
            {"content": "Important deadline reminder"},
            {"content": "Free offer!!! Click now"},
            {"content": "Just saying hi"},
        ]
        classified = self.ai.classify_priority(messages)
        priorities = {c["priority"] for c in classified}
        assert "urgent" in priorities
        assert "spam" in priorities
        assert "normal" in priorities

    def test_translate_message(self):
        result = self.ai.translate_message("Hello world", "spanish")
        assert "Traducción" in result

    def test_clear_history(self):
        context = AssistantContext(provider="telegram", conversation_id="c1", messages=[{"content": "Hi", "sender_name": "A"}])
        self.ai.generate_draft(context, ReplyStyle.PROFESSIONAL)
        self.ai.summarize_conversation([{"content": "Hi", "sender_name": "A"}], "c1")
        self.ai.clear_history()
        assert len(self.ai._draft_history) == 0
        assert len(self.ai._summary_cache) == 0


class TestMessageAutomationEngine:
    def _make_rule(self, **kwargs) -> AutomationRule:
        defaults = dict(id="r1", name="Test Rule", provider="all", trigger=AutomationTrigger.MESSAGE_RECEIVED, action=AutomationAction.SEND_REPLY)
        defaults.update(kwargs)
        return AutomationRule(**defaults)

    def test_add_and_list_rules(self, tmp_storage):
        eng = MessageAutomationEngine(tmp_storage)
        eng.add_rule(self._make_rule())
        assert len(eng.list_rules()) == 1

    def test_update_rule(self, tmp_storage):
        eng = MessageAutomationEngine(tmp_storage)
        eng.add_rule(self._make_rule())
        assert eng.update_rule("r1", enabled=False) is True
        assert eng.get_rule("r1").enabled is False

    def test_remove_rule(self, tmp_storage):
        eng = MessageAutomationEngine(tmp_storage)
        eng.add_rule(self._make_rule())
        assert eng.remove_rule("r1") is True
        assert eng.get_rule("r1") is None

    def test_keyword_matching(self, tmp_storage):
        eng = MessageAutomationEngine(tmp_storage)
        eng.add_rule(self._make_rule(id="r1", name="Keyword Rule", trigger=AutomationTrigger.KEYWORD_DETECTED, trigger_config={"keywords": ["urgent", "asap"]}))
        matched = eng.evaluate("telegram", {"content": "This is urgent!", "sender_id": "s1"})
        assert len(matched) == 1
        matched2 = eng.evaluate("telegram", {"content": "Just saying hi", "sender_id": "s1"})
        assert len(matched2) == 0

    def test_sender_matching(self, tmp_storage):
        eng = MessageAutomationEngine(tmp_storage)
        eng.add_rule(self._make_rule(id="r1", name="Sender Rule", trigger=AutomationTrigger.SENDER_MATCH, trigger_config={"sender_ids": ["known_user"]}))
        matched = eng.evaluate("telegram", {"content": "Hello", "sender_id": "known_user"})
        assert len(matched) == 1
        matched2 = eng.evaluate("telegram", {"content": "Hello", "sender_id": "unknown"})
        assert len(matched2) == 0

    def test_record_execution(self, tmp_storage):
        eng = MessageAutomationEngine(tmp_storage)
        eng.add_rule(self._make_rule())
        exec = eng.record_execution("r1", "telegram", "message_received", "completed", "Hello", "Reply ok")
        assert exec.rule_id == "r1"
        assert exec.status == "completed"

    def test_approve_execution(self, tmp_storage):
        eng = MessageAutomationEngine(tmp_storage)
        eng.add_rule(self._make_rule())
        exec = eng.record_execution("r1", "telegram", "message_received", "pending", "Hello", "", "", True)
        assert eng.approve_execution(exec.id) is True
        assert eng.get_pending_approvals() == []

    def test_cooldown(self, tmp_storage):
        import time
        eng = MessageAutomationEngine(tmp_storage)
        eng.add_rule(self._make_rule(id="r1", cooldown_seconds=3600))
        matched = eng.evaluate("telegram", {"content": "Hi", "sender_id": "s1"})
        assert len(matched) == 1


class TestNotificationManager:
    def test_notify(self, tmp_storage):
        nm = NotificationManager(tmp_storage)
        notif = nm.notify("Test", "Body", NotificationCategory.MESSAGE)
        assert notif is not None
        assert notif.title == "Test"
        assert len(nm.get_unread()) == 1

    def test_mark_read(self, tmp_storage):
        nm = NotificationManager(tmp_storage)
        nm.notify("Test", "Body")
        nm.mark_read(nm.get_unread()[0].id)
        assert len(nm.get_unread()) == 0

    def test_mark_all_read(self, tmp_storage):
        nm = NotificationManager(tmp_storage)
        nm.notify("A", "B")
        nm.notify("C", "D")
        nm.mark_all_read()
        assert len(nm.get_unread()) == 0

    def test_clear(self, tmp_storage):
        nm = NotificationManager(tmp_storage)
        nm.notify("Test", "Body")
        nm.clear_all()
        assert len(nm.get_recent()) == 0

    def test_rules(self, tmp_storage):
        nm = NotificationManager(tmp_storage)
        rules = nm.get_rules()
        assert len(rules) >= 5
        nm.update_rule(rules[0].id, enabled=False)
        assert nm.get_rules()[0].enabled is False


class TestPrivacyManager:
    def test_default_settings(self, tmp_storage):
        pm = PrivacyManager(tmp_storage)
        settings = pm.get_settings()
        assert settings.ai_processing_enabled is True
        assert settings.ai_processing_provider == ProcessingScope.LOCAL_ONLY

    def test_update_settings(self, tmp_storage):
        pm = PrivacyManager(tmp_storage)
        pm.update_settings(ai_processing_enabled=False, cloud_sync_enabled=True)
        settings = pm.get_settings()
        assert settings.ai_processing_enabled is False
        assert settings.cloud_sync_enabled is True

    def test_register_account_access(self, tmp_storage):
        pm = PrivacyManager(tmp_storage)
        pm.register_account_access("telegram", "My Telegram", ["read", "send"])
        accounts = pm.get_connected_accounts()
        assert len(accounts) == 1
        assert accounts[0].provider == "telegram"

    def test_remove_account(self, tmp_storage):
        pm = PrivacyManager(tmp_storage)
        pm.register_account_access("telegram", "TG", ["read"])
        assert pm.remove_account("telegram") is True
        assert len(pm.get_connected_accounts()) == 0

    def test_audit_log(self, tmp_storage):
        pm = PrivacyManager(tmp_storage)
        pm.log_access("send", "telegram", "Sent message to @john")
        pm.log_access("read", "gmail", "Read inbox")
        log = pm.get_audit_log()
        assert len(log) == 2

    def test_can_process_with_ai(self, tmp_storage):
        pm = PrivacyManager(tmp_storage)
        assert pm.can_process_with_ai() is True
        pm.update_settings(ai_processing_enabled=False)
        assert pm.can_process_with_ai() is False

    def test_retention_days(self, tmp_storage):
        pm = PrivacyManager(tmp_storage)
        assert pm.get_data_retention_days() == 90
        pm.update_settings(data_retention=DataRetentionPolicy.KEEP_30_DAYS)
        assert pm.get_data_retention_days() == 30

    def test_ai_processing_summary(self, tmp_storage):
        pm = PrivacyManager(tmp_storage)
        summary = pm.get_ai_processing_summary()
        assert summary["enabled"] is True
        assert summary["scope"] == "local_only"

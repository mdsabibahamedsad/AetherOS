"""Tests for the /folder, /pin, and /import slash commands.

Verifies that:
- /folder assigns, lists, and clears session folders (current + explicit session)
- /pin pins and unpins sessions, defaults to on
- /import reads a session export (JSON / JSONL) and creates a copy
- All three degrade gracefully when the session DB is unavailable
"""

import json
import os
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def session_db(tmp_path):
    """Create a real SessionDB for testing."""
    os.environ["AETHEROS_HOME"] = str(tmp_path / ".aetheros")
    os.makedirs(tmp_path / ".aetheros", exist_ok=True)
    from aetheros_state import SessionDB
    db = SessionDB(db_path=tmp_path / ".aetheros" / "test_sessions.db")
    yield db
    db.close()


@pytest.fixture
def cli_instance(tmp_path, session_db):
    """Create a minimal AetherosCLI-like object for testing the handlers."""
    cli = MagicMock()
    cli._session_db = session_db
    cli.session_id = "20260403_120000_abc123"
    cli.agent = None
    cli.conversation_history = []

    session_db.create_session(
        session_id=cli.session_id,
        source="cli",
        model="test-model",
    )
    session_db.append_message(session_id=cli.session_id, role="user", content="Hello")
    return cli


class TestFolderCommandCLI:
    """Test the /folder command logic for the CLI."""

    def test_folder_assign_current_session(self, cli_instance, session_db):
        from cli import AetherosCLI

        AetherosCLI._handle_folder_command(cli_instance, "/folder work")
        assert session_db.get_session_folder(cli_instance.session_id) == "work"

    def test_folder_assign_explicit_session(self, cli_instance, session_db):
        from cli import AetherosCLI

        session_db.create_session(session_id="other", source="cli")
        AetherosCLI._handle_folder_command(cli_instance, "/folder other work")
        assert session_db.get_session_folder("other") == "work"

    def test_folder_clear_current(self, cli_instance, session_db):
        from cli import AetherosCLI

        session_db.set_session_folder(cli_instance.session_id, "work")
        AetherosCLI._handle_folder_command(cli_instance, "/folder clear")
        assert session_db.get_session_folder(cli_instance.session_id) is None

    def test_folder_clear_explicit(self, cli_instance, session_db):
        from cli import AetherosCLI

        session_db.create_session(session_id="other", source="cli")
        session_db.set_session_folder("other", "work")
        AetherosCLI._handle_folder_command(cli_instance, "/folder clear other")
        assert session_db.get_session_folder("other") is None

    def test_folder_list_shows_counts(self, cli_instance, session_db):
        from cli import AetherosCLI

        session_db.set_session_folder(cli_instance.session_id, "work")
        AetherosCLI._handle_folder_command(cli_instance, "/folder list")
        folders = session_db.list_folders()
        assert folders == [{"folder": "work", "session_count": 1}]

    def test_folder_unknown_session(self, cli_instance, session_db):
        from cli import AetherosCLI

        # Should not raise for a missing session target.
        AetherosCLI._handle_folder_command(cli_instance, "/folder nope work")
        assert session_db.get_session_folder("nope") is None

    def test_folder_missing_db(self, cli_instance):
        from cli import AetherosCLI

        cli_instance._session_db = None
        # Should not raise when the DB is unavailable.
        AetherosCLI._handle_folder_command(cli_instance, "/folder work")


class TestPinCommandCLI:
    """Test the /pin command logic for the CLI."""

    def test_pin_current_defaults_on(self, cli_instance, session_db):
        from cli import AetherosCLI

        AetherosCLI._handle_pin_command(cli_instance, "/pin on")
        assert session_db.is_session_pinned(cli_instance.session_id) is True

    def test_pin_explicit_on(self, cli_instance, session_db):
        from cli import AetherosCLI

        AetherosCLI._handle_pin_command(cli_instance, "/pin on")
        assert session_db.is_session_pinned(cli_instance.session_id) is True

    def test_pin_explicit_off(self, cli_instance, session_db):
        from cli import AetherosCLI

        session_db.set_session_pinned(cli_instance.session_id, True)
        AetherosCLI._handle_pin_command(cli_instance, "/pin off")
        assert session_db.is_session_pinned(cli_instance.session_id) is False

    def test_pin_other_session(self, cli_instance, session_db):
        from cli import AetherosCLI

        session_db.create_session(session_id="other", source="cli")
        AetherosCLI._handle_pin_command(cli_instance, "/pin other on")
        assert session_db.is_session_pinned("other") is True

    def test_pin_other_session_defaults_on(self, cli_instance, session_db):
        from cli import AetherosCLI

        session_db.create_session(session_id="other", source="cli")
        AetherosCLI._handle_pin_command(cli_instance, "/pin other")
        assert session_db.is_session_pinned("other") is True

    def test_pin_missing_db(self, cli_instance):
        from cli import AetherosCLI

        cli_instance._session_db = None
        AetherosCLI._handle_pin_command(cli_instance, "/pin on")


class TestImportCommandCLI:
    """Test the /import command logic for the CLI."""

    def _write_export(self, tmp_path, data):
        p = tmp_path / "session_export.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return str(p)

    def test_import_single_session(self, cli_instance, session_db, tmp_path):
        from cli import AetherosCLI

        export = session_db.export_session(cli_instance.session_id)
        path = self._write_export(tmp_path, export)

        AetherosCLI._handle_import_command(cli_instance, f"/import {path}")

        # A copy should exist with a fresh id and the same messages.
        import re as _re
        imported = [s for s in session_db.list_sessions_rich(include_archived=True) if s["id"].startswith("import_")]
        assert len(imported) == 1
        assert len(session_db.get_messages(imported[0]["id"])) == 1
        assert imported[0]["id"] != cli_instance.session_id

    def test_import_with_folder(self, cli_instance, session_db, tmp_path):
        from cli import AetherosCLI

        export = session_db.export_session(cli_instance.session_id)
        path = self._write_export(tmp_path, export)

        AetherosCLI._handle_import_command(cli_instance, f"/import {path} --folder archive")

        imported = [s for s in session_db.list_sessions_rich(include_archived=True) if s["id"].startswith("import_")]
        assert session_db.get_session_folder(imported[0]["id"]) == "archive"

    def test_import_jsonl(self, cli_instance, session_db, tmp_path):
        from cli import AetherosCLI

        export = session_db.export_session(cli_instance.session_id)
        p = tmp_path / "sessions.jsonl"
        p.write_text(json.dumps(export) + "\n" + json.dumps(export), encoding="utf-8")

        AetherosCLI._handle_import_command(cli_instance, f"/import {p}")

        imported = [s for s in session_db.list_sessions_rich(include_archived=True) if s["id"].startswith("import_")]
        assert len(imported) == 2

    def test_import_missing_file(self, cli_instance, session_db, tmp_path):
        from cli import AetherosCLI

        AetherosCLI._handle_import_command(cli_instance, "/import nope.json")

    def test_import_invalid_json(self, cli_instance, session_db, tmp_path):
        from cli import AetherosCLI

        p = tmp_path / "bad.json"
        p.write_text("{not json", encoding="utf-8")
        AetherosCLI._handle_import_command(cli_instance, f"/import {p}")

    def test_import_no_args(self, cli_instance, session_db):
        from cli import AetherosCLI

        AetherosCLI._handle_import_command(cli_instance, "/import")

    def test_import_missing_db(self, cli_instance, session_db, tmp_path):
        from cli import AetherosCLI

        export = session_db.export_session(cli_instance.session_id)
        path = self._write_export(tmp_path, export)
        cli_instance._session_db = None
        AetherosCLI._handle_import_command(cli_instance, f"/import {path}")

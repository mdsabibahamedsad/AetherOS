"""Tests for AetherOS minimal banner."""

from unittest.mock import patch

from rich.console import Console

import aetheros_cli.banner as banner


def test_build_welcome_banner_shows_minimal_info():
    """New minimal banner shows AetherOS name and project path."""
    with (
        patch.object(banner, "get_available_skills", return_value={}),
        patch.object(banner, "get_update_result", return_value=None),
    ):
        console = Console(
            record=True, force_terminal=False, color_system=None, width=160
        )
        banner.build_welcome_banner(
            console=console,
            model="anthropic/test-model",
            cwd="/tmp/project",
            session_id="abc123",
        )

    output = console.export_text()
    assert "AetherOS" in output
    assert "/tmp/project" in output
    assert "test-model" in output


def test_build_welcome_banner_shows_context():
    """Context length is shown when provided."""
    with (
        patch.object(banner, "get_available_skills", return_value={}),
        patch.object(banner, "get_update_result", return_value=None),
    ):
        console = Console(
            record=True, force_terminal=False, color_system=None, width=160
        )
        banner.build_welcome_banner(
            console=console,
            model="gpt-5",
            cwd="/tmp",
            session_id="abc123",
            context_length=128000,
        )

    output = console.export_text()
    assert "128K" in output or "128000" in output


def test_build_welcome_banner_upate_check_optional():
    """Update check failure doesn't break banner."""
    with (
        patch.object(banner, "get_available_skills", return_value={}),
        patch.object(banner, "get_update_result", return_value=None),
    ):
        console = Console(
            record=True, force_terminal=False, color_system=None, width=160
        )
        banner.build_welcome_banner(
            console=console,
            model="x",
            cwd="/tmp",
        )

    output = console.export_text()
    assert "AetherOS" in output

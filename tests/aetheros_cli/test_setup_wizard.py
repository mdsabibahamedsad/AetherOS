"""
Unit tests for aetheros_cli/setup_wizard.py.

Covers:
- SetupCheckpoint save/load/delete/completed/skipped/mark_editing
- SetupStep base class behavior and validation
- All 16 step implementations (Welcome, Profile, Purpose, Experience,
  AI Providers, Local Detection, API Config, Default Models, Connect
  Services, Automation, Tools, Memory, Privacy, Workspace, Review, Finish)
- Shared renderer helpers (icon, make_step_progress, make_nav_bar,
  make_success_screen, STEP_ICONS)
- AdvancedSetupWizard step building, navigation, and state management
- Entry point functions (run_advanced_setup_wizard, backup_config)
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from aetheros_cli.setup_wizard import (
    STEP_ICONS,
    AdvancedSetupWizard,
    AIProviderStep,
    APIConfigStep,
    AutomationStep,
    ConnectServicesStep,
    DefaultModelsStep,
    ExperienceStep,
    FinishStep,
    LocalDetectionStep,
    MemoryStep,
    PrivacyStep,
    ProfileStep,
    PurposeStep,
    ReviewStep,
    SetupCheckpoint,
    SetupStep,
    ToolsStep,
    WelcomeStep,
    WorkspaceStep,
    backup_config,
    icon,
    make_nav_bar,
    make_step_progress,
    make_success_screen,
    run_advanced_setup_wizard,
)


# =============================================================================
# Rich text rendering helper (Rich objects don't have __str__)
# =============================================================================


def _rich_text(renderable) -> str:
    """Render a Rich renderable to plain text for assertions."""
    console = Console(file=StringIO(), force_terminal=False, width=200)
    console.print(renderable)
    return console.file.getvalue()


def _make_wizard(**kwargs) -> MagicMock:
    """Build a mock wizard with a usable config/checkpoint surface."""
    wizard = MagicMock()
    wizard.config = kwargs.get("config", {})
    wizard.checkpoint = kwargs.get("checkpoint", SetupCheckpoint())
    wizard.steps = kwargs.get("steps", [])
    return wizard


# =============================================================================
# SetupCheckpoint Tests
# =============================================================================


class TestSetupCheckpoint:
    """Test the checkpoint system for crash recovery and resume."""

    def test_default_state(self):
        """Checkpoint starts with empty state."""
        cp = SetupCheckpoint()
        assert cp.current_step == 0
        assert cp.state["completed_steps"] == []
        assert cp.state["skipped_steps"] == []
        assert cp.state["version"] == 3

    def test_load_from_state_dict(self):
        """Load checkpoint from pre-existing state dict."""
        state = {
            "version": 3,
            "current_step": 5,
            "completed_steps": ["profile", "purpose", "experience"],
            "skipped_steps": ["ai_providers"],
            "step_data": {"profile": {"name": "Test"}},
            "last_updated": "2026-01-01T00:00:00",
        }
        cp = SetupCheckpoint(state)
        assert cp.current_step == 5
        assert cp.is_completed("profile")
        assert cp.is_completed("purpose")
        assert cp.is_skipped("ai_providers")
        assert not cp.is_skipped("profile")

    def test_save_and_load(self, tmp_path, monkeypatch):
        """Save to disk and load back."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        cp = SetupCheckpoint()
        cp.save(current_step=3, completed=["profile", "purpose"])

        loaded = SetupCheckpoint.load()
        assert loaded is not None
        assert loaded.current_step == 3
        assert loaded.is_completed("profile")
        assert loaded.is_completed("purpose")
        assert not loaded.is_completed("experience")

    def test_save_with_skipped(self, tmp_path, monkeypatch):
        """Save with skipped steps."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        cp = SetupCheckpoint()
        cp.save(
            current_step=2,
            completed=["profile"],
            skipped=["ai_providers"],
            step_data={"profile": {"name": "Test"}},
        )

        loaded = SetupCheckpoint.load()
        assert loaded is not None
        assert loaded.is_completed("profile")
        assert loaded.is_skipped("ai_providers")

    def test_delete(self, tmp_path, monkeypatch):
        """Delete checkpoint file from disk."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        cp = SetupCheckpoint()
        cp.save(current_step=1, completed=[])

        assert SetupCheckpoint.load() is not None
        cp.delete()
        assert SetupCheckpoint.load() is None

    def test_delete_nonexistent_not_crash(self):
        """Deleting a non-existent checkpoint does not raise."""
        cp = SetupCheckpoint()
        cp.delete()  # should not raise

    def test_load_missing_returns_none(self, tmp_path, monkeypatch):
        """Load returns None when no checkpoint file exists."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        assert SetupCheckpoint.load() is None

    def test_load_corrupted_returns_none(self, tmp_path, monkeypatch):
        """Load returns None for corrupt JSON."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        checkpoint_path = tmp_path / "setup_checkpoint.json"
        checkpoint_path.write_text("not valid json", encoding="utf-8")
        assert SetupCheckpoint.load() is None

    def test_mark_editing(self, tmp_path, monkeypatch):
        """mark_editing removes a step from completed list."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        cp = SetupCheckpoint()
        cp.save(current_step=5, completed=["profile", "purpose", "experience"])
        cp.mark_editing("purpose")
        assert not cp.is_completed("purpose")
        assert cp.is_completed("profile")
        assert cp.is_completed("experience")

    def test_mark_editing_not_completed(self, tmp_path, monkeypatch):
        """mark_editing on a not-yet-completed step is a no-op."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        cp = SetupCheckpoint()
        cp.save(current_step=3, completed=["profile"])
        cp.mark_editing("automation")  # never completed
        assert not cp.is_completed("automation")
        assert cp.is_completed("profile")

    def test_complete_step_idempotent(self, tmp_path, monkeypatch):
        """complete_step adds a step once; repeats are ignored."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        cp = SetupCheckpoint()
        cp.complete_step("profile")
        cp.complete_step("profile")
        assert cp.is_completed("profile")
        assert cp.state["completed_steps"].count("profile") == 1

    def test_skip_step_idempotent(self, tmp_path, monkeypatch):
        """skip_step adds a step once; repeats are ignored."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        cp = SetupCheckpoint()
        cp.skip_step("ai_providers")
        cp.skip_step("ai_providers")
        assert cp.is_skipped("ai_providers")
        assert cp.state["skipped_steps"].count("ai_providers") == 1

    def test_save_updates_last_updated(self, tmp_path, monkeypatch):
        """Save sets last_updated timestamp."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        cp = SetupCheckpoint()
        assert cp.state["last_updated"] is None
        cp.save(current_step=1, completed=[])
        assert cp.state["last_updated"] is not None

    def test_save_merges_step_data(self, tmp_path, monkeypatch):
        """Step data is merged across saves."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        cp = SetupCheckpoint()
        cp.save(current_step=1, completed=["profile"], step_data={"profile": {"name": "Test"}})
        cp.save(
            current_step=2, completed=["profile", "purpose"], step_data={"purpose": {"purposes": ["research"]}}
        )
        loaded = SetupCheckpoint.load()
        assert loaded.state["step_data"]["profile"]["name"] == "Test"
        assert loaded.state["step_data"]["purpose"]["purposes"] == ["research"]


# =============================================================================
# SetupStep Base Class Tests
# =============================================================================


class TestSetupStepBase:
    """Test the base SetupStep class."""

    def test_render_raises_not_implemented(self):
        """Base SetupStep.render() raises NotImplementedError."""
        wizard = MagicMock()
        step = SetupStep(wizard)
        with pytest.raises(NotImplementedError):
            step.render()

    def test_handle_action_returns_none(self):
        """Default handle_action returns None."""
        wizard = MagicMock()
        step = SetupStep(wizard)
        assert step.handle_action("up") is None
        assert step.handle_action("down") is None
        assert step.handle_action("confirm") is None

    def test_validate_defaults_false(self):
        """Default validate returns False."""
        wizard = MagicMock()
        step = SetupStep(wizard)
        assert not step.validate()

    def test_on_enter_is_noop(self):
        """on_enter does not raise."""
        wizard = MagicMock()
        step = SetupStep(wizard)
        step.on_enter()  # should not raise

    def test_on_exit_returns_none(self):
        """on_exit returns None by default."""
        wizard = MagicMock()
        step = SetupStep(wizard)
        assert step.on_exit() is None

    def test_save_to_config_is_noop(self):
        """save_to_config does not raise."""
        wizard = MagicMock()
        step = SetupStep(wizard)
        step.save_to_config()  # should not raise

    def test_on_skip_returns_none(self):
        """on_skip returns None by default."""
        wizard = MagicMock()
        step = SetupStep(wizard)
        assert step.on_skip() is None

    def test_config_delegates_to_wizard(self):
        """Config property returns wizard.config."""
        wizard = MagicMock()
        wizard.config = {"key": "value"}
        step = SetupStep(wizard)
        assert step.config == {"key": "value"}

    def test_step_icon_from_name(self):
        """step_icon property returns the icon for the step name."""
        wizard = MagicMock()
        step = SetupStep(wizard)
        step.name = "welcome"
        assert step.step_icon == "◆"

    def test_step_icon_fallback(self):
        """step_icon property returns fallback for unknown names."""
        wizard = MagicMock()
        step = SetupStep(wizard)
        step.name = "nonexistent"
        assert step.step_icon == "◇"

    def test_field_index_and_count_defaults(self):
        """Field navigation attributes exist by default."""
        wizard = MagicMock()
        step = SetupStep(wizard)
        assert step._field_index == 0
        assert step._field_count == 1

    def test_required_flag_defaults_to_false(self):
        """required flag is False by default on base class."""
        wizard = MagicMock()
        step = SetupStep(wizard)
        assert not step.required


# =============================================================================
# Step Implementation Tests
# =============================================================================


class TestWelcomeStep:
    """Test the Welcome step."""

    def test_initial_state(self):
        """WelcomeStep is valid by default."""
        wizard = MagicMock()
        step = WelcomeStep(wizard)
        assert step.name == "welcome"
        assert step.step_number == 1
        assert step.required
        assert step.validate()

    def test_render_returns_panel(self):
        """render returns a Rich renderable containing the welcome text."""
        wizard = MagicMock()
        step = WelcomeStep(wizard)
        assert "AetherOS" in _rich_text(step.render())


class TestProfileStep:
    """Test the Profile step."""

    def test_initial_state(self):
        """ProfileStep starts with empty name and defaults."""
        wizard = MagicMock()
        step = ProfileStep(wizard)
        assert step.name == "profile"
        assert step.required
        assert step._name == ""
        assert step._username == ""
        assert step._language == "en"
        assert step._timezone == "UTC"
        assert step._theme == "dark"
        assert step._field_count == 5

    def test_invalid_until_name_and_username(self):
        """on_enter only validates once both name and username are set."""
        wizard = MagicMock()
        step = ProfileStep(wizard)
        step.on_enter()
        assert not step.validate()
        step.set_input("Alice")
        step.on_enter()
        assert not step.validate()
        step.set_input("alice")
        step.on_enter()
        assert step.validate()

    def test_set_input_advances_fields(self):
        """set_input fills name then username and advances the field index."""
        wizard = MagicMock()
        step = ProfileStep(wizard)
        assert step._field_index == 0
        step.set_input("Alice")
        assert step._name == "Alice"
        assert step._field_index == 1
        step.set_input("alice")
        assert step._username == "alice"
        assert step._field_index == 2

    def test_on_exit_returns_profile_data(self):
        """on_exit returns the collected profile fields."""
        wizard = MagicMock()
        step = ProfileStep(wizard)
        step._name = "Alice"
        step._username = "alice"
        step._language = "fr"
        step._timezone = "Europe/Paris"
        step._theme = "light"
        data = step.on_exit()
        assert data == {
            "name": "Alice",
            "username": "alice",
            "language": "fr",
            "timezone": "Europe/Paris",
            "theme": "light",
        }

    def test_save_to_config_sets_skin(self):
        """save_to_config writes onboarding + display.skin."""
        wizard = _make_wizard()
        step = ProfileStep(wizard)
        step._theme = "light"
        step.save_to_config()
        assert wizard.config["onboarding"]["profile_build"] == "completed"
        assert wizard.config["display"]["skin"] == "daylight"

    def test_handle_action_language_selection(self):
        """Confirm on the language field picks the selected language."""
        wizard = MagicMock()
        step = ProfileStep(wizard)
        step._field_index = 2
        step._lang_selected = 1
        step.handle_action("confirm")
        assert step._language == "es"

    def test_handle_action_theme_cycle(self):
        """Up/down on the theme field cycles the theme."""
        wizard = MagicMock()
        step = ProfileStep(wizard)
        step._field_index = 4
        step._theme = "dark"
        step.handle_action("down")
        assert step._theme == "light"


class TestPurposeStep:
    """Test the Purpose step."""

    def test_initial_state(self):
        """PurposeStep is optional and valid by default."""
        wizard = MagicMock()
        step = PurposeStep(wizard)
        assert step.name == "purpose"
        assert not step.required
        assert step._selected == set()
        assert step.validate()

    def test_toggle_selection(self):
        """Space toggles the purpose at the cursor."""
        wizard = MagicMock()
        step = PurposeStep(wizard)
        step._cursor = 0
        step.handle_action(" ")
        assert "programming" in step._selected
        step.handle_action(" ")
        assert "programming" not in step._selected

    def test_navigate_cursor(self):
        """Up/down moves the cursor within bounds."""
        wizard = MagicMock()
        step = PurposeStep(wizard)
        step.handle_action("up")
        assert step._cursor == 0
        step.handle_action("down")
        assert step._cursor == 1

    def test_on_exit_returns_purposes(self):
        """on_exit returns the selected purposes."""
        wizard = MagicMock()
        step = PurposeStep(wizard)
        step._selected = {"research", "programming"}
        assert sorted(step.on_exit()["purposes"]) == ["programming", "research"]


class TestExperienceStep:
    """Test the Experience Level step."""

    def test_initial_state(self):
        """ExperienceStep defaults to the intermediate index."""
        wizard = MagicMock()
        step = ExperienceStep(wizard)
        assert not step.required
        assert step._selected == 1
        assert step._cursor == 1

    def test_confirm_sets_selected(self):
        """Confirm sets the experience level from the cursor."""
        wizard = MagicMock()
        step = ExperienceStep(wizard)
        step._cursor = 3
        step.handle_action("confirm")
        assert step._selected == "expert"

    def test_on_exit(self):
        """on_exit returns the experience level."""
        wizard = MagicMock()
        step = ExperienceStep(wizard)
        step._selected = "advanced"
        assert step.on_exit() == {"experience_level": "advanced"}


class TestAIProviderStep:
    """Test the AI Providers step."""

    def test_initial_state(self):
        """AIProviderStep starts with no selection and is optional."""
        wizard = MagicMock()
        step = AIProviderStep(wizard)
        assert not step.required
        assert step._selected == set()
        assert step.validate()

    def test_toggle_provider(self):
        """Space toggles the provider at the cursor."""
        wizard = MagicMock()
        step = AIProviderStep(wizard)
        step._cursor = 0
        step.handle_action(" ")
        assert "openai" in step._selected
        step.handle_action(" ")
        assert "openai" not in step._selected

    def test_on_exit_returns_providers(self):
        """on_exit returns the selected providers."""
        wizard = MagicMock()
        step = AIProviderStep(wizard)
        step._selected = {"anthropic", "openai"}
        assert sorted(step.on_exit()["providers"]) == ["anthropic", "openai"]

    def test_save_to_config(self):
        """save_to_config persists selected providers under onboarding."""
        wizard = _make_wizard()
        step = AIProviderStep(wizard)
        step._selected = {"openrouter"}
        step.save_to_config()
        assert wizard.config["onboarding"]["selected_providers"] == ["openrouter"]


class TestLocalDetectionStep:
    """Test the Local Detection step."""

    def test_initial_state(self):
        """LocalDetectionStep starts unscanned and valid."""
        wizard = MagicMock()
        step = LocalDetectionStep(wizard)
        assert not step.required
        assert step._scanned is False
        assert step._scanning is False
        assert step._scan_results == {}
        assert step.validate()

    def test_scan_marks_results(self):
        """_scan records per-provider detection results."""
        wizard = MagicMock()
        step = LocalDetectionStep(wizard)
        with patch("urllib.request.urlopen", side_effect=OSError("no local provider")):
            step._scan()
        assert step._scanned is True
        assert step._scanning is False
        assert set(step._scan_results) == {"ollama", "lm_studio", "vllm", "open_webui"}
        assert all(v is False for v in step._scan_results.values())

    def test_on_exit_returns_scan_results(self):
        """on_exit returns the per-provider detection map."""
        wizard = MagicMock()
        step = LocalDetectionStep(wizard)
        step._scan_results = {"ollama": True}
        data = step.on_exit()
        assert data["local_providers"]["ollama"] is True
        assert data["local_providers"]["vllm"] is False
        assert set(data["local_providers"]) == {"ollama", "lm_studio", "vllm", "open_webui"}


class TestAPIConfigStep:
    """Test the API Configuration step."""

    def test_initial_state(self):
        """APIConfigStep is optional and valid by default."""
        wizard = MagicMock()
        step = APIConfigStep(wizard)
        assert not step.required
        assert step._api_keys == {}
        assert step.validate()

    def test_navigate_providers(self):
        """Up/down moves the active provider within bounds."""
        wizard = MagicMock()
        step = APIConfigStep(wizard)
        step.handle_action("down")
        assert step._active_provider == 1
        step.handle_action("up")
        assert step._active_provider == 0

    def test_on_exit_returns_key_names(self):
        """on_exit returns the names of configured providers."""
        wizard = MagicMock()
        step = APIConfigStep(wizard)
        step._api_keys = {"openai": "sk-test"}
        assert step.on_exit() == {"api_keys": ["openai"]}


class TestDefaultModelsStep:
    """Test the Default Models step."""

    def test_initial_state(self):
        """DefaultModelsStep is optional and valid by default."""
        wizard = MagicMock()
        step = DefaultModelsStep(wizard)
        assert not step.required
        assert step.validate()

    def test_on_exit_returns_categories(self):
        """on_exit returns the model category list."""
        wizard = MagicMock()
        step = DefaultModelsStep(wizard)
        data = step.on_exit()
        assert "coding" in data["model_categories"]
        assert "vision" in data["model_categories"]


class TestConnectServicesStep:
    """Test the Connect Services step."""

    def test_initial_state(self):
        """ConnectServicesStep starts with nothing connected."""
        wizard = MagicMock()
        step = ConnectServicesStep(wizard)
        assert not step.required
        assert step._connected == set()

    def test_toggle_service(self):
        """Space toggles the service at the cursor."""
        wizard = MagicMock()
        step = ConnectServicesStep(wizard)
        step._cursor = 0
        step.handle_action(" ")
        assert "telegram" in step._connected
        step.handle_action(" ")
        assert "telegram" not in step._connected

    def test_on_exit(self):
        """on_exit returns the connected services."""
        wizard = MagicMock()
        step = ConnectServicesStep(wizard)
        step._connected = {"github"}
        assert step.on_exit() == {"connected_services": ["github"]}


class TestAutomationStep:
    """Test the Automation step."""

    def test_defaults_selected(self):
        """AutomationStep pre-selects background agents and notifications."""
        wizard = MagicMock()
        step = AutomationStep(wizard)
        assert "background_agents" in step._selected
        assert "notifications" in step._selected
        assert not step.required

    def test_toggle(self):
        """Space toggles an automation option."""
        wizard = MagicMock()
        step = AutomationStep(wizard)
        step._cursor = 1  # scheduled_tasks
        step.handle_action(" ")
        assert "scheduled_tasks" in step._selected

    def test_on_exit(self):
        """on_exit returns the automation selection."""
        wizard = MagicMock()
        step = AutomationStep(wizard)
        step._selected = {"cron_jobs"}
        assert step.on_exit() == {"automation": ["cron_jobs"]}


class TestToolsStep:
    """Test the Tools step."""

    def test_defaults_selected(self):
        """ToolsStep pre-selects core tools."""
        wizard = MagicMock()
        step = ToolsStep(wizard)
        for tool in ("filesystem", "terminal", "web_search", "browser"):
            assert tool in step._selected
        assert not step.required

    def test_toggle(self):
        """Space toggles a tool."""
        wizard = MagicMock()
        step = ToolsStep(wizard)
        step._cursor = 3  # docker
        step.handle_action(" ")
        assert "docker" in step._selected

    def test_on_exit(self):
        """on_exit returns the tool selection."""
        wizard = MagicMock()
        step = ToolsStep(wizard)
        step._selected = {"filesystem", "python"}
        result = step.on_exit()
        assert set(result["tools"]) == {"filesystem", "python"}


class TestMemoryStep:
    """Test the Memory step."""

    def test_defaults_selected(self):
        """MemoryStep pre-selects personal and workspace memory."""
        wizard = MagicMock()
        step = MemoryStep(wizard)
        assert "personal_memory" in step._selected
        assert "workspace_memory" in step._selected

    def test_on_exit(self):
        """on_exit returns the memory selection."""
        wizard = MagicMock()
        step = MemoryStep(wizard)
        step._selected = {"project_memory"}
        assert step.on_exit() == {"memory": ["project_memory"]}


class TestPrivacyStep:
    """Test the Privacy step."""

    def test_defaults_selected(self):
        """PrivacyStep pre-selects encrypted storage and auto updates."""
        wizard = MagicMock()
        step = PrivacyStep(wizard)
        assert "encrypted_storage" in step._selected
        assert "auto_updates" in step._selected

    def test_on_exit(self):
        """on_exit returns the privacy selection."""
        wizard = MagicMock()
        step = PrivacyStep(wizard)
        step._selected = {"local_only"}
        assert step.on_exit() == {"privacy": ["local_only"]}


class TestWorkspaceStep:
    """Test the Workspace step."""

    def test_initial_state(self):
        """WorkspaceStep starts on the projects preset."""
        wizard = MagicMock()
        step = WorkspaceStep(wizard)
        assert not step.required
        assert step._selected == 0
        assert "aetheros-projects" in step._projects_path

    def test_navigate_presets(self):
        """Up/down moves between workspace presets."""
        wizard = MagicMock()
        step = WorkspaceStep(wizard)
        step.handle_action("down")
        assert step._selected == 1
        step.handle_action("up")
        assert step._selected == 0

    def test_on_exit_returns_workspace_key(self):
        """on_exit returns the chosen preset key and path."""
        wizard = MagicMock()
        step = WorkspaceStep(wizard)
        data = step.on_exit()
        assert data["workspace"] == "projects"
        assert "aetheros-projects" in data["workspace_path"]

    def test_save_to_config_sets_terminal_cwd(self):
        """save_to_config sets terminal.cwd for the projects preset."""
        wizard = _make_wizard()
        step = WorkspaceStep(wizard)
        step.save_to_config()
        assert wizard.config["terminal"]["cwd"] == step._projects_path


class TestReviewStep:
    """Test the Review step."""

    def test_initial_state(self):
        """ReviewStep starts at the first section and is required."""
        wizard = _make_wizard()
        step = ReviewStep(wizard)
        assert step.required
        assert step._cursor == 0
        assert step.validate()

    def test_navigate_sections(self):
        """Up/down arrows navigate sections."""
        wizard = _make_wizard()
        step = ReviewStep(wizard)
        step.handle_action("down")
        assert step._cursor == 1
        step.handle_action("up")
        assert step._cursor == 0

    def test_edit_returns_edit_directive(self):
        """Edit returns edit:<section> for the current cursor."""
        wizard = _make_wizard()
        step = ReviewStep(wizard)
        step._cursor = 0
        assert step.handle_action("edit") == "edit:profile"
        step._cursor = 3
        assert step.handle_action("e") == "edit:ai_providers"

    def test_edit_bounds(self):
        """Edit stays within the section list."""
        wizard = _make_wizard()
        step = ReviewStep(wizard)
        step._cursor = len(step._section_names) - 1
        result = step.handle_action("edit")
        assert result.startswith("edit:")
        assert result in {f"edit:{s}" for s in step._section_names}


class TestFinishStep:
    """Test the Finish step."""

    def test_initial_state(self):
        """FinishStep defaults to terminal launch and is required."""
        wizard = _make_wizard()
        step = FinishStep(wizard)
        assert step.required
        assert step._launch_choice == "1"

    def test_handle_action_selects_launch(self):
        """Pressing a number selects the launch choice."""
        wizard = _make_wizard()
        step = FinishStep(wizard)
        step.handle_action("2")
        assert step._launch_choice == "2"
        step.handle_action("3")
        assert step._launch_choice == "3"

    def test_handle_action_confirm_launches(self):
        """Confirm returns the launch directive."""
        wizard = _make_wizard()
        step = FinishStep(wizard)
        assert step.handle_action("confirm") == "launch"

    def test_on_exit(self):
        """on_exit returns the launch choice."""
        wizard = _make_wizard()
        step = FinishStep(wizard)
        step._launch_choice = "2"
        assert step.on_exit() == {"launch_choice": "2"}


# =============================================================================
# Renderer Helper Tests
# =============================================================================


class TestIconHelper:
    """Test the icon helper."""

    def test_returns_emoji_for_known_steps(self):
        """Known step names return emoji strings."""
        assert icon("welcome") == "◆"
        assert len(icon("profile")) > 0

    def test_fallback_for_unknown(self):
        """Unknown step names return fallback diamond."""
        assert icon("nonexistent") == "◇"

    def test_all_icons_have_values(self):
        """All icons in STEP_ICONS have non-empty values."""
        for key, value in STEP_ICONS.items():
            assert value, f"Icon for {key} is empty"
            assert len(value) > 0, f"Icon for {key} is too short"

    def test_every_registry_step_has_icon(self):
        """Every wizard step name maps to a non-fallback icon."""
        from aetheros_cli.setup_wizard import _STEP_REGISTRY

        for name, _, _ in _STEP_REGISTRY:
            assert icon(name) != "◇", f"No icon registered for step {name}"


class TestRenderProgress:
    """Test the progress bar rendering."""

    def test_returns_panel(self):
        """make_step_progress returns a Panel with step context."""
        panel = make_step_progress(3, 15, "Test Step")
        rendered = _rich_text(panel)
        assert "Step 3/15" in rendered
        assert "Test Step" in rendered

    def test_first_step_shows_properly(self):
        """First step shows Step 1 of N."""
        panel = make_step_progress(1, 15, "Language")
        assert "Step 1/15" in _rich_text(panel)

    def test_last_step(self):
        """Last step shows Step N of N."""
        panel = make_step_progress(15, 15, "Finish")
        assert "Step 15/15" in _rich_text(panel)


class TestRenderNav:
    """Test the navigation bar rendering."""

    def test_shows_back_when_can_back(self):
        """Back button shown when can_back is True."""
        panel = make_nav_bar(can_back=True, can_next=False)
        assert "Back" in _rich_text(panel)

    def test_hides_skip_when_not_skip(self):
        """Skip button hidden for required steps."""
        panel = make_nav_bar(can_back=False, can_next=False, can_skip=False)
        assert "Skip" not in _rich_text(panel)

    def test_shows_skip_when_can_skip(self):
        """Skip button shown for optional steps."""
        panel = make_nav_bar(can_back=False, can_next=False, can_skip=True)
        assert "Skip" in _rich_text(panel)

    def test_shows_next(self):
        """Next button always shown."""
        panel = make_nav_bar(can_back=False, can_next=True)
        assert "Next" in _rich_text(panel)

    def test_shows_save_and_cancel(self):
        """Save and Cancel always shown."""
        panel = make_nav_bar(can_back=False, can_next=False)
        rendered = _rich_text(panel)
        assert "Save" in rendered
        assert "Cancel" in rendered


class TestRenderSuccessScreen:
    """Test the success screen rendering."""

    def test_shows_title_and_message(self):
        """make_success_screen shows the title and message."""
        panel = make_success_screen("Done", "Language set to English")
        rendered = _rich_text(panel)
        assert "Done" in rendered
        assert "Language set to English" in rendered

    def test_shows_details(self):
        """make_success_screen renders optional detail lines."""
        panel = make_success_screen("Done", "Setup complete", details=["Step 1", "Step 2"])
        rendered = _rich_text(panel)
        assert "Step 1" in rendered
        assert "Step 2" in rendered


# =============================================================================
# Wizard Tests
# =============================================================================


class TestAdvancedSetupWizardBuildSteps:
    """Test the wizard's step building."""

    def test_build_steps_matches_registry(self):
        """_build_steps creates one step per registry entry."""
        from aetheros_cli.setup_wizard import _STEP_REGISTRY

        wizard = AdvancedSetupWizard()
        wizard._build_steps()
        assert len(wizard.steps) == len(_STEP_REGISTRY)
        for i, (name, step_cls, required) in enumerate(_STEP_REGISTRY):
            step = wizard.steps[i]
            assert step.name == name
            assert isinstance(step, step_cls)
            assert step.required == required

    def test_build_steps_correct_order(self):
        """Steps are built in registry order."""
        from aetheros_cli.setup_wizard import _STEP_REGISTRY

        wizard = AdvancedSetupWizard()
        wizard._build_steps()
        step_names = [s.name for s in wizard.steps]
        assert step_names == [r[0] for r in _STEP_REGISTRY]

    def test_steps_have_correct_step_numbers(self):
        """Each step has a monotonic step_number."""
        wizard = AdvancedSetupWizard()
        wizard._build_steps()
        numbers = [step.step_number for step in wizard.steps]
        assert numbers == list(range(1, len(numbers) + 1))

    def test_steps_have_wizard_reference(self):
        """Each step references back to the wizard."""
        wizard = AdvancedSetupWizard()
        wizard._build_steps()
        for step in wizard.steps:
            assert step.wizard is wizard


class TestAdvancedSetupWizardNavigation:
    """Test the wizard's navigation logic."""

    def test_initial_index_is_zero(self):
        """Wizard starts at step 0."""
        wizard = AdvancedSetupWizard()
        wizard._build_steps()
        assert wizard._current_index == 0

    def test_process_action_confirm_returns_next(self):
        """Confirm action returns 'next'."""
        wizard = AdvancedSetupWizard()
        wizard._build_steps()
        step = wizard.steps[0]
        assert wizard._process_action(step, "confirm") == "next"

    def test_process_action_back_returns_back(self):
        """Back action returns 'back'."""
        wizard = AdvancedSetupWizard()
        wizard._build_steps()
        step = wizard.steps[0]
        assert wizard._process_action(step, "back") == "back"

    def test_process_action_skip_returns_skip(self):
        """Skip action returns 'skip'."""
        wizard = AdvancedSetupWizard()
        wizard._build_steps()
        step = wizard.steps[4]  # AI Providers (optional)
        assert wizard._process_action(step, "skip") == "skip"

    def test_process_action_save_returns_save(self):
        """Save action returns 'save'."""
        wizard = AdvancedSetupWizard()
        wizard._build_steps()
        step = wizard.steps[0]
        assert wizard._process_action(step, "save") == "save"

    def test_process_action_save_exit_returns_save_exit(self):
        """Save & Exit action returns 'save_exit'."""
        wizard = AdvancedSetupWizard()
        wizard._build_steps()
        step = wizard.steps[0]
        assert wizard._process_action(step, "save_exit") == "save_exit"

    def test_process_action_cancel_returns_cancel(self):
        """Cancel action returns 'cancel'."""
        wizard = AdvancedSetupWizard()
        wizard._build_steps()
        step = wizard.steps[0]
        assert wizard._process_action(step, "cancel") == "cancel"

    def test_process_action_launch_returns_launch(self):
        """Launch action returns 'launch'."""
        wizard = AdvancedSetupWizard()
        wizard._build_steps()
        step = wizard.steps[-1]  # Finish
        assert wizard._process_action(step, "launch") == "launch"

    def test_process_action_unknown_returns_none(self):
        """Unknown action returns None."""
        wizard = AdvancedSetupWizard()
        wizard._build_steps()
        step = wizard.steps[0]
        assert wizard._process_action(step, "unknown") is None

    def test_handle_back_does_not_underflow(self):
        """handle_back does not move below step 0."""
        wizard = AdvancedSetupWizard()
        wizard._build_steps()
        wizard._current_index = 0
        wizard._handle_back()
        assert wizard._current_index == 0

    def test_handle_next_advances_and_completes(self, tmp_path, monkeypatch):
        """handle_next completes the step and advances the index."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        wizard = AdvancedSetupWizard()
        wizard.config = {}
        wizard.checkpoint = SetupCheckpoint()
        wizard._build_steps()
        with patch("aetheros_cli.setup_wizard.save_config") as mock_save:
            wizard._handle_next(wizard.steps[0])
        assert wizard._current_index == 1
        assert wizard.checkpoint.is_completed("welcome")
        mock_save.assert_called()


class TestAdvancedSetupWizardState:
    """Test the wizard's internal state management."""

    def test_running_flag_defaults_to_true(self):
        """Wizard starts in running state."""
        wizard = AdvancedSetupWizard()
        assert wizard._running

    def test_edit_return_defaults_to_false(self):
        """Edit return flag starts as False."""
        wizard = AdvancedSetupWizard()
        assert not wizard._edit_return

    def test_config_starts_empty(self):
        """Wizard config starts empty."""
        wizard = AdvancedSetupWizard()
        assert wizard.config == {}

    def test_checkpoint_starts_none(self):
        """Wizard checkpoint starts as None."""
        wizard = AdvancedSetupWizard()
        assert wizard.checkpoint is None


# =============================================================================
# Entry Point Tests
# =============================================================================


class TestRunAdvancedSetupWizard:
    """Test the run_advanced_setup_wizard entry point."""

    def test_runs_wizard(self, tmp_path, monkeypatch):
        """run_advanced_setup_wizard backs up config and runs the wizard."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        with (
            patch("aetheros_cli.setup_wizard.backup_config") as mock_backup,
            patch("aetheros_cli.setup_wizard.AdvancedSetupWizard") as MockWizard,
        ):
            run_advanced_setup_wizard(args=None)
        mock_backup.assert_called_once()
        MockWizard.assert_called_once()
        MockWizard.return_value.run.assert_called_once()


class TestBackupConfig:
    """Test backup_config function."""

    def test_backup_existing_config(self, tmp_path, monkeypatch):
        """Backup creates a .bak file when config exists."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        config_path = tmp_path / "config.yaml"
        config_path.write_text("model: test", encoding="utf-8")
        backup_config()
        backups = list(tmp_path.glob("config.yaml.bak.*"))
        assert len(backups) == 1

    def test_backup_no_config_no_crash(self, tmp_path, monkeypatch):
        """Backup does nothing when no config exists."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        backup_config()  # should not raise

    def test_backup_preserves_original(self, tmp_path, monkeypatch):
        """Backup preserves the original config content."""
        monkeypatch.setenv("AETHEROS_HOME", str(tmp_path))
        config_path = tmp_path / "config.yaml"
        config_path.write_text("model: test", encoding="utf-8")
        backup_config()
        assert config_path.read_text(encoding="utf-8") == "model: test"

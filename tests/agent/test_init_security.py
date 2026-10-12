"""Tests for agent initialization security binding."""

import pytest

import agent.agent_init as agent_init
from aetheros_security.runtime import clear_security_context, get_security_context


class MockAgent:
    """Mock agent for testing initialization."""
    def __init__(self):
        self.session_id = None
        self.user_id = None
        self.user_id_alt = None
        self.provider = None
        self.workspace = ""
        self.mission = ""
        self.task = ""
        # Add other attributes as needed to prevent AttributeError
        self.api_mode = None
        self.acp_command = None
        self.acp_args = None
        self.command = None
        self.args = None
        self.model = ""
        self.max_iterations = 90
        self.tool_delay = 1.0
        self.enabled_toolsets = None
        self.disabled_toolsets = None
        self.save_trajectories = False
        self.verbose_logging = False
        self.quiet_mode = False
        self.tool_progress_mode = "all"
        self.ephemeral_system_prompt = None
        self.log_prefix_chars = 100
        self.log_prefix = ""
        self.providers_allowed = None
        self.providers_ignored = None
        self.providers_order = None
        self.provider_sort = None
        self.provider_require_parameters = False
        self.provider_data_collection = None
        self.openrouter_min_coding_score = None
        self.iteration_budget = None
        self.fallback_model = None
        self.credential_pool = None
        self.checkpoints_enabled = False
        self.checkpoint_max_snapshots = 20
        self.checkpoint_max_total_size_mb = 500
        self.checkpoint_max_file_size_mb = 10
        self.pass_session_id = False
        self.session_db = None
        self.parent_session_id = None
        self.logs_dir = None
        self._session_json_enabled = False
        self._session_messages = []
        # Set by AIAgent.__init__ before init_agent runs in production;
        # mirrored here so the extracted initializer's contract stays honest.
        self._base_url_hostname = ""
        self._base_url_lower = ""

    # --- Runtime helper methods init_agent calls on a fully-built AIAgent ---
    def _get_transport(self):
        return None

    def _is_azure_openai_url(self):
        return False

    def _is_direct_openai_url(self):
        return False

    def _is_openrouter_url(self):
        return False

    def _provider_model_requires_responses_api(self, *args, **kwargs):
        return False

    def _anthropic_prompt_cache_policy(self, *args, **kwargs):
        return (False, False)

    def _apply_user_default_headers(self, *args, **kwargs):
        return None

    def _create_openai_client(self, *args, **kwargs):
        from unittest.mock import MagicMock
        return MagicMock()

    def _ensure_lmstudio_runtime_loaded(self, *args, **kwargs):
        return None


@pytest.fixture(autouse=True)
def _isolated_security_context():
    clear_security_context()
    yield
    clear_security_context()


@pytest.fixture(autouse=True)
def _no_network_metadata(monkeypatch):
    """init_agent probes model metadata / local servers over HTTP;
    tests here must stay hermetic. Patch both the source module and
    agent_init's import-time bindings."""
    monkeypatch.setattr(
        "agent.model_metadata.get_model_context_length", lambda *a, **k: 128000
    )
    monkeypatch.setattr(
        "agent.model_metadata.fetch_model_metadata", lambda *a, **k: {}
    )
    monkeypatch.setattr(
        "agent.model_metadata.query_ollama_num_ctx", lambda *a, **k: None
    )
    for name in ("fetch_model_metadata", "is_local_endpoint", "query_ollama_num_ctx"):
        if hasattr(agent_init, name):
            if name == "fetch_model_metadata":
                monkeypatch.setattr(agent_init, name, lambda *a, **k: {})
            elif name == "query_ollama_num_ctx":
                monkeypatch.setattr(agent_init, name, lambda *a, **k: None)
            else:
                monkeypatch.setattr(agent_init, name, lambda *a, **k: False)


# Self-contained provider config so init_agent's provider-resolution block
# succeeds in the hermetic test env (no API keys, no config.yaml providers).
_PROVIDER_KWARGS = dict(
    provider="custom",
    api_key="test-key",
    base_url="http://127.0.0.1:9999/v1",
    model="test-model",
)


def test_init_agent_security_binding():
    """Test that init_agent sets up security context without throwing."""
    agent = MockAgent()
    # Set required attributes
    agent.session_id = "test-session-123"
    agent.user_id = "test-user"
    agent.provider = "custom"
    agent.workspace = "test-workspace"

    # This should not raise an exception
    try:
        agent_init.init_agent(
            agent,
            session_id="test-session-123",
            user_id="test-user",
            **_PROVIDER_KWARGS,
        )
        # If we get here, the function completed without exception
        assert True
    except Exception as e:
        # Re-raise to see the failure in test output
        raise e


def test_init_agent_with_minimal_params():
    """Test init_agent with minimal parameters (plus a self-contained provider)."""
    agent = MockAgent()
    # This should not raise an exception
    try:
        agent_init.init_agent(agent, **_PROVIDER_KWARGS)
        # If we get here, the function completed without exception
        assert True
    except Exception as e:
        # Re-raise to see the failure in test output
        raise e


def test_no_security_context_when_gate_disabled(monkeypatch):
    """Gate off (default): no principal is provisioned and no context bound."""
    agent = MockAgent()
    agent.session_id = "test-session-gate-off"
    agent.user_id = "gate-off-user"

    monkeypatch.setattr(
        agent_init, "_control_plane_tool_authorization_enabled", lambda: False
    )
    agent_init.init_agent(agent, **_PROVIDER_KWARGS)

    assert get_security_context().principal == ""


def test_security_context_bound_when_gate_enabled(monkeypatch):
    """Gate on: init provisions identity + token and binds the context."""
    agent = MockAgent()
    agent.session_id = "test-session-gate-on"
    agent.user_id = "alice"
    agent.provider = "custom"
    agent.workspace = "w"

    monkeypatch.setattr(
        agent_init, "_control_plane_tool_authorization_enabled", lambda: True
    )
    agent_init.init_agent(agent, **_PROVIDER_KWARGS)

    ctx = get_security_context()
    assert ctx.principal == "user:alice"
    assert ctx.session_token, "session token must be provisioned"
    assert ctx.agent_id.startswith("agent:")

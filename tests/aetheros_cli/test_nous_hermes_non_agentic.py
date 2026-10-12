"""Tests for the Nous-Aetheros-3/4 non-agentic warning detector.

Prior to this check, the warning fired on any model whose name contained
``"aetheros"`` anywhere (case-insensitive). That false-positived on unrelated
local Modelfiles such as ``hermes-brain:qwen3-14b-ctx16k`` â€” a tool-capable
Qwen3 wrapper that happens to live under the "aetheros" tag namespace.

``is_nous_aetheros_non_agentic`` should only match the actual Nous Research
Aetheros-3 / Aetheros-4 chat family.
"""

from __future__ import annotations

import pytest

from aetheros_cli.model_switch import (
    _HERMES_MODEL_WARNING,
    _check_aetheros_model_warning,
    is_nous_aetheros_non_agentic,
)


@pytest.mark.parametrize(
    "model_name",
    [
        "aetheros/Aetheros-3-Llama-3.1-70B",
        "aetheros/Aetheros-3-Llama-3.1-405B",
        "aetheros-3",
        "Aetheros-3",
        "aetheros-4",
        "aetheros-4-405b",
        "aetheros_4_70b",
        "openrouter/aetheros3:70b",
        "openrouter/aetheros/aetheros-4-405b",
        "aetheros/Aetheros3",
        "aetheros-3.1",
    ],
)
def test_matches_real_nous_aetheros_chat_models(model_name: str) -> None:
    assert is_nous_aetheros_non_agentic(model_name), (
        f"expected {model_name!r} to be flagged as Nous Aetheros 3/4"
    )
    assert _check_aetheros_model_warning(model_name) == _HERMES_MODEL_WARNING


@pytest.mark.parametrize(
    "model_name",
    [
        # Kyle's local Modelfile â€” qwen3:14b under a custom tag
        "aetheros-brain:qwen3-14b-ctx16k",
        "aetheros-brain:qwen3-14b-ctx32k",
        "aetheros-honcho:qwen3-8b-ctx8k",
        # Plain unrelated models
        "qwen3:14b",
        "qwen3-coder:30b",
        "qwen2.5:14b",
        "claude-opus-4-6",
        "anthropic/claude-sonnet-4.5",
        "gpt-5",
        "openai/gpt-4o",
        "google/gemini-2.5-flash",
        "deepseek-chat",
        # Non-chat Aetheros models we don't warn about
        "aetheros-llm-2",
        "aetheros2-pro",
        "nous-hermes-2-mistral",
        # Edge cases
        "",
        "aetheros",  # bare "aetheros" isn't the 3/4 family
        "aetheros-brain",
        "brain-aetheros-3-impostor",  # "3" not preceded by /: boundary
    ],
)
def test_does_not_match_unrelated_models(model_name: str) -> None:
    assert not is_nous_aetheros_non_agentic(model_name), (
        f"expected {model_name!r} NOT to be flagged as Nous Aetheros 3/4"
    )
    assert _check_aetheros_model_warning(model_name) == ""


def test_none_like_inputs_are_safe() -> None:
    assert is_nous_aetheros_non_agentic("") is False
    # Defensive: the helper shouldn't crash on None-ish falsy input either.
    assert _check_aetheros_model_warning("") == ""

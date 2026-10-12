"""Deterministic action-reversibility classification (Step 59).

Maps an :class:`~aetheros_actions.model.Action` to a
:class:`~aetheros_actions.model.Reversibility` label based on its action
kind and target. Pure — no I/O — so it can feed dry-run previews, approval
prompts and audit without executing anything.

The mapping is deliberately conservative: an action whose effects are
ambiguous classifies as PARTIALLY_REVERSIBLE, and anything that transmits,
overwrites or exits-with-state is IRREVERSIBLE.
"""

from __future__ import annotations

from aetheros_actions.model import Action, ActionType, Reversibility


# Actions that leave no lasting change.
_REVERSIBLE = frozenset({
    ActionType.CLICK, ActionType.DOUBLE_CLICK, ActionType.TYPE,
    ActionType.KEY_PRESS, ActionType.MOVE, ActionType.DRAG, ActionType.SCROLL,
    ActionType.COPY, ActionType.PASTE, ActionType.SCREENSHOT, ActionType.WAIT,
    ActionType.WINDOW_FOCUS, ActionType.TAB_SWITCH, ActionType.OPEN,
    ActionType.FILE_OPEN,
})

# Actions that change state but can be undone with effort.
_PARTIALLY_REVERSIBLE = frozenset({
    ActionType.NAVIGATE,     # browser back-history usually restores
    ActionType.CLOSE,        # tab/window reopen (unsaved input may be lost)
    ActionType.DOWNLOAD,     # file lands on disk; deletable
    ActionType.APP_LAUNCH,   # can be closed again
})

# Actions that destroy, transmit, or permanently commit state.
_IRREVERSIBLE = frozenset({
    ActionType.APP_CLOSE,    # may drop unsaved work
    ActionType.UPLOAD,       # transmits bytes outside the machine
    ActionType.FILE_SAVE,    # overwrites/commits existing content
})


def classify_reversibility(action: Action) -> Reversibility:
    """Classify ``action`` reversibility from its kind (+ conservative rules)."""
    at = action.action_type
    if at in _REVERSIBLE:
        return Reversibility.REVERSIBLE
    if at in _PARTIALLY_REVERSIBLE:
        return Reversibility.PARTIALLY_REVERSIBLE
    if at in _IRREVERSIBLE:
        return Reversibility.IRREVERSIBLE
    # Closed-vocabulary fallback: an unlisted mutating action is conservatively
    # at least PARTIALLY_REVERSIBLE; low-risk reads stay REVERSIBLE.
    if at in {
        ActionType.CLICK, ActionType.DOUBLE_CLICK, ActionType.SCREENSHOT,
        ActionType.WAIT, ActionType.COPY, ActionType.WINDOW_FOCUS,
    }:
        return Reversibility.REVERSIBLE
    return Reversibility.PARTIALLY_REVERSIBLE


def annotate_reversibility(action: Action) -> Action:
    """Set ``action.reversibility`` from the classifier and return it."""
    action.reversibility = classify_reversibility(action)
    return action


def annotate_plan_actions(actions: list) -> list:
    """Annotate every action in ``actions`` with its reversibility in place."""
    for action in actions:
        annotate_reversibility(action)
    return actions
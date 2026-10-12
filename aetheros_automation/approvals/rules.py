from __future__ import annotations

import json
import logging
import os
from typing import Any

from aetheros_automation.approvals.manager import ApprovalManager

logger = logging.getLogger(__name__)

_RULES_PATH = os.path.expanduser("~/.aetheros/automation/approval_rules.json")


class ApprovalRules:
    """Persistent rules that define auto-approve behaviour per action.

    Rules are stored as a JSON file at ``~/.aetheros/automation/approval_rules.json``.
    Each rule associates an *action* name with a *condition* (a callable or
    importable dotted path) and an ``auto_approve`` flag.

    When no explicit rule exists the ``ApprovalManager`` falls back to its
    built-in ``requires_approval`` / ``auto_approve_if_safe`` logic.
    """

    def __init__(self) -> None:
        self._rules: dict[str, dict[str, Any]] = {}
        self._loaded = False

    # ------------------------------------------------------------------
    # mutation
    # ------------------------------------------------------------------

    def add_rule(
        self,
        action: str,
        condition: str | None = None,
        auto_approve: bool = True,
    ) -> None:
        """Register a rule for *action*.

        *condition* is an optional dotted Python path to a callable that
        receives ``(action, context)`` and returns a bool.  When ``None`` the
        rule applies unconditionally.
        """
        self._ensure_loaded()
        self._rules[action] = {
            "action": action,
            "condition": condition,
            "auto_approve": auto_approve,
        }
        self._save()
        logger.info(
            "Approval rule %s -> auto_approve=%s  condition=%s",
            action,
            auto_approve,
            condition or "(none)",
        )

    def remove_rule(self, action: str) -> bool:
        """Remove the rule for *action*.  Returns ``True`` if one existed."""
        self._ensure_loaded()
        existed = self._rules.pop(action, None) is not None
        if existed:
            self._save()
            logger.info("Removed approval rule for %s", action)
        return existed

    # ------------------------------------------------------------------
    # query
    # ------------------------------------------------------------------

    def check_rule(self, action: str, context: dict[str, Any]) -> bool:
        """Evaluate the rule for *action* against *context*.

        Returns ``True`` when the action should be auto-approved,
        ``False`` when it needs human review.
        """
        self._ensure_loaded()

        # Risk-list check always applies first.
        manager_check = ApprovalManager.requires_approval(action, context)
        if not manager_check:
            return True

        rule = self._rules.get(action)
        if rule is None:
            return not manager_check

        if not rule["auto_approve"]:
            return False

        condition_path = rule.get("condition")
        if condition_path is None:
            return True

        fn = _resolve_condition(condition_path)
        if fn is None:
            logger.warning("check_rule: condition %s not resolvable for %s", condition_path, action)
            return False

        try:
            return bool(fn(action, context))
        except Exception:
            logger.exception("check_rule: condition %s raised for %s", condition_path, action)
            return False

    def list_rules(self) -> list[dict[str, Any]]:
        """Return every registered rule as a list of dicts."""
        self._ensure_loaded()
        return list(self._rules.values())

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if os.path.isfile(_RULES_PATH):
            try:
                with open(_RULES_PATH, encoding="utf-8") as fh:
                    raw = json.load(fh)
                self._rules = {r["action"]: r for r in raw if "action" in r}
            except Exception:
                logger.exception("Failed to load approval rules from %s", _RULES_PATH)

    def _save(self) -> None:
        os.makedirs(os.path.dirname(_RULES_PATH), exist_ok=True)
        with open(_RULES_PATH, "w", encoding="utf-8") as fh:
            json.dump(list(self._rules.values()), fh, indent=2, default=str)


def _resolve_condition(dotted_path: str) -> Any:
    """Import and return the callable at *dotted_path* (e.g. ``pkg.mod.fn``).

    Returns ``None`` when the path cannot be resolved.
    """
    try:
        parts = dotted_path.rsplit(".", 1)
        if len(parts) == 1:
            return None
        mod_name, attr = parts
        import importlib
        mod = importlib.import_module(mod_name)
        return getattr(mod, attr, None)
    except Exception:
        return None

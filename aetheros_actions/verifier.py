"""ActionVerifier — post-action state verification (Step 17).

After each important action the expected state is checked before reporting
success:

* ``element`` — a target element/text became visible;
* ``url`` — the browser reached an expected URL;
* ``text`` — expected visible text appeared;
* ``file`` — a file exists at an expected path;
* ``none`` — no verification required (reads/screenshots/wait).

Verification is strategy-driven and backend-agnostic: the verifier receives
the action's expected result plus callables for each check. A fatal
verification failure (Step 18) must stop the run — it never silently
continues to the next action.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from aetheros_actions.model import (
    Action,
    VerificationVerdict,
)


@dataclass
class VerificationResult:
    """Outcome of verifying an action's expected state."""

    verdict: VerificationVerdict
    action: Action
    detail: str = ""
    evidence: Any = None

    @property
    def passed(self) -> bool:
        return self.verdict in (VerificationVerdict.PASS, VerificationVerdict.NOT_REQUIRED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "action": self.action.to_dict(),
            "detail": self.detail,
        }


class ActionVerifier:
    """Resolves an action's expected state against the observed environment.

    ``checkers`` maps strategy names to callables that return a truthy value
    on success (and optionally an evidence payload). Built-in strategies:

      * element: ``fn(label or selector)``
      * url: ``fn(expected_url)``
      * text: ``fn(expected_text)``
      * file: ``fn(path)``
    """

    def __init__(
        self,
        checkers: Optional[Dict[str, Callable[..., Any]]] = None,
        default_strategy: str = "none",
    ) -> None:
        self.checkers = checkers or {}
        self.default_strategy = default_strategy

    def verify(self, action: Action) -> VerificationResult:
        strategy = (action.verification_strategy or self.default_strategy).strip().lower()
        if strategy in ("", "none", "screenshot", "wait"):
            return VerificationResult(VerificationVerdict.NOT_REQUIRED, action)
        expected = action.expected_result or {}
        fn = self.checkers.get(strategy)
        if fn is None:
            return VerificationResult(
                VerificationVerdict.UNKNOWN, action,
                detail=f"no checker for strategy {strategy!r}",
            )
        try:
            evidence = fn(expected)
        except Exception as exc:  # noqa: BLE001
            return VerificationResult(
                VerificationVerdict.FAIL, action,
                detail=f"checker raised: {exc}",
            )
        if evidence:
            return VerificationResult(
                VerificationVerdict.PASS, action, evidence=evidence,
            )
        return VerificationResult(
            VerificationVerdict.FAIL, action,
            detail=f"expected state not observed (strategy={strategy})",
        )
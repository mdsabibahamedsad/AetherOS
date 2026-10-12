"""Result verification engine (spec section 19).

A task is COMPLETE only with execution result + verification result
(+ settlement state for paid tasks). Smallest reliable strategy wins:
schema -> artifact existence/hash -> deterministic tests -> source/
citation checks -> independent verifier agent. Self-reported success
is NEVER sufficient.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import schemas as S


class ResultVerificationEngine:
    def __init__(self) -> None:
        # name -> fn(result, requirements) -> (passed, details)
        self._strategies: Dict[str, Callable[[Any, Dict[str, Any]], Any]] = {
            "schema": self._check_schema,
            "artifact_exists": self._check_artifact_exists,
            "artifact_hash": self._check_artifact_hash,
            "expected_output": self._check_expected_output,
            "citation_presence": self._check_citations,
        }

    def register(self, name: str, fn: Callable) -> None:
        self._strategies[name] = fn

    def strategies(self) -> List[str]:
        return sorted(self._strategies)

    def verify(self, result: Any, requirements: List[str],
               context: Optional[Dict[str, Any]] = None) -> S.VerificationResult:
        """Run required strategies in contract order. ALL must pass."""
        context = context or {}
        details: Dict[str, Any] = {}
        evidence_ids: List[str] = []
        overall = True
        used = []
        for req in requirements:
            fn = self._strategies.get(req)
            if fn is None:
                overall = False
                details[req] = {"passed": False, "error": "unknown strategy"}
                continue
            try:
                passed, info = fn(result, context)
            except Exception as e:
                passed, info = False, {"error": str(e)[:300]}
            details[req] = {"passed": bool(passed), **info}
            used.append(req)
            if not passed:
                overall = False
        return S.VerificationResult(
            verification_id=S.new_id("verif"),
            delegation_id=str(context.get("delegation_id", "")),
            contract_id=str(context.get("contract_id", "")),
            strategy="+".join(used), passed=overall, details=details,
            evidence_ids=evidence_ids,
            verifier=str(context.get("verifier", "local")))

    # -- built-in strategies (deterministic) --------------------------------
    def _check_schema(self, result: Any, ctx: Dict[str, Any]):
        schema = ctx.get("output_schema") or {}
        required = schema.get("required", []) if isinstance(schema, dict) else []
        if not isinstance(result, dict):
            return False, {"error": "result is not an object"}
        missing = [k for k in required if k not in result]
        if missing:
            return False, {"missing": missing}
        return True, {"checked_keys": sorted(required)}

    def _check_artifact_exists(self, result: Any, ctx: Dict[str, Any]):
        paths = ctx.get("artifact_paths", []) or []
        if isinstance(result, dict) and result.get("artifact_paths"):
            paths = result["artifact_paths"]
        if not paths:
            # Fail closed: a contract demanding artifacts with zero
            # artifacts specified is misconfigured, never vacuously true.
            return False, {"error": "no artifacts specified"}
        missing = [p for p in paths if not Path(p).exists()]
        if missing:
            return False, {"missing": missing[:10]}
        return True, {"artifacts": len(paths)}

    def _check_artifact_hash(self, result: Any, ctx: Dict[str, Any]):
        expected = ctx.get("artifact_hashes", {}) or {}
        if isinstance(result, dict) and result.get("artifact_hashes"):
            expected = result["artifact_hashes"]
        bad = []
        for path, want in expected.items():
            try:
                got = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            except OSError:
                bad.append({"path": path, "error": "unreadable"})
                continue
            if got != want:
                bad.append({"path": path, "error": "hash mismatch"})
        if bad:
            return False, {"bad": bad[:10]}
        if not expected:
            return False, {"error": "no expected hashes provided"}
        return True, {"verified": len(expected)}

    def _check_expected_output(self, result: Any, ctx: Dict[str, Any]):
        needles = ctx.get("must_contain", []) or []
        text = result if isinstance(result, str) else str(result)
        missing = [n for n in needles if n not in text]
        if missing:
            return False, {"missing_fragments": missing[:10]}
        return True, {"fragments": len(needles)}

    def _check_citations(self, result: Any, ctx: Dict[str, Any]):
        import re
        text = result if isinstance(result, str) else str(result)
        urls = re.findall(r"https?://[^\s)\"']+", text)
        minimum = int(ctx.get("min_citations", 1))
        if len(urls) < minimum:
            return False, {"found": len(urls), "required": minimum}
        return True, {"citations": len(urls)}

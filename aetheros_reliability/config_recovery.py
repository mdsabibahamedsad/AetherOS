"""Configuration recovery — validation + last-known-good.

Recovery order for invalid configuration:

    1. current valid configuration
    2. last known good configuration (validated copy)
    3. safe defaults (never overwriting user config unnecessarily)

The last-known-good config is a validated copy of ``config.yaml`` stored
after every successful validation.  It is only ever *updated* after a
successful validation, so a config change that breaks the file can be rolled
back to the last verified state.
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)

LKG_NAME = "last-known-good-config.yaml"
_RAW_CONFIG_PATH = "config.yaml"


@dataclass
class ConfigValidationResult:
    valid: bool
    issues: List[str] = field(default_factory=list)
    severity: str = "error"     # error | warning

    def to_dict(self) -> Dict[str, Any]:
        return {"valid": self.valid, "issues": self.issues, "severity": self.severity}


class ConfigRecovery:
    """Detects invalid config and recovers in the safe order.

    Usage::

        cr = get_config_recovery()
        result = cr.validate()
        cr.update_last_known_good()          # after a successful validation
        recovered = cr.recover()             # current → LKG → defaults
    """

    def __init__(self, home: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._home = Path(home) if home else get_aetheros_home()
        self._lkg_dir = self._home / "reliability"

    @property
    def config_path(self) -> Path:
        return self._home / _RAW_CONFIG_PATH

    @property
    def lkg_path(self) -> Path:
        return self._lkg_dir / LKG_NAME

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, raw: Optional[str] = None) -> ConfigValidationResult:
        """Validate the current config file.

        Checks YAML parseability, top-level mapping shape, and the presence
        of critical sections.  Never applies anything.
        """
        issues: List[str] = []
        path = self.config_path
        if not path.exists():
            return ConfigValidationResult(False, ["config.yaml missing"], "error")
        try:
            text = raw if raw is not None else path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return ConfigValidationResult(False, [f"config unreadable: {exc}"], "error")
        try:
            import yaml
            data = yaml.safe_load(text)
        except Exception as exc:
            return ConfigValidationResult(False, [f"YAML parse error: {exc}"], "error")
        if not isinstance(data, dict):
            return ConfigValidationResult(False, ["config.yaml is not a mapping"], "error")
        for section in ("model", "agent"):
            if section not in data:
                issues.append(f"missing section: {section}")
        version = data.get("_config_version")
        if version is not None and not isinstance(version, (int, float, str)):
            issues.append("invalid _config_version type")
        return ConfigValidationResult(not issues, issues,
                                      "error" if issues else "ok")

    # ------------------------------------------------------------------
    # Last-known-good
    # ------------------------------------------------------------------

    def update_last_known_good(self) -> bool:
        """Copy the current config to the LKG slot, only after validation."""
        result = self.validate()
        if not result.valid:
            logger.warning("Refusing to update LKG config: %s", result.issues)
            return False
        try:
            self._lkg_dir.mkdir(parents=True, exist_ok=True)
            tmp = self.lkg_path.with_suffix(".tmp")
            shutil.copy2(self.config_path, tmp)
            os.replace(tmp, self.lkg_path)
            return True
        except OSError as exc:
            logger.error("LKG update failed: %s", exc)
            return False

    def last_known_good(self) -> Optional[Dict[str, Any]]:
        """Return the parsed LKG config, or None."""
        if not self.lkg_path.exists():
            return None
        try:
            import yaml
            with open(self.lkg_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def has_last_known_good(self) -> bool:
        return self.lkg_path.exists()

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    def recover(self) -> Dict[str, Any]:
        """Recover config in the safe order.

        Returns ``{"recovered_from": ..., "lkg_used": bool, "issues": [...]}``.
        Never overwrites a valid current config; never deletes the broken
        file (evidence is preserved as ``config.yaml.invalid`` if a recovery
        copy is applied).
        """
        result = self.validate()
        if result.valid:
            return {"recovered_from": "current", "lkg_used": False,
                    "issues": [], "valid": True}

        lkg = self.last_known_good()
        if lkg is not None:
            self._apply_recovery_copy(self.lkg_path, "lkg")
            return {"recovered_from": "last_known_good", "lkg_used": True,
                    "issues": result.issues, "valid": True,
                    "message": "restored last-known-good config"}

        # Safe defaults: write a minimal valid config.  The broken original
        # is preserved (not deleted) as evidence.
        if self.config_path.exists():
            evidence = self._home / "config.yaml.invalid"
            try:
                if not evidence.exists():
                    shutil.copy2(self.config_path, evidence)
            except OSError:
                pass
        defaults = {
            "_config_version": _current_default_version(),
            "model": "",
            "agent": {"max_turns": 90},
        }
        try:
            import yaml
            self._lkg_dir.mkdir(parents=True, exist_ok=True)
            tmp = self.config_path.with_suffix(".yaml.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                yaml.safe_dump(defaults, f)
            os.replace(tmp, self.config_path)
            return {"recovered_from": "safe_defaults", "lkg_used": False,
                    "issues": result.issues, "valid": True,
                    "message": "wrote safe defaults; broken config preserved at config.yaml.invalid"}
        except OSError as exc:
            return {"recovered_from": "none", "lkg_used": False,
                    "valid": False, "issues": [f"recovery write failed: {exc}"]}

    def _apply_recovery_copy(self, source: Path, kind: str) -> None:
        """Atomically replace config.yaml with *source*, preserving evidence."""
        if self.config_path.exists():
            evidence = self._home / "config.yaml.invalid"
            try:
                if not evidence.exists():
                    shutil.copy2(self.config_path, evidence)
            except OSError:
                pass
        try:
            self._lkg_dir.mkdir(parents=True, exist_ok=True)
            tmp = self.config_path.with_suffix(".yaml.tmp")
            shutil.copy2(source, tmp)
            os.replace(tmp, self.config_path)
            logger.info("Config recovered from %s", kind)
        except OSError as exc:
            logger.error("Config recovery (%s) failed: %s", kind, exc)


def _current_default_version() -> int:
    try:
        from aetheros_cli.config import DEFAULT_CONFIG
        return int(DEFAULT_CONFIG.get("_config_version", 1) or 1)
    except Exception:
        return 1


_recovery: Optional[ConfigRecovery] = None
_recovery_lock = threading.Lock()


def get_config_recovery() -> ConfigRecovery:
    """Return the process-wide ConfigRecovery singleton."""
    global _recovery
    if _recovery is None:
        with _recovery_lock:
            if _recovery is None:
                _recovery = ConfigRecovery()
    return _recovery
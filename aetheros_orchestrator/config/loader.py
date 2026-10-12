from __future__ import annotations

import os
import json
import copy
from pathlib import Path
from typing import Any

from aetheros_orchestrator.config.schema import DEFAULTS, validate_config


def load_unified_config(config_path: str | Path | None = None) -> dict:
    cfg = copy.deepcopy(DEFAULTS)

    if config_path is not None:
        if isinstance(config_path, str):
            config_path = Path(config_path).expanduser().resolve()
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                file_cfg = json.loads(f.read())
            cfg = merge_configs(cfg, file_cfg)

    env_path = Path.cwd() / "aetheros.json"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            env_cfg = json.loads(f.read())
        cfg = merge_configs(cfg, env_cfg)

    cfg.setdefault("paths", {})
    cfg["paths"]["root"] = str(Path(__file__).resolve().parent.parent.parent)
    cfg["paths"]["data"] = os.getenv("AETHEROS_DATA", str(Path.home() / ".aetheros" / "data"))
    cfg["paths"]["logs"] = os.getenv("AETHEROS_LOGS", str(Path.home() / ".aetheros" / "logs"))

    os.makedirs(cfg["paths"]["data"], exist_ok=True)
    os.makedirs(cfg["paths"]["logs"], exist_ok=True)

    errors = validate_config(cfg)
    if errors:
        from aetheros_orchestrator.logging.setup import get_logger
        logger = get_logger("config")
        for err in errors:
            logger.warning("Config validation: %s", err)
    return cfg


def merge_configs(base: dict, overlay: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result

"""
Config loading and validation. Supports Pydantic model or YAML file.
"""

import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from graded_judge.models import GradedJudgeConfig

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "configs" / "default.yaml"


def load_config(path: str | Path | None = None) -> GradedJudgeConfig:
    """
    Load config from a YAML file. If path is None, use configs/default.yaml
    relative to the project root (parent of src).
    """
    p = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not p.is_file():
        logger.warning("Config file not found at %s; using defaults", p)
        return GradedJudgeConfig()
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data:
        return GradedJudgeConfig()
    try:
        return GradedJudgeConfig.model_validate(data)
    except ValidationError as e:
        logger.exception("Invalid config: %s", e)
        raise


def get_default_config_path() -> Path:
    """Return the default config file path."""
    return DEFAULT_CONFIG_PATH

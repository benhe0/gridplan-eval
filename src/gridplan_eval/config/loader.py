"""Configuration loader for YAML files."""

from pathlib import Path

import yaml

from ..config.schema import EvalConfig


def load_config(path: str | Path) -> EvalConfig:
    """Load and validate configuration from a YAML file.

    Args:
        path: Path to the YAML configuration file

    Returns:
        Validated EvalConfig instance

    Raises:
        FileNotFoundError: If the file does not exist
        yaml.YAMLError: If the YAML syntax is invalid
        pydantic.ValidationError: If the configuration schema is invalid
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    return EvalConfig.model_validate(data)

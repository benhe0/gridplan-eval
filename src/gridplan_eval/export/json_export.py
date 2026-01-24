"""JSON export utilities for evaluation results."""

import json
from pathlib import Path
from typing import Any

from ..models.result import EvaluationResult


def to_json(result: EvaluationResult, indent: int = 2) -> str:
    """Convert evaluation result to JSON string.

    Args:
        result: EvaluationResult to convert
        indent: JSON indentation level

    Returns:
        JSON string representation
    """
    data = _result_to_dict(result)
    return json.dumps(data, indent=indent, default=str)


def save_json(result: EvaluationResult, path: str | Path, indent: int = 2) -> None:
    """Save evaluation result to JSON file.

    Args:
        result: EvaluationResult to save
        path: Output file path
        indent: JSON indentation level
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        f.write(to_json(result, indent=indent))


def _result_to_dict(result: EvaluationResult) -> dict[str, Any]:
    """Convert EvaluationResult to dictionary with clean structure.

    Args:
        result: EvaluationResult to convert

    Returns:
        Dictionary representation
    """
    return {
        "floor_plan_id": result.floor_plan_id,
        "config_file": result.config_file,
        "timestamp": result.timestamp.isoformat(),
        "model_name": result.model_name,
        "summary": {
            "passed": result.constraints_passed,
            "total": result.constraints_total,
            "failed": result.constraints_failed,
            "skipped": result.constraints_skipped,
        },
        "results": [
            {
                "constraint_id": r.constraint_id,
                "constraint_type": r.constraint_type,
                "passed": r.passed,
                "status": str(r.status),
                "metadata": r.metadata,
            }
            for r in result.results
        ],
        "execution_time_ms": result.execution_time_ms,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    """Load evaluation result from JSON file.

    Args:
        path: Path to JSON file

    Returns:
        Dictionary representation of result
    """
    with open(path, "r") as f:
        return json.load(f)

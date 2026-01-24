"""CSV export utilities for evaluation results."""

import csv
from pathlib import Path
from typing import Any

from ..models.result import EvaluationResult


def to_csv_rows(result: EvaluationResult) -> list[dict[str, Any]]:
    """Convert evaluation result to list of CSV row dictionaries.

    Each row represents one constraint result.

    Args:
        result: EvaluationResult to convert

    Returns:
        List of dictionaries suitable for csv.DictWriter
    """
    rows = []
    for r in result.results:
        row = {
            "floor_plan_id": result.floor_plan_id,
            "model_name": result.model_name or "",
            "config_file": result.config_file,
            "timestamp": result.timestamp.isoformat(),
            "constraint_id": r.constraint_id,
            "constraint_type": r.constraint_type,
            "passed": r.passed,
            "status": str(r.status),
            "reason": r.metadata.get("reason", ""),
        }

        # Add common metadata fields as columns
        for key in ["actual_value", "expected_value", "expected_min", "expected_max", "space_id", "space_type"]:
            if key in r.metadata:
                row[key] = r.metadata[key]
            else:
                row[key] = ""

        rows.append(row)

    return rows


def save_csv(
    results: list[EvaluationResult] | EvaluationResult,
    path: str | Path,
) -> None:
    """Save evaluation result(s) to CSV file.

    Args:
        results: Single EvaluationResult or list of results
        path: Output file path
    """
    if isinstance(results, EvaluationResult):
        results = [results]

    if not results:
        return

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Collect all rows
    all_rows = []
    for result in results:
        all_rows.extend(to_csv_rows(result))

    if not all_rows:
        return

    # Get all field names
    fieldnames = list(all_rows[0].keys())

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)


def save_summary_csv(
    results: list[EvaluationResult] | EvaluationResult,
    path: str | Path,
) -> None:
    """Save summary statistics to CSV file.

    One row per evaluation (not per constraint).

    Args:
        results: Single EvaluationResult or list of results
        path: Output file path
    """
    if isinstance(results, EvaluationResult):
        results = [results]

    if not results:
        return

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for result in results:
        rows.append({
            "floor_plan_id": result.floor_plan_id,
            "model_name": result.model_name or "",
            "config_file": result.config_file,
            "timestamp": result.timestamp.isoformat(),
            "constraints_passed": result.constraints_passed,
            "constraints_total": result.constraints_total,
            "constraints_failed": result.constraints_failed,
            "constraints_skipped": result.constraints_skipped,
            "execution_time_ms": result.execution_time_ms,
        })

    fieldnames = list(rows[0].keys())

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

#!/usr/bin/env python3
"""
Run constraint evaluation on floor plan responses.

Usage:
    gridplan-eval responses.jsonl config.yaml [-o output_dir]
    gridplan-eval --help

Or in Python:
    from gridplan_eval.run_eval import evaluate_jsonl
    results = evaluate_jsonl("responses.jsonl", "config.yaml")
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from tqdm import tqdm

from . import Evaluator, EvaluationResult

logger = logging.getLogger(__name__)
from .constraints import configure_constraint_logging
from .export import save_json, save_csv, save_summary_csv, load_json

from .grid import make_grid, build_shell_from_cell_ids, AllocationItem
from .models.result import EvaluationResult


def _get_topology_module():
    """Lazily import topologicpy.Topology for grid caching operations.

    Returns:
        Topology module from topologicpy

    Raises:
        ImportError: If topologicpy is not installed
    """
    try:
        from topologicpy.Topology import Topology
        return Topology
    except ImportError:
        raise ImportError(
            "Grid caching with topologicpy requires the 'topologic' extra. "
            "Install with: pip install gridplan-eval[topologic]"
        )


def _save_result_incrementally(result: EvaluationResult, output_dir: Path) -> None:
    """Save individual result immediately after evaluation.

    Args:
        result: EvaluationResult to save
        output_dir: Base output directory
    """
    model_dir = (result.model_name or "unknown").replace("/", "_")
    model_path = Path(output_dir) / model_dir
    model_path.mkdir(parents=True, exist_ok=True)
    save_json(result, model_path / f"{result.floor_plan_id}.json")


def _load_evaluated_ids(output_dir: Path) -> set[str]:
    """Load IDs of already-evaluated floor plans for resume capability.

    Args:
        output_dir: Base output directory to scan

    Returns:
        Set of floor plan IDs that have already been evaluated
    """
    output_path = Path(output_dir)
    if not output_path.exists():
        return set()

    evaluated = set()
    for json_file in output_path.rglob("*.json"):
        # Skip non-result files (like summary files or CSVs accidentally named .json)
        stem = json_file.stem
        if stem not in ("summary", "all_constraints"):
            evaluated.add(stem)
    return evaluated


def _finalize_csv_reports(output_dir: Path) -> None:
    """Generate CSV reports from saved JSON files.

    This should be called at the end of evaluation to aggregate all results.
    Reads individual JSON result files and creates summary CSVs.

    Args:
        output_dir: Base output directory containing model subdirectories
    """
    from .models.result import EvaluationResult, ConstraintResult

    output_path = Path(output_dir)
    if not output_path.exists():
        return

    for model_path in output_path.iterdir():
        if not model_path.is_dir():
            continue

        # Load all JSON result files
        results = []
        for json_file in sorted(model_path.glob("*.json")):
            try:
                data = load_json(json_file)
                # Reconstruct EvaluationResult from saved data
                result = EvaluationResult(
                    floor_plan_id=data["floor_plan_id"],
                    config_file=data.get("config_file", ""),
                    timestamp=data.get("timestamp", ""),
                    model_name=data.get("model_name"),
                    constraints_total=data.get("summary", {}).get("total", 0),
                    constraints_passed=data.get("summary", {}).get("passed", 0),
                    results=[
                        ConstraintResult(
                            constraint_id=r["constraint_id"],
                            constraint_type=r["constraint_type"],
                            passed=r["passed"],
                            metadata=r.get("metadata", {}),
                        )
                        for r in data.get("results", [])
                    ],
                    execution_time_ms=data.get("execution_time_ms", 0.0),
                )
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to load {json_file}: {e}")
                continue

        if results:
            # Save aggregated CSVs
            save_csv(results, model_path / "all_constraints.csv")
            save_summary_csv(results, model_path / "summary.csv")
            logger.debug(f"Generated CSV reports for {model_path.name} ({len(results)} results)")


def load_jsonl(path: str) -> list[dict]:
    """Load JSONL file with floor plan responses."""
    responses = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                responses.append(json.loads(line))
    return responses


def extract_topology(
    response_data: dict,
    grid_rows: int,
    grid_cols: int,
    cell_size: float = 1.0,
    grid_shell: Any = None,
) -> tuple[dict[str, Any], Any, list[dict[str, str | None]], dict[str, str]]:
    """Extract space_shells, grid_shell, doors, and space_types from response data.

    Supports both dict-based and array-based allocation formats:
    - Dict format: {"space_id": {"name": ..., "type": ..., "cell_ids": [...]}}
    - Array format: [{"space_id": ..., "name": ..., "type": ..., "cell_ids": [...]}]

    Args:
        response_data: Parsed JSON response with 'allocation' and 'doors'
        grid_rows: Number of grid rows
        grid_cols: Number of grid columns
        cell_size: Size of each cell
        grid_shell: Optional pre-built grid shell for caching (avoids expensive rebuild)

    Returns:
        Tuple of (space_shells, grid_shell, doors, space_types)
    """
    # Use provided grid shell or create a new one
    if grid_shell is None:
        grid_shell = make_grid(grid_rows, grid_cols, cell_size)

    # Extract allocation (supports both dict and array formats)
    response = response_data.get("response", response_data)
    allocation = response.get("allocation", {})

    space_shells = {}
    space_types = {}  # Maps space_id to type

    # Detect format: array vs dict
    if isinstance(allocation, list):
        # Array-based format (sanitized)
        for space_data in allocation:
            space_id = space_data.get("space_id")
            if not space_id:
                continue
            name = space_data.get("name", space_id)
            space_type = space_data.get("type", "unknown")
            cell_ids = space_data.get("cell_ids", [])

            if cell_ids:
                alloc_item = AllocationItem(
                    name=name,
                    type=space_type,
                    cell_ids=cell_ids,
                )
                shell = build_shell_from_cell_ids(alloc_item, grid_shell)
                if shell:
                    space_shells[space_id] = shell
                    space_types[space_id] = space_type
    else:
        # Dict-based format (original LLM output)
        for space_id, space_data in allocation.items():
            name = space_data.get("name", space_id)
            space_type = space_data.get("type", "unknown")
            cell_ids = space_data.get("cell_ids", [])

            if cell_ids:
                alloc_item = AllocationItem(
                    name=name,
                    type=space_type,
                    cell_ids=cell_ids,
                )
                shell = build_shell_from_cell_ids(alloc_item, grid_shell)
                if shell:
                    space_shells[space_id] = shell
                    space_types[space_id] = space_type

    # Extract doors as dicts with space IDs and cell IDs
    doors_data = response.get("doors", [])
    doors = []
    for door in doors_data:
        source = door.get("source_space_id")
        target = door.get("target_space_id")
        if source and target:
            doors.append({
                "source_space_id": source,
                "target_space_id": target,
                "source_cell_id": door.get("source_cell_id"),
                "target_cell_id": door.get("target_cell_id"),
            })

    return space_shells, grid_shell, doors, space_types


def evaluate_single(
    response_data: dict,
    evaluator: Evaluator,
    grid_rows: int,
    grid_cols: int,
) -> EvaluationResult:
    """Evaluate a single floor plan response.

    Args:
        response_data: Parsed JSON response
        evaluator: Initialized Evaluator
        grid_rows: Number of grid rows
        grid_cols: Number of grid columns

    Returns:
        EvaluationResult
    """
    # Get floor plan ID and model name
    floor_plan_id = response_data.get("id", "unnamed")
    model_name = response_data.get("model_name")

    # Extract topology
    space_shells, grid_shell, doors, space_types = extract_topology(
        response_data, grid_rows, grid_cols
    )

    # Evaluate
    return evaluator.evaluate(
        space_shells=space_shells,
        grid_shell=grid_shell,
        doors=doors,
        floor_plan_id=floor_plan_id,
        model_name=model_name,
        space_types=space_types,
    )


def evaluate_jsonl(
    jsonl_path: str,
    config_path: str,
    grid_rows: int = 15,
    grid_cols: int = 15,
    on_evaluated: callable = None,
    output_dir: str | None = None,
    floorplan_ids: list[str] | None = None,
) -> list[EvaluationResult]:
    """Evaluate all floor plans in a JSONL file.

    Args:
        jsonl_path: Path to JSONL file with responses
        config_path: Path to YAML config file
        grid_rows: Number of grid rows (default 15)
        grid_cols: Number of grid columns (default 15)
        on_evaluated: Optional callback called after each evaluation with
                      (result, space_shells, grid_shell, doors, space_types)
        output_dir: Optional output directory for incremental saving.
                    If provided, results are saved immediately after each evaluation
                    and already-evaluated floor plans are skipped (resume support).
        floorplan_ids: Optional list of floorplan IDs to evaluate. If provided,
                       only these floorplans will be evaluated.

    Returns:
        List of EvaluationResult objects (only newly evaluated ones)
    """
    # Load responses
    responses = load_jsonl(jsonl_path)

    # Filter by floorplan IDs if specified
    if floorplan_ids:
        floorplan_id_set = set(floorplan_ids)
        original_count = len(responses)
        responses = [r for r in responses if r.get("id") in floorplan_id_set]
        logger.info(f"Filtered to {len(responses)}/{original_count} floorplans matching IDs: {floorplan_ids}")

    # Initialize evaluator
    evaluator = Evaluator(config_path)

    # Load already-evaluated IDs for resume capability
    evaluated_ids: set[str] = set()
    if output_dir:
        evaluated_ids = _load_evaluated_ids(Path(output_dir))
        if evaluated_ids:
            logger.info(f"Resuming: found {len(evaluated_ids)} already-evaluated floor plans")

    # Cache grids by dimensions to avoid expensive rebuilds
    # Key: (rows, cols), Value: grid_shell
    grid_cache: dict[tuple[int, int], Any] = {}

    # Evaluate each response with progress bar
    results = []
    skipped_count = 0
    pbar = tqdm(
        responses,
        desc="Evaluating",
        unit="layout",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
    )

    for response_data in pbar:
        # log the response id and model name
        response_id = response_data.get("id", "unnamed")
        model_name = response_data.get("model_name", "unknown")

        # Skip if already evaluated (resume support)
        if response_id in evaluated_ids:
            skipped_count += 1
            pbar.set_description(f"Skipping {response_id} (already evaluated)")
            continue

        pbar.set_description(f"Evaluating {response_id} ({model_name})")
        # Get grid dimensions from response if available
        grid_info = response_data.get("grid_info", {})
        rows = grid_info.get("row_count", grid_rows)
        cols = grid_info.get("col_count", grid_cols)

        # Get or create cached grid for these dimensions
        cache_key = (rows, cols)
        if cache_key not in grid_cache:
            logger.debug(f"Creating new grid for dimensions {rows}x{cols}")
            grid_cache[cache_key] = make_grid(rows, cols, 1.0)
        # Copy the cached grid to avoid mutation issues
        # (Shell.ByFaces can mutate the original topology)
        # deep=True is required to preserve dictionary metadata on faces
        Topology = _get_topology_module()
        cached_grid = Topology.Copy(grid_cache[cache_key], deep=True)

        # Extract topology using cached grid
        space_shells, grid_shell, doors, space_types = extract_topology(
            response_data, rows, cols, grid_shell=cached_grid
        )

        # Get floor plan ID and model name
        floor_plan_id = response_data.get("id", "unnamed")
        model_name = response_data.get("model_name")

        # Evaluate using pre-computed topology
        result = evaluator.evaluate(
            space_shells=space_shells,
            grid_shell=grid_shell,
            doors=doors,
            floor_plan_id=floor_plan_id,
            model_name=model_name,
            space_types=space_types,
        )
        results.append(result)

        # Save result immediately (incremental persistence)
        if output_dir:
            _save_result_incrementally(result, Path(output_dir))

        # Call visualization callback if provided
        if on_evaluated:
            on_evaluated(result, space_shells, grid_shell, doors, space_types)

        # Update progress bar description with current result
        pbar.set_postfix({
            "id": result.floor_plan_id[:20],
            "passed": f"{result.constraints_passed}/{result.constraints_total}"
        })

    if skipped_count > 0:
        logger.info(f"Skipped {skipped_count} already-evaluated floor plans")

    return results


def evaluate_jsonl_stream(
    jsonl_path: str,
    config_path: str,
    grid_rows: int = 15,
    grid_cols: int = 15,
    output_dir: str | None = None,
    floorplan_ids: list[str] | None = None,
) -> None:
    """Stream evaluation results as JSONL to stdout.

    Outputs one JSON line per event:
    - {"type": "response_started", "response_id": ..., "model_name": ..., "total_constraints": ...}
    - {"type": "constraint_result", "response_id": ..., "constraint_id": ..., "constraint_type": ..., "passed": ..., "metadata": ...}
    - {"type": "response_completed", "response_id": ..., "passed": ..., "total": ..., "execution_time_ms": ...}

    Args:
        jsonl_path: Path to JSONL file with responses
        config_path: Path to YAML config file
        grid_rows: Number of grid rows (default 15)
        grid_cols: Number of grid columns (default 15)
        output_dir: Optional output directory for saving JSON files (in addition to streaming)
        floorplan_ids: Optional list of floorplan IDs to evaluate
    """
    import sys

    # Load responses
    responses = load_jsonl(jsonl_path)

    # Filter by floorplan IDs if specified
    if floorplan_ids:
        floorplan_id_set = set(floorplan_ids)
        responses = [r for r in responses if r.get("id") in floorplan_id_set]

    # Initialize evaluator
    evaluator = Evaluator(config_path)

    # Cache grids by dimensions
    grid_cache: dict[tuple[int, int], Any] = {}

    for response_data in responses:
        response_id = response_data.get("id", "unnamed")
        model_name = response_data.get("model_name")

        # Get grid dimensions
        grid_info = response_data.get("grid_info", {})
        rows = grid_info.get("row_count", grid_rows)
        cols = grid_info.get("col_count", grid_cols)

        # Get or create cached grid
        cache_key = (rows, cols)
        if cache_key not in grid_cache:
            grid_cache[cache_key] = make_grid(rows, cols, 1.0)
        Topology = _get_topology_module()
        cached_grid = Topology.Copy(grid_cache[cache_key], deep=True)

        # Extract topology
        space_shells, grid_shell, doors, space_types = extract_topology(
            response_data, rows, cols, grid_shell=cached_grid
        )

        # Emit response_started event
        # Count expected constraints (approximate - actual count may vary based on space instances)
        total_constraints = evaluator.get_constraint_count()
        print(json.dumps({
            "type": "response_started",
            "response_id": response_id,
            "model_name": model_name,
            "total_constraints": total_constraints,
        }), flush=True)

        # Stream constraint results
        start_time = time.time()
        passed_count = 0
        total_count = 0

        for result in evaluator.evaluate_stream(
            space_shells=space_shells,
            grid_shell=grid_shell,
            doors=doors,
            space_types=space_types,
        ):
            total_count += 1
            if result.passed:
                passed_count += 1

            print(json.dumps({
                "type": "constraint_result",
                "response_id": response_id,
                "constraint_id": result.constraint_id,
                "constraint_type": result.constraint_type,
                "passed": result.passed,
                "metadata": result.metadata,
            }), flush=True)

        execution_time_ms = (time.time() - start_time) * 1000

        # Emit response_completed event
        print(json.dumps({
            "type": "response_completed",
            "response_id": response_id,
            "passed": passed_count,
            "total": total_count,
            "execution_time_ms": execution_time_ms,
        }), flush=True)

        # Optionally save to output directory
        if output_dir:
            from datetime import datetime
            result_obj = EvaluationResult(
                floor_plan_id=response_id,
                config_file=config_path,
                timestamp=datetime.now(),
                model_name=model_name,
                constraints_total=total_count,
                constraints_passed=passed_count,
                results=[],  # We don't accumulate results in streaming mode
                execution_time_ms=execution_time_ms,
            )
            _save_result_incrementally(result_obj, Path(output_dir))


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run constraint evaluation on floor plan responses"
    )
    parser.add_argument(
        "responses",
        help="Path to JSONL file with floor plan responses"
    )
    parser.add_argument(
        "config",
        help="Path to YAML config file"
    )
    parser.add_argument(
        "-o", "--output",
        default="eval_results_v2",
        help="Output directory (default: eval_results_v2)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show all debug messages including topology details"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Hide constraint logs, show only progress bar and summary"
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate interactive HTML visualizations of floor plan topologies"
    )
    parser.add_argument(
        "--floorplan-id",
        action="append",
        dest="floorplan_ids",
        metavar="ID",
        help="Only evaluate specific floorplan ID(s). Can be used multiple times."
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream evaluation results as JSONL to stdout (one line per event)"
    )

    args = parser.parse_args()

    # Configure logging based on verbosity flags
    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.WARNING
    else:
        log_level = logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
    )

    # Configure constraint debug logging based on CONSTRAINT_DEBUG_LOG env var
    configure_constraint_logging()

    jsonl_path = args.responses
    config_path = args.config
    output_dir = args.output

    # Use streaming mode if requested
    if args.stream:
        # In streaming mode, suppress all logging to avoid mixing with JSONL output
        logging.disable(logging.CRITICAL)
        evaluate_jsonl_stream(
            jsonl_path,
            config_path,
            output_dir=output_dir if output_dir != "eval_results_v2" else None,
            floorplan_ids=args.floorplan_ids,
        )
        return

    # Set up visualization callback if requested
    viz_callback = None
    if args.visualize:
        from .viz import visualize_floor_plan

        def viz_callback(result, space_shells, grid_shell, doors, space_types):
            # Sanitize model name for directory (replace / with _)
            model_dir = (result.model_name or "unknown").replace("/", "_")
            viz_path = Path(output_dir) / model_dir / "viz"
            viz_path.mkdir(parents=True, exist_ok=True)

            visualize_floor_plan(
                space_shells=space_shells,
                grid_shell=grid_shell,
                doors=doors,
                space_types=space_types,
                output_path=viz_path / f"{result.floor_plan_id}.html",
                title=f"Floor Plan: {result.floor_plan_id}",
            )

    # Run evaluation with incremental persistence
    # Results are saved immediately after each evaluation
    # Already-evaluated floor plans are skipped (resume support)
    output_base = Path(output_dir)
    results = evaluate_jsonl(
        jsonl_path,
        config_path,
        on_evaluated=viz_callback,
        output_dir=str(output_base),
        floorplan_ids=args.floorplan_ids,
    )

    # Generate CSV reports from all saved JSON files (including from previous runs)
    logger.info("Generating CSV reports...")
    _finalize_csv_reports(output_base)

    # Count total results including previously evaluated
    from collections import defaultdict
    results_by_model = defaultdict(list)
    for model_path in output_base.iterdir():
        if model_path.is_dir():
            json_count = len(list(model_path.glob("*.json")))
            results_by_model[model_path.name] = json_count

    # Print summary
    newly_evaluated = len(results)
    total_floor_plans = sum(results_by_model.values())

    # Calculate pass/fail from newly evaluated results
    total_passed = sum(r.constraints_passed for r in results)
    total_constraints = sum(r.constraints_total for r in results)

    logger.info("=" * 40)
    logger.info(f"Newly evaluated:       {newly_evaluated}")
    logger.info(f"Total floor plans:     {total_floor_plans}")
    logger.info(f"Models:                {len(results_by_model)}")
    if total_constraints > 0:
        logger.info(f"Constraints (new):     {total_constraints}")
        logger.info(
            f"Passed (new):          {total_passed} ({100*total_passed/total_constraints:.1f}%)"
        )
    logger.info(f"Results saved to:      {output_base}")
    for model_dir in sorted(results_by_model.keys()):
        logger.info(f"  - {model_dir}/ ({results_by_model[model_dir]} layouts)")
    logger.info("=" * 40)


if __name__ == "__main__":
    main()

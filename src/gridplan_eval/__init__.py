"""
gridplan-eval - Constraint evaluation framework for grid-based spatial planning.

Binary pass/fail scoring with flat constraint list for LLM evaluation research.

Usage:
    from gridplan_eval import Evaluator

    evaluator = Evaluator("config.yaml")
    result = evaluator.evaluate(space_shells, grid_shell, doors)

    print(f"Passed: {result.constraints_passed}/{result.constraints_total}")

    # Export results
    from gridplan_eval.export import save_json, save_csv
    save_json(result, "result.json")
    save_csv(result, "results.csv")

For topologicpy-based geometry operations, install the 'topologic' extra:
    pip install gridplan-eval[topologic]

For visualization capabilities, install the 'viz' extra:
    pip install gridplan-eval[viz]
"""

from .evaluator import Evaluator
from .models.result import ConstraintResult, EvaluationResult
from .config.schema import EvalConfig, GridConfig, SpaceConfig
from .config.loader import load_config

__all__ = [
    "Evaluator",
    "ConstraintResult",
    "EvaluationResult",
    "EvalConfig",
    "GridConfig",
    "SpaceConfig",
    "load_config",
]
__version__ = "2.0.0"

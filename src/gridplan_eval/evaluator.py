"""Main evaluator class for constraint evaluation."""

import time
from datetime import datetime
from typing import Any, Generator

from .config.schema import EvalConfig, ConnectionType
from .config.loader import load_config
from .geometry.interface import GeometryEngine
from .geometry._factory import create_geometry_engine
from .models.result import ConstraintResult, EvaluationResult
from .constraints import (
    Constraint,
    CountConstraint,
    AreaConstraint,
    ContiguityConstraint,
    ShapeConstraint,
    FacadeConstraint,
    MinWidthConstraint,
    AdjacencyConstraint,
    DoorConstraint,
    AvoidanceConstraint,
    GlobalConnectivityConstraint,
    GridBoundsConstraint,
    CellOverlapConstraint,
    AllocationConstraint,
)


class Evaluator:
    """Main constraint evaluator.

    Evaluates floor plans against a set of constraints defined in configuration.
    Produces binary pass/fail results with metadata for each constraint.
    """

    def __init__(
        self,
        config: EvalConfig | str,
        geometry: GeometryEngine | None = None,
    ):
        """Initialize evaluator.

        Args:
            config: EvalConfig instance or path to YAML config file
            geometry: Optional geometry engine (defaults to TopologicGeometry)
        """
        if isinstance(config, str):
            self.config = load_config(config)
            self.config_path = config
        else:
            self.config = config
            self.config_path = "<inline>"

        if geometry is not None:
            self.geometry = geometry
        else:
            self.geometry = create_geometry_engine(
                engine_type=self.config.geometry_engine,
                grid_rows=self.config.grid.height,
                grid_cols=self.config.grid.width,
            )
        self._constraints = self._build_constraints()

    def _build_constraints(self) -> list[Constraint]:
        """Build constraint list from configuration."""
        constraints: list[Constraint] = []

        # Layout integrity constraints (always applied)
        constraints.append(GridBoundsConstraint(self.config.grid))
        constraints.append(CellOverlapConstraint())
        constraints.append(AllocationConstraint(self.config.grid))
        constraints.append(GlobalConnectivityConstraint())

        # Per-space-type constraints
        for space_type, space_cfg in self.config.spaces.items():
            # Count constraint
            constraints.append(CountConstraint(space_type, space_cfg.count))

            # Area constraint (if bounds specified)
            if space_cfg.min_area is not None or space_cfg.max_area is not None:
                constraints.append(
                    AreaConstraint(space_type, space_cfg.min_area, space_cfg.max_area)
                )

            # Contiguity constraint (if required)
            if space_cfg.contiguous:
                constraints.append(ContiguityConstraint(space_type))

            # Shape constraint (if specified)
            if space_cfg.shape is not None:
                constraints.append(ShapeConstraint(space_type, space_cfg.shape))

            # Facade access constraint (if specified)
            if space_cfg.facade_access is not None:
                constraints.append(FacadeConstraint(space_type, space_cfg.facade_access))

            # Min width constraint (if specified)
            if space_cfg.min_width is not None:
                constraints.append(MinWidthConstraint(space_type, space_cfg.min_width))

        # Connectivity constraints
        for rule in self.config.get_connectivity_rules():
            if rule.relation == ConnectionType.ADJACENT_TO:
                constraints.append(AdjacencyConstraint(rule.source, rule.target))
            elif rule.relation == ConnectionType.DOOR_TO:
                constraints.append(DoorConstraint(rule.source, rule.target))
            elif rule.relation == ConnectionType.AVOID:
                constraints.append(AvoidanceConstraint(rule.source, rule.target))

        return constraints

    def evaluate(
        self,
        space_shells: dict[str, Any],
        grid_shell: Any,
        doors: list[dict[str, str | None]] | None = None,
        floor_plan_id: str = "unnamed",
        model_name: str | None = None,
        space_types: dict[str, str] | None = None,
    ) -> EvaluationResult:
        """Evaluate all constraints for a floor plan.

        Args:
            space_shells: Dictionary mapping space_id to Shell/Cluster
            grid_shell: Shell representing the entire grid
            doors: List of door dicts with source_space_id, target_space_id, source_cell_id, target_cell_id
            floor_plan_id: Identifier for this floor plan
            model_name: Optional model name that generated this layout
            space_types: Optional mapping of space_id to type for type lookup

        Returns:
            EvaluationResult with all constraint results
        """
        start_time = time.time()
        doors = doors or []

        results: list[ConstraintResult] = []

        for constraint in self._constraints:
            for result in constraint.evaluate(
                self.geometry,
                space_shells,
                grid_shell,
                doors,
                self.config,
                space_types,
            ):
                results.append(result)

        execution_time_ms = (time.time() - start_time) * 1000

        return EvaluationResult(
            floor_plan_id=floor_plan_id,
            config_file=self.config_path,
            timestamp=datetime.now(),
            model_name=model_name,
            constraints_total=len(results),
            constraints_passed=sum(1 for r in results if r.passed),
            results=results,
            execution_time_ms=execution_time_ms,
        )

    def evaluate_stream(
        self,
        space_shells: dict[str, Any],
        grid_shell: Any,
        doors: list[dict[str, str | None]] | None = None,
        space_types: dict[str, str] | None = None,
    ) -> Generator[ConstraintResult, None, None]:
        """Stream constraint results as they are evaluated.

        Yields each ConstraintResult immediately as it's computed,
        allowing real-time progress tracking.

        Args:
            space_shells: Dictionary mapping space_id to Shell/Cluster
            grid_shell: Shell representing the entire grid
            doors: List of door dicts with source_space_id, target_space_id, etc.
            space_types: Optional mapping of space_id to type for type lookup

        Yields:
            ConstraintResult for each constraint check
        """
        doors = doors or []

        for constraint in self._constraints:
            for result in constraint.evaluate(
                self.geometry,
                space_shells,
                grid_shell,
                doors,
                self.config,
                space_types,
            ):
                yield result

    def get_constraint_count(self) -> int:
        """Get the number of constraint types configured.

        Note: This is the number of constraint *types*, not results.
        The actual result count depends on how many space instances exist.
        """
        return len(self._constraints)

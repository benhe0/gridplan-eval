"""Allocation constraint - validates total grid utilization."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig, GridConfig


class AllocationConstraint(Constraint):
    """Validates that grid utilization meets target allocation."""

    constraint_type = "allocation"

    def __init__(
        self,
        grid_config: GridConfig,
        target_percentage: float = 100.0,
        tolerance: int = 1,
    ):
        """Initialize allocation constraint.

        Args:
            grid_config: Grid configuration with width and height
            target_percentage: Target utilization percentage (default 100%)
            tolerance: Cell count tolerance for exact match
        """
        self.total_cells = grid_config.width * grid_config.height
        self.target_percentage = target_percentage
        self.tolerance = tolerance

    def evaluate(
        self,
        geometry: GeometryEngine,
        space_shells: dict[str, Any],
        grid_shell: Any,
        doors: list[tuple[str, str]],
        windows: list,
        config: EvalConfig,
        space_types: dict[str, str] | None = None,
    ) -> Iterator[ConstraintResult]:
        """Evaluate total allocation.

        Checks if total allocated cells match target utilization.
        """
        # Count total allocated cells (avoiding double-counting overlaps)
        all_cell_ids = set()
        for space_id, shell in space_shells.items():
            cell_ids = geometry.get_cell_ids(shell)
            all_cell_ids.update(cell_ids)

        allocated_cells = len(all_cell_ids)
        target_cells = int(self.total_cells * self.target_percentage / 100)

        # Check if within tolerance
        diff = abs(allocated_cells - target_cells)
        passed = diff <= self.tolerance

        actual_percentage = (allocated_cells / self.total_cells * 100) if self.total_cells > 0 else 0

        if passed:
            reason = f"Allocated {allocated_cells}/{target_cells} cells ({actual_percentage:.1f}%)"
        elif allocated_cells < target_cells:
            reason = f"Under-allocated: {allocated_cells}/{target_cells} cells ({actual_percentage:.1f}%)"
        else:
            reason = f"Over-allocated: {allocated_cells}/{target_cells} cells ({actual_percentage:.1f}%)"

        yield self._make_result(
            constraint_id="allocation",
            passed=passed,
            allocated_cells=allocated_cells,
            target_cells=target_cells,
            total_cells=self.total_cells,
            actual_percentage=actual_percentage,
            target_percentage=self.target_percentage,
            reason=reason,
        )

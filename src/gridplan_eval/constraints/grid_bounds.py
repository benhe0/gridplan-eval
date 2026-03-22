"""Grid bounds constraint - validates all cells are within grid dimensions."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig, GridConfig


class GridBoundsConstraint(Constraint):
    """Validates that all allocated cells are within grid bounds."""

    constraint_type = "grid_bounds"

    def __init__(self, grid_config: GridConfig):
        """Initialize grid bounds constraint.

        Args:
            grid_config: Grid configuration with width and height
        """
        self.width = grid_config.width
        self.height = grid_config.height

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
        """Evaluate grid bounds.

        Checks if any space has cells marked as invalid (out of bounds).
        """
        invalid_cells = []

        for space_id, shell in space_shells.items():
            invalid_ids = geometry.get_invalid_cell_ids(shell)
            if invalid_ids:
                for cell_id in invalid_ids:
                    invalid_cells.append({"space_id": space_id, "cell_id": cell_id})

        passed = len(invalid_cells) == 0

        if passed:
            reason = f"All cells within grid [{self.width}x{self.height}]"
        else:
            reason = f"{len(invalid_cells)} cells out of bounds"

        yield self._make_result(
            constraint_id="grid_bounds",
            passed=passed,
            grid_width=self.width,
            grid_height=self.height,
            invalid_cells=invalid_cells,
            reason=reason,
        )

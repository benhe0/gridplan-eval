"""Window placement constraint - validates windows are on exterior-facing edges."""

from collections import defaultdict
from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult, ConstraintStatus
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig, GridConfig


class WindowPlacementConstraint(Constraint):
    """Validates that all windows are on perimeter cells with edges facing the exterior.

    Yields one result per space that has windows, so each space is scored independently.
    """

    constraint_type = "window_placement"

    def __init__(self, grid_config: GridConfig):
        self.width = grid_config.width
        self.height = grid_config.height

    def _is_valid_placement(self, row: int, col: int, edge: str) -> bool:
        """Check whether a window on the given edge faces the grid exterior."""
        return (
            (edge == "top" and row == 0)
            or (edge == "bottom" and row == self.height - 1)
            or (edge == "left" and col == 0)
            or (edge == "right" and col == self.width - 1)
        )

    def evaluate(
        self,
        geometry: GeometryEngine,
        space_shells: dict[str, Any],
        grid_shell: Any,
        doors: list[dict[str, str | None]],
        windows: list,
        config: EvalConfig,
        space_types: dict[str, str] | None = None,
    ) -> Iterator[ConstraintResult]:
        if not windows:
            yield self._make_result(
                constraint_id="window_placement",
                passed=False,
                status=ConstraintStatus.SKIPPED,
                reason="No windows to validate",
                skipped_reason="no_windows",
            )
            return

        # Group windows by space_id
        by_space: dict[str | None, list] = defaultdict(list)
        for window in windows:
            by_space[window.space_id].append(window)

        # Yield one result per space
        for space_id, space_windows in by_space.items():
            invalid_windows = []

            for w in space_windows:
                row, col = (int(x) for x in w.cell_id.split(";"))

                if not self._is_valid_placement(row, col, w.edge):
                    invalid_windows.append({
                        "cell_id": w.cell_id,
                        "edge": w.edge,
                        "reason": f"Edge '{w.edge}' at cell ({row},{col}) does not face the exterior",
                    })

            label = space_id or "unallocated"
            constraint_id = f"window_placement_{label}"
            passed = len(invalid_windows) == 0

            if passed:
                reason = f"All {len(space_windows)} windows are on exterior-facing edges"
            else:
                reason = f"{len(invalid_windows)} of {len(space_windows)} windows not on exterior-facing edges"

            yield self._make_result(
                constraint_id=constraint_id,
                passed=passed,
                instance_id=space_id,
                total_windows=len(space_windows),
                invalid_windows=invalid_windows,
                reason=reason,
            )

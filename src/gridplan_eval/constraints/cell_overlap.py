"""Cell overlap constraint - validates no cell is allocated to multiple spaces."""

from typing import Iterator, Any
from collections import defaultdict

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig


class CellOverlapConstraint(Constraint):
    """Validates that each cell is allocated to at most one space."""

    constraint_type = "cell_overlap"

    def evaluate(
        self,
        geometry: GeometryEngine,
        space_shells: dict[str, Any],
        grid_shell: Any,
        doors: list[tuple[str, str]],
        config: EvalConfig,
        space_types: dict[str, str] | None = None,
    ) -> Iterator[ConstraintResult]:
        """Evaluate cell overlap.

        Checks if any cell is assigned to multiple spaces.
        """
        # Map cell_id to list of space_ids that claim it
        cell_to_spaces: dict[str, list[str]] = defaultdict(list)

        for space_id, shell in space_shells.items():
            cell_ids = geometry.get_cell_ids(shell)
            for cell_id in cell_ids:
                cell_to_spaces[cell_id].append(space_id)

        # Find overlaps (cells with multiple spaces)
        overlaps = []
        for cell_id, space_ids in cell_to_spaces.items():
            if len(space_ids) > 1:
                overlaps.append({"cell_id": cell_id, "spaces": space_ids})

        passed = len(overlaps) == 0

        if passed:
            reason = "No cell overlaps detected"
        else:
            reason = f"{len(overlaps)} cells allocated to multiple spaces"

        yield self._make_result(
            constraint_id="cell_overlap",
            passed=passed,
            overlap_count=len(overlaps),
            overlaps=overlaps,
            reason=reason,
        )

"""Area constraint - validates space area bounds."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig


class AreaConstraint(Constraint):
    """Validates that space instances meet area requirements."""

    constraint_type = "area"

    def __init__(
        self,
        space_type: str,
        min_area: int | None = None,
        max_area: int | None = None,
    ):
        """Initialize area constraint.

        Args:
            space_type: Type of space to check (e.g., "bedroom")
            min_area: Minimum area in cells (optional)
            max_area: Maximum area in cells (optional)
        """
        self.space_type = space_type
        self.min_area = min_area
        self.max_area = max_area

    def evaluate(
        self,
        geometry: GeometryEngine,
        space_shells: dict[str, Any],
        grid_shell: Any,
        doors: list[tuple[str, str]],
        config: EvalConfig,
        space_types: dict[str, str] | None = None,
    ) -> Iterator[ConstraintResult]:
        """Evaluate area constraint for each instance."""
        matching = geometry.find_spaces_by_type(space_shells, self.space_type, space_types)

        if not matching:
            yield self._make_skipped_result(
                constraint_id=f"area_{self.space_type}",
                space_type=self.space_type,
            )
            return

        for idx, (space_id, shell) in enumerate(sorted(matching.items())):
            actual_area = geometry.get_cell_count(shell)

            passed = True
            reason = f"Area {actual_area} cells"

            if self.min_area is not None and actual_area < self.min_area:
                passed = False
                reason = f"Area {actual_area} < min {self.min_area}"
            elif self.max_area is not None and actual_area > self.max_area:
                passed = False
                reason = f"Area {actual_area} > max {self.max_area}"
            elif self.min_area is not None and self.max_area is not None:
                reason = f"Area {actual_area} within [{self.min_area}, {self.max_area}]"

            yield self._make_result(
                constraint_id=f"area_{self.space_type}_{idx}",
                passed=passed,
                space_id=space_id,
                space_type=self.space_type,
                actual_value=actual_area,
                expected_min=self.min_area,
                expected_max=self.max_area,
                reason=reason,
            )

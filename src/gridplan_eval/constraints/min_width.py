"""Minimum width constraint - validates spaces have no bottlenecks."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig


class MinWidthConstraint(Constraint):
    """Validates that space instances meet minimum width requirements."""

    constraint_type = "min_width"

    def __init__(self, space_type: str, min_width: int):
        """Initialize min width constraint.

        Args:
            space_type: Type of space to check (e.g., "circulation")
            min_width: Minimum width in cells (typically 2 for no bottlenecks)
        """
        self.space_type = space_type
        self.min_width = min_width

    def evaluate(
        self,
        geometry: GeometryEngine,
        space_shells: dict[str, Any],
        grid_shell: Any,
        doors: list[tuple[str, str]],
        config: EvalConfig,
        space_types: dict[str, str] | None = None,
    ) -> Iterator[ConstraintResult]:
        """Evaluate minimum width for each space instance."""
        matching = geometry.find_spaces_by_type(space_shells, self.space_type, space_types)

        if not matching:
            yield self._make_skipped_result(
                constraint_id=f"min_width_{self.space_type}",
                space_type=self.space_type,
            )
            return

        for idx, (space_id, shell) in enumerate(sorted(matching.items())):
            # For min_width >= 2, check for bottlenecks (1-cell-wide sections)
            if self.min_width >= 2:
                has_bottleneck = geometry.has_bottleneck(shell)
                passed = not has_bottleneck

                if passed:
                    reason = f"No bottlenecks detected, min width >= {self.min_width}"
                else:
                    reason = f"Bottleneck detected, violates min width {self.min_width}"
            else:
                # min_width = 1 always passes
                passed = True
                has_bottleneck = False
                reason = "Min width 1 always satisfied"

            yield self._make_result(
                constraint_id=f"min_width_{self.space_type}_{idx}",
                passed=passed,
                space_id=space_id,
                space_type=self.space_type,
                min_width=self.min_width,
                has_bottleneck=has_bottleneck,
                reason=reason,
            )

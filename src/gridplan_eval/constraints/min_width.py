"""Minimum width constraint - validates spaces have no bottlenecks."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig, extract_type_from_instance_id


class MinWidthConstraint(Constraint):
    """Validates that a specific space instance meets minimum width requirements."""

    constraint_type = "min_width"

    def __init__(self, instance_id: str, min_width: int):
        """Initialize min width constraint.

        Args:
            instance_id: Instance ID to check (e.g., "circulation_1")
            min_width: Minimum width in cells (typically 2 for no bottlenecks)
        """
        self.instance_id = instance_id
        self.min_width = min_width

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
        """Evaluate minimum width for the specific instance."""
        space_type = extract_type_from_instance_id(self.instance_id)
        shell = space_shells.get(self.instance_id)

        if shell is None:
            yield self._make_skipped_result(
                constraint_id=f"min_width_{self.instance_id}",
                space_type=space_type,
                reason=f"Instance '{self.instance_id}' not found",
            )
            return

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
            constraint_id=f"min_width_{self.instance_id}",
            passed=passed,
            instance_id=self.instance_id,
            space_type=space_type,
            min_width=self.min_width,
            has_bottleneck=has_bottleneck,
            reason=reason,
        )

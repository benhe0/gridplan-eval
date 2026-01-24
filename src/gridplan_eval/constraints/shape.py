"""Shape constraint - validates space rectangularity."""

from typing import Iterator, Any, Literal

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig


# Threshold for considering a space "rectangular"
RECTANGULARITY_THRESHOLD = 0.8


class ShapeConstraint(Constraint):
    """Validates that space instances meet shape requirements."""

    constraint_type = "shape"

    def __init__(self, space_type: str, shape: Literal["rectangular"]):
        """Initialize shape constraint.

        Args:
            space_type: Type of space to check (e.g., "bedroom")
            shape: Required shape (currently only "rectangular" supported)
        """
        self.space_type = space_type
        self.shape = shape

    def evaluate(
        self,
        geometry: GeometryEngine,
        space_shells: dict[str, Any],
        grid_shell: Any,
        doors: list[tuple[str, str]],
        config: EvalConfig,
        space_types: dict[str, str] | None = None,
    ) -> Iterator[ConstraintResult]:
        """Evaluate shape constraint for each space instance."""
        matching = geometry.find_spaces_by_type(space_shells, self.space_type, space_types)

        if not matching:
            yield self._make_skipped_result(
                constraint_id=f"shape_{self.space_type}",
                space_type=self.space_type,
            )
            return

        for idx, (space_id, shell) in enumerate(sorted(matching.items())):
            rectangularity = geometry.get_rectangularity(shell)
            passed = rectangularity >= RECTANGULARITY_THRESHOLD

            if passed:
                reason = f"Rectangularity {rectangularity:.2f} >= {RECTANGULARITY_THRESHOLD}"
            else:
                reason = f"Rectangularity {rectangularity:.2f} < {RECTANGULARITY_THRESHOLD}"

            yield self._make_result(
                constraint_id=f"shape_{self.space_type}_{idx}",
                passed=passed,
                space_id=space_id,
                space_type=self.space_type,
                rectangularity=rectangularity,
                threshold=RECTANGULARITY_THRESHOLD,
                required_shape=self.shape,
                reason=reason,
            )

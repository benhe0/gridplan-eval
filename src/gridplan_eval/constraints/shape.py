"""Shape constraint - validates space rectangularity."""

from typing import Iterator, Any, Literal

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig, extract_type_from_instance_id


# Threshold for considering a space "rectangular"
RECTANGULARITY_THRESHOLD = 0.8


class ShapeConstraint(Constraint):
    """Validates that a specific space instance meets shape requirements."""

    constraint_type = "shape"

    def __init__(self, instance_id: str, shape: Literal["rectangular"]):
        """Initialize shape constraint.

        Args:
            instance_id: Instance ID to check (e.g., "bedroom_1")
            shape: Required shape (currently only "rectangular" supported)
        """
        self.instance_id = instance_id
        self.shape = shape

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
        """Evaluate shape constraint for the specific instance."""
        space_type = extract_type_from_instance_id(self.instance_id)
        shell = space_shells.get(self.instance_id)

        if shell is None:
            yield self._make_skipped_result(
                constraint_id=f"shape_{self.instance_id}",
                space_type=space_type,
                reason=f"Instance '{self.instance_id}' not found",
            )
            return

        rectangularity = geometry.get_rectangularity(shell)
        passed = rectangularity >= RECTANGULARITY_THRESHOLD

        if passed:
            reason = f"Rectangularity {rectangularity:.2f} >= {RECTANGULARITY_THRESHOLD}"
        else:
            reason = f"Rectangularity {rectangularity:.2f} < {RECTANGULARITY_THRESHOLD}"

        yield self._make_result(
            constraint_id=f"shape_{self.instance_id}",
            passed=passed,
            instance_id=self.instance_id,
            space_type=space_type,
            rectangularity=rectangularity,
            threshold=RECTANGULARITY_THRESHOLD,
            required_shape=self.shape,
            reason=reason,
        )

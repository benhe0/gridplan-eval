"""Area constraint - validates space area bounds."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig, extract_type_from_instance_id


class AreaConstraint(Constraint):
    """Validates that a specific space instance meets area requirements."""

    constraint_type = "area"

    def __init__(
        self,
        instance_id: str,
        min_area: int | None = None,
        max_area: int | None = None,
    ):
        """Initialize area constraint.

        Args:
            instance_id: Instance ID to check (e.g., "bedroom_1")
            min_area: Minimum area in cells (optional)
            max_area: Maximum area in cells (optional)
        """
        self.instance_id = instance_id
        self.min_area = min_area
        self.max_area = max_area

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
        """Evaluate area constraint for the specific instance."""
        space_type = extract_type_from_instance_id(self.instance_id)
        shell = space_shells.get(self.instance_id)

        if shell is None:
            # Instance not present - PresenceConstraint handles this as FAIL
            # We skip to avoid duplicate errors
            yield self._make_skipped_result(
                constraint_id=f"area_{self.instance_id}",
                space_type=space_type,
                reason=f"Instance '{self.instance_id}' not found",
            )
            return

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
            constraint_id=f"area_{self.instance_id}",
            passed=passed,
            instance_id=self.instance_id,
            space_type=space_type,
            actual_value=actual_area,
            expected_min=self.min_area,
            expected_max=self.max_area,
            reason=reason,
        )

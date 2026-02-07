"""Presence constraint - validates that configured instances exist in the floor plan."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig, extract_type_from_instance_id


class PresenceConstraint(Constraint):
    """Validates that a specific configured instance exists in the floor plan.

    Unlike the old CountConstraint which checked type counts, this checks
    for the presence of exact instance IDs. Missing instance = FAIL (not SKIP).
    """

    constraint_type = "presence"

    def __init__(self, instance_id: str):
        """Initialize presence constraint.

        Args:
            instance_id: Expected instance ID (e.g., "bedroom_1")
        """
        self.instance_id = instance_id

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
        """Evaluate presence constraint.

        Checks if the configured instance ID exists in the floor plan.
        This is a hard constraint - missing instance = FAIL (not SKIP).
        """
        exists = self.instance_id in space_shells
        space_type = extract_type_from_instance_id(self.instance_id)

        if exists:
            reason = f"Instance '{self.instance_id}' found in floor plan"
        else:
            reason = f"Instance '{self.instance_id}' NOT found in floor plan"

        yield self._make_result(
            constraint_id=f"presence_{self.instance_id}",
            passed=exists,
            instance_id=self.instance_id,
            space_type=space_type,
            reason=reason,
        )

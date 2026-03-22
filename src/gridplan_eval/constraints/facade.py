"""Facade access constraint - validates perimeter access requirements."""

from typing import Iterator, Any, Literal

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig, extract_type_from_instance_id


class FacadeConstraint(Constraint):
    """Validates that a specific space instance meets facade access requirements."""

    constraint_type = "facade_access"

    def __init__(
        self,
        instance_id: str,
        requirement: Literal["required", "avoid"],
    ):
        """Initialize facade constraint.

        Args:
            instance_id: Instance ID to check (e.g., "bedroom_1")
            requirement: "required" if space must touch perimeter,
                        "avoid" if space must not touch perimeter
        """
        self.instance_id = instance_id
        self.requirement = requirement

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
        """Evaluate facade access for the specific instance."""
        space_type = extract_type_from_instance_id(self.instance_id)
        shell = space_shells.get(self.instance_id)

        if shell is None:
            yield self._make_skipped_result(
                constraint_id=f"facade_{self.instance_id}",
                space_type=space_type,
                reason=f"Instance '{self.instance_id}' not found",
            )
            return

        has_access = geometry.check_facade_access(shell, grid_shell)

        if self.requirement == "required":
            passed = has_access
            if passed:
                reason = "Space has facade access as required"
            else:
                reason = "Space lacks required facade access"
        else:  # avoid
            passed = not has_access
            if passed:
                reason = "Space correctly avoids facade"
            else:
                reason = "Space touches facade but should avoid it"

        yield self._make_result(
            constraint_id=f"facade_{self.instance_id}",
            passed=passed,
            instance_id=self.instance_id,
            space_type=space_type,
            has_facade_access=has_access,
            requirement=self.requirement,
            reason=reason,
        )

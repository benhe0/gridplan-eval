"""Facade access constraint - validates perimeter access requirements."""

from typing import Iterator, Any, Literal

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig


class FacadeConstraint(Constraint):
    """Validates that space instances meet facade access requirements."""

    constraint_type = "facade_access"

    def __init__(
        self,
        space_type: str,
        requirement: Literal["required", "avoid"],
    ):
        """Initialize facade constraint.

        Args:
            space_type: Type of space to check (e.g., "bedroom")
            requirement: "required" if space must touch perimeter,
                        "avoid" if space must not touch perimeter
        """
        self.space_type = space_type
        self.requirement = requirement

    def evaluate(
        self,
        geometry: GeometryEngine,
        space_shells: dict[str, Any],
        grid_shell: Any,
        doors: list[tuple[str, str]],
        config: EvalConfig,
        space_types: dict[str, str] | None = None,
    ) -> Iterator[ConstraintResult]:
        """Evaluate facade access for each space instance."""
        matching = geometry.find_spaces_by_type(space_shells, self.space_type, space_types)

        if not matching:
            yield self._make_skipped_result(
                constraint_id=f"facade_{self.space_type}",
                space_type=self.space_type,
            )
            return

        for idx, (space_id, shell) in enumerate(sorted(matching.items())):
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
                constraint_id=f"facade_{self.space_type}_{idx}",
                passed=passed,
                space_id=space_id,
                space_type=self.space_type,
                has_facade_access=has_access,
                requirement=self.requirement,
                reason=reason,
            )

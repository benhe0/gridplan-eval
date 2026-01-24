"""Avoidance constraint - validates spaces are not adjacent."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig


class AvoidanceConstraint(Constraint):
    """Validates that spaces of given types are not adjacent."""

    constraint_type = "avoidance"

    def __init__(self, source_type: str, target_type: str):
        """Initialize avoidance constraint.

        Args:
            source_type: Source space type (e.g., "bedroom")
            target_type: Target space type to avoid (e.g., "kitchen")
        """
        self.source_type = source_type
        self.target_type = target_type

    def evaluate(
        self,
        geometry: GeometryEngine,
        space_shells: dict[str, Any],
        grid_shell: Any,
        doors: list[tuple[str, str]],
        config: EvalConfig,
        space_types: dict[str, str] | None = None,
    ) -> Iterator[ConstraintResult]:
        """Evaluate avoidance between space types.

        Uses universal "none" logic: passes only if NO source instance
        is adjacent to ANY target instance.

        SKIPs if either source or target type has no instances.
        """
        source_spaces = geometry.find_spaces_by_type(space_shells, self.source_type, space_types)
        target_spaces = geometry.find_spaces_by_type(space_shells, self.target_type, space_types)

        constraint_id = f"avoidance_{self.source_type}_{self.target_type}"

        # Skip if source or target spaces are missing
        if not source_spaces:
            yield self._make_skipped_result(
                constraint_id=constraint_id,
                space_type=self.source_type,
                reason=f"No instances of source type '{self.source_type}' found",
            )
            return

        if not target_spaces:
            yield self._make_skipped_result(
                constraint_id=constraint_id,
                space_type=self.target_type,
                reason=f"No instances of target type '{self.target_type}' found",
            )
            return

        # Check if any pair is adjacent (violation)
        violations = []

        for source_id, source_shell in source_spaces.items():
            for target_id, target_shell in target_spaces.items():
                if geometry.check_adjacent(source_shell, target_shell):
                    violations.append((source_id, target_id))

        passed = len(violations) == 0

        if passed:
            reason = f"No {self.source_type} is adjacent to any {self.target_type}"
        else:
            reason = f"Violations: {violations}"

        yield self._make_result(
            constraint_id=constraint_id,
            passed=passed,
            source_type=self.source_type,
            target_type=self.target_type,
            violations=violations,
            reason=reason,
        )

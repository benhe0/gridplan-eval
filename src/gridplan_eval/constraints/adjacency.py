"""Adjacency constraint - validates spaces are adjacent to each other."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig


class AdjacencyConstraint(Constraint):
    """Validates that spaces of given types are adjacent."""

    constraint_type = "adjacency"

    def __init__(self, source_type: str, target_type: str):
        """Initialize adjacency constraint.

        Args:
            source_type: Source space type (e.g., "bedroom")
            target_type: Target space type (e.g., "bathroom")
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
        """Evaluate adjacency between space types.

        Uses existential "any" logic: passes if ANY source instance
        is adjacent to ANY target instance.

        SKIPs if either source or target type has no instances.
        """
        source_spaces = geometry.find_spaces_by_type(space_shells, self.source_type, space_types)
        target_spaces = geometry.find_spaces_by_type(space_shells, self.target_type, space_types)

        constraint_id = f"adjacency_{self.source_type}_{self.target_type}"

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

        # Check if any pair is adjacent
        any_adjacent = False
        adjacent_pairs = []

        for source_id, source_shell in source_spaces.items():
            for target_id, target_shell in target_spaces.items():
                if geometry.check_adjacent(source_shell, target_shell):
                    any_adjacent = True
                    adjacent_pairs.append((source_id, target_id))

        if any_adjacent:
            reason = f"Adjacent pairs found: {adjacent_pairs}"
        else:
            reason = f"No {self.source_type} is adjacent to any {self.target_type}"

        yield self._make_result(
            constraint_id=constraint_id,
            passed=any_adjacent,
            source_type=self.source_type,
            target_type=self.target_type,
            adjacent_pairs=adjacent_pairs,
            reason=reason,
        )

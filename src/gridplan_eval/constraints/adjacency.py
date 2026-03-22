"""Adjacency constraint - validates two specific instances are adjacent."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig, extract_type_from_instance_id


class AdjacencyConstraint(Constraint):
    """Validates that two specific space instances are adjacent."""

    constraint_type = "adjacency"

    def __init__(self, source_id: str, target_id: str):
        """Initialize adjacency constraint.

        Args:
            source_id: Source space instance ID (e.g., "bedroom_1")
            target_id: Target space instance ID (e.g., "bathroom_1")
        """
        self.source_id = source_id
        self.target_id = target_id

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
        """Evaluate adjacency between two specific instances."""
        source_shell = space_shells.get(self.source_id)
        target_shell = space_shells.get(self.target_id)

        constraint_id = f"adjacency_{self.source_id}_{self.target_id}"
        source_type = extract_type_from_instance_id(self.source_id)
        target_type = extract_type_from_instance_id(self.target_id)

        # Skip if source instance is missing (PresenceConstraint handles as FAIL)
        if source_shell is None:
            yield self._make_skipped_result(
                constraint_id=constraint_id,
                space_type=source_type,
                reason=f"Source instance '{self.source_id}' not found",
            )
            return

        # Skip if target instance is missing
        if target_shell is None:
            yield self._make_skipped_result(
                constraint_id=constraint_id,
                space_type=target_type,
                reason=f"Target instance '{self.target_id}' not found",
            )
            return

        is_adjacent = geometry.check_adjacent(source_shell, target_shell)

        if is_adjacent:
            reason = f"'{self.source_id}' is adjacent to '{self.target_id}'"
        else:
            reason = f"'{self.source_id}' is NOT adjacent to '{self.target_id}'"

        yield self._make_result(
            constraint_id=constraint_id,
            passed=is_adjacent,
            source_id=self.source_id,
            target_id=self.target_id,
            source_type=source_type,
            target_type=target_type,
            reason=reason,
        )

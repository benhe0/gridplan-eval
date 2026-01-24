"""Contiguity constraint - validates spaces are single connected regions."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig


class ContiguityConstraint(Constraint):
    """Validates that space instances are contiguous (not fragmented)."""

    constraint_type = "contiguity"

    def __init__(self, space_type: str):
        """Initialize contiguity constraint.

        Args:
            space_type: Type of space to check (e.g., "bedroom")
        """
        self.space_type = space_type

    def evaluate(
        self,
        geometry: GeometryEngine,
        space_shells: dict[str, Any],
        grid_shell: Any,
        doors: list[tuple[str, str]],
        config: EvalConfig,
        space_types: dict[str, str] | None = None,
    ) -> Iterator[ConstraintResult]:
        """Evaluate contiguity for each space instance."""
        matching = geometry.find_spaces_by_type(space_shells, self.space_type, space_types)

        if not matching:
            yield self._make_skipped_result(
                constraint_id=f"contiguity_{self.space_type}",
                space_type=self.space_type,
            )
            return

        for idx, (space_id, shell) in enumerate(sorted(matching.items())):
            is_contiguous = geometry.check_contiguous(shell)

            if is_contiguous:
                reason = "Space is contiguous"
            else:
                reason = "Space is fragmented into multiple regions"

            yield self._make_result(
                constraint_id=f"contiguity_{self.space_type}_{idx}",
                passed=is_contiguous,
                space_id=space_id,
                space_type=self.space_type,
                is_contiguous=is_contiguous,
                reason=reason,
            )

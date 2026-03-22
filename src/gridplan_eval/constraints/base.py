"""Base constraint class for all constraint types."""

from abc import ABC, abstractmethod
from typing import Iterator, Any

from ..models.result import ConstraintResult, ConstraintStatus
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig


class Constraint(ABC):
    """Base class for all constraint types.

    Each constraint evaluates a specific requirement and yields
    one or more ConstraintResult objects (one per instance for
    per-instance constraints like area).
    """

    constraint_type: str  # e.g., "area", "count", "door"

    @abstractmethod
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
        """Evaluate the constraint and yield results.

        Args:
            geometry: Geometry engine for spatial operations
            space_shells: Dictionary mapping space_id to Shell
            grid_shell: Shell representing the entire grid
            doors: List of door dicts with source_space_id, target_space_id, source_cell_id, target_cell_id
            windows: List of Window objects on cell edges
            config: Evaluation configuration
            space_types: Optional mapping of space_id to type for type lookup

        Yields:
            ConstraintResult for each instance evaluated
        """
        pass

    def _make_result(
        self,
        constraint_id: str,
        passed: bool,
        status: ConstraintStatus = ConstraintStatus.EVALUATED,
        **metadata,
    ) -> ConstraintResult:
        """Helper to create a ConstraintResult.

        Args:
            constraint_id: Unique identifier for this constraint instance
            passed: Whether the constraint passed
            status: Evaluation status (EVALUATED or SKIPPED)
            **metadata: Additional metadata fields

        Returns:
            ConstraintResult instance
        """
        return ConstraintResult(
            constraint_id=constraint_id,
            constraint_type=self.constraint_type,
            passed=passed,
            status=status,
            metadata=metadata,
        )

    def _make_skipped_result(
        self,
        constraint_id: str,
        space_type: str,
        reason: str | None = None,
    ) -> ConstraintResult:
        """Create a skipped result when required space type is missing.

        Args:
            constraint_id: Unique identifier for this constraint instance
            space_type: The space type that was not found
            reason: Optional custom reason message

        Returns:
            ConstraintResult with status=SKIPPED
        """
        return self._make_result(
            constraint_id=constraint_id,
            passed=False,
            status=ConstraintStatus.SKIPPED,
            space_type=space_type,
            reason=reason or f"No instances of '{space_type}' found to evaluate",
            skipped_reason="missing_space_type",
        )

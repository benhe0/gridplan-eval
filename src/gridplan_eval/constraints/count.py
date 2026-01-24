"""Count constraint - validates number of space instances."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig


class CountConstraint(Constraint):
    """Validates that the correct number of space instances exist."""

    constraint_type = "count"

    def __init__(self, space_type: str, expected_count: int):
        """Initialize count constraint.

        Args:
            space_type: Type of space to count (e.g., "bedroom")
            expected_count: Expected number of instances
        """
        self.space_type = space_type
        self.expected_count = expected_count

    def evaluate(
        self,
        geometry: GeometryEngine,
        space_shells: dict[str, Any],
        grid_shell: Any,
        doors: list[tuple[str, str]],
        config: EvalConfig,
        space_types: dict[str, str] | None = None,
    ) -> Iterator[ConstraintResult]:
        """Evaluate count constraint.

        Yields a single result for the space type.
        """
        matching = geometry.find_spaces_by_type(space_shells, self.space_type, space_types)
        actual_count = len(matching)

        passed = actual_count == self.expected_count

        if passed:
            reason = f"Count {actual_count} matches expected {self.expected_count}"
        elif actual_count < self.expected_count:
            reason = f"Count {actual_count} < expected {self.expected_count}"
        else:
            reason = f"Count {actual_count} > expected {self.expected_count}"

        yield self._make_result(
            constraint_id=f"count_{self.space_type}",
            passed=passed,
            space_type=self.space_type,
            actual_value=actual_count,
            expected_value=self.expected_count,
            reason=reason,
        )

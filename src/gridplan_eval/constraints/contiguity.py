"""Contiguity constraint - validates spaces are single connected regions."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig, extract_type_from_instance_id


class ContiguityConstraint(Constraint):
    """Validates that a specific space instance is contiguous (not fragmented)."""

    constraint_type = "contiguity"

    def __init__(self, instance_id: str):
        """Initialize contiguity constraint.

        Args:
            instance_id: Instance ID to check (e.g., "bedroom_1")
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
        """Evaluate contiguity for the specific instance."""
        space_type = extract_type_from_instance_id(self.instance_id)
        shell = space_shells.get(self.instance_id)

        if shell is None:
            yield self._make_skipped_result(
                constraint_id=f"contiguity_{self.instance_id}",
                space_type=space_type,
                reason=f"Instance '{self.instance_id}' not found",
            )
            return

        is_contiguous = geometry.check_contiguous(shell)

        if is_contiguous:
            reason = "Space is contiguous"
        else:
            reason = "Space is fragmented into multiple regions"

        yield self._make_result(
            constraint_id=f"contiguity_{self.instance_id}",
            passed=is_contiguous,
            instance_id=self.instance_id,
            space_type=space_type,
            is_contiguous=is_contiguous,
            reason=reason,
        )

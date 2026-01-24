"""Global connectivity constraint - validates all spaces are connected via doors."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig


class GlobalConnectivityConstraint(Constraint):
    """Validates that all spaces form a connected graph via doors."""

    constraint_type = "global_connectivity"

    def evaluate(
        self,
        geometry: GeometryEngine,
        space_shells: dict[str, Any],
        grid_shell: Any,
        doors: list[dict[str, str | None]],
        config: EvalConfig,
        space_types: dict[str, str] | None = None,
    ) -> Iterator[ConstraintResult]:
        """Evaluate global connectivity.

        Passes if all spaces are reachable from any space via door connections.
        """
        if not space_shells:
            yield self._make_result(
                constraint_id="global_connectivity",
                passed=True,
                num_spaces=0,
                num_components=0,
                reason="No spaces to check",
            )
            return

        is_connected, num_components = geometry.build_connectivity_graph(
            space_shells, doors
        )

        if is_connected:
            reason = f"All {len(space_shells)} spaces connected"
        else:
            reason = f"{num_components} disconnected components found"

        yield self._make_result(
            constraint_id="global_connectivity",
            passed=is_connected,
            num_spaces=len(space_shells),
            num_components=num_components,
            reason=reason,
        )

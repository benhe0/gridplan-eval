"""Door constraint - validates a door connection exists between two specific instances."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig, extract_type_from_instance_id


class DoorConstraint(Constraint):
    """Validates that a door connection exists between two specific space instances."""

    constraint_type = "door"

    def __init__(self, source_id: str, target_id: str):
        """Initialize door constraint.

        Args:
            source_id: Source space instance ID (e.g., "bedroom_1")
            target_id: Target space instance ID (e.g., "circulation_1")
        """
        self.source_id = source_id
        self.target_id = target_id

    @staticmethod
    def _cells_adjacent(cell_id_1: str | None, cell_id_2: str | None) -> bool:
        """Check if two cell IDs are 4-adjacent (share an edge).

        Args:
            cell_id_1: First cell ID in "row;col" format
            cell_id_2: Second cell ID in "row;col" format

        Returns:
            True if cells share an edge (Manhattan distance == 1)
        """
        if not cell_id_1 or not cell_id_2:
            return False

        try:
            r1, c1 = map(int, cell_id_1.split(";"))
            r2, c2 = map(int, cell_id_2.split(";"))
            manhattan_distance = abs(r1 - r2) + abs(c1 - c2)
            return manhattan_distance == 1
        except (ValueError, AttributeError):
            return False

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
        """Evaluate door constraint between two specific instances."""
        source_shell = space_shells.get(self.source_id)
        target_shell = space_shells.get(self.target_id)

        constraint_id = f"door_{self.source_id}_{self.target_id}"
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

        # Build door lookup for this specific pair (bidirectional)
        door_cells: list[tuple[str | None, str | None]] = []
        for door in doors:
            src = door.get("source_space_id")
            tgt = door.get("target_space_id")

            src_cell_id = door.get("source_cell_id")
            tgt_cell_id = door.get("target_cell_id")

            # Check both directions (doors are bidirectional)
            if src == self.source_id and tgt == self.target_id:
                door_cells.append(
                    (src_cell_id, tgt_cell_id))
            elif src == self.target_id and tgt == self.source_id:
                door_cells.append(
                    (tgt_cell_id, src_cell_id))

        has_door = False
        failure_reason = None

        if not door_cells:
            failure_reason = f"No door defined between '{self.source_id}' and '{self.target_id}'"
        else:
            # Check space adjacency first
            spaces_adjacent = geometry.check_adjacent(
                source_shell, target_shell)
            if not spaces_adjacent:
                failure_reason = f"""
                Spaces '{self.source_id}' and '{self.target_id}' are not adjacent.
                The specified door cells {src_cell_id} and {tgt_cell_id} cannot be valid if the spaces themselves do not share a boundary.
                """
            else:
                # Check cell adjacency for each door between these spaces
                for src_cell, tgt_cell in door_cells:
                    if self._cells_adjacent(src_cell, tgt_cell):
                        has_door = True
                        break
                    else:
                        failure_reason = f"""
                        Door cells {src_cell} and {tgt_cell} not adjacent.
                        Even though spaces '{self.source_id}' and '{self.target_id}' are adjacent, the specified door cells do not share an edge, so the door connection is invalid.
                        """

        if has_door:
            reason = f"Door exists between '{self.source_id}' and '{self.target_id}'"
        else:
            reason = failure_reason or f"No valid door between instances"

        yield self._make_result(
            constraint_id=constraint_id,
            passed=has_door,
            source_id=self.source_id,
            target_id=self.target_id,
            source_type=source_type,
            target_type=target_type,
            reason=reason,
        )

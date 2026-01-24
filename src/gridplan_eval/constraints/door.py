"""Door constraint - validates door connections exist between spaces."""

from typing import Iterator, Any

from ..constraints.base import Constraint
from ..models.result import ConstraintResult
from ..geometry.interface import GeometryEngine
from ..config.schema import EvalConfig


class DoorConstraint(Constraint):
    """Validates that door connections exist between space types."""

    constraint_type = "door"

    def __init__(self, source_type: str, target_type: str):
        """Initialize door constraint.

        Args:
            source_type: Source space type (e.g., "bedroom")
            target_type: Target space type (e.g., "circulation")
        """
        self.source_type = source_type
        self.target_type = target_type

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
        config: EvalConfig,
        space_types: dict[str, str] | None = None,
    ) -> Iterator[ConstraintResult]:
        """Evaluate door constraint for each source instance.

        Each source instance must have a door to at least one target instance.
        Yields one result per source instance.
        """
        source_spaces = geometry.find_spaces_by_type(space_shells, self.source_type, space_types)

        if not source_spaces:
            yield self._make_skipped_result(
                constraint_id=f"door_{self.source_type}_to_{self.target_type}",
                space_type=self.source_type,
                reason=f"No instances of source type '{self.source_type}' found",
            )
            return

        target_spaces = geometry.find_spaces_by_type(space_shells, self.target_type, space_types)
        target_ids = set(target_spaces.keys())

        # Build door lookup with cell IDs for adjacency validation
        # Maps (source_space, target_space) -> list of (source_cell, target_cell) pairs
        door_connections: dict[tuple[str, str], list[tuple[str | None, str | None]]] = {}
        for door in doors:
            src_id = door["source_space_id"]
            tgt_id = door["target_space_id"]
            src_cell = door.get("source_cell_id")
            tgt_cell = door.get("target_cell_id")

            # Store both directions (doors are bidirectional)
            key_fwd = (src_id, tgt_id)
            key_rev = (tgt_id, src_id)

            if key_fwd not in door_connections:
                door_connections[key_fwd] = []
            door_connections[key_fwd].append((src_cell, tgt_cell))

            if key_rev not in door_connections:
                door_connections[key_rev] = []
            door_connections[key_rev].append((tgt_cell, src_cell))

        for idx, (source_id, source_shell) in enumerate(sorted(source_spaces.items())):
            # Check if this source has a valid door to any target
            has_door = False
            connected_target = None
            failure_reasons = []

            for target_id in target_ids:
                key = (source_id, target_id)
                if key not in door_connections:
                    continue

                target_shell = space_shells.get(target_id)

                # Check space adjacency
                spaces_adjacent = geometry.check_adjacent(source_shell, target_shell)
                if not spaces_adjacent:
                    failure_reasons.append(f"spaces {source_id} and {target_id} not adjacent")
                    continue

                # Check cell adjacency for each door between these spaces
                for src_cell, tgt_cell in door_connections[key]:
                    if self._cells_adjacent(src_cell, tgt_cell):
                        has_door = True
                        connected_target = target_id
                        break
                    else:
                        failure_reasons.append(
                            f"door cells {src_cell} and {tgt_cell} not adjacent"
                        )

                if has_door:
                    break

            if has_door:
                reason = f"Door exists to {connected_target}"
            else:
                if failure_reasons:
                    reason = f"No valid door from {source_id} to any {self.target_type}: {failure_reasons[0]}"
                else:
                    reason = f"No door from {source_id} to any {self.target_type}"

            yield self._make_result(
                constraint_id=f"door_{self.source_type}_{idx}_{self.target_type}",
                passed=has_door,
                source_id=source_id,
                source_type=self.source_type,
                target_type=self.target_type,
                connected_target=connected_target,
                reason=reason,
            )

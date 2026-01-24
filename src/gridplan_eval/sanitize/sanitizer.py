"""Core sanitization logic for space ID normalization.

Converts dict-based allocation to array-based format and normalizes
space_ids to canonical {type}_{index} format. Also normalizes space
types to canonical forms (e.g., "meeting room" -> "meeting").
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from ..sanitize.models import (
    DoorConnection,
    FloorPlanRecord,
    SanitizationMapping,
    SanitizedFloorPlanRecord,
    SanitizedLLMResponse,
    SpaceAllocationOutput,
    SpaceIdMapping,
)
from ..sanitize.type_normalizer import normalize_type


class SpaceIdSanitizer:
    """Sanitizes LLM-generated space_ids to canonical format.

    Transforms dict-based allocation to array-based format and normalizes
    all space_ids to the pattern {type}_{index}.
    """

    def sanitize_record(
        self, record: FloorPlanRecord
    ) -> tuple[SanitizedFloorPlanRecord, SanitizationMapping]:
        """Sanitize a single floor plan record.

        Args:
            record: Input record with dict-based allocation

        Returns:
            Tuple of (sanitized record with array allocation, ID mapping for traceability)
        """
        allocation = record.response.allocation

        # Step 1: Normalize types and build type mapping
        # Maps original space_id -> normalized type
        normalized_types: dict[str, str] = {}
        for space_id, space_data in allocation.items():
            normalized_types[space_id] = normalize_type(
                space_data.type, space_data.name
            )

        # Step 2: Assign canonical IDs: {normalized_type}_{1-based-index}
        id_mapping: dict[str, str] = {}  # original -> canonical
        type_indices: dict[str, int] = defaultdict(int)

        for space_id in allocation.keys():
            norm_type = normalized_types[space_id]
            type_indices[norm_type] += 1
            index = type_indices[norm_type]
            canonical_id = f"{norm_type}_{index}"
            id_mapping[space_id] = canonical_id

        # Step 3: Transform allocation dict to array with canonical keys and types
        new_allocation: list[SpaceAllocationOutput] = []
        for original_id, space_data in allocation.items():
            canonical_id = id_mapping[original_id]
            norm_type = normalized_types[original_id]
            new_allocation.append(
                SpaceAllocationOutput(
                    space_id=canonical_id,
                    name=space_data.name,
                    type=norm_type,  # Use normalized type
                    cell_ids=space_data.cell_ids,
                )
            )

        # Step 4: Remap door references (preserve cell_ids)
        new_doors: list[DoorConnection] = []
        for door in record.response.doors:
            new_doors.append(
                DoorConnection(
                    source_space_id=id_mapping.get(
                        door.source_space_id, door.source_space_id
                    ),
                    target_space_id=id_mapping.get(
                        door.target_space_id, door.target_space_id
                    ),
                    source_cell_id=door.source_cell_id,
                    target_cell_id=door.target_cell_id,
                )
            )

        # Step 5: Build output structures
        sanitized_record = SanitizedFloorPlanRecord(
            id=record.id,
            model_name=record.model_name,
            grid_info=record.grid_info,
            response=SanitizedLLMResponse(
                allocation=new_allocation,
                doors=new_doors,
            ),
        )

        # Build mapping for traceability
        mappings: list[SpaceIdMapping] = []
        for original_id, canonical_id in id_mapping.items():
            norm_type = normalized_types[original_id]
            index = int(canonical_id.rsplit("_", 1)[1])
            mappings.append(
                SpaceIdMapping(
                    original_id=original_id,
                    canonical_id=canonical_id,
                    space_type=norm_type,  # Use normalized type
                    index=index,
                )
            )

        mapping = SanitizationMapping(
            floor_plan_id=record.id,
            model_name=record.model_name,
            mappings=mappings,
            timestamp=datetime.now().isoformat(),
        )

        return sanitized_record, mapping


def sanitize_jsonl(
    input_path: str | Path,
    output_path: str | Path,
    mapping_path: str | Path | None = None,
) -> tuple[int, int]:
    """Sanitize all records in a JSONL file.

    Args:
        input_path: Path to input JSONL file
        output_path: Path for sanitized output JSONL
        mapping_path: Optional path for mapping JSON file

    Returns:
        Tuple of (records_processed, records_failed)
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    sanitizer = SpaceIdSanitizer()
    all_mappings: list[SanitizationMapping] = []
    processed = 0
    failed = 0

    with open(input_path) as f_in, open(output_path, "w") as f_out:
        for line in f_in:
            line = line.strip()
            if not line:
                continue

            try:
                record = FloorPlanRecord.model_validate_json(line)
                sanitized, mapping = sanitizer.sanitize_record(record)
                f_out.write(sanitized.model_dump_json() + "\n")
                all_mappings.append(mapping)
                processed += 1
            except Exception:
                failed += 1

    if mapping_path:
        mapping_path = Path(mapping_path)
        with open(mapping_path, "w") as f:
            json.dump([m.model_dump() for m in all_mappings], f, indent=2)

    return processed, failed

"""Pydantic models for space ID sanitization.

Input models handle the dict-based allocation format from LLM responses.
Output models use array-based allocation format for consistent comparison.
"""

from pydantic import BaseModel, Field


class SpaceAllocationInput(BaseModel):
    """Space allocation from LLM response (dict-based input format).

    The space_id is the key in the allocation dict, not a field here.
    """

    name: str
    type: str
    cell_ids: list[str]


class SpaceAllocationOutput(BaseModel):
    """Space allocation in sanitized output (array-based format).

    Includes space_id as an explicit field for array storage.
    """

    space_id: str
    name: str
    type: str
    cell_ids: list[str]


class DoorConnection(BaseModel):
    """Door connection between two spaces."""

    source_space_id: str
    target_space_id: str
    source_cell_id: str | None = None
    target_cell_id: str | None = None


class GridInfo(BaseModel):
    """Grid dimensions."""

    row_count: int
    col_count: int


class LLMResponse(BaseModel):
    """LLM response with dict-based allocation (input format)."""

    allocation: dict[str, SpaceAllocationInput]
    doors: list[DoorConnection] = Field(default_factory=list)


class SanitizedLLMResponse(BaseModel):
    """Sanitized response with array-based allocation (output format)."""

    allocation: list[SpaceAllocationOutput]
    doors: list[DoorConnection] = Field(default_factory=list)


class FloorPlanRecord(BaseModel):
    """Complete floor plan record from JSONL (input format with dict allocation)."""

    id: str
    model_name: str | None = None
    grid_info: GridInfo
    response: LLMResponse


class SanitizedFloorPlanRecord(BaseModel):
    """Sanitized floor plan record (output with array allocation)."""

    id: str
    model_name: str | None = None
    grid_info: GridInfo
    response: SanitizedLLMResponse


class SpaceIdMapping(BaseModel):
    """Mapping from original to canonical space ID."""

    original_id: str
    canonical_id: str
    space_type: str
    index: int


class SanitizationMapping(BaseModel):
    """Complete ID mapping for one floor plan (for traceability file)."""

    floor_plan_id: str
    model_name: str | None = None
    mappings: list[SpaceIdMapping]
    timestamp: str

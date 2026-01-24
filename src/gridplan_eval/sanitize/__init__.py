"""Sanitization module for normalizing LLM-generated space IDs.

This module provides tools to:
- Convert dict-based allocation format to array-based format
- Normalize space_ids to canonical {type}_{index} format
- Remap door references to use canonical IDs
- Generate mapping files for traceability
"""

from ..sanitize.models import (
    SpaceAllocationInput,
    SpaceAllocationOutput,
    DoorConnection,
    GridInfo,
    LLMResponse,
    SanitizedLLMResponse,
    FloorPlanRecord,
    SanitizedFloorPlanRecord,
    SpaceIdMapping,
    SanitizationMapping,
)
from ..sanitize.sanitizer import SpaceIdSanitizer, sanitize_jsonl
from ..sanitize.type_normalizer import normalize_type

__all__ = [
    # Models
    "SpaceAllocationInput",
    "SpaceAllocationOutput",
    "DoorConnection",
    "GridInfo",
    "LLMResponse",
    "SanitizedLLMResponse",
    "FloorPlanRecord",
    "SanitizedFloorPlanRecord",
    "SpaceIdMapping",
    "SanitizationMapping",
    # Sanitizer
    "SpaceIdSanitizer",
    "sanitize_jsonl",
    # Type normalization
    "normalize_type",
]

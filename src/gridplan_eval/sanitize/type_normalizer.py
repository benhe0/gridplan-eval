"""Type normalization for heterogeneous space type names from LLM responses.

Maps variant type names (e.g., "open work area", "Meeting Room 1") to
canonical forms (e.g., "open_work_area", "meeting").

Based on constraint_eval/color_palette.py normalization patterns.
"""

import re


# Type normalization patterns: maps various names to canonical types
# Patterns are in order of specificity (more specific first)
TYPE_PATTERNS: dict[str, list[str]] = {
    "open_work_area": [
        r"^open[_\s]work[_\s]area$",
        r"^open[_\s]work$",
        r"^work[_\s]area$",
        r"^workspace$",
        r"^work$",
        r"^office$",
    ],
    "meeting": [
        r"^meeting[_\s]room[_\s]\d+$",  # Meeting Room 1, Meeting Room 2
        r"^meeting[_\s]room[_\s][a-z]$",  # Meeting Room A, Meeting Room B
        r"^meeting[_\s]room$",
        r"^meeting_room_\d+$",
        r"^meeting$",
        r"^private$",
    ],
    "phone_booth": [
        r"^phone[_\s]booth[_\s]\d+$",  # Phone Booth 1, 2, 3
        r"^phone[_\s]booth$",
        r"^phone_booth_\d+$",
        r"^phone$",
    ],
    "bathroom_women": [
        r"^bathroom[_\s]women$",
        r"^bath[_\s]women$",
        r"^bathroom_women$",
        r"^bath_women$",
    ],
    "bathroom_men": [
        r"^bathroom[_\s]men$",
        r"^bath[_\s]men$",
        r"^bathroom_men$",
        r"^bath_men$",
    ],
    "bathroom": [
        r"^bathroom$",
        r"^bath$",
        r"^restroom$",
        r"^wc$",
        r"^toilet$",
    ],
    "kitchen": [
        r"^kitchen$",
    ],
    "lounge": [
        r"^lounge$",
        r"^social$",
        r"^amenity$",
    ],
    "reception": [
        r"^reception$",
    ],
    "circulation": [
        r"^circulation[_\s]\d+$",  # Circulation 2, Circulation 3
        r"^circulation[_\s]branch$",
        r"^branch[_\s]circulation$",
        r"^main[_\s]circulation$",
        r"^flexible[_\s]circulation$",
        r"^circulation$",
        r".*circulation.*",  # Fallback for any circulation variant
    ],
    "storage": [
        r"^storage$",
        r"^utility$",
    ],
    "buffer": [
        r"^buffer$",
        r"^unallocated",
    ],
}


def normalize_type(space_type: str, space_name: str | None = None) -> str:
    """Normalize a space type string to canonical form.

    For ambiguous types like "bathroom" or "restroom", uses the space_name
    to determine the specific type (bathroom_men vs bathroom_women).

    If no pattern matches, applies basic format normalization:
    - lowercase
    - replace spaces with underscores
    - strip whitespace

    Args:
        space_type: Raw space type string (may be heterogeneous)
        space_name: Optional space name for context (e.g., "Bathroom Men")

    Returns:
        Normalized canonical type name

    Example:
        >>> normalize_type("open work area")
        'open_work_area'
        >>> normalize_type("bathroom", "Bathroom Men")
        'bathroom_men'
        >>> normalize_type("Meeting Room 2")
        'meeting'
        >>> normalize_type("some unknown type")
        'some_unknown_type'
    """
    if not space_type or not space_type.strip():
        return "unknown"

    # Normalize input: lowercase, strip whitespace
    normalized_input = space_type.lower().strip()

    # Special handling for generic bathroom/restroom - use name for context
    if normalized_input in ["bathroom", "restroom"] and space_name:
        name_lower = space_name.lower()
        if "men" in name_lower and "women" not in name_lower:
            return "bathroom_men"
        elif "women" in name_lower:
            return "bathroom_women"
        # If name doesn't specify, continue with normal matching

    # Try to match against patterns (in order of specificity)
    for canonical_type, patterns in TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, normalized_input, re.IGNORECASE):
                return canonical_type

    # No pattern match - apply basic format normalization
    # Replace spaces with underscores, keep lowercase
    return re.sub(r"\s+", "_", normalized_input)

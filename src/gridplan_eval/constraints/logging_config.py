"""Logging configuration for constraint evaluators."""

import logging
import os
import sys

_TRUTHY_VALUES = ("1", "true", "yes")


def is_debug_enabled() -> bool:
    """Check if constraint debug logging is enabled.

    Reads CONSTRAINT_DEBUG_LOG environment variable.

    Returns:
        True if debug logging is enabled, False otherwise.
    """
    return os.environ.get("CONSTRAINT_DEBUG_LOG", "").lower() in _TRUTHY_VALUES


def configure_constraint_logging() -> None:
    """Configure logging for constraint evaluators based on environment.

    Reads CONSTRAINT_DEBUG_LOG environment variable:
    - "1", "true", "yes" (case-insensitive): Enable DEBUG level
    - Otherwise: Use WARNING level (effectively silent)

    Output goes to stderr only.
    """
    level = logging.DEBUG if is_debug_enabled() else logging.WARNING

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))

    # Configure the constraints namespace logger
    logger = logging.getLogger("constraint_eval_v2.constraints")
    logger.setLevel(level)

    # Avoid adding duplicate handlers
    if not logger.handlers:
        logger.addHandler(handler)

    # Allow propagation for testing compatibility (pytest caplog needs it)
    # The handler still writes to stderr as intended
    logger.propagate = True

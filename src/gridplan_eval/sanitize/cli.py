#!/usr/bin/env python3
"""CLI for space_id sanitization.

Usage:
    python -m constraint_eval_v2.sanitize.cli input.jsonl output.jsonl
    python -m constraint_eval_v2.sanitize.cli input.jsonl output.jsonl --mapping mapping.json
    python -m constraint_eval_v2.sanitize.cli input.jsonl output.jsonl --dry-run
"""

import argparse
import sys
from pathlib import Path

from ..sanitize.models import FloorPlanRecord
from ..sanitize.sanitizer import SpaceIdSanitizer, sanitize_jsonl


def main() -> int:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Sanitize LLM-generated space_ids to canonical format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic sanitization
    python -m constraint_eval_v2.sanitize.cli responses.jsonl sanitized.jsonl

    # With mapping file for traceability
    python -m constraint_eval_v2.sanitize.cli responses.jsonl sanitized.jsonl --mapping mappings.json

    # Dry run to preview without writing
    python -m constraint_eval_v2.sanitize.cli responses.jsonl sanitized.jsonl --dry-run
        """,
    )

    parser.add_argument("input", type=Path, help="Input JSONL file with LLM responses")
    parser.add_argument(
        "output", type=Path, help="Output JSONL file for sanitized responses"
    )
    parser.add_argument(
        "--mapping", "-m", type=Path, help="Output JSON file for ID mappings"
    )
    parser.add_argument(
        "--dry-run", "-n", action="store_true", help="Preview without writing files"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1

    if args.dry_run:
        # Preview mode: process but don't write
        sanitizer = SpaceIdSanitizer()
        count = 0

        with open(args.input) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                record = FloorPlanRecord.model_validate_json(line)
                _, mapping = sanitizer.sanitize_record(record)
                count += 1

                if args.verbose:
                    print(f"\n{record.id}:")
                    for m in mapping.mappings:
                        print(f"  {m.original_id} -> {m.canonical_id}")

        print(f"\nDry run complete. {count} record(s) would be processed.")
        print("No files written.")
        return 0

    # Normal processing
    processed, failed = sanitize_jsonl(args.input, args.output, args.mapping)

    if args.verbose:
        # Re-read to show mappings
        sanitizer = SpaceIdSanitizer()
        with open(args.input) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                record = FloorPlanRecord.model_validate_json(line)
                _, mapping = sanitizer.sanitize_record(record)
                print(f"\n{record.id}:")
                for m in mapping.mappings:
                    print(f"  {m.original_id} -> {m.canonical_id}")

    print(f"\nProcessed: {processed}, Failed: {failed}")
    print(f"Output: {args.output}")
    if args.mapping:
        print(f"Mapping: {args.mapping}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Main CLI entry point for uwacomm."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..cli.analyze import analyze_file


def main() -> int:
    """Main entry point for the uwacomm CLI.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(
        description="uwacomm: Underwater Communications Codec",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uwacomm --analyze message.py          Analyze message schema
  uwacomm --version                      Show version

For more information, see: https://github.com/patel999jay/uwacomm
        """,
    )

    parser.add_argument(
        "--analyze",
        metavar="FILE",
        type=str,
        help="Analyze message schema and show field sizes",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="uwacomm 0.1.0",
    )

    args = parser.parse_args()

    # Handle --analyze
    if args.analyze:
        file_path = Path(args.analyze)
        if not file_path.exists():
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            return 1

        try:
            analyze_file(file_path)
            return 0
        except Exception as e:
            print(f"Error analyzing file: {e}", file=sys.stderr)
            return 1

    # If no command specified, show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

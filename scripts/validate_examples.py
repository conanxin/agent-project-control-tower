"""
validate_examples.py — ACT-1 thin wrapper.

This exists for backward compatibility with the ACT-1 contract. Internally
it just delegates to validate.py with --source examples. New code should
call validate.py directly.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    return subprocess.call(
        [sys.executable, str(HERE / "validate.py"), "--source", "examples"]
    )


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Record one `Agent` spawn and the model its caller names, if any; print nothing and exit 0."""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))

from rulesets.hook_entry import record_spawn


def main() -> int:
    try:
        stdin = sys.stdin.buffer.read()
    except Exception:
        return 0
    result = record_spawn(sys.argv, stdin, os.environ)
    sys.stderr.write(result.stderr)
    sys.stdout.write(result.stdout)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())

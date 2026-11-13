#!/usr/bin/env python3
"""Record each instruction file the harness loads; print nothing and exit 0."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))

from rulesets.record_entry import record_load
from rulesets.script_process import run_script


def main() -> int:
    return run_script(record_load, tolerate_unreadable_stdin=True)


if __name__ == "__main__":
    sys.exit(main())

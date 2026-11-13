#!/usr/bin/env python3
"""Record one `Agent` spawn and the model its caller names, if any; print nothing and exit 0."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))

from rulesets.record_entry import record_spawn
from rulesets.script_process import run_script


def main() -> int:
    return run_script(record_spawn, tolerate_unreadable_stdin=True)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""One part of one delivery, or the end of a session; `deliver.py --help` names the arguments."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))

from rulesets.hook_entry import deliver
from rulesets.script_process import run_script


def main() -> int:
    return run_script(deliver, tolerate_unreadable_stdin=False)


if __name__ == "__main__":
    sys.exit(main())

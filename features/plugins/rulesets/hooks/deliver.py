#!/usr/bin/env python3
"""One part of one delivery, or the end of a session; `deliver.py --help` names the arguments."""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))

from rulesets.hook_entry import deliver


def main() -> int:
    result = deliver(sys.argv, sys.stdin.buffer.read(), os.environ)
    sys.stderr.write(result.stderr)
    sys.stdout.write(result.stdout)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())

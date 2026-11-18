#!/usr/bin/env python3
"""Link the rulesets directory's skills into the personal skills folder; print only what blocks a link."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))

from rulesets.script_process import run_script
from rulesets.skill_links import link_at_session_start


def main() -> int:
    return run_script(link_at_session_start, tolerate_unreadable_stdin=True)


if __name__ == "__main__":
    sys.exit(main())

"""The one place a hook script touches its process: stdin, argv, the environment, and both output streams."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping, Sequence

from rulesets.record_entry import HookResult


def run_script(
    entry: Callable[[Sequence[str], bytes, Mapping[str, str]], HookResult],
    *,
    tolerate_unreadable_stdin: bool,
) -> int:
    """Call `entry` with this process's argv, stdin bytes, and environment; write its output and return its exit code.

    Where stdin cannot be read, a tolerant script exits 0 having written nothing, and any other
    script lets the error end the run.
    """
    if tolerate_unreadable_stdin:
        try:
            stdin = sys.stdin.buffer.read()
        except Exception:
            return 0
    else:
        stdin = sys.stdin.buffer.read()
    result = entry(sys.argv, stdin, os.environ)
    sys.stderr.write(result.stderr)
    sys.stdout.write(result.stdout)
    return result.exit_code

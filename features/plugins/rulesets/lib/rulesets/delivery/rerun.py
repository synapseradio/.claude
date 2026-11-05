"""The command that runs a failed first part again on the payload it failed on."""

from __future__ import annotations

import contextlib
import hashlib
import pathlib
import shlex

from rulesets.locations import Locations

RERUN_FLAG = "--rerun"


def rerun_command(raw_payload: str, locations: Locations, hooks: pathlib.Path) -> str:
    """A shell command that feeds the payload to the first part again, standing apart from any delivery.

    The payload goes to a file under the state directory; where that file cannot be written, the
    command carries the payload itself.
    """

    run = f"bash {shlex.quote(str(hooks / 'with-python.sh'))} {shlex.quote(str(hooks / 'deliver.py'))} --part 1 {RERUN_FLAG}"
    name = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()[:16]
    path = locations.state / "payloads" / f"{name}.json"
    with contextlib.suppress(OSError):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw_payload, encoding="utf-8")
        return f"{run} < {shlex.quote(str(path))}"
    return f"printf %s {shlex.quote(raw_payload)} | {run}"

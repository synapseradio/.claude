#!/usr/bin/env python3.14
"""Forward to the model-scoped-rulesets plugin's load-recording hook.

The live `settings.json` is untracked, so a checkout that moved this file's
code reaches a running session before the alignment sweep rewrites the
command that names it. This file keeps the old command path executable and
hands stdin to the new shim, naming the state directory the old code wrote
to, so `load-check` reads one session's records from one place across the
migration.

A target that is not there is the hazard this file exists for, met one step
later, exactly as `rulesets-deliver.py` meets it. `InstructionsLoaded`
carries no decision control, though, so nothing this hook emits reaches a
session's context the way a delivery's stdout does: the gap is recorded
instead where this hook already writes, the audit trail under the state
directory, and the process exits zero either way. Nothing here imports the
plugin, at module scope or inside the gap it announces, since the plugin
being absent is the exact window this file is for.

It is deleted once the live `settings.json` names the plugin's own hooks and
one session has verified delivery through them.
"""

import json
import os
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "features" / "model-scoped-rulesets"


def config_root() -> pathlib.Path:
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    if override:
        return pathlib.Path(override)
    return pathlib.Path.home() / ".claude"


def _safe(key: str) -> str:
    """Sanitize a session or agent identifier before it becomes a filename.

    Mirrors `rulesets.audit._safe`, duplicated rather than imported: the
    plugin housing that module is exactly what may be missing here.
    """

    cleaned = "".join(c for c in str(key) if c.isalnum() or c in "-_")
    return cleaned or "session"


def announce_missing(target: pathlib.Path, state: pathlib.Path) -> int:
    """Note, in the audit trail this hook writes to, that its target is gone.

    A load this hook cannot record is not a load it should block, so the
    process still exits zero. The note lands as a JSONL line shaped like
    the records `rulesets.audit` writes, under the same directory, so a
    later read of the trail finds it beside everything else that session
    carried.
    """

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    session_id = payload.get("session_id") or "session"
    agent_id = payload.get("agent_id")
    record = {
        "kind": "gap",
        "reason": f"the hook this command forwards to is not there: {target}",
    }
    try:
        directory = state / "audit" / _safe(session_id)
        directory.mkdir(parents=True, exist_ok=True)
        name = f"{_safe(agent_id)}.jsonl" if agent_id else "session.jsonl"
        with (directory / name).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
    except OSError:
        pass
    return 0


def main() -> int:
    target = PLUGIN_ROOT / "hooks" / "record-load.py"
    state = config_root() / ".tmp" / "rulesets"
    if not target.is_file():
        return announce_missing(target, state)
    os.execv(
        sys.executable,
        [
            sys.executable,
            str(target),
            "--state",
            str(state),
        ],
    )


if __name__ == "__main__":
    sys.exit(main())

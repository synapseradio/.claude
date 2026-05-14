"""Per-flow state for block-once semantics.

Tracks the first time a `(transcript_path, tool)` flow was denied so
that subsequent re-emissions of `ExitPlanMode` for the same
transcript are allowed through with an injected context sentence
rather than blocked again.

State lives at `~/.claude/arbiter/state/arbiter-flows/<hash>.json`, where
`<hash>` is `sha256(transcript_path + "|" + tool).hexdigest()[:16]`.
Each entry records a UTC timestamp and the tool name. Entries older
than `STATE_TTL_SECONDS` (24h) are pruned on read so a stale
transcript path cannot silently keep a flow approved forever.

Writes use `os.open` with `O_CREAT | O_EXCL` so a concurrent insert
race surfaces as `False` and the loser treats the flow as already
marked.

Error policy. State is an optimization on top of the deny path, so a
state-op failure must not crash the hook — but it must not vanish
either. Two kinds of error are distinguished at every filesystem
call site:

  - `FileNotFoundError` on a cleanup unlink is the expected race
    (another dispatcher already removed it). Silent.
  - Any other `OSError` (permission denied, disk full, read-only
    filesystem) is a real signal. Logged to `arbiter.log` under
    `event=state` so a `tail -f` shows breakage, while the function
    still returns the safe default. The dispatcher then behaves as
    if there were no prior block, which is the same shape as today's
    first-time deny path.
"""

import contextlib
import hashlib
import json
import os
import pathlib
from datetime import UTC, datetime

STATE_DIR = pathlib.Path.home() / ".claude" / "arbiter" / "state" / "arbiter-flows"
STATE_TTL_SECONDS = 24 * 60 * 60

# Same log file the judge client writes to. State entries land under
# `event=state` so existing log readers (which key on `event=`) pick
# them up without changes.
LOG_PATH = pathlib.Path.home() / ".claude" / "arbiter" / "logs" / "arbiter.log"


def _log_state_error(reason: str) -> None:
    """Append one line to `arbiter.log` describing an unexpected state-op
    failure. Format mirrors `client.log_call` so the same parsers handle
    both: `<ts>  event=state  duration_ms=0  verdicts=ERROR:<reason>`.

    A failure to log is itself suppressed — there is nowhere to
    escalate to from inside the logger, and the caller's return
    contract does not depend on the log line landing.
    """
    with contextlib.suppress(OSError):
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{ts}  event=state  duration_ms=0  verdicts=ERROR:{reason}\n")


def _safe_unlink(path: pathlib.Path, label: str) -> None:
    """Unlink a file, treating the file-already-gone race as expected
    and any other failure as worth logging. `label` describes the call
    site so a log line points to which path triggered."""
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except OSError as exc:
        _log_state_error(f"{label}-unlink:{type(exc).__name__}")


def _flow_key(transcript_path: str, tool: str) -> str:
    """Stable 16-hex-char key for a `(transcript_path, tool)` flow."""
    raw = f"{transcript_path}|{tool}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _flow_path(transcript_path: str, tool: str) -> pathlib.Path:
    return STATE_DIR / f"{_flow_key(transcript_path, tool)}.json"


def _entry_age_seconds(payload: dict) -> float | None:
    """Seconds since `first_blocked_at` in `payload`, or None if unparseable."""
    raw = payload.get("first_blocked_at")
    if not isinstance(raw, str):
        return None
    try:
        dt = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None
    return (datetime.now(UTC) - dt).total_seconds()


def prune_expired() -> None:
    """Remove any state file whose `first_blocked_at` is older than the TTL.

    Run on every read so the directory does not accumulate forever.
    Per-file failures fall through to the logger via `_safe_unlink`;
    a directory listing failure logs once and bails for this call.
    """
    if not STATE_DIR.exists():
        return
    try:
        entries = list(STATE_DIR.iterdir())
    except OSError as exc:
        _log_state_error(f"prune-iterdir:{type(exc).__name__}")
        return
    for entry in entries:
        if entry.suffix != ".json":
            continue
        try:
            with entry.open(encoding="utf-8") as fh:
                payload = json.load(fh)
        except FileNotFoundError:
            continue
        except (OSError, ValueError) as exc:
            _log_state_error(f"prune-read:{type(exc).__name__}")
            _safe_unlink(entry, "prune-corrupt")
            continue
        age = _entry_age_seconds(payload)
        if age is None or age > STATE_TTL_SECONDS:
            _safe_unlink(entry, "prune-expired")


def has_first_block(transcript_path: str, tool: str) -> bool:
    """True if a state file already exists for this flow within the TTL.

    Prunes expired entries first so a stale 25h-old file does not
    keep a flow in re-emission mode forever. Returns False on any
    unexpected read failure (logged); the dispatcher then treats the
    flow as fresh, which is the safe default.
    """
    prune_expired()
    path = _flow_path(transcript_path, tool)
    if not path.exists():
        return False
    try:
        with path.open(encoding="utf-8") as fh:
            payload = json.load(fh)
    except FileNotFoundError:
        return False
    except (OSError, ValueError) as exc:
        _log_state_error(f"has-first-block-read:{type(exc).__name__}")
        return False
    age = _entry_age_seconds(payload)
    if age is None or age > STATE_TTL_SECONDS:
        _safe_unlink(path, "has-first-block-expired")
        return False
    return True


def record_first_block(transcript_path: str, tool: str) -> bool:
    """Atomically record that this flow has fired its first block.

    Returns True on a successful create. Returns False on any of:
      - `FileExistsError`: a concurrent dispatcher won the race
        (expected, no log)
      - Any other `OSError`: real failure (logged, treated by the
        caller as if state were unwritable and the flow had no prior
        block)
    """
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _log_state_error(f"record-mkdir:{type(exc).__name__}")
        return False
    path = _flow_path(transcript_path, tool)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {"first_blocked_at": timestamp, "tool": tool}
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False
    except OSError as exc:
        _log_state_error(f"record-open:{type(exc).__name__}")
        return False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
    except OSError as exc:
        _log_state_error(f"record-write:{type(exc).__name__}")
        _safe_unlink(path, "record-rollback")
        return False
    return True

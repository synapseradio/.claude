"""Hold each part's exit until the part before it has exited.

The harness appends hook context in the order the hooks exit, so parts that
exit in sequence reach the context in sequence. Every slot of one event reads
the same stdin, so a hash of it names the directory the slots of that event
share. Each slot takes an exclusive lock on its own file for its lifetime,
and part k blocks on part k-1's lock, which the kernel releases when that
process exits.
https://man7.org/linux/man-pages/man2/flock.2.html
"""

import fcntl
import hashlib
import pathlib
import shutil
import threading
import time
from typing import IO

ORDER_DEADLINE = 3.0
STARTUP_POLL = 0.005
STALE_AFTER = 3600

_held: list[IO] = []


def slot_dir(state: pathlib.Path | str, raw_payload: str) -> pathlib.Path:
    """The directory the slots answering one payload share."""

    key = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()[:16]
    return pathlib.Path(state) / "order" / key


def register(slots: pathlib.Path, part: int) -> None:
    """Lock `part`'s file until this process exits; part 1 also clears stale directories."""

    if part == 1:
        _prune(slots.parent, keep=slots)
    slots.mkdir(parents=True, exist_ok=True)
    handle = open(slots / f"{part}.lock", "a")
    fcntl.flock(handle, fcntl.LOCK_EX)
    _held.append(handle)
    (slots / f"{part}.ready").touch()


def wait_for_predecessor(slots: pathlib.Path, part: int, deadline: float = ORDER_DEADLINE) -> bool:
    """Block until part-1's process has exited; False where the deadline passed first."""

    if part == 1:
        return True
    start = time.monotonic()
    ready = slots / f"{part - 1}.ready"
    # The one wait the lock cannot cover: the predecessor has not taken its
    # lock yet, and a lock nobody holds would let this part straight through.
    while not ready.exists():
        if time.monotonic() - start >= deadline:
            return False
        time.sleep(STARTUP_POLL)

    released = threading.Event()

    def acquire() -> None:
        with open(slots / f"{part - 1}.lock", "a") as handle:
            fcntl.flock(handle, fcntl.LOCK_SH)
        released.set()

    threading.Thread(target=acquire, daemon=True).start()
    return released.wait(max(deadline - (time.monotonic() - start), 0.0))


def _prune(order_root: pathlib.Path, keep: pathlib.Path) -> None:
    if not order_root.is_dir():
        return
    cutoff = time.time() - STALE_AFTER
    for entry in order_root.iterdir():
        if entry != keep and entry.is_dir() and entry.stat().st_mtime < cutoff:
            shutil.rmtree(entry, ignore_errors=True)

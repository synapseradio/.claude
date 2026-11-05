"""Hold each part's exit until the part before it, of the same delivery, has exited.

The harness appends hook context in the order the hooks exit, so parts that
exit in sequence reach the context in sequence. Every slot of one event reads
the same stdin, so a hash of it names the directory the slots of that event
share. A delivery is named by the generation its first part makes. Each part
takes an exclusive lock on its own file for its lifetime, and part k blocks on
part k-1's lock of the same generation, which the kernel releases when that
process exits.
https://man7.org/linux/man-pages/man2/flock.2.html
"""

import fcntl
import hashlib
import os
import pathlib
import shutil
import threading
import time
import uuid

ORDER_DEADLINE = 3.0
STARTUP_POLL = 0.005
STALE_AFTER = 3600

_held: list[int] = []


def slot_dir(state: pathlib.Path | str, raw_payload: str) -> pathlib.Path:
    """The directory the slots answering one payload share."""

    key = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()[:16]
    return pathlib.Path(state) / "order" / key


def private_slot_dir(state: pathlib.Path | str) -> pathlib.Path:
    """A directory no other run shares, for a run that stands apart from any delivery."""

    return pathlib.Path(state) / "order" / f"alone-{uuid.uuid4().hex}"


def hold(slots: pathlib.Path, generation: str, part: int) -> None:
    """Lock `part`'s file of `generation` until this process exits; part 1 also clears stale directories."""

    if part == 1:
        _prune(slots.parent, keep=slots)
    slots.mkdir(parents=True, exist_ok=True)
    fd = os.open(slots / f"{generation}.{part}.lock", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    _held.append(fd)
    (slots / f"{generation}.{part}.ready").touch()


def wait_for_predecessor(
    slots: pathlib.Path, generation: str, part: int, deadline: float = ORDER_DEADLINE
) -> bool:
    """Block until part-1's process of `generation` has exited; False where the deadline passed first."""

    if part == 1:
        return True
    start = time.monotonic()
    ready = slots / f"{generation}.{part - 1}.ready"
    # The one wait the lock cannot cover: the predecessor has not taken its
    # lock yet, and a lock nobody holds would let this part straight through.
    while not ready.exists():
        if time.monotonic() - start >= deadline:
            return False
        time.sleep(STARTUP_POLL)

    released = threading.Event()

    def acquire() -> None:
        with open(slots / f"{generation}.{part - 1}.lock", "a") as handle:
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
    if keep.is_dir():
        for stale in keep.iterdir():
            if stale.is_file() and stale.stat().st_mtime < cutoff:
                stale.unlink(missing_ok=True)

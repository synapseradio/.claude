"""The machine-wide pool of worker slots every worktree's runs share, one flock'd file per slot."""

import fcntl
import os
import sys
import zlib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def default_dir() -> Path:
    """`$XDG_CACHE_HOME/claude-verify/slots`, with `$HOME/.cache` where XDG_CACHE_HOME is unset or relative.

    https://specifications.freedesktop.org/basedir-spec/latest/
    """
    cache = Path(os.environ.get("XDG_CACHE_HOME", ""))
    base = cache if cache.is_absolute() else Path.home() / ".cache"
    return base / "claude-verify" / "slots"


class SlotPool:
    def __init__(self, directory: Path, size: int) -> None:
        self.directory = directory
        self.size = size
        self.directory.mkdir(parents=True, exist_ok=True)

    def open(self, index: int) -> int:
        # os.open returns a descriptor no child inherits (PEP 446), so a
        # runner's own children never keep a slot past the suite.
        # https://docs.python.org/3/library/os.html#fd-inheritance
        return os.open(self.directory / f"slot-{index}", os.O_RDWR | os.O_CREAT, 0o644)

    def grab(self, wanted: int, skip: frozenset[int] = frozenset()) -> list[int]:
        """Take up to `wanted` free slots without blocking; returns their descriptors."""
        held: list[int] = []
        for index in range(self.size):
            if len(held) >= wanted:
                break
            if index in skip:
                continue
            fd = self.open(index)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(fd)
                continue
            held.append(fd)
        return held

    @contextmanager
    def take(self, name: str, wanted: int) -> Iterator[int]:
        """Hold between one and `wanted` slots for the block, blocking only while none is free.

        A flock belongs to the open file description, so closing the
        descriptor releases the slot.
        https://man7.org/linux/man-pages/man2/flock.2.html
        """
        held = self.grab(wanted)
        try:
            if not held:
                print(f"verify: {name} waiting for a slot", file=sys.stderr, flush=True)
                index = zlib.crc32(name.encode()) % self.size
                fd = self.open(index)
                held.append(fd)
                fcntl.flock(fd, fcntl.LOCK_EX)
                held += self.grab(wanted - 1, skip=frozenset({index}))
            yield len(held)
        finally:
            for fd in held:
                os.close(fd)

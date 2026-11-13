"""The machine-wide pool of worker slots every worktree's runs share, one flock'd file per slot."""

import fcntl
import os
import sys
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path


def default_dir() -> Path:
    """`$XDG_CACHE_HOME/claude-verify/slots`, with `$HOME/.cache` where XDG_CACHE_HOME is unset or relative.

    https://specifications.freedesktop.org/basedir-spec/latest/
    """
    cache = Path(os.environ.get("XDG_CACHE_HOME", ""))
    base = cache if cache.is_absolute() else Path.home() / ".cache"
    return base / "claude-verify" / "slots"


RETRY_PAUSE = 0.05


def fair_shares(wants: Mapping[str, int], size: int) -> dict[str, int]:
    """Divide `size` slots among the named suites, each getting at least 1 and at most its want.

    Every name gets 1; the slots left go out in proportion to `want - 1`,
    rounded down, then one each by largest remainder, ties settled by name order.
    """
    shares = dict.fromkeys(wants, 1)
    weights = {name: max(want - 1, 0) for name, want in wants.items()}
    total = sum(weights.values())
    spare = min(max(size - len(wants), 0), total)
    if not spare:
        return shares

    remainders: dict[str, int] = {}
    leftover = spare
    for name, weight in weights.items():
        extra, remainders[name] = divmod(spare * weight, total)
        shares[name] += extra
        leftover -= extra
    for name in sorted(wants, key=lambda name: (-remainders[name], name)):
        if leftover and shares[name] < wants[name]:
            shares[name] += 1
            leftover -= 1
    return shares


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

    def grab(self, wanted: int) -> list[int]:
        """Take up to `wanted` free slots without blocking; returns their descriptors."""
        held: list[int] = []
        for index in range(self.size):
            if len(held) >= wanted:
                break
            fd = self.open(index)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(fd)
                continue
            held.append(fd)
        return held

    @contextmanager
    def take(
        self, name: str, wanted: int, on_wait: Callable[[], None] | None = None
    ) -> Iterator[int]:
        """Hold between one and `wanted` slots for the block, waiting only while none is free.

        With none free, `on_wait` is called once (or, omitted, a line goes to
        stderr), then the pool is polled until any holder frees any slot.
        flock cannot wait on several files at once, so the wait is a retry loop.

        A flock belongs to the open file description, so closing the
        descriptor releases the slot.
        https://man7.org/linux/man-pages/man2/flock.2.html
        """
        held = self.grab(wanted)
        try:
            if not held:
                if on_wait is None:
                    print(f"verify: {name} waiting for a slot", file=sys.stderr, flush=True)
                else:
                    on_wait()
                while not held:
                    time.sleep(RETRY_PAUSE)
                    held = self.grab(wanted)
            yield len(held)
        finally:
            for fd in held:
                os.close(fd)

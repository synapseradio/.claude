"""Starting tasks: finding their programs, holding slots while each runs, and writing each one's log."""

import contextlib
import hashlib
import os
import queue
import shutil
import signal
import subprocess
import threading
import time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import events
import progress
from events import Event
from slots import SlotPool, fair_shares

from tasks import Task

STOP_GRACE_SECONDS = 2.0

INSTALL_HINTS = {
    "claude": (
        "verify: claude is not on PATH; install Claude Code, which provides it "
        "(the Brewfile does not)"
    ),
}


@dataclass(frozen=True)
class Missing:
    program: str

    def message(self) -> str:
        if self.program in INSTALL_HINTS:
            return INSTALL_HINTS[self.program]
        if "/" in self.program:
            return f"verify: {self.program} is missing; run just setup to install it"
        return f"verify: {self.program} is not on PATH; run just tools to install it"


def missing(root: Path, programs: Iterable[str], env: dict[str, str]) -> list[Missing]:
    """Programs that cannot start: a path holding `/` is repository-relative, any other name is looked up on PATH."""
    absent = []
    for program in dict.fromkeys(programs):
        if "/" in program:
            found = shutil.which(str(root / program))
        else:
            found = shutil.which(program, path=env.get("PATH", ""))
        if found is None:
            absent.append(Missing(program))
    return absent


def digests(root: Path, paths: Iterable[str]) -> dict[str, str | None]:
    """Content hash of each repository-relative path; None for a path that does not exist."""
    found: dict[str, str | None] = {}
    for path in paths:
        try:
            found[path] = hashlib.sha256((root / path).read_bytes()).hexdigest()
        except OSError:
            found[path] = None
    return found


def run_dir(log_root: Path, log_name: str, pid: int) -> Path:
    directory = log_root / log_name / f"{datetime.now():%Y%m%d-%H%M%S}-{pid}"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


@dataclass(frozen=True)
class Finished:
    task: Task
    command: list[str]
    exit: int
    seconds: float
    log: Path
    fixed: tuple[str, ...] = ()


class Interrupted(Exception):
    """The run got SIGINT or SIGTERM and ended every suite still running."""


@dataclass(frozen=True)
class Crashed:
    error: Exception


def shares_for(tasks: list[Task], size: int, cap: int | None, serial: bool) -> dict[str, int]:
    """Workers each task starts with: a fair share of the pool, or the whole pool one task at a time under `serial`."""
    wants = {task.name: task.wants if cap is None else min(task.wants, cap) for task in tasks}
    if serial:
        return {name: min(want, size) for name, want in wants.items()}
    return fair_shares(wants, size)


class Running:
    """The process groups of suites still running, so that an interrupt can end every one.

    Each suite starts in a session of its own, so the terminal's Ctrl-C reaches only the
    runner, which then signals each group: the suite's program and every process it started.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._processes: dict[int, subprocess.Popen[bytes]] = {}
        self._stopping = False

    def start(
        self, command: list[str], cwd: Path, env: dict[str, str]
    ) -> subprocess.Popen[bytes] | None:
        """Start `command` in its own process group, its output merged on one pipe; None once `stop` has begun."""
        with self._lock:
            if self._stopping:
                return None
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            self._processes[process.pid] = process
            return process

    def forget(self, process: subprocess.Popen[bytes]) -> None:
        with self._lock:
            self._processes.pop(process.pid, None)

    def stop(self) -> None:
        """Send SIGTERM to every group, wait out the grace period, then SIGKILL what is left."""
        with self._lock:
            self._stopping = True
            processes = list(self._processes.values())
        signal_groups(processes, signal.SIGTERM)
        deadline = time.monotonic() + STOP_GRACE_SECONDS
        for process in processes:
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=max(deadline - time.monotonic(), 0))
        signal_groups(processes, signal.SIGKILL)


def signal_groups(processes: list[subprocess.Popen[bytes]], signum: int) -> None:
    for process in processes:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(process.pid, signum)


@contextlib.contextmanager
def sigterm_as_interrupt() -> Iterator[None]:
    """Raise KeyboardInterrupt on SIGTERM too, so that `kill` stops the run as Ctrl-C does."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    previous = signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


@dataclass(frozen=True)
class Runner:
    root: Path
    env: dict[str, str]
    pool: SlotPool
    logs: Path
    cap: int | None
    announce_waits: bool = False

    def run_one(
        self, task: Task, share: int, emit: Callable[[Event], None], running: Running
    ) -> Finished | None:
        """Run `task` on up to `share` workers, emitting its events; None when the run stopped before it started."""
        log = self.logs / f"{task.name.replace('/', '-')}.log"
        on_wait = (lambda: emit(events.SuiteWaiting(task.name))) if self.announce_waits else None
        with self.pool.take(task.name, share, on_wait) as workers:
            command = task.argv(workers)
            before = digests(self.root, task.fixable)
            started = time.monotonic()
            process = running.start(command, self.root, {**self.env, **task.env})
            if process is None:
                return None
            emit(events.SuiteStarted(task.name, workers))
            parser = (
                None
                if task.kind == "lint"
                else progress.parser_for(task.kind, task.name, task.root)
            )
            with log.open("wb") as out:
                for raw in process.stdout:
                    out.write(raw)
                    if parser is not None:
                        for event in parser.feed(raw.decode("utf-8", "replace").rstrip("\r\n")):
                            emit(event)
            code = process.wait()
            running.forget(process)
            seconds = time.monotonic() - started
        after = digests(self.root, task.fixable)
        fixed = tuple(path for path in task.fixable if before[path] != after[path])
        return Finished(task, command, code, seconds, log, fixed)

    def run_all(
        self,
        tasks: list[Task],
        serial: bool,
        done: Callable[[Finished], None],
        on_event: Callable[[Event], None] = lambda _: None,
    ) -> None:
        """Run every task, calling `done` and `on_event` on the calling thread as each one ends or reports.

        Raises Interrupted, after every suite's processes have ended, on SIGINT or SIGTERM.
        """
        shares = shares_for(tasks, self.pool.size, self.cap, serial)
        inbox: queue.SimpleQueue[Event | Finished | Crashed] = queue.SimpleQueue()
        running = Running()

        def work(batch: list[Task]) -> None:
            for task in batch:
                try:
                    finished = self.run_one(task, shares[task.name], inbox.put, running)
                except Exception as error:
                    inbox.put(Crashed(error))
                    return
                if finished is None:
                    return
                inbox.put(finished)

        batches = [tasks] if serial else [[task] for task in tasks]
        threads = [threading.Thread(target=work, args=(batch,), daemon=True) for batch in batches]
        with sigterm_as_interrupt():
            try:
                for thread in threads:
                    thread.start()
                remaining = len(tasks)
                while remaining:
                    match inbox.get():
                        case Finished() as finished:
                            remaining -= 1
                            done(finished)
                        case Crashed(error):
                            raise error
                        case event:
                            on_event(event)
            except KeyboardInterrupt:
                running.stop()
                raise Interrupted from None
            except BaseException:
                running.stop()
                raise

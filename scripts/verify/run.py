"""Starting tasks: finding their programs, holding slots while each runs, and writing each one's log."""

import shutil
import subprocess
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from slots import SlotPool
from tasks import Task


@dataclass(frozen=True)
class Missing:
    program: str

    def message(self) -> str:
        if self.program == "claude":
            return (
                "verify: claude is not on PATH; install Claude Code, which provides it "
                "(the Brewfile does not)"
            )
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


@dataclass(frozen=True)
class Runner:
    root: Path
    env: dict[str, str]
    pool: SlotPool
    logs: Path
    cap: int | None

    def run_one(self, task: Task) -> Finished:
        wanted = task.wants if self.cap is None else min(task.wants, self.cap)
        log = self.logs / f"{task.name.replace('/', '-')}.log"
        with self.pool.take(task.name, wanted) as workers:
            command = task.build(workers)
            started = time.monotonic()
            with log.open("wb") as out:
                process = subprocess.Popen(
                    command,
                    cwd=self.root,
                    env=self.env,
                    stdin=subprocess.DEVNULL,
                    stdout=out,
                    stderr=subprocess.STDOUT,
                )
                code = process.wait()
            seconds = time.monotonic() - started
        return Finished(task, command, code, seconds, log)

    def run_all(self, tasks: list[Task], serial: bool, done: Callable[[Finished], None]) -> None:
        """Run every task, calling `done` on the calling thread as each one ends."""
        if serial or len(tasks) <= 1:
            for task in tasks:
                done(self.run_one(task))
            return
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = [executor.submit(self.run_one, task) for task in tasks]
            for future in as_completed(futures):
                done(future.result())

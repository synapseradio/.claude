"""Scratch repositories, stubbed programs, and a slot holder for the verify runner tests.

Every sandbox lives under one pytest tmp_path: HOME, the XDG directories, the
global git config, the slot pool, and the log root all point inside it, and the
child environment starts empty rather than from the caller's, so no run reads
or writes the machine's own state.

Every program the runner starts is a stub: `uv`, `bats`, `claude`, `treefmt`,
`shellcheck`, `taplo`, `yamlfmt`, and `shfmt` on PATH, and
`node_modules/.bin/{biome,tsc}` inside the scratch
repository. A stub appends a start record (program, argv, cwd, environment,
whether the release marker existed) to `calls.jsonl`, prints the canned output
of the first response whose program matches and whose substring occurs in its
argv, appends an end record, and exits with that response's code. A response
may also name files to rewrite, which the stub does before printing, to
simulate a fixer changing what it was handed.

The scratch repository is built once per pytest process and copied into each
sandbox, so no test starts git to set one up and none can write into the
shared copy. `Sandbox.run` calls `cli.main` in this process, with the
sandbox's environment, working directory, and captured streams, and puts all
three back afterwards. It starts a real process instead for `fmt` and `verify`,
whose formatter inherits the caller's output descriptors, and while a `Holder`
of that sandbox is alive, because a run waiting on a held slot needs a timeout.
"""

import atexit
import contextlib
import fcntl
import functools
import io
import itertools
import json
import os
import pathlib
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import types
from collections.abc import Iterator

WORKTREE = pathlib.Path(__file__).resolve().parents[2]
VERIFY_DIR = WORKTREE / "scripts" / "verify"
CLI = VERIFY_DIR / "cli.py"
REAL_MANIFEST = VERIFY_DIR / "jobs.toml"

# A commit starts a detached `git maintenance run --auto`, whose lock files
# can vanish while a test copies the repository.
# https://git-scm.com/docs/git-config#Documentation/git-config.txt-maintenanceauto
GITCONFIG = (
    "[user]\n\tname = t\n\temail = t@t\n"
    "[init]\n\tdefaultBranch = main\n"
    "[commit]\n\tgpgsign = false\n"
    "[maintenance]\n\tauto = false\n"
)

GIT_LOCATORS = ("GIT_DIR", "GIT_INDEX_FILE", "GIT_PREFIX", "GIT_WORK_TREE", "GIT_COMMON_DIR")
RUN_TIMEOUT = 20

PROCESS_COMMANDS = ("fmt", "verify")
HANDLED_SIGNALS = (signal.SIGINT, signal.SIGTERM)

PATH_PROGRAMS = ("uv", "bats", "claude", "treefmt", "shellcheck", "taplo", "yamlfmt", "shfmt")
REPO_PROGRAMS = ("biome", "tsc")

MANIFEST = """\
[[job]]
name = "py-a"
kind = "pytest"
tests = ["pkg_a/tests"]
sources = ["pkg_a/**", "pyproject.toml"]
langs = ["py"]

[[job]]
name = "py-b"
kind = "pytest"
tests = ["pkg_b/tests"]
sources = ["pkg_b/**", "pyproject.toml", "plugins/*/manifest.json"]
langs = ["py"]

[[job]]
name = "sh-bats"
kind = "bats"
tests = ["shell/tests"]
sources = ["shell/**"]
langs = ["bats", "sh"]

[[job]]
name = "mod-gauge"
kind = "mod"
tests = ["mod"]
sources = ["mod/**"]
langs = ["ts"]

[[job]]
name = "ruff"
kind = "lint"
mode = "files"
command = ["uv", "run", "--frozen", "ruff", "check"]
sources = ["**/*.py"]
langs = ["py"]
"""

TREEFMT = """\
[formatter.biome]
command = "node_modules/.bin/biome"
options = ["check", "--write", "--no-errors-on-unmatched", "--files-ignore-unknown=true"]
includes = ["*.ts", "*.json"]

[formatter.rumdl]
command = "uv"
options = ["run", "--frozen", "rumdl", "fmt"]
includes = ["*.md"]

[formatter.ruff-check]
command = "uv"
options = ["run", "--frozen", "ruff", "check", "--fix"]
includes = ["*.py"]
priority = 0

[formatter.ruff-format]
command = "uv"
options = ["run", "--frozen", "ruff", "format"]
includes = ["*.py"]
priority = 1

[formatter.yamlfmt]
command = "yamlfmt"
includes = ["*.yaml", "*.yml"]

[formatter.taplo]
command = "taplo"
options = ["fmt"]
includes = ["*.toml"]

[formatter.shfmt]
command = "shfmt"
options = ["-i", "2", "-w"]
includes = ["*.sh", "*.bash", "*.bats"]
"""

FILES = {
    ".gitignore": "node_modules/\n",
    "pyproject.toml": '[project]\nname = "proj"\n',
    "README.md": "# proj\n",
    "LICENSE": "MIT\n",
    "treefmt.toml": TREEFMT,
    "pkg_a/src/a.py": "VALUE = 1\n",
    "pkg_a/tests/test_a1.py": "def test_one():\n    pass\n",
    "pkg_a/tests/test_a2.py": "def test_two():\n    pass\n",
    "pkg_a/tests/test_a3.py": "def test_three():\n    pass\n",
    "pkg_b/src/b.py": "VALUE = 2\n",
    "pkg_b/tests/test_b1.py": "def test_b():\n    pass\n",
    "plugins/x/manifest.json": "{}\n",
    "plugins/x/deep/manifest.json": "{}\n",
    "shell/lib.sh": "greet() { echo hi; }\n",
    "shell/tests/one.bats": "@test 'first case passes' { true; }\n",
    "shell/tests/two.bats": "@test 'second case passes' { true; }\n",
    "mod/src/index.ts": "export const gauge = 1;\n",
    "mod/tests/gauge.test.ts": 'test("renders the gauge bar", () => {});\n',
    "scripts/verify/jobs.toml": MANIFEST,
}

# A tree laid out like this repository, linted under the real job manifest.
PLUGIN = '{"name": "p"}\n'
REAL_TREE = {
    ".gitignore": "node_modules/\n",
    "Brewfile": 'brew "just"\n',
    "justfile": "default:\n    just --list\n",
    "top.py": "TOP = 1\n",
    "app/main.py": "MAIN = 1\n",
    "README.md": "# tree\n",
    "docs/guide.md": "# guide\n",
    "conf/a.yaml": "a: 1\n",
    "conf/b.toml": "b = 1\n",
    "bin/run.sh": "#!/bin/bash\necho run\n",
    "web/app.ts": "export const app = 1;\n",
    "data/x.json": "{}\n",
    ".claude-plugin/marketplace.json": '{"plugins": []}\n',
    "features/plugins/warden/.claude-plugin/plugin.json": PLUGIN,
    "features/plugins/warden/hooks/h.sh": "#!/bin/bash\ntrue\n",
    "features/plugins/planning/.claude-plugin/plugin.json": PLUGIN,
    "features/plugins/planning/skills/s.md": "# skill\n",
    "features/mods/context-gauge/.claude-plugin/plugin.json": PLUGIN,
    "features/mods/context-gauge/src/gauge.ts": "export const gauge = 1;\n",
    "features/plugins/rulesets/.claude-plugin/plugin.json": PLUGIN,
    "features/plugins/rulesets/lib/rulesets/cli.py": "CLI = 1\n",
    "features/plugins/rulesets/hooks/with-python.sh": "#!/bin/bash\ntrue\n",
    "rulesets/config.yaml": "rules: []\n",
    "rulesets/rules/a.md": "# rule\n",
}

PYTEST_PASS = "...                                                    [100%]\n3 passed in 0.10s\n"
BATS_PASS = "1..3\nok 1 first case passes\nok 2 second case passes\nok 3 third case passes\n"
CLAUDE_PASS = "1 passed\n"
PYTEST_NONE_SELECTED = "3 deselected in 0.01s\n"

PYTEST_ONE_FAILURE = """\
.F.                                                                      [100%]
=================================== FAILURES ===================================
___________________________________ test_two ___________________________________
    def test_two():
>       assert False, "boom"
E       AssertionError: boom
=========================== short test summary info ============================
FAILED pkg_a/tests/test_a1.py::test_two - AssertionError: boom
1 failed, 2 passed in 0.12s
"""

BATS_TWO_FAILURES = """\
1..4
ok 1 first case passes
not ok 2 second case fails
# (in test file shell/tests/one.bats, line 5)
#   `false' failed
ok 3 third case passes
not ok 4 fourth case fails
# (in test file shell/tests/two.bats, line 2)
"""

DEFAULT_OUTPUT = {"uv": PYTEST_PASS, "bats": BATS_PASS, "claude": CLAUDE_PASS}

STUB = """\
#!{python}
import fcntl, json, os, pathlib, sys

STATE = pathlib.Path({state!r})
MARKER = pathlib.Path({marker!r})
DEFAULT = {default!r}

prog = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]


def record(entry):
    with open(STATE / "calls.jsonl", "a", encoding="utf-8") as log:
        fcntl.flock(log, fcntl.LOCK_EX)
        log.write(json.dumps(entry) + "\\n")


record({{
    "event": "start",
    "pid": os.getpid(),
    "prog": prog,
    "args": args,
    "cwd": os.getcwd(),
    "env": dict(os.environ),
    "released": MARKER.exists(),
}})
responses_file = STATE / "responses.json"
responses = json.loads(responses_file.read_text()) if responses_file.exists() else []
joined = " ".join(args)
stdout, code = DEFAULT, 0
for response in responses:
    if response["prog"] == prog and response["match"] in joined:
        stdout, code = response["stdout"], response["exit"]
        for name in response.get("rewrite", []):
            target = pathlib.Path(name)
            target.write_text(target.read_text() + "# rewritten\\n")
        break
sys.stdout.write(stdout)
sys.stdout.flush()
record({{"event": "end", "pid": os.getpid(), "prog": prog, "args": args}})
sys.exit(code)
"""

HOLDER = """\
import fcntl, pathlib, sys

marker = pathlib.Path(sys.argv[1])
handles = []
for name in sys.argv[2:]:
    path = pathlib.Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a")
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    handles.append(handle)
print("held", flush=True)
sys.stdin.readline()
marker.write_text("released")
for handle in handles:
    fcntl.flock(handle, fcntl.LOCK_UN)
    handle.close()
print("released", flush=True)
"""


def run_git(git: str, cwd: pathlib.Path, env: dict[str, str], *args: str) -> str:
    result = subprocess.run(
        [git, *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=RUN_TIMEOUT,
    )
    assert result.returncode == 0, f"git {' '.join(args)} failed: {result.stderr}"
    return result.stdout.strip()


_templates: dict[tuple, pathlib.Path] = {}


@functools.cache
def _template_root() -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix="verify-fixtures-")).resolve()
    atexit.register(shutil.rmtree, root, ignore_errors=True)
    return root


def template_repo(files: dict[str, str]) -> pathlib.Path:
    """The repository holding exactly `files` on branch `work`, built the first time it is asked for."""
    key = tuple(files.items())
    if key not in _templates:
        directory = _template_root() / str(len(_templates))
        _build_template(directory, files)
        _templates[key] = directory / "proj"
    return _templates[key]


def _build_template(directory: pathlib.Path, files: dict[str, str]) -> None:
    git = shutil.which("git")
    assert git, "the sandbox builds its repository with the machine's git"
    gitconfig = directory / "gitconfig"
    repo = directory / "proj"
    repo.mkdir(parents=True)
    gitconfig.write_text(GITCONFIG)
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(directory),
        "XDG_CACHE_HOME": str(directory / "cache"),
        "XDG_CONFIG_HOME": str(directory / "config"),
        "GIT_CONFIG_GLOBAL": str(gitconfig),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    run_git(git, repo, env, "init", "-q", "-b", "main")
    for relative, text in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    run_git(git, repo, env, "add", "-A")
    run_git(git, repo, env, "commit", "-q", "-m", "init")
    run_git(git, repo, env, "checkout", "-q", "-b", "work")


@contextlib.contextmanager
def in_process_state(cwd: pathlib.Path, env: dict[str, str]) -> Iterator[None]:
    """Run the body in `cwd` with exactly `env`, then restore the working directory, environment, and signal handlers."""
    saved_cwd = os.getcwd()
    saved_env = dict(os.environ)
    on_main_thread = threading.current_thread() is threading.main_thread()
    saved_handlers = (
        {sig: signal.getsignal(sig) for sig in HANDLED_SIGNALS} if on_main_thread else {}
    )
    os.chdir(cwd)
    os.environ.clear()
    os.environ.update(env)
    try:
        yield
    finally:
        os.chdir(saved_cwd)
        os.environ.clear()
        os.environ.update(saved_env)
        for sig, handler in saved_handlers.items():
            if handler is not None:
                signal.signal(sig, handler)


def load_cli() -> types.ModuleType:
    if str(VERIFY_DIR) not in sys.path:
        sys.path.insert(0, str(VERIFY_DIR))
    import cli

    return cli


class Sandbox:
    """One scratch repository `proj` on branch `work`, its stubs, and an environment confined to tmp_path."""

    def __init__(self, tmp_path: pathlib.Path, files: dict[str, str] = FILES) -> None:
        self.root = tmp_path.resolve()
        self.home = self.root / "home"
        self.cache = self.root / "cache"
        self.logs = self.root / "logs"
        self.state = self.root / "stub-state"
        self.stubs = self.root / "stubs"
        self.tools = self.root / "tools"
        self.marker = self.root / "released"
        self.repo = self.root / "proj"
        self.slot_dir = self.cache / "claude-verify" / "slots"
        for directory in (self.home, self.cache, self.logs, self.state, self.stubs, self.tools):
            directory.mkdir(parents=True)
        (self.root / "tmp").mkdir()
        self.holders: list[Holder] = []
        gitconfig = self.root / "gitconfig"
        gitconfig.write_text(GITCONFIG)
        git = shutil.which("git")
        assert git, "the sandbox links the machine's git into its PATH"
        (self.tools / "git").symlink_to(git)
        self.env = {
            "PATH": os.pathsep.join([str(self.stubs), str(self.tools), "/usr/bin", "/bin"]),
            "HOME": str(self.home),
            "TMPDIR": str(self.root / "tmp"),
            "XDG_CACHE_HOME": str(self.cache),
            "XDG_CONFIG_HOME": str(self.root / "config"),
            "XDG_DATA_HOME": str(self.root / "data"),
            "XDG_STATE_HOME": str(self.root / "xdg-state"),
            "GIT_CONFIG_GLOBAL": str(gitconfig),
            "GIT_CONFIG_NOSYSTEM": "1",
            "VERIFY_SLOTS": "8",
            "VERIFY_LOG_DIR": str(self.logs),
            "LANG": "C.UTF-8",
        }
        self.build_repo(files)
        for prog in PATH_PROGRAMS:
            self.install_stub(self.stubs / prog)
        for prog in REPO_PROGRAMS:
            self.install_stub(self.repo / "node_modules" / ".bin" / prog)

    def install_stub(self, path: pathlib.Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            STUB.format(
                python=sys.executable,
                state=str(self.state),
                marker=str(self.marker),
                default=DEFAULT_OUTPUT.get(path.name, ""),
            )
        )
        path.chmod(0o755)

    def remove_stub(self, prog: str) -> None:
        """Remove a stub from PATH, or from node_modules/.bin for the repository's own tools."""
        if prog in REPO_PROGRAMS:
            (self.repo / "node_modules" / ".bin" / prog).unlink()
        else:
            (self.stubs / prog).unlink()

    def respond(
        self,
        prog: str,
        match: str,
        stdout: str,
        exit_code: int = 0,
        rewrite: list[str] | None = None,
    ) -> None:
        """Make `prog` print `stdout` and exit `exit_code` when its argv contains `match`.

        Each path in `rewrite`, relative to the stub's working directory, gains a line first.
        """
        path = self.state / "responses.json"
        responses = json.loads(path.read_text()) if path.exists() else []
        responses.append(
            {
                "prog": prog,
                "match": match,
                "stdout": stdout,
                "exit": exit_code,
                "rewrite": rewrite or [],
            }
        )
        path.write_text(json.dumps(responses))

    def git(self, *args: str, cwd: pathlib.Path | None = None) -> str:
        return run_git("git", cwd or self.repo, self.env, *args)

    def write(self, relative: str, text: str) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def build_repo(self, files: dict[str, str]) -> None:
        shutil.copytree(template_repo(files), self.repo, symlinks=True)

    def add_origin(self) -> pathlib.Path:
        bare = self.root / "origin.git"
        self.git("init", "-q", "--bare", "-b", "main", str(bare), cwd=self.root)
        self.git("remote", "add", "origin", str(bare))
        return bare

    def run(self, *args: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
        env = {**self.env, **(extra_env or {})}
        holding = any(holder.process.poll() is None for holder in self.holders)
        if holding or (args and args[0] in PROCESS_COMMANDS):
            return self.run_as_process(args, env)
        return self.run_in_process(args, env)

    def run_in_process(self, args: tuple[str, ...], env: dict) -> subprocess.CompletedProcess:
        cli = load_cli()
        out, err = io.StringIO(), io.StringIO()
        with (
            in_process_state(self.repo, env),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            code = self.dispatch_like_main(cli, list(args))
        return subprocess.CompletedProcess(
            [sys.executable, str(CLI), *args], code, out.getvalue(), err.getvalue()
        )

    @staticmethod
    def dispatch_like_main(cli, argv: list[str]) -> int:
        try:
            return cli.main(argv)
        except SystemExit as stop:
            if isinstance(stop.code, str):
                print(stop.code, file=sys.stderr)
                return 1
            return stop.code or 0
        except Exception:
            traceback.print_exc()
            return 1

    def run_as_process(self, args: tuple[str, ...], env: dict) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=RUN_TIMEOUT,
        )

    def run_expecting(
        self, command: str, *args: str, expect: int = 0
    ) -> subprocess.CompletedProcess:
        result = self.run(command, *args)
        assert result.returncode == expect, (
            f"{command} {' '.join(args)} exited {result.returncode}, wanted {expect}: {result.stderr}"
        )
        return result

    def run_json(self, *args: str, expect: int = 0) -> dict:
        result = self.run(*args, "--json")
        assert result.returncode == expect, (
            f"cli.py {' '.join(args)} --json exited {result.returncode}, wanted {expect}: "
            f"{result.stderr}"
        )
        return json.loads(result.stdout)

    def popen(self, *args: str, extra_env: dict | None = None) -> subprocess.Popen:
        env = {**self.env, **(extra_env or {})}
        return subprocess.Popen(
            [sys.executable, str(CLI), *args],
            cwd=self.repo,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

    def events(self) -> list[dict]:
        """Every start and end record, in the order the stubs wrote them."""
        path = self.state / "calls.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line]

    def calls(self, prog: str | None = None) -> list[dict]:
        """Start records, optionally of one program."""
        return [
            event
            for event in self.events()
            if event["event"] == "start" and (prog is None or event["prog"] == prog)
        ]

    def call_for(self, prog: str, needle: str) -> dict:
        """The one recorded call of `prog` whose argv mentions `needle`."""
        matching = [call for call in self.calls(prog) if needle in " ".join(call["args"])]
        assert len(matching) == 1, (
            f"wanted one {prog} call mentioning {needle!r}, got {[c['args'] for c in self.calls(prog)]}"
        )
        return matching[0]

    def paths_in(self, call: dict) -> list[str]:
        """The existing repository paths a recorded call names, relative to the repository root."""
        base = pathlib.Path(call["cwd"])
        found = []
        for arg in call["args"]:
            if arg.startswith("-"):
                continue
            path = pathlib.Path(arg)
            path = (path if path.is_absolute() else base / path).resolve()
            if path.exists() and path.is_relative_to(self.repo) and path != self.repo:
                found.append(path.relative_to(self.repo).as_posix())
        return found

    def tracked(self, suffix: str) -> set[str]:
        return {path for path in self.git("ls-files").splitlines() if path.endswith(suffix)}

    def slot(self, index: int) -> pathlib.Path:
        return self.slot_dir / f"slot-{index}"

    def held_slots(self, size: int) -> list[str]:
        """The names of the pool's first `size` slots some process still holds a lock on."""
        held = []
        for index in range(size):
            with open(self.slot(index), "a") as handle:
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    held.append(self.slot(index).name)
        return held

    def hold(self, *indexes: int) -> Holder:
        return Holder(self, [self.slot(index) for index in indexes])


class RealManifestSandbox(Sandbox):
    """A tree shaped like this repository, carrying a copy of the real job manifest, with `bash` stubbed."""

    def __init__(self, tmp_path: pathlib.Path) -> None:
        files = dict(REAL_TREE)
        if REAL_MANIFEST.is_file():
            files["scripts/verify/jobs.toml"] = REAL_MANIFEST.read_text(encoding="utf-8")
        super().__init__(tmp_path, files)
        self.install_stub(self.stubs / "bash")

    def run(self, *args: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
        assert REAL_MANIFEST.is_file(), f"{REAL_MANIFEST} is the job manifest the runner reads"
        return super().run(*args, extra_env=extra_env)


class Holder:
    """A child process holding flocks on slot files until told to release them."""

    def __init__(self, sandbox: Sandbox, slots: list[pathlib.Path]) -> None:
        script = sandbox.root / "holder.py"
        script.write_text(HOLDER)
        self.process = subprocess.Popen(
            [sys.executable, str(script), str(sandbox.marker), *map(str, slots)],
            env=sandbox.env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        line = self.process.stdout.readline()
        assert line.strip() == "held", (
            f"the holder failed to lock {slots}: {self.process.stderr.read()}"
        )
        sandbox.holders.append(self)

    def release(self) -> None:
        self.process.stdin.write("release\n")
        self.process.stdin.flush()
        out, err = self.process.communicate(timeout=RUN_TIMEOUT)
        assert "released" in out, f"the holder failed to release: {err}"

    def kill(self) -> None:
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait(timeout=RUN_TIMEOUT)


def read_until(stream, needle: bytes, timeout: float = RUN_TIMEOUT) -> tuple[bool, bytes]:
    """Read lines from an unbuffered pipe until one holds `needle`, the pipe closes, or `timeout` passes.

    Returns whether the needle arrived and every byte read so far.
    """
    deadline = time.monotonic() + timeout
    seen = b""
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False, seen
        ready, _, _ = select.select([stream], [], [], remaining)
        if not ready:
            return False, seen
        line = stream.readline()
        if not line:
            return False, seen
        seen += line
        if needle in line:
            return True, seen


def pair(args: list[str], flag: str, value: str) -> bool:
    """Whether `flag` appears in `args` immediately followed by `value`."""
    return any(a == flag and b == value for a, b in itertools.pairwise(args))


def ran(report: dict) -> set[str]:
    """Names of the suites a JSON report says ran, passing or failing."""
    return {suite["name"] for suite in report["suites"] if suite["status"] in ("pass", "fail")}


def indented_block(lines: list[str], header_index: int) -> list[str]:
    """The two-space-indented lines directly under `lines[header_index]`, unindented."""
    block = []
    for line in lines[header_index + 1 :]:
        if not line.startswith("  "):
            break
        block.append(line[2:])
    return block


def find_line(lines: list[str], pattern: str) -> tuple[int, re.Match]:
    for index, line in enumerate(lines):
        match = re.fullmatch(pattern, line)
        if match:
            return index, match
    raise AssertionError(f"no line matches {pattern!r} in:\n" + "\n".join(lines))

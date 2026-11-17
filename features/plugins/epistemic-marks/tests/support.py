"""What the epistemic-marks tests share: an isolated environment, a hook runner, and transcript lines.

conftest.py puts the plugin root on the import path, and pytest puts this
directory there, so a test module imports this one as `support`.
"""

import contextlib
import functools
import importlib.util
import io
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from unittest import mock

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
VERIFY_MARKS = PLUGIN_ROOT / "hooks" / "verify-marks.py"

# Each test finishes within ten seconds, so a launch that outlasts this fails
# the test with room to report it.
HOOK_TIMEOUT = 8

# What a test never inherits: the variables that could point a hook at a real
# session's state or at the developer's own git and XDG configuration.
_SCRUBBED = ("VERIFY_MARKS_STATE_DIR", "CLAUDE_PLUGIN_DATA")
_SCRUBBED_PREFIXES = ("XDG_", "GIT_")


def isolated_environment(
    home: Path,
    *,
    path_dirs: Sequence[str] | None = None,
    plugin_data: Path | None = None,
    state_dir: Path | None = None,
) -> dict[str, str]:
    """A child process's environment: a throwaway HOME, XDG directories and git config.

    Without `path_dirs` the rest of the caller's environment carries over,
    minus the variables a hook could be pointed at real state through. With
    `path_dirs` the environment is only what this function sets, PATH being
    those directories. CLAUDE_PLUGIN_DATA is set where `plugin_data` is given,
    as the harness sets it for a hook and as it is absent outside the harness;
    VERIFY_MARKS_STATE_DIR likewise follows `state_dir`.
    """
    inherited = (
        {}
        if path_dirs is not None
        else {
            key: value
            for key, value in os.environ.items()
            if key not in _SCRUBBED and not key.startswith(_SCRUBBED_PREFIXES)
        }
    )
    environment = {
        **inherited,
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_STATE_HOME": str(home / ".local" / "state"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    if path_dirs is not None:
        environment["PATH"] = os.pathsep.join(path_dirs)
    if plugin_data is not None:
        environment["CLAUDE_PLUGIN_DATA"] = str(plugin_data)
    if state_dir is not None:
        environment["VERIFY_MARKS_STATE_DIR"] = str(state_dir)
    return environment


def exit_status(code: str | int | None) -> int:
    """The process status `sys.exit(code)` produces: None is 0, a message is 1."""
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    return 1


@functools.cache
def load_entrypoint(script: Path) -> ModuleType:
    """A hook script's module, loaded once so a pass can run without a launch."""
    spec = importlib.util.spec_from_file_location(f"{script.stem}_entrypoint", script)
    if spec is None or spec.loader is None:
        message = f"no loader for {script}"
        raise ImportError(message)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_hook(
    payload,
    *args: str,
    env: dict[str, str],
    script: Path = VERIFY_MARKS,
    in_process: bool = False,
    timeout: float = HOOK_TIMEOUT,
) -> tuple[int, str]:
    """Drive a hook script's entry the way the harness does, as (exit code, stdout).

    The script runs in a child process under `env` and `timeout`. With
    `in_process` its `main` runs in this one instead, under the same `env`,
    for a case that drives many passes and cannot afford a launch each.
    """
    if not in_process:
        completed = subprocess.run(
            [sys.executable, str(script), *args],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=timeout,
        )
        return completed.returncode, completed.stdout
    entrypoint = load_entrypoint(script)
    stdout = io.StringIO()
    code = 0
    with (
        mock.patch.dict(os.environ, env, clear=True),
        mock.patch.object(sys, "argv", [str(script), *args]),
        mock.patch.object(sys, "stdin", io.StringIO(json.dumps(payload))),
        contextlib.redirect_stdout(stdout),
    ):
        try:
            entrypoint.main()
        except SystemExit as ended:
            code = exit_status(ended.code)
    return code, stdout.getvalue()


def entry(kind, content) -> str:
    """One transcript line."""
    return json.dumps({"type": kind, "message": {"role": kind, "content": content}})


def user_text(text) -> str:
    return entry("user", text)


def assistant_text(text) -> str:
    return entry("assistant", [{"type": "text", "text": text}])

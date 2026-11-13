"""Where the rulesets directory and the engine's state sit under a configuration directory."""

from __future__ import annotations

import dataclasses
import os
import pathlib
import pwd
from collections.abc import Mapping


@dataclasses.dataclass(frozen=True)
class Locations:
    config: pathlib.Path

    @property
    def rulesets(self) -> pathlib.Path:
        return self.config / "rulesets"

    @property
    def state(self) -> pathlib.Path:
        return self.config / ".tmp" / "rulesets-engine"

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> Locations:
        """The locations under `CLAUDE_CONFIG_DIR`, or `~/.claude` where it is unset or empty.

        `~` is the home directory `environ` names, found as `os.path.expanduser` finds it:
        https://docs.python.org/3.15/library/os.path.html#os.path.expanduser
        """
        configured = environ.get("CLAUDE_CONFIG_DIR")
        return cls(pathlib.Path(configured) if configured else home_directory(environ) / ".claude")


def home_directory(environ: Mapping[str, str]) -> pathlib.Path:
    """The directory `~` names under `environ`: its `HOME`, or the user's password entry without one."""
    home = environ.get("HOME")
    if home is None:
        home = pwd.getpwuid(os.getuid()).pw_dir
    return pathlib.Path(home.rstrip("/") or "/")

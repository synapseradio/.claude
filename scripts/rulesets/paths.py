#!/usr/bin/env python3.14
"""Every path this change reads, derived from the configuration directory.

`CLAUDE_CONFIG_DIR` overrides the configuration directory wholesale, so a
hardcoded home path would read an empty tier directory under a second
configuration directory and fall open to nothing. One module computes
every path, and each other module and hook calls it.
"""

import os
import pathlib

CONFIG_ENV = "CLAUDE_CONFIG_DIR"
STATE_ENV = "RULESETS_STATE_DIR"


def config_root() -> pathlib.Path:
    """The configuration directory every other path derives from."""

    override = os.environ.get(CONFIG_ENV)
    if override:
        return pathlib.Path(override)
    return pathlib.Path.home() / ".claude"


def load_dir() -> pathlib.Path:
    """The directory the harness itself auto-loads."""

    return config_root() / "rules"


def rulesets_root() -> pathlib.Path:
    """The root holding one directory per tier."""

    return config_root() / "rulesets"


def manifest_path() -> pathlib.Path:
    return rulesets_root() / "manifest.yaml"


def state_dir() -> pathlib.Path:
    """Where per-session records live, with its own override."""

    override = os.environ.get(STATE_ENV)
    if override:
        return pathlib.Path(override)
    return config_root() / ".tmp" / "rulesets"

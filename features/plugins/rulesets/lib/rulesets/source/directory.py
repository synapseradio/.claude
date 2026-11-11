"""The rulesets directory read whole: its pool and its config."""

from __future__ import annotations

import dataclasses
import pathlib

from rulesets.source.config import (
    CONFIG_FILE,
    OLD_CONFIG_FILE,
    Config,
    ConfigParseError,
    read_config,
)
from rulesets.source.pool import Pool, read_pool


@dataclasses.dataclass(frozen=True)
class Present:
    config: Config


@dataclasses.dataclass(frozen=True)
class Missing:
    """No config file stands in the directory. `old_file` is the old file left standing there, if any."""

    old_file: pathlib.Path | None = None


@dataclasses.dataclass(frozen=True)
class Unparsable:
    error: ConfigParseError


type ConfigState = Present | Missing | Unparsable


@dataclasses.dataclass(frozen=True)
class RulesetsDirectory:
    root: pathlib.Path
    pool: Pool
    config: ConfigState


def read_directory(root: pathlib.Path) -> RulesetsDirectory:
    """Read the pool and the config. A config that does not parse is a state, not a raise."""

    config: ConfigState
    if not (root / CONFIG_FILE).is_file():
        old_file = root / OLD_CONFIG_FILE
        config = Missing(old_file if old_file.is_file() else None)
    else:
        try:
            config = Present(read_config(root))
        except ConfigParseError as failure:
            config = Unparsable(failure)
    return RulesetsDirectory(root, read_pool(root), config)

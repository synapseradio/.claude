"""Where the rulesets directory and the engine's state sit under a configuration directory."""

from __future__ import annotations

import dataclasses
import pathlib
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
        """The locations under `CLAUDE_CONFIG_DIR`, or `~/.claude` where it is unset or empty."""

        configured = environ.get("CLAUDE_CONFIG_DIR")
        return cls(pathlib.Path(configured) if configured else pathlib.Path.home() / ".claude")

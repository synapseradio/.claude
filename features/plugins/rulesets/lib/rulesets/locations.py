"""Where the rulesets directory and the engine's state sit under a configuration directory."""

import dataclasses
import pathlib


@dataclasses.dataclass(frozen=True)
class Locations:
    config: pathlib.Path

    @property
    def rulesets(self) -> pathlib.Path:
        return self.config / "rulesets"

    @property
    def state(self) -> pathlib.Path:
        return self.config / ".tmp" / "rulesets-engine"

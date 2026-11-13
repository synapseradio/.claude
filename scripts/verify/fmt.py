"""The treefmt call `fmt` makes: its formatters from `treefmt.toml`, and the ones a language selects."""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from manifest import LANG_EXTENSIONS, read_toml


@dataclass(frozen=True)
class Formatter:
    name: str
    command: str
    includes: tuple[str, ...]

    def covers(self, lang: str) -> bool:
        return any(
            PurePosixPath(f"sample{extension}").full_match(include)
            for extension in LANG_EXTENSIONS[lang]
            for include in self.includes
        )


def formatters(path: Path) -> list[Formatter]:
    config = read_toml(path)
    return [
        Formatter(name, entry["command"], tuple(entry.get("includes", ())))
        for name, entry in config.get("formatter", {}).items()
    ]


def command(files: list[str], names: list[str]) -> list[str]:
    selected = ["--formatters", ",".join(names)] if names else []
    return ["treefmt", *selected, *files]

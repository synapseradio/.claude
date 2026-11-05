"""Tier corpora and agent definitions built in temporary directories, shaped like a real tier corpus."""

import pathlib

import yaml

FAMILIES = ("opus", "sonnet", "haiku", "fable")


class Corpus:
    """A directory of tier directories with a manifest of tier entries and a map of model prefixes.

    Every tier directory exists and holds no file until `body` writes one. A tier includes every
    stem unless `left_out` names stems for it to leave out.
    """

    def __init__(
        self,
        tmp_path: pathlib.Path,
        *,
        left_out: dict[str, list[str]] | None = None,
        extra_tiers: tuple[str, ...] = (),
        order: list[str] | None = None,
    ):
        self.root = tmp_path / "corpus"
        tiers: dict[str, dict] = {
            tier: {"include": "*"} for tier in ("default", *FAMILIES, *extra_tiers)
        }
        for tier, stems in (left_out or {}).items():
            tiers[tier]["exclude"] = list(stems)
        manifest: dict = {"tiers": tiers}
        if order is not None:
            manifest["order"] = order
        self.root.mkdir()
        for tier in tiers:
            (self.root / tier).mkdir()
        self._dump("manifest.yaml", manifest)
        self._dump("models.yaml", {tier: [tier, f"claude-{tier}"] for tier in FAMILIES})

    def _dump(self, name: str, document: dict) -> None:
        (self.root / name).write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    def body(self, tier: str, stem: str, text: str | None = None) -> str:
        """Write `<tier>/<stem>.md` and return its text."""

        written = f"{stem} as {tier} writes it\n" if text is None else text
        (self.root / tier / f"{stem}.md").write_text(written, encoding="utf-8")
        return written


def define_agent(config: pathlib.Path, name: str, excluded: list[str]) -> pathlib.Path:
    """An agent definition under `config/agents` whose `metadata.rulesets` excludes the stems."""

    front = {
        "name": name,
        "description": "a test agent",
        "metadata": {"rulesets": {"exclude": excluded}},
    }
    path = config / "agents" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{yaml.safe_dump(front, sort_keys=False)}---\nbody\n", encoding="utf-8")
    return path

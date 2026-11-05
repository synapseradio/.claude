"""A tier corpus read as tiers: each tier's entry and files, the prefix map, and the files set aside."""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Collection, Mapping

import yaml

from rulesets.adopt.path_scope import is_path_scoped
from rulesets.adopt.skipped import NO_DEFAULT_FORM, PATH_SCOPED, Skipped

DEFAULT_TIER = "default"
MANIFEST_FILE = "manifest.yaml"
_PREFIX_FILE = "models.yaml"


class SourceError(Exception):
    """The source is not a corpus or folder adopt can read."""


@dataclasses.dataclass(frozen=True)
class EveryStem:
    """A tier entry that includes every stem but those in `exclude`."""

    exclude: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class Listed:
    """A tier entry that lists the stems it includes."""

    stems: tuple[str, ...]


type TierEntry = EveryStem | Listed


@dataclasses.dataclass(frozen=True)
class Tier:
    """A tier other than `default`: its entry and the files it holds for a stem `default` holds."""

    name: str
    entry: TierEntry
    files: Mapping[str, pathlib.Path]


@dataclasses.dataclass(frozen=True)
class TierCorpus:
    """`default` holds the stems by file; `tiers` follow the manifest's sequence."""

    root: pathlib.Path
    default: Mapping[str, pathlib.Path]
    tiers: Mapping[str, Tier]
    prefixes: Mapping[str, tuple[str, ...]]
    skipped: tuple[Skipped, ...]


def delivered_stems(entry: TierEntry, default_stems: Collection[str]) -> tuple[str, ...]:
    """The stems a tier delivers, sorted, among those `default` holds."""

    match entry:
        case EveryStem(exclude):
            return tuple(sorted(stem for stem in default_stems if stem not in exclude))
        case Listed(stems):
            return tuple(sorted(stem for stem in stems if stem in default_stems))


def _yaml_mapping(path: pathlib.Path) -> dict:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as failure:
        raise SourceError(f"{path} cannot be read as YAML: {failure}") from failure
    if not isinstance(document, dict):
        raise SourceError(f"{path} is not a mapping")
    return document


def _stems(value: object, where: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(stem, str) for stem in value):
        raise SourceError(f"{where} is not a list of stems")
    return tuple(value)


def _entry(tier: str, raw: object, manifest: pathlib.Path) -> TierEntry:
    if not isinstance(raw, dict):
        raise SourceError(f"tier {tier} in {manifest} is not a mapping")
    include = raw.get("include")
    if include == "*":
        return EveryStem(_stems(raw.get("exclude"), f"exclude of tier {tier} in {manifest}"))
    if isinstance(include, list):
        return Listed(_stems(include, f"include of tier {tier} in {manifest}"))
    raise SourceError(f"tier {tier} in {manifest} states no include of either form")


def _prefixes(root: pathlib.Path) -> dict[str, tuple[str, ...]]:
    path = root / _PREFIX_FILE
    if not path.is_file():
        return {}
    return {
        str(tier): _stems(patterns, f"{tier} in {path}")
        for tier, patterns in _yaml_mapping(path).items()
    }


def _files(directory: pathlib.Path) -> dict[str, pathlib.Path]:
    return {file.stem: file for file in sorted(directory.glob("*.md")) if file.is_file()}


def read_tier_corpus(root: pathlib.Path) -> TierCorpus:
    """Read the manifest's tiers, the prefix map, and each tier directory.

    A path-scoped file, and a tier file whose stem `default` does not hold, are set aside.
    """

    manifest = root / MANIFEST_FILE
    raw_tiers = _yaml_mapping(manifest).get("tiers")
    if not isinstance(raw_tiers, dict):
        raise SourceError(f"{manifest} has no `tiers` mapping")

    skipped: list[Skipped] = []
    default: dict[str, pathlib.Path] = {}
    for stem, file in _files(root / DEFAULT_TIER).items():
        if is_path_scoped(file):
            skipped.append(Skipped(f"{DEFAULT_TIER}/{file.name}", PATH_SCOPED))
        else:
            default[stem] = file

    tiers: dict[str, Tier] = {}
    for name, raw in raw_tiers.items():
        if name == DEFAULT_TIER:
            continue
        kept: dict[str, pathlib.Path] = {}
        for stem, file in _files(root / name).items():
            if is_path_scoped(file):
                skipped.append(Skipped(f"{name}/{file.name}", PATH_SCOPED))
            elif stem not in default:
                skipped.append(Skipped(f"{name}/{file.name}", NO_DEFAULT_FORM))
            else:
                kept[stem] = file
        tiers[str(name)] = Tier(str(name), _entry(str(name), raw, manifest), kept)

    return TierCorpus(root, default, tiers, _prefixes(root), tuple(skipped))

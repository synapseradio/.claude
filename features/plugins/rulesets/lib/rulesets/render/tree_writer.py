"""The render tree written to its folder, or compared with what the folder holds."""

from __future__ import annotations

import dataclasses
import pathlib
import shutil
from collections.abc import Mapping


@dataclasses.dataclass(frozen=True)
class Written:
    """The file names the folder holds after a write, sorted."""

    names: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class Fresh:
    """The folder holds exactly the tree."""


@dataclasses.dataclass(frozen=True)
class Stale:
    """The names whose bytes differ from the tree, that the tree lacks, or that the folder lacks, sorted."""

    differing: tuple[str, ...]


def write_tree(folder: pathlib.Path, tree: Mapping[str, str]) -> Written:
    """Replace everything in `folder` with the tree, a mapping from file name to text."""

    folder.mkdir(parents=True, exist_ok=True)
    for entry in folder.iterdir():
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    for name, text in tree.items():
        (folder / name).write_bytes(text.encode("utf-8"))
    return Written(tuple(sorted(tree)))


def check_tree(folder: pathlib.Path, tree: Mapping[str, str]) -> Stale | Fresh:
    """Compare the folder with the tree and write nothing."""

    held = {entry.name for entry in folder.iterdir()} if folder.is_dir() else set()
    differing = set(held ^ tree.keys())
    differing |= {
        name
        for name in held & tree.keys()
        if (folder / name).is_dir() or (folder / name).read_bytes() != tree[name].encode("utf-8")
    }
    return Stale(tuple(sorted(differing))) if differing else Fresh()

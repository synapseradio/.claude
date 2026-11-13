"""The repository the runner works in: its file lists, its changes, and the environment its children get."""

import os
import subprocess
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

# Git hands a hook run from a linked worktree GIT_DIR and GIT_INDEX_FILE. The
# runner's own git calls keep them so they read the hook's repository; a child
# would carry them into its own scratch repositories, so children lose them.
# https://git-scm.com/docs/githooks
GIT_LOCATORS = ("GIT_DIR", "GIT_INDEX_FILE", "GIT_PREFIX", "GIT_WORK_TREE", "GIT_COMMON_DIR")


class GitError(Exception):
    """A git query the runner depends on failed."""


def child_env() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key not in GIT_LOCATORS}


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = f"git {' '.join(args)}: {result.stderr.strip() or f'exit {result.returncode}'}"
        raise GitError(message)
    return result.stdout


def null_split(output: str) -> list[str]:
    return [item for item in output.split("\0") if item]


@dataclass(frozen=True)
class Changes:
    """Repository-relative paths a change touched, deleted ones included, and how the base was found."""

    paths: frozenset[str]
    note: str | None = None


@dataclass(frozen=True)
class Repo:
    root: Path

    @classmethod
    def at(cls, cwd: Path) -> Repo:
        return cls(Path(git(cwd, "rev-parse", "--show-toplevel").strip()))

    def git(self, *args: str) -> str:
        return git(self.root, *args)

    @cached_property
    def tracked(self) -> tuple[str, ...]:
        return tuple(null_split(self.git("ls-files", "-z", "--cached")))

    @cached_property
    def untracked(self) -> tuple[str, ...]:
        return tuple(null_split(self.git("ls-files", "-z", "--others", "--exclude-standard")))

    def exists(self, path: str) -> bool:
        return (self.root / path).is_file()

    def listed_under(self, path: str) -> list[str]:
        """Tracked and untracked, unignored files at or under a repository-relative path."""
        return null_split(
            self.git("ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", path)
        )

    def changed_since(self, base: str) -> Changes:
        """Files changed between the merge-base with `base` and the working tree, untracked ones included."""
        fork = self.git("merge-base", base, "HEAD").strip()
        changed = null_split(self.git("diff", "--name-only", "--no-renames", "-z", fork))
        return Changes(frozenset(changed) | frozenset(self.untracked))

    def unpushed(self) -> Changes:
        """Files the commits not yet on `@{push}` touch, falling back to the fork from origin/main."""
        try:
            target = self.git("rev-parse", "--verify", "--quiet", "@{push}").strip()
            note = None
        except GitError:
            target = self.git("rev-parse", "--verify", "--quiet", "origin/main").strip()
            note = (
                "--prepush: @{push} does not resolve; diffed from the merge-base with origin/main"
            )
        fork = self.git("merge-base", target, "HEAD").strip()
        changed = null_split(self.git("diff", "--name-only", "--no-renames", "-z", fork, "HEAD"))
        return Changes(frozenset(changed), note)

    def log_name(self) -> str:
        """`<repo>-<branch>`, the repository named by the directory holding its common git dir."""
        common = Path(self.git("rev-parse", "--path-format=absolute", "--git-common-dir").strip())
        repo = common.parent.name
        if repo.startswith("."):
            repo = f"-{repo[1:]}"
        branch = self.git("branch", "--show-current").strip() or "detached"
        return f"{repo}-{branch.replace('/', '-')}"

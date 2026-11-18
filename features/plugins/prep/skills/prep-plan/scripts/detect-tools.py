"""Report the tools a plan can lean on, as JSON on stdout.

    uv run --python 3.14 --no-project detect-tools.py [--repo PATH]

Looks at the commands on PATH and the files of the repository holding PATH
(default: the current directory). For each job a plan has, it lists what it
found, strongest first, as {"tool", "command", "evidence"}; "command" is null
where the configuration exists and the command is missing from PATH. An empty
list means the plan uses nothing for that job.

Reads only; contacts no network; prints a remote's host and never its URL.
Runs on Python 3.14 and later with the standard library alone.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HOOK_MANAGERS = (
    (
        "lefthook",
        (
            "lefthook.yml",
            "lefthook.yaml",
            ".lefthook.yml",
            ".lefthook.yaml",
            "lefthook.toml",
            "lefthook.json",
        ),
    ),
    ("husky", (".husky",)),
    ("pre-commit", (".pre-commit-config.yaml", ".pre-commit-config.yml")),
)
TASK_RUNNERS = (
    ("just", ("justfile", "Justfile", ".justfile")),
    ("make", ("Makefile", "makefile", "GNUmakefile")),
    ("task", ("Taskfile.yml", "Taskfile.yaml")),
    ("mise", ("mise.toml", ".mise.toml")),
)
LOCKFILES = ("bun.lock", "bun.lockb", "pnpm-lock.yaml", "yarn.lock", "package-lock.json")
TRACKERS = (
    ("gh", "github"),
    ("glab", "gitlab"),
    ("acli", None),
    ("jira", None),
    ("linear", None),
    ("ntn", None),
)


def run(args: list[str], cwd: Path) -> str | None:
    """Return a command's stdout, or None where it fails or is missing."""
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except OSError, subprocess.TimeoutExpired:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def finding(tool: str, command: str | None, evidence: list[str]) -> dict:
    return {"tool": tool, "command": command, "evidence": evidence}


def on_path(command: str) -> str | None:
    return command if shutil.which(command) else None


def first_present(directory: Path, names: tuple[str, ...]) -> str | None:
    present = {entry.name for entry in directory.iterdir()}
    return next((name for name in names if name in present), None)


def remote_host(root: Path) -> str | None:
    url = run(["git", "remote", "get-url", "origin"], root)
    if not url:
        return None
    match = re.match(r"^[a-z+]+://(?:[^@/]*@)?([^/:]+)", url) or re.match(
        r"^(?:[^@/]*@)?([^/:]+):", url
    )
    return match.group(1) if match else None


def repository(start: Path) -> dict | None:
    root = run(["git", "rev-parse", "--show-toplevel"], start)
    if not root:
        return None
    listing = run(["git", "worktree", "list", "--porcelain"], start) or ""
    primary, primary_branch = root, None
    for line in listing.splitlines():
        if line.startswith("worktree ") and primary_branch is None:
            primary = line[len("worktree ") :]
        elif line.startswith("branch refs/heads/"):
            primary_branch = line[len("branch refs/heads/") :]
            break
        elif not line:
            break
    origin_head = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], start)
    if origin_head:
        trunk, source = origin_head.split("/", 1)[1], "origin/HEAD"
    elif primary_branch:
        trunk, source = primary_branch, "the primary checkout's branch"
    else:
        trunk, source = None, None
    return {
        "root": root,
        "primary_checkout": primary,
        "trunk": trunk,
        "trunk_source": source,
        "remote_host": remote_host(Path(root)),
    }


def commit_hooks(root: Path) -> list[dict]:
    found = []
    for tool, names in HOOK_MANAGERS:
        name = first_present(root, names)
        if name:
            found.append(finding(tool, on_path(tool), [name]))
    evidence = []
    hooks_path = run(["git", "config", "--get", "core.hooksPath"], root)
    if hooks_path:
        evidence.append(f"core.hooksPath={hooks_path}")
    common = run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root)
    hooks = Path(common) / "hooks" if common else None
    if hooks and hooks.is_dir():
        evidence.extend(
            f"hooks/{hook.name}"
            for hook in sorted(hooks.iterdir())
            if hook.is_file() and not hook.name.endswith(".sample") and os.access(hook, os.X_OK)
        )
    if evidence and not found:
        found.append(finding("git hooks", None, evidence))
    return found


def task_runner(directory: Path) -> list[dict]:
    found = []
    for tool, names in TASK_RUNNERS:
        name = first_present(directory, names)
        if name:
            found.append(finding(tool, on_path(tool), [name]))
    package = directory / "package.json"
    if package.is_file():
        try:
            scripts = json.loads(package.read_text(encoding="utf-8")).get("scripts")
        except OSError, ValueError, AttributeError:
            scripts = None
        if scripts:
            lockfile = first_present(directory, LOCKFILES)
            found.append(
                finding(
                    "package scripts", None, ["package.json"] + ([lockfile] if lockfile else [])
                )
            )
    return found


def tracker(host: str | None) -> list[dict]:
    found = []
    for command, host_word in TRACKERS:
        if not on_path(command):
            continue
        evidence = [f"{command} on PATH"]
        if host and host_word and host_word in host:
            evidence.append(f"origin is on {host}")
        found.append(finding(command, command, evidence))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").partition("\n")[0])
    parser.add_argument("--repo", default=".", help="a path inside the repository to inspect")
    start = Path(parser.parse_args().repo).resolve()
    repo = repository(start)
    root = Path(repo["root"]) if repo else start
    report = {
        "repository": repo,
        "jobs": {
            "commit_hooks": commit_hooks(root) if repo else [],
            "task_runner": task_runner(root),
            "tracker": tracker(repo["remote_host"] if repo else None),
        },
    }
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

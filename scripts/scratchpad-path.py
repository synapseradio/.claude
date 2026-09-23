#!/usr/bin/env python3
"""Print the scratchpad path for a working file, timestamped from the clock.

    scratchpad-path.py <slug>

The path is `$HOME/.scratchpad/$repo/$branch/$slug__$hh-$mm$AMPM_$DD-$MM-$YYYY.md`,
with the branch directory dropped where no branch is checked out. `$repo` is
the basename of the directory holding the common git dir, so every worktree of
one repository shares a tree. The directory is created; the file is not, so
the caller's first write sets it. SCRATCHPAD_PATH_NOW, an ISO 8601 datetime,
stands in for the clock.
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def git(*args):
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def main():
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        sys.exit("usage: scratchpad-path.py <slug>")
    slug = sys.argv[1].strip()

    common_dir = git("rev-parse", "--path-format=absolute", "--git-common-dir")
    if common_dir is None:
        sys.exit("not inside a git repository; use the path the harness names")
    directory = Path.home() / ".scratchpad" / Path(common_dir).parent.name
    branch = git("branch", "--show-current")
    if branch:
        directory /= branch

    override = os.environ.get("SCRATCHPAD_PATH_NOW")
    now = datetime.fromisoformat(override) if override else datetime.now()
    directory.mkdir(parents=True, exist_ok=True)
    print(directory / f"{slug}__{now:%I-%M%p_%d-%m-%Y}.md")


if __name__ == "__main__":
    main()

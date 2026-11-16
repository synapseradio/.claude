"""Check the shell files named on the command line, apply ShellCheck's auto-fixes where it finds anything, and report every finding left.

`shellcheck -f diff` prints its fixes as a unified diff for `git apply`:
https://github.com/koalaman/shellcheck/blob/v0.11.0/shellcheck.1.md#L171-L173
The exit status is that of the last plain shellcheck run, and 3 when shellcheck is not on PATH.
"""

import shutil
import subprocess
import sys

MISSING = 3


def main(paths: list[str]) -> int:
    if shutil.which("shellcheck") is None:
        print("verify: shellcheck is not on PATH; run just tools to install it", file=sys.stderr)
        return MISSING
    if subprocess.run(["shellcheck", *paths], capture_output=True).returncode == 0:
        return 0
    fixes = subprocess.run(["shellcheck", "--format=diff", *paths], capture_output=True, text=True)
    if fixes.stdout:
        subprocess.run(["git", "apply", "-"], input=fixes.stdout, text=True, check=True)
    return subprocess.run(["shellcheck", *paths]).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

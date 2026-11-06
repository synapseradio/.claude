## shell-scripts

For every shell script and every shell startup file you write or review, optimize for a script that runs what its writer named and reads like every other script here.

- the guide: `~/.claude/references/bash-style-guide.md`, a distillation of Google's at https://google.github.io/styleguide/shellguide.html, the one source of every script's conventions

Read the guide in full before writing or reviewing bash, and follow it. Write every script in bash, opening each executable on `#!/bin/bash`. Quote every value the shell would otherwise re-expand. Hold every list in an array. Check every step's status, in the form the guide gives.
A script needs a data structure beyond a string, an array, or an associative array, or control flow beyond a branch, a loop, and a function call ? write it in another language.

Write every script to run on the oldest bash its target machines resolve, macOS /bin/bash 3.2 for one, a script opening on `#!/usr/bin/env bash` included.
A script runs only under a newer bash, in CI alone for one ? keep old-bash guards out of it and its tests.

In a file zsh sources, probe for a function with `declare -f <name>`, with `declare -F` and `typeset -F` kept out. Test a file both shells source under `zsh -c` and under `bash -c`.

The file is a script ? name it in kebab-case : take the name the guide gives.
Resolve an ambiguous choice toward the convention the surrounding scripts hold, and treat consistency as no ground for keeping an outdated convention.

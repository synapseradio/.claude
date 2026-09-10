---
paths:
  - "**/*.{sh,bash,zsh,ksh,fish,bats}"
  - "**/{.bashrc,.bash_profile,.zshrc,.profile,.zshenv,.bash_aliases}"
---

<!-- rule: shell-scripts -->

## shell-scripts

For every shell script and every shell startup file you write or review, optimize for a script that runs what its writer named and reads like every other script here.

Read `~/.claude/references/bash-style-guide.md` in full before writing or reviewing bash. Follow it. Hold the guide as the one source of every script's conventions. Treat the guide as a distillation of Google's, published at https://google.github.io/styleguide/shellguide.html. Write every script in bash. Open each executable on `#!/bin/bash`. Quote every value the shell would otherwise re-expand. Hold every list in an array. Check every step's status, in the form the guide gives. Where a script needs a data structure beyond a string, an array, or an associative array, or control flow beyond a branch, a loop, and a function call, write it in another language.

Where the file is a script, name it in kebab-case. Otherwise, take the name the guide gives. Resolve an ambiguous choice toward the convention the surrounding scripts hold. Never keep an outdated convention on consistency's account.

---
paths:
  - "**/*.{sh,bash,zsh,ksh,fish,bats}"
  - "**/{.bashrc,.bash_profile,.zshrc,.profile,.zshenv,.bash_aliases}"
---

<rule name="shell-scripts">

  <applies_when>
    You are writing or reviewing a shell script, or a shell startup file.
  </applies_when>

  <optimize_for>
    a script that runs what its writer named and reads like every other script here.
    <why_it_matters>
      A shell script runs whatever its text expands to. The shell re-expands text by default, so a value takes quotes and a list takes an array. A command reports failure in a status nobody must read, so a failed step runs on unchecked. Past 100 lines, or control flow beyond the straightforward, another language repays it. One guide settles every script's conventions. Consistency resolves an ambiguous choice and never justifies an outdated one, so kebab-case script names here stand against the guide's `make_template, never make-template`. The guide distills Google's own, published at https://google.github.io/styleguide/shellguide.html.
    </why_it_matters>
  </optimize_for>

  <do>
    Read `~/.claude/references/bash-style-guide.md` in full before writing or reviewing bash, then follow it. Write every script in bash. Open each executable on `#!/bin/bash`.
  </do>

  <decide>
    Where the file is a script, name it in kebab-case. Otherwise, take the name the guide gives.
  </decide>

</rule>

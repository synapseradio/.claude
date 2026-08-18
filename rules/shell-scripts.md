---
paths:
  - "**/*.{sh,bash,zsh,ksh,fish,bats}"
  - "**/{.bashrc,.bash_profile,.zshrc,.profile,.zshenv,.bash_aliases}"
---

ShellScripts {
  AppliesWhen { writing or reviewing shell scripts }

  constraint GoogleStyleGuide {
    read `~/.claude/references/bash-style-guide.md` in full before writing
      or reviewing bash, and follow it
    name script files in kebab-case, overriding the guide's underscore
      default
  }
}

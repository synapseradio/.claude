---
paths:
  - "**/*.sh"
  - "**/*.bash"
  - "**/*.zsh"
  - "**/*.ksh"
  - "**/*.fish"
  - "**/*.bats"
  - "**/.bashrc"
  - "**/.bash_profile"
  - "**/.zshrc"
  - "**/.profile"
  - "**/.zshenv"
  - "**/.bash_aliases"
---

# Shell Scripts

Shell work follows the Google Shell Style Guide, read in full before any bash
gets written or reviewed. One repository convention overrides the guide:
filenames stay kebab-case.

ShellScripts {
  Applies { writing or reviewing shell scripts }

  follow the Google Shell Style Guide {
    read(../references/bash-style-guide.md) in full before writing
      or reviewing bash
    // bash fails quietly where other languages throw
  }

  RepoConvention {
    kebab-case script filenames take precedence over the guide's
      underscore default
  }
}

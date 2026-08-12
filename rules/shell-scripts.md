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

```sudolang
ShellScripts {
  Applies { writing or reviewing shell scripts }

  follow the Google Shell Style Guide {
    read(../references/bash-style-guide.md) in full before writing
      or reviewing bash
    // the reference stays a reference deliberately: heavy on context,
    // far to the side of other tasks. bash fails quietly where other
    // languages throw.
  }

  RepoConvention {
    kebab-case script filenames take precedence over the guide's
      underscore default
  }
}
```

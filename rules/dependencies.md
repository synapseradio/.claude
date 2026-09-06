---
paths:
  - "**/{package.json,package-lock.json,npm-shrinkwrap.json,yarn.lock,pnpm-lock.yaml,pnpm-workspace.yaml,bun.lock,bun.lockb,.npmrc}"
  - "**/{requirements*.txt,pyproject.toml,poetry.lock,uv.lock,Pipfile,Pipfile.lock,setup.py,setup.cfg,environment.yml,environment.yaml,conda.yaml}"
  - "**/{Cargo.toml,Cargo.lock,go.mod,go.sum,go.work,Gemfile,Gemfile.lock,*.gemspec}"
  - "**/{build.gradle,build.gradle.kts,settings.gradle,settings.gradle.kts,pom.xml,gradle.properties}"
  - "**/{composer.json,composer.lock,Package.swift,Package.resolved,Podfile,Podfile.lock,Cartfile,Cartfile.resolved}"
  - "**/{*.csproj,*.fsproj,*.vbproj,packages.config,paket.dependencies,paket.lock}"
  - "**/{mix.exs,mix.lock,pubspec.yaml,pubspec.lock,stack.yaml,cabal.project,*.cabal,elm.json}"
---

# Dependencies

This applies when adding, removing, or updating any package dependency.

We value a dependency change the resolver made and the lockfile records. A hand-edited lockfile or a version pinned on the command line takes the choice from the resolver and leaves the tree in a state the manager never produced. The repo's own dependency docs outrank this rule wherever the two conflict.

```sudolang
manager = lockfile => match (lockfile) {
  case bun.lock or bun.lockb => bun
  case pnpm-lock.yaml => pnpm
  case yarn.lock => yarn
  case package-lock.json => npm
  case Cargo.lock => cargo
  default => the tool that writes that lockfile
}
several JavaScript lockfiles present => bun, then pnpm, then yarn, then npm

fn changeDependency() {
  the repo carries its own dependency docs => read them first, follow them over this rule
  detect the manager
  run the manager's own add or remove command, such as `bun add <name>`,
    `bun add -D <name>`, `pnpm add <name>`, or `npm install <name>`
  install and audit
  a version constraint required => write the version the lockfile resolved, in config:
    a workspace catalog, an overrides block, or the package's own package.json edited as text
}

require never edit a lockfile by hand
require never pin a version on the CLI: no <name>@<version>, no flag that hand-picks a version
```

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

When the repo carries its own dependency docs, read them before touching any dependency, and follow them wherever they conflict with this rule.

The manager is the tool that writes the lockfile present in the tree: bun for bun.lock or bun.lockb, pnpm for pnpm-lock.yaml, yarn for yarn.lock, npm for package-lock.json, cargo for Cargo.lock, and otherwise the tool that writes that lockfile. When several JavaScript lockfiles are present, prefer bun, then pnpm, then yarn, then npm.

The resolver picks versions. Never edit a lockfile by hand. Never pin a version on the CLI: no `<name>@<version>`, no flag that hand-picks a version. When a version constraint is genuinely required, write it in config: the lockfile's resolved version, a workspace catalog, an `overrides` block, or the package's own `package.json` edited as text.

To change a dependency, detect the manager, run the manager's own add or remove command, such as `bun add <name>`, `bun add -D <name>`, `pnpm add <name>`, or `npm install <name>`, then install and audit.

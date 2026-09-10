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

<!-- rule: dependencies -->

## dependencies

When you are adding, removing, or updating a package dependency, optimize for a dependency change the resolver made and the lockfile records.

A hand-edited lockfile or a version pinned on the command line takes the choice from the resolver and leaves the tree in a state the manager never produced. The repo's own dependency docs outrank this rule wherever the two conflict.

Read the manager off the lockfile: bun for bun.lock or bun.lockb, pnpm for pnpm-lock.yaml, yarn for yarn.lock, npm for package-lock.json, cargo for Cargo.lock, and otherwise the tool that writes that lockfile. Where several JavaScript lockfiles are present, take bun, then pnpm, then yarn, then npm.

Where the repo carries its own dependency docs, read them first and follow them over this rule. Detect the manager. Run the manager's own add or remove command, `bun add <name>` for one. Install and audit. Where a version constraint is required, write the version the lockfile resolved in config: a workspace catalog, an overrides block, or the package's own package.json edited as text.

Never edit a lockfile by hand. Never pin a version on the CLI, whether as `<name>@<version>` or through a flag that hand-picks a version.

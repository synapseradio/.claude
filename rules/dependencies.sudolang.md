---
paths:
  - "**/package.json"
  - "**/package-lock.json"
  - "**/npm-shrinkwrap.json"
  - "**/yarn.lock"
  - "**/pnpm-lock.yaml"
  - "**/pnpm-workspace.yaml"
  - "**/bun.lock"
  - "**/bun.lockb"
  - "**/.npmrc"
  - "**/requirements*.txt"
  - "**/pyproject.toml"
  - "**/poetry.lock"
  - "**/uv.lock"
  - "**/Pipfile"
  - "**/Pipfile.lock"
  - "**/setup.py"
  - "**/setup.cfg"
  - "**/environment.yml"
  - "**/environment.yaml"
  - "**/conda.yaml"
  - "**/Cargo.toml"
  - "**/Cargo.lock"
  - "**/go.mod"
  - "**/go.sum"
  - "**/go.work"
  - "**/Gemfile"
  - "**/Gemfile.lock"
  - "**/*.gemspec"
  - "**/build.gradle"
  - "**/build.gradle.kts"
  - "**/settings.gradle"
  - "**/settings.gradle.kts"
  - "**/pom.xml"
  - "**/gradle.properties"
  - "**/composer.json"
  - "**/composer.lock"
  - "**/Package.swift"
  - "**/Package.resolved"
  - "**/Podfile"
  - "**/Podfile.lock"
  - "**/Cartfile"
  - "**/Cartfile.resolved"
  - "**/*.csproj"
  - "**/*.fsproj"
  - "**/*.vbproj"
  - "**/packages.config"
  - "**/paket.dependencies"
  - "**/paket.lock"
  - "**/mix.exs"
  - "**/mix.lock"
  - "**/pubspec.yaml"
  - "**/pubspec.lock"
  - "**/stack.yaml"
  - "**/cabal.project"
  - "**/*.cabal"
  - "**/elm.json"
---

# Dependencies

A package manager's resolver decides versions, so adding, removing, and
updating dependencies runs through its CLI rather than through hand edits to
a manifest or a lockfile. A repository carrying its own dependency docs
overrides Dependencies wherever the two conflict.

Dependencies {
  Applies { adding, removing, or updating any package dependency }

  GitCommit.DeterminismWins governs dependency work too: where deterministic
    repo tooling settles the question, the tooling settles it
    via(GitCommit.DeterminismWins)

  TheRepoIsTheSOP {
    (the repo carries its own dependency-management docs) =>
      read them before touching deps, and on conflict they override
      Dependencies
  }

  UseTheTool {
    fn detectManager() {
      the lockfile names the manager, never your preference: read bun.lock as
        bun, pnpm-lock.yaml as pnpm, Cargo.lock as cargo, and every other
        lockfile as the manager that writes it
      (several JavaScript lockfiles present at once) =>
        prefer bun, then pnpm, then yarn, then npm
    }
    run   { `bun add <name>` | `bun add -D <name>`
          | `npm install <name>` | `pnpm add <name>` }
    never { `bun add <name>@<version>`
          | any flag or suffix that hand-picks a version on the CLI }
    require lockfiles are never edited by hand, since the resolver writes each
      one to record the versions it settled on
    fn afterChange() { install |> audit }
  }

  Constraining {
    (a version constraint is genuinely required) => it goes in a config file:
      the lockfile's resolved version | a workspace catalog | an `overrides`
      block | the package's own `package.json` edited as text
  }
}

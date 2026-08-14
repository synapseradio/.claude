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
    // the package manager is a tool we've been given: its resolver decides
    // versions deterministically, and hand edits bypass it

  TheRepoIsTheSOP {
    (the repo carries its own dependency-management docs) =>
      read them before touching deps, and on conflict they override
      Dependencies
    // conventions like Bun workspace catalogs, pnpm patches, or npm overrides
    // change where a version range belongs. skipping the docs usually means
    // putting the range in the wrong place and redoing the work
  }

  UseTheTool {
    fn detectManager() {
      the lockfile names the manager, never your preference
      // bun.lock means bun, pnpm-lock.yaml means pnpm, Cargo.lock means
      // cargo, and so on
      (several JavaScript lockfiles present at once) =>
        prefer bun, then pnpm, then yarn, then npm
    }
    run   { `bun add <name>` | `bun add -D <name>`
          | `npm install <name>` | `pnpm add <name>` }
    never { `bun add <name>@<version>`
          | any flag or suffix that hand-picks a version on the CLI }
    require lockfiles are never edited by hand
      // the lockfile records what the resolver decided. editing it asserts
      // a resolution nobody ran
    fn afterChange() { install |> audit }  // let the tool verify
  }

  Constraining {
    // the CLI adds the dependency. a file constrains it
    (a version constraint is genuinely required) => it goes in a config file:
      the lockfile's resolved version | a workspace catalog | an `overrides`
      block | the package's own `package.json` edited as text
  }
}

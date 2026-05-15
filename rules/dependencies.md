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

When adding, removing, or updating any package dependency.

Never pin a version on the command line. Run the bare package name and let the package manager resolve the current release.

- `bun add <name>` / `bun add -D <name>` — yes
- `npm install <name>` / `pnpm add <name>` — yes
- `bun add <name>@<version>` — no
- Any flag or suffix that hand-picks a version on the CLI — no

If a version constraint is genuinely required, its home is a config file: the lockfile's resolved version, a workspace catalog, an `overrides` block, or the package's own `package.json` edited as text. The CLI is for adding the dependency; the file is for constraining it.

Before touching deps in a repo with its own dependency-management docs, read those docs first. Conventions like Bun workspace catalogs, pnpm patches, or npm overrides change where a version range belongs. The default cost of skipping the docs is putting the range in the wrong place and having to redo the work.

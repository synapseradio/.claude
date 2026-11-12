#!/usr/bin/env bats
#
# Tests for deny-hook-covered-check.sh, the PreToolUse Bash guard that denies
# a manual run of a check the current repository's git hooks already run.
#
# Every case builds its own repository under the test's temporary directory,
# with HOME, the XDG directories, and the git configuration pointed there
# too, so no case reads the machine's repositories or settings. Hook
# configuration is written per case; the guard reads it from the repository
# that holds the session's working directory.

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  export HOOK="${BATS_TEST_DIRNAME}/../hooks/deny-hook-covered-check.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"

  export HOME="${BATS_TEST_TMPDIR}/home"
  export XDG_CONFIG_HOME="${HOME}/.config"
  export XDG_DATA_HOME="${HOME}/.local/share"
  export XDG_CACHE_HOME="${HOME}/.cache"
  export XDG_STATE_HOME="${HOME}/.local/state"
  export GIT_CONFIG_GLOBAL="${HOME}/gitconfig"
  export GIT_CONFIG_NOSYSTEM=1
  unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
  mkdir -p "${HOME}"
  : >"${GIT_CONFIG_GLOBAL}"

  REPO="${BATS_TEST_TMPDIR}/repo"
  mkdir -p "${REPO}/sub"
  git -C "${REPO}" init -q
}

#######################################
# Write lefthook.yml in the test repository from stdin.
#######################################
write_lefthook() {
  cat >"${REPO}/lefthook.yml"
}

#######################################
# Write a lefthook.yml whose pre-commit hook runs one command.
# Arguments:
#   $1 - the run: value, as written in the YAML.
#######################################
lefthook_runs() {
  printf 'pre-commit:\n  commands:\n    check:\n      run: %s\n' "$1" |
    write_lefthook
}

@test "a manual run of a package script a hook runs is denied" {
  lefthook_runs 'bun run lint'
  assert_denies_in "${REPO}" 'bun run lint'
}

@test "a package script a hook runs is denied without the run word" {
  lefthook_runs 'bun run lint'
  assert_denies_in "${REPO}" 'bun lint'
}

@test "a package script is denied behind other commands" {
  lefthook_runs 'bun run lint'
  assert_denies_in "${REPO}" 'echo start && bun run lint | tail -5'
}

@test "bun run build stays allowed when a hook runs bun run build:check" {
  lefthook_runs 'bun run build:check'
  assert_silent_in "${REPO}" 'bun run build'
}

@test "bun run lint:fix stays allowed when a hook runs bun run lint" {
  lefthook_runs 'bun run lint'
  assert_silent_in "${REPO}" 'bun run lint:fix'
}

@test "a package script scoped to a workspace is a different check" {
  lefthook_runs 'bun run lint'
  assert_silent_in "${REPO}" 'bun run --filter @app/web lint'
}

@test "a different package manager running the same script name stays allowed" {
  lefthook_runs 'bun run lint'
  assert_silent_in "${REPO}" 'npm run lint'
}

@test "package manager commands that run no script stay allowed" {
  lefthook_runs 'bun run lint'
  assert_silent_in "${REPO}" 'bun install'
  assert_silent_in "${REPO}" 'bun add left-pad'
  assert_silent_in "${REPO}" 'bun x cowsay hi'
}

@test "a tool and subcommand a hook runs is denied with other arguments" {
  lefthook_runs 'biome check --staged {staged_files}'
  assert_denies_in "${REPO}" 'biome check src'
}

@test "a tool run through a package runner is denied" {
  lefthook_runs 'biome check --staged {staged_files}'
  assert_denies_in "${REPO}" 'bunx biome check src'
  assert_denies_in "${REPO}" 'npx --yes biome check'
  assert_denies_in "${REPO}" './node_modules/.bin/biome check'
}

@test "another subcommand of the same tool stays allowed" {
  lefthook_runs 'biome check --staged {staged_files}'
  assert_silent_in "${REPO}" 'biome lint src'
  assert_silent_in "${REPO}" 'biome format src'
}

@test "a hook run through bunx covers the tool itself" {
  lefthook_runs 'bunx markdownlint-cli2 --fix {staged_files}'
  assert_denies_in "${REPO}" 'markdownlint-cli2 README.md'
}

@test "a tool with no subcommand needs the flag the hook passes" {
  lefthook_runs 'tsc --noEmit'
  assert_denies_in "${REPO}" 'tsc --noEmit -p tsconfig.json'
  assert_silent_in "${REPO}" 'tsc -p tsconfig.json'
  assert_silent_in "${REPO}" 'tsc --version'
}

@test "a flag that only changes how a tool runs does not set the check apart" {
  lefthook_runs 'eslint --fix {staged_files}'
  assert_denies_in "${REPO}" 'eslint src'
}

@test "a bare tool the hook passes files to is denied" {
  lefthook_runs 'shellcheck {staged_files}'
  assert_denies_in "${REPO}" 'shellcheck scripts/build.sh'
}

@test "each command of a chained hook run is covered" {
  lefthook_runs 'ruff check --fix {staged_files} && ruff format {staged_files}'
  assert_denies_in "${REPO}" 'ruff check src'
  assert_denies_in "${REPO}" 'ruff format src'
  assert_silent_in "${REPO}" 'ruff rule E501'
}

@test "a tool started through uv run is matched as the tool" {
  lefthook_runs 'uv run ruff check {staged_files}'
  assert_denies_in "${REPO}" 'ruff check .'
  assert_denies_in "${REPO}" 'uv run ruff check .'
  assert_silent_in "${REPO}" 'uv run pytest'
}

@test "a nested subcommand a hook runs is denied with other arguments" {
  lefthook_runs 'claude plugin validate .'
  assert_denies_in "${REPO}" 'claude plugin validate some/plugin'
}

@test "claude plugin test stays allowed when a hook runs claude plugin validate" {
  lefthook_runs 'claude plugin validate .'
  assert_silent_in "${REPO}" 'claude plugin test some/plugin'
}

@test "another nested subcommand of the same group stays allowed" {
  lefthook_runs 'claude plugin validate .'
  assert_silent_in "${REPO}" 'claude plugin list'
  assert_silent_in "${REPO}" 'claude plugin'
  assert_silent_in "${REPO}" 'claude mcp validate'
}

@test "helm lint is denied with a chart name that no hook passed" {
  lefthook_runs 'helm lint'
  assert_denies_in "${REPO}" 'helm lint mychart'
  assert_denies_in "${REPO}" 'helm lint charts/a'
}

@test "terraform validate is denied with a directory name that no hook passed" {
  lefthook_runs 'terraform validate'
  assert_denies_in "${REPO}" 'terraform validate modules'
}

@test "docker build is denied with a context name that no hook passed" {
  lefthook_runs 'docker build .'
  assert_denies_in "${REPO}" 'docker build web'
}

@test "claude plugin test stays allowed with no arguments when a hook runs claude plugin validate" {
  lefthook_runs 'claude plugin validate'
  assert_silent_in "${REPO}" 'claude plugin test'
}

@test "a make target a hook runs is denied and other targets stay allowed" {
  lefthook_runs 'make lint'
  assert_denies_in "${REPO}" 'make lint'
  assert_silent_in "${REPO}" 'make build'
  assert_silent_in "${REPO}" 'make'
}

@test "a hook script file that is run by name is denied" {
  lefthook_runs './scripts/check-docs.sh'
  assert_denies_in "${REPO}" 'scripts/check-docs.sh'
}

@test "test runs stay allowed when a hook runs them" {
  lefthook_runs 'bun run test'
  assert_silent_in "${REPO}" 'bun run test'
  assert_silent_in "${REPO}" 'bun test'

  lefthook_runs 'bun run test:scripts'
  assert_silent_in "${REPO}" 'bun run test:scripts'

  lefthook_runs 'vitest run'
  assert_silent_in "${REPO}" 'vitest run src'

  lefthook_runs 'bats tests'
  assert_silent_in "${REPO}" 'bats tests/a.bats'

  lefthook_runs 'cargo test'
  assert_silent_in "${REPO}" 'cargo test'

  lefthook_runs 'npm test'
  assert_silent_in "${REPO}" 'npm test'
}

@test "generic programs a hook runs are never denied" {
  lefthook_runs 'git diff --cached --quiet'
  assert_silent_in "${REPO}" 'git diff --cached --quiet'
  assert_silent_in "${REPO}" 'git diff'

  lefthook_runs 'node scripts/check.js'
  assert_silent_in "${REPO}" 'node scripts/other.js'

  lefthook_runs 'python3.15 scripts/check.py --check'
  assert_silent_in "${REPO}" 'python3.15 scripts/other.py'

  lefthook_runs 'bash scripts/check.sh'
  assert_silent_in "${REPO}" 'bash scripts/other.sh'

  lefthook_runs 'echo checking'
  assert_silent_in "${REPO}" 'echo hello'
}

@test "a command that only mentions the check in a string stays allowed" {
  lefthook_runs 'bun run lint'
  assert_silent_in "${REPO}" 'echo "bun run lint"'
  assert_silent_in "${REPO}" 'grep -n "bun run lint" README.md'
  assert_silent_in "${REPO}" 'git commit -m "docs: say bun run lint runs on commit"'
}

@test "a block scalar run is read line by line" {
  write_lefthook <<'EOF'
pre-push:
  jobs:
    - name: sync
      run: |
        set -e
        python3.15 scripts/sync.py
        shellcheck {push_files} || {
          echo "shellcheck failed"
          exit 1
        }
EOF
  assert_denies_in "${REPO}" 'shellcheck scripts/build.sh'
  assert_silent_in "${REPO}" 'python3.15 scripts/sync.py'
  assert_silent_in "${REPO}" 'echo "shellcheck failed"'
}

@test "a run inside a group of jobs is read" {
  write_lefthook <<'EOF'
pre-commit:
  jobs:
    - name: lint
      group:
        parallel: true
        jobs:
          - name: shfmt
            glob: "*.{sh,bash}"
            run: shfmt -i 2 -w {staged_files}
EOF
  assert_denies_in "${REPO}" 'shfmt -i 2 -d scripts/build.sh'
}

@test "quoted and commented run values are read as the command" {
  write_lefthook <<'EOF'
pre-commit:
  commands:
    a:
      run: "bun run lint"
    b:
      run: 'biome check {staged_files}'
    c:
      run: ruff check {staged_files} # lint python
    d:
      # run: bun run never-run
      glob: "*.md"
EOF
  assert_denies_in "${REPO}" 'bun run lint'
  assert_denies_in "${REPO}" 'biome check src'
  assert_denies_in "${REPO}" 'ruff check src'
  assert_silent_in "${REPO}" 'bun run never-run'
}

@test "a pre-push hook is read" {
  printf 'pre-push:\n  commands:\n    types:\n      run: tsc --noEmit\n' |
    write_lefthook
  assert_denies_in "${REPO}" 'tsc --noEmit'
}

@test "hooks that run on neither commit nor push are not read" {
  write_lefthook <<'EOF'
post-checkout:
  commands:
    deps:
      run: bun run codegen
commit-msg:
  commands:
    msg:
      run: commitlint --edit {1}
EOF
  assert_silent_in "${REPO}" 'bun run codegen'
  assert_silent_in "${REPO}" 'commitlint --edit msg.txt'
}

@test "every lefthook file name is read" {
  local name
  for name in lefthook.yaml .lefthook.yml .lefthook.yaml lefthook-local.yml; do
    printf 'pre-commit:\n  commands:\n    x:\n      run: bun run lint\n' \
      >"${REPO}/${name}"
    assert_denies_in "${REPO}" 'bun run lint'
    mv "${REPO}/${name}" "${BATS_TEST_TMPDIR}/moved-${name}"
    assert_silent_in "${REPO}" 'bun run lint'
  done
}

@test "a husky pre-commit script is read" {
  mkdir -p "${REPO}/.husky"
  cat >"${REPO}/.husky/pre-commit" <<'EOF'
. "$(dirname -- "$0")/_/husky.sh"
# lint what is staged
bun run lint-staged
EOF
  assert_denies_in "${REPO}" 'bun run lint-staged'
  assert_silent_in "${REPO}" 'bun run lint'
}

@test "a husky pre-push script is read" {
  mkdir -p "${REPO}/.husky"
  printf 'tsc --noEmit && bun run lint\n' >"${REPO}/.husky/pre-push"
  assert_denies_in "${REPO}" 'tsc --noEmit'
  assert_denies_in "${REPO}" 'bun run lint'
}

@test "a pre-commit configuration entry is read" {
  cat >"${REPO}/.pre-commit-config.yaml" <<'EOF'
repos:
  - repo: https://example.com/hooks
    hooks:
      - id: end-of-file-fixer
  - repo: local
    hooks:
      - id: shellcheck
        name: shellcheck
        entry: shellcheck
        language: system
      - id: slow
        name: slow
        entry: 'bun run slow-audit'
        language: system
        stages: [manual]
EOF
  assert_denies_in "${REPO}" 'shellcheck scripts/build.sh'
  assert_silent_in "${REPO}" 'bun run slow-audit'
  assert_silent_in "${REPO}" 'end-of-file-fixer README.md'
}

@test "an executable hook in the git hooks directory is read" {
  printf '#!/bin/sh\nruff check .\n' >"${REPO}/.git/hooks/pre-commit"
  chmod +x "${REPO}/.git/hooks/pre-commit"
  assert_denies_in "${REPO}" 'ruff check src'
}

@test "a hook in the git hooks directory that is not executable is not read" {
  printf '#!/bin/sh\nruff check .\n' >"${REPO}/.git/hooks/pre-commit"
  assert_silent_in "${REPO}" 'ruff check src'
}

@test "a sample hook is not read" {
  printf '#!/bin/sh\nruff check .\n' >"${REPO}/.git/hooks/pre-commit.sample"
  chmod +x "${REPO}/.git/hooks/pre-commit.sample"
  assert_silent_in "${REPO}" 'ruff check src'
}

@test "the hooks directory named by core.hooksPath is read" {
  mkdir -p "${REPO}/githooks"
  printf '#!/bin/sh\nruff check .\n' >"${REPO}/githooks/pre-push"
  chmod +x "${REPO}/githooks/pre-push"
  assert_silent_in "${REPO}" 'ruff check src'
  git -C "${REPO}" config core.hooksPath githooks
  assert_denies_in "${REPO}" 'ruff check src'
}

@test "a shim that calls the hook runner does not make the runner a refused command" {
  printf '#!/bin/sh\nexec lefthook run pre-commit "$@"\n' \
    >"${REPO}/.git/hooks/pre-commit"
  chmod +x "${REPO}/.git/hooks/pre-commit"
  assert_silent_in "${REPO}" 'lefthook run pre-commit'
}

@test "a lefthook shim and a command that redirects stderr with 2>&1 stay allowed" {
  cat >"${REPO}/.git/hooks/pre-commit" <<'EOF'
#!/bin/sh

if [ "$LEFTHOOK_VERBOSE" = "1" -o "$LEFTHOOK_VERBOSE" = "true" ]; then
  set -x
fi

if [ "$LEFTHOOK" = "0" ]; then
  exit 0
fi

call_lefthook()
{
  if test -n "$LEFTHOOK_BIN"
  then
    "$LEFTHOOK_BIN" "$@"
  elif lefthook -h >/dev/null 2>&1
  then
    lefthook "$@"
  fi
}

call_lefthook run "pre-commit" "$@"
EOF
  chmod +x "${REPO}/.git/hooks/pre-commit"
  assert_silent_in "${REPO}" 'python3.15 -m pytest some/tests -q > /tmp/out.txt 2>&1'
}

@test "a command that redirects both streams with &> stays allowed" {
  lefthook_runs 'bun run lint'
  assert_silent_in "${REPO}" 'python3.15 -m pytest some/tests -q &> /tmp/out.txt'
}

@test "a check a hook runs is denied when its output is redirected" {
  lefthook_runs 'ruff check .'
  assert_denies_in "${REPO}" 'ruff check . > /tmp/out.txt 2>&1'
  assert_denies_in "${REPO}" 'ruff check . &> /tmp/out.txt'
  assert_denies_in "${REPO}" 'ruff check . 2>&1 | tail -5'
}

@test "a refusal names the file that runs the check and the command" {
  lefthook_runs 'bun run lint'
  run_bash_hook_in "${REPO}" 'bun run lint'
  assert_decision 'deny' 'bun run lint'
  local reason
  reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")"
  [[ "${reason}" == *'git hooks run this check on commit or push'* ]]
  [[ "${reason}" == *'Commit, and let the hook run it'* ]]
  [[ "${reason}" == *'lefthook.yml runs: bun run lint'* ]]
}

@test "a session in a subdirectory of the repository is covered" {
  lefthook_runs 'bun run lint'
  assert_denies_in "${REPO}/sub" 'bun run lint'
}

@test "a cd into the repository moves the check to its hooks" {
  lefthook_runs 'bun run lint'
  mkdir -p "${BATS_TEST_TMPDIR}/elsewhere"
  assert_denies_in "${BATS_TEST_TMPDIR}/elsewhere" "cd ${REPO} && bun run lint"
}

@test "a relative cd into the repository moves the check to its hooks" {
  lefthook_runs 'bun run lint'
  assert_denies_in "${BATS_TEST_TMPDIR}" 'cd repo/sub && bun run lint'
}

@test "a cd through the home directory moves the check to its hooks" {
  lefthook_runs 'bun run lint'
  assert_denies_in "${BATS_TEST_TMPDIR}/home" 'cd ~/../repo && bun run lint'
}

@test "a cd out of the repository leaves the check outside its hooks" {
  lefthook_runs 'bun run lint'
  mkdir -p "${BATS_TEST_TMPDIR}/elsewhere"
  assert_silent_in "${REPO}" "cd ${BATS_TEST_TMPDIR}/elsewhere && bun run lint"
}

@test "a directory that is no repository stays silent" {
  mkdir -p "${BATS_TEST_TMPDIR}/plain"
  printf 'pre-commit:\n  commands:\n    x:\n      run: bun run lint\n' \
    >"${BATS_TEST_TMPDIR}/plain/lefthook.yml"
  assert_silent_in "${BATS_TEST_TMPDIR}/plain" 'bun run lint'
}

@test "a repository with no hook configuration stays silent" {
  assert_silent_in "${REPO}" 'bun run lint'
  assert_silent_in "${REPO}" 'biome check src'
}

@test "a working directory that does not exist stays silent" {
  lefthook_runs 'bun run lint'
  assert_silent_in "${BATS_TEST_TMPDIR}/missing" 'bun run lint'
}

@test "an envelope with no command stays silent" {
  lefthook_runs 'bun run lint'
  assert_silent_in "${REPO}" ''
}

@test "an unreadable hook configuration stays silent" {
  printf 'pre-commit:\n  commands:\n    x:\n      run: "bun run lint\n  : [\n' |
    write_lefthook
  run_bash_hook_in "${REPO}" 'bun run lint'
  assert_exited_clean
}

@test "binary garbage as hook configuration stays silent" {
  head -c 2048 /dev/urandom >"${REPO}/lefthook.yml"
  run_bash_hook_in "${REPO}" 'bun run lint'
  assert_exited_clean
  assert_no_decision 'garbage configuration'
}

@test "an envelope that is not JSON stays silent" {
  lefthook_runs 'bun run lint'
  run_hook_envelope 'not json'
  assert_exited_clean
  assert_no_decision 'not json'
}

@test "a very large hook configuration is answered inside the timeout" {
  {
    printf 'pre-commit:\n  commands:\n'
    local number
    for ((number = 0; number < 1500; number++)); do
      printf '    c%d:\n      run: tool%d check {staged_files}\n' \
        "${number}" "${number}"
    done
  } >"${REPO}/lefthook.yml"
  local started="${SECONDS}"
  run_bash_hook_in "${REPO}" 'bun run lint'
  assert_exited_clean
  ((SECONDS - started < 5))
}

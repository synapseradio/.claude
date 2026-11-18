#!/bin/bash
#
# Shared setup for the bats suites under scripts/: a sandboxed environment,
# command stubs that log their calls, and fixture repositories.

#######################################
# Move every location a script could read or write into BATS_TEST_TMPDIR.
# Globals:
#   BATS_TEST_TMPDIR
#   HOME, TMPDIR, XDG_*, GIT_CONFIG_GLOBAL, GIT_CONFIG_NOSYSTEM (set)
#   CALL_LOG, STUB_BIN, STUB_BODIES, PATH (set)
# Arguments:
#   None
#######################################
setup_sandbox_test_env() {
  if [[ -z "${BATS_TEST_TMPDIR:-}" ]]; then
    echo "setup_sandbox_test_env requires BATS_TEST_TMPDIR" >&2
    return 1
  fi
  export HOME="${BATS_TEST_TMPDIR}/home"
  export TMPDIR="${BATS_TEST_TMPDIR}/tmp"
  export XDG_CONFIG_HOME="${HOME}/.config"
  export XDG_CACHE_HOME="${HOME}/.cache"
  export XDG_DATA_HOME="${HOME}/.local/share"
  export XDG_STATE_HOME="${HOME}/.local/state"
  mkdir -p "${HOME}" "${TMPDIR}" "${XDG_CONFIG_HOME}" "${XDG_CACHE_HOME}" \
    "${XDG_DATA_HOME}" "${XDG_STATE_HOME}"

  export GIT_CONFIG_GLOBAL="${HOME}/.gitconfig"
  export GIT_CONFIG_NOSYSTEM=1
  write_git_config "${GIT_CONFIG_GLOBAL}"
  unset GIT_DIR GIT_INDEX_FILE GIT_PREFIX GIT_WORK_TREE GIT_COMMON_DIR

  export CALL_LOG="${BATS_TEST_TMPDIR}/calls.log"
  : >"${CALL_LOG}"
  STUB_BIN="${BATS_TEST_TMPDIR}/bin"
  export STUB_BIN STUB_BODIES="${BATS_TEST_TMPDIR}/stub-bodies"
  mkdir -p "${STUB_BIN}" "${STUB_BODIES}"
  export PATH="${STUB_BIN}:${PATH}"
}

#######################################
# Write the git identity and default branch every fixture repository needs.
# Arguments:
#   The config file.
#######################################
write_git_config() {
  printf '[user]\n\tname = Test\n\temail = test@example.com\n[init]\n\tdefaultBranch = main\n' \
    >"$1"
}

#######################################
# Write the one executable every stub in this file links to, and run it once.
# It appends "<name> <args>" to CALL_LOG, then sources the body the case
# wrote for the name it was called by. macOS scans each newly written
# executable on its first exec, about a quarter second each and slower still
# while other processes queue for the same scan; a link to a file already run
# skips it:
# https://lapcatsoftware.com/articles/2024/2/3.html
# Call from setup_file.
# Globals:
#   BATS_FILE_TMPDIR
#   STUB_EXEC (set, exported)
#######################################
build_stub_once() {
  export STUB_EXEC="${BATS_FILE_TMPDIR}/stub"
  cat >"${STUB_EXEC}" <<'EOF'
#!/bin/bash
stub_name="${0##*/}"
printf '%s\n' "${stub_name} $*" >>"${CALL_LOG}"
# shellcheck source=/dev/null
source "${STUB_BODIES}/${stub_name}"
EOF
  chmod +x "${STUB_EXEC}"
  CALL_LOG=/dev/null STUB_BODIES="${BATS_FILE_TMPDIR}/no-bodies" \
    "${STUB_EXEC}" >/dev/null 2>&1 || true
}

#######################################
# Put a stub named for a command on PATH: it appends "<name> <args>" to
# CALL_LOG, then runs the body read from STDIN.
# Globals:
#   STUB_BIN, STUB_BODIES, STUB_EXEC
# Arguments:
#   The command name.
#######################################
write_stub() {
  local name="$1"
  cat >"${STUB_BODIES}/${name}"
  ln -sf "${STUB_EXEC:?build_stub_once runs in setup_file}" "${STUB_BIN}/${name}"
}

#######################################
# Fail unless CALL_LOG holds the given line whole.
# Arguments:
#   The line.
#######################################
assert_logged() {
  if ! grep -Fxq -- "$1" "${CALL_LOG}"; then
    echo "expected call not logged: $1" >&2
    cat "${CALL_LOG}" >&2
    return 1
  fi
}

#######################################
# Fail where any CALL_LOG line holds the given text.
# Arguments:
#   The text.
#######################################
refute_logged() {
  if grep -Fq -- "$1" "${CALL_LOG}"; then
    echo "unexpected call logged: $1" >&2
    cat "${CALL_LOG}" >&2
    return 1
  fi
}

#######################################
# Stub bun, uv, brew, and claude. A stubbed bun install and uv sync create the
# product each leaves behind; BUN_STATUS makes bun fail, and BREW_CHECK_STATUS
# sets the exit status of brew bundle check.
# Arguments:
#   None
#######################################
stub_toolchain() {
  write_stub bun <<'EOF'
if [[ "${1:-}" == install ]]; then
  if (( ${BUN_STATUS:-0} != 0 )); then exit "${BUN_STATUS}"; fi
  mkdir -p node_modules/.bin
  : >node_modules/.bin/biome
fi
EOF
  write_stub uv <<'EOF'
if [[ "${1:-}" == sync ]]; then
  mkdir -p .venv/bin
  : >.venv/bin/python
fi
EOF
  write_stub brew <<'EOF'
if [[ "${1:-} ${2:-}" == "bundle check" ]]; then exit "${BREW_CHECK_STATUS:-0}"; fi
EOF
  write_stub claude <<'EOF'
exit 0
EOF
}

#######################################
# Write the rulesets CLI launcher into a fixture repository as a stub that logs
# its arguments. RULESETS_CHECK_STATUS and RULESETS_RENDER_CHECK_STATUS set the
# exit status of `check` and of `render --check`.
# Arguments:
#   The fixture repository.
#######################################
stub_rulesets_cli() {
  local repo="$1"
  local stub="${repo}/features/plugins/rulesets/hooks/with-python.sh"
  mkdir -p "${stub%/*}"
  cat >"${stub}" <<'EOF'
#!/bin/bash
printf '%s\n' "with-python $*" >>"${CALL_LOG}"
case "$2 $3" in
  "check --root") exit "${RULESETS_CHECK_STATUS:-0}" ;;
  "render --check") exit "${RULESETS_RENDER_CHECK_STATUS:-0}" ;;
esac
EOF
  chmod +x "${stub}"
}

#######################################
# Create a git repository holding the files the setup steps hash. Git runs
# against a home and a config beside the repository, never the caller's.
# Arguments:
#   The repository directory.
#######################################
make_fixture_repo() {
  local repo="$1"
  mkdir -p "${repo}" "${repo}.home"
  (
    export HOME="${repo}.home"
    export XDG_CONFIG_HOME="${HOME}/.config"
    export GIT_CONFIG_GLOBAL="${HOME}/.gitconfig"
    export GIT_CONFIG_NOSYSTEM=1
    unset GIT_DIR GIT_INDEX_FILE GIT_PREFIX GIT_WORK_TREE GIT_COMMON_DIR
    write_git_config "${GIT_CONFIG_GLOBAL}"
    git -C "${repo}" init -q
    printf 'lock 1\n' >"${repo}/bun.lock"
    printf '{}\n' >"${repo}/package.json"
    printf 'lock 1\n' >"${repo}/uv.lock"
    printf '[project]\n' >"${repo}/pyproject.toml"
    printf 'brew "just"\n' >"${repo}/Brewfile"
    git -C "${repo}" add -A
    git -C "${repo}" commit -q -m 'fixture'
  )
}

#######################################
# Build the fixture repository once for a test file; call from setup_file.
# Globals:
#   BATS_FILE_TMPDIR
#   FIXTURE_REPO (set, exported)
# Arguments:
#   None
#######################################
build_fixture_repo_once() {
  export FIXTURE_REPO="${BATS_FILE_TMPDIR}/fixture"
  make_fixture_repo "${FIXTURE_REPO}"
}

#######################################
# Add a linked worktree to a fixture repository.
# Arguments:
#   The primary checkout, then the linked worktree's directory.
#######################################
add_linked_worktree() {
  git -C "$1" worktree add -q -b linked "$2"
}

#######################################
# Sandbox the test, stub the toolchain, and enter a private copy of the
# fixture repository built by build_fixture_repo_once.
# Arguments:
#   The copy's directory name under BATS_TEST_TMPDIR.
#######################################
enter_fixture_repo() {
  setup_sandbox_test_env
  stub_toolchain
  cp -R "${FIXTURE_REPO:?build_fixture_repo_once runs in setup_file}" \
    "${BATS_TEST_TMPDIR}/$1" || return 1
  cd "${BATS_TEST_TMPDIR}/$1" || return 1
}

enter_linked_worktree() {
  LINKED="${BATS_TEST_TMPDIR}/linked"
  add_linked_worktree "${PWD}" "${LINKED}"
  cd "${LINKED}" || return 1
}

#######################################
# Write the engine-generated gauge types into a checkout.
# Arguments:
#   The checkout, then the file content.
#######################################
write_gauge_types() {
  local types="$1/features/mods/context-gauge/.claude-plugin/types"
  mkdir -p "${types}"
  printf '%s\n' "$2" >"${types}/tsconfig.json"
}

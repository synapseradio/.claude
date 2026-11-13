#!/usr/bin/env bats
#
# Tests for ask-fetch-and-run.sh, the PreToolUse Bash hook that prompts
# before a command resolves a package from a registry and runs it.
#
# The ask cases cover each fetch-and-run form, each command position the
# match may sit at, and the wrapper words in front of it. The silent cases
# cover bunx and bun x, the neighbors of each form that run nothing fetched,
# and the form names inside a quoted string or as an argument.

# Single quotes are intentional throughout: the guard has to receive the
# literal text, never its expansion (SC2016). setup sets HOOK and the
# helpers read it, which shellcheck cannot see (SC2034).
# shellcheck disable=SC2016,SC2034

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  HOOK="${BATS_TEST_DIRNAME}/../hooks/ask-fetch-and-run.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  isolate_home
}

@test "npx asks" {
  assert_asks 'npx cowsay@1.6.0 hello'
}

@test "npm exec asks" {
  assert_asks 'npm exec cowsay@1.6.0 -- hello'
}

@test "npm x asks" {
  assert_asks 'npm x cowsay@1.6.0 hello'
}

@test "npm create asks" {
  assert_asks 'npm create vite@5.4.0 my-app'
}

@test "npm init with an initializer name asks" {
  assert_asks 'npm init vite@5.4.0 my-app'
}

@test "npm init with an option before the initializer name asks" {
  assert_asks 'npm init --yes vite@5.4.0'
}

@test "pnpm dlx asks" {
  assert_asks 'pnpm dlx cowsay@1.6.0 hello'
}

@test "pnpx asks" {
  assert_asks 'pnpx cowsay@1.6.0 hello'
}

@test "pnpm create asks" {
  assert_asks 'pnpm create vite@5.4.0 my-app'
}

@test "yarn dlx asks" {
  assert_asks 'yarn dlx cowsay@1.6.0 hello'
}

@test "yarn create asks" {
  assert_asks 'yarn create vite@5.4.0 my-app'
}

@test "bun create asks" {
  assert_asks 'bun create vite@5.4.0 my-app'
}

@test "bx asks" {
  assert_asks 'bx cowsay@1.6.0 hello'
}

@test "uvx asks" {
  assert_asks 'uvx ruff@0.8.0 check .'
}

@test "uv tool run asks" {
  assert_asks 'uv tool run ruff@0.8.0 check .'
}

@test "pipx run asks" {
  assert_asks 'pipx run cowsay==6.0 hello'
}

@test "docker run asks" {
  assert_asks 'docker run --rm alpine:3.20 echo hi'
}

@test "docker container run asks" {
  assert_asks 'docker container run --rm alpine:3.20 echo hi'
}

@test "podman run asks" {
  assert_asks 'podman run --rm alpine:3.20 echo hi'
}

@test "an unpinned npx asks" {
  assert_asks 'npx cowsay hello'
}

@test "a package manager option before the subcommand still asks" {
  assert_asks 'npm --prefix ./app exec cowsay@1.6.0'
}

@test "a fetch-and-run after && asks" {
  assert_asks 'cd app && npx cowsay@1.6.0 hello'
}

@test "a fetch-and-run after a semicolon asks" {
  assert_asks 'git status; uvx ruff@0.8.0 check .'
}

@test "a fetch-and-run after a pipe asks" {
  assert_asks 'echo hi | npx cowsay@1.6.0'
}

@test "a fetch-and-run on a later line asks" {
  assert_asks $'cd app\nnpm exec cowsay@1.6.0'
}

@test "a fetch-and-run inside a subshell asks" {
  assert_asks '(cd app && pnpm dlx cowsay@1.6.0)'
}

@test "a fetch-and-run inside a command substitution asks" {
  assert_asks 'echo "$(npx cowsay@1.6.0 hi)"'
}

@test "a fetch-and-run behind sudo asks" {
  assert_asks 'sudo docker run --rm alpine:3.20'
}

@test "a fetch-and-run behind env asks" {
  assert_asks 'env CI=1 npx cowsay@1.6.0'
}

@test "a fetch-and-run behind exec asks" {
  assert_asks 'exec npx cowsay@1.6.0'
}

@test "a fetch-and-run behind command asks" {
  assert_asks 'command npx cowsay@1.6.0'
}

@test "a fetch-and-run behind xargs asks" {
  assert_asks 'echo hi | xargs npx cowsay@1.6.0'
}

@test "a fetch-and-run in a bash -c string asks" {
  assert_asks "bash -c 'cd app && npx cowsay@1.6.0'"
}

@test "an ask names the package, the version, and the tool that falls short" {
  run_bash_hook 'npx cowsay hello'
  local reason
  reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")"
  [[ "${reason}" == *'the package'* ]]
  [[ "${reason}" == *'the version the command pins'* ]]
  [[ "${reason}" == *'what it executes'* ]]
  [[ "${reason}" == *'which installed tool falls short'* ]]
  [[ "${reason}" == *'must pin a version'* ]]
}

@test "a fetch-and-run emits an ask and no deny" {
  run_bash_hook 'npx cowsay hello'
  [[ "$(jq -r '.hookSpecificOutput.permissionDecision' \
    <<<"${HOOK_OUTPUT}")" == ask ]]
}

@test "bunx stays silent" {
  assert_silent 'bunx cowsay@1.6.0 hello'
}

@test "bun x stays silent" {
  assert_silent 'bun x cowsay@1.6.0 hello'
}

@test "npm init without an initializer name stays silent" {
  assert_silent 'npm init -y'
}

@test "npm install stays silent" {
  assert_silent 'npm install cowsay@1.6.0'
}

@test "npm run stays silent" {
  assert_silent 'npm run exec'
}

@test "bun run stays silent" {
  assert_silent 'bun run create'
}

@test "pnpm install stays silent" {
  assert_silent 'pnpm install'
}

@test "yarn add stays silent" {
  assert_silent 'yarn add cowsay@1.6.0'
}

@test "uv run stays silent" {
  assert_silent 'uv run pytest'
}

@test "uv tool install stays silent" {
  assert_silent 'uv tool install ruff==0.8.0'
}

@test "pipx install stays silent" {
  assert_silent 'pipx install cowsay==6.0'
}

@test "docker ps stays silent" {
  assert_silent 'docker ps -a'
}

@test "docker build stays silent" {
  assert_silent 'docker build -t app .'
}

@test "docker rm named run stays silent" {
  assert_silent 'docker rm run'
}

@test "podman images stays silent" {
  assert_silent 'podman images'
}

@test "npx named inside a quoted argument stays silent" {
  assert_silent 'echo "npx cowsay hello"'
}

@test "npx as an argument stays silent" {
  assert_silent 'grep -rn npx scripts/'
}

@test "docker run named inside a commit message stays silent" {
  assert_silent 'git commit -m "docs: explain docker run"'
}

@test "a word ending in npx stays silent" {
  assert_silent 'mynpx cowsay'
}

@test "a path containing npx stays silent" {
  assert_silent 'cat docs/npx.md'
}

@test "an empty command stays silent" {
  assert_silent ''
}

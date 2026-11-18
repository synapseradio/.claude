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
# literal text, never its expansion (SC2016).
# shellcheck disable=SC2016

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load_guard ask-fetch-and-run
  isolate_home
}

@test "each package-runner form asks before it runs" {
  local -a forms=(
    'npx cowsay@1.6.0 hello'
    'npm exec cowsay@1.6.0 -- hello'
    'npm x cowsay@1.6.0 hello'
    'npm create vite@5.4.0 my-app'
    'npm init vite@5.4.0 my-app'
    'npm init --yes vite@5.4.0'
    'pnpm dlx cowsay@1.6.0 hello'
    'pnpx cowsay@1.6.0 hello'
    'pnpm create vite@5.4.0 my-app'
    'yarn dlx cowsay@1.6.0 hello'
    'yarn create vite@5.4.0 my-app'
    'bun create vite@5.4.0 my-app'
    'bx cowsay@1.6.0 hello'
    'uvx ruff@0.8.0 check .'
    'uv tool run ruff@0.8.0 check .'
    'pipx run cowsay==6.0 hello'
    'docker run --rm alpine:3.20 echo hi'
    'docker container run --rm alpine:3.20 echo hi'
    'podman run --rm alpine:3.20 echo hi'
    'npx cowsay hello'
    'npm --prefix ./app exec cowsay@1.6.0'
  )
  local form
  for form in "${forms[@]}"; do
    assert_asks "${form}"
  done
}

@test "a package runner asks at each command position and behind each wrapper word" {
  local -a forms=(
    'cd app && npx cowsay@1.6.0 hello'
    'git status; uvx ruff@0.8.0 check .'
    'echo hi | npx cowsay@1.6.0'
    $'cd app\nnpm exec cowsay@1.6.0'
    '(cd app && pnpm dlx cowsay@1.6.0)'
    'echo "$(npx cowsay@1.6.0 hi)"'
    'sudo docker run --rm alpine:3.20'
    'env CI=1 npx cowsay@1.6.0'
    'exec npx cowsay@1.6.0'
    'command npx cowsay@1.6.0'
    'echo hi | xargs npx cowsay@1.6.0'
    "bash -c 'cd app && npx cowsay@1.6.0'"
  )
  local form
  for form in "${forms[@]}"; do
    assert_asks "${form}"
  done
}

@test "bunx, bun x, and the neighbors of each form that run nothing fetched stay silent" {
  local -a forms=(
    'bunx cowsay@1.6.0 hello'
    'bun x cowsay@1.6.0 hello'
    'npm init -y'
    'npm install cowsay@1.6.0'
    'npm run exec'
    'bun run create'
    'pnpm install'
    'yarn add cowsay@1.6.0'
    'uv run pytest'
    'uv tool install ruff==0.8.0'
    'pipx install cowsay==6.0'
    'docker ps -a'
    'docker build -t app .'
    'docker rm run'
    'podman images'
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "a form named inside text, as an argument, or as part of a longer word stays silent" {
  local -a forms=(
    'echo "npx cowsay hello"'
    'grep -rn npx scripts/'
    'git commit -m "docs: explain docker run"'
    'mynpx cowsay'
    'cat docs/npx.md'
    ''
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "an envelope proposing npx prints a PreToolUse ask" {
  assert_main_prints ask \
    '{"tool_name":"Bash","tool_input":{"command":"npx cowsay hi"}}'
}

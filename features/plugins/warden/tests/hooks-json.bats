#!/usr/bin/env bats
#
# Tests for hooks/hooks.json, the file through which the harness runs each
# guard: every command it registers runs a guard file that ships in hooks/.
# The guard tests call each guard's functions directly, so this is the one
# check that the harness reaches them.

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  isolate_home
}

@test "every command in hooks.json runs a guard file that exists" {
  local plugin="${BATS_TEST_DIRNAME}/.." command path
  # The text hooks.json holds, which the harness expands and this test must
  # not (SC2016).
  # shellcheck disable=SC2016
  local prefix='bash "${CLAUDE_PLUGIN_ROOT}/'
  local -a commands=()
  while IFS= read -r command; do
    commands+=("${command}")
  done < <(jq -r '.hooks[][].hooks[].command' "${plugin}/hooks/hooks.json")

  ((${#commands[@]} > 0)) || {
    echo 'hooks.json registers no command' >&2
    return 1
  }
  for command in "${commands[@]}"; do
    [[ "${command}" == "${prefix}"hooks/*.sh\" ]] || {
      echo "not a guard run by bash from the plugin root: ${command}" >&2
      return 1
    }
    path="${command#"${prefix}"}"
    path="${path%\"}"
    [[ -f "${plugin}/${path}" ]] || {
      echo "hooks.json runs ${path}, which does not exist" >&2
      return 1
    }
  done
}

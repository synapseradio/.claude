#!/usr/bin/env bats
#
# Tests for deny-rm.sh against scratch git repositories: rm at each command
# position and behind each wrapper word, rm after another step, git that
# does not answer or is not installed, and the envelope main reads.
# deny-rm.bats covers each spelling and what git says of each operand.

export BATS_TEST_TIMEOUT=10

setup_file() {
  export FIXTURE="${BATS_FILE_TMPDIR}/repo"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load "${BATS_TEST_DIRNAME}/deny-rm-fixture.bash"
  export HOME="${BATS_FILE_TMPDIR}/home"
  mkdir -p "${HOME}"
  isolate_git_config
  build_fixture
}

setup() {
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load "${BATS_TEST_DIRNAME}/deny-rm-fixture.bash"
  load_guard deny-rm
  isolate_home
  isolate_git_config
}

@test "rm at each command position is judged by the rule" {
  make_repo
  printf 'new\n' >"${REPO}/new.txt"
  local template
  for template in '@ && true' '@ || false' '@; true' '@ | cat' $'@\necho go' \
    '(@)' "echo \$(@)" '{ @; }' "bash -c '@'"; do
    assert_silent "${template//@/rm ${REPO}/tracked.txt}"
    assert_denies "${template//@/rm ${REPO}/new.txt}"
  done
}

@test "rm behind each wrapper word is judged by the rule" {
  make_repo
  printf 'new\n' >"${REPO}/new.txt"
  local wrapper
  for wrapper in 'sudo' 'sudo -u root' 'command' 'env' 'env LC_ALL=C' 'exec' 'nohup' 'time'; do
    assert_silent "${wrapper} rm ${REPO}/tracked.txt"
    assert_denies "${wrapper} rm ${REPO}/new.txt"
  done
}

@test "rm after another step is denied, even on a clean tracked file" {
  make_repo
  local -a forms=(
    "mkdir ${REPO}/d && echo x > ${REPO}/d/f && rm -r ${REPO}/d"
    "echo x >> ${REPO}/tracked.txt && rm ${REPO}/tracked.txt"
    "npm run build && rm -rf ${REPO}/dir"
    "> ${REPO}/tracked.txt && rm ${REPO}/tracked.txt"
    "true; rm ${REPO}/tracked.txt"
    "false || rm ${REPO}/tracked.txt"
    "echo x | rm ${REPO}/tracked.txt"
    "sleep 1 & rm ${REPO}/tracked.txt"
    $'echo go\n'"rm ${REPO}/tracked.txt"
    "if true; then rm ${REPO}/tracked.txt; fi"
    "for f in a b; do rm ${REPO}/tracked.txt; done"
    "(echo x > ${REPO}/f; rm ${REPO}/f)"
    "(true; rm ${REPO}/tracked.txt)"
    "echo \$(echo x >> ${REPO}/tracked.txt; rm ${REPO}/tracked.txt)"
    "echo \`true; rm ${REPO}/tracked.txt\`"
    "true; echo \$(rm ${REPO}/tracked.txt)"
    "bash -c 'echo x >> ${REPO}/tracked.txt && rm ${REPO}/tracked.txt'"
    "true && sh -c 'rm ${REPO}/tracked.txt'"
    "true && sudo rm ${REPO}/tracked.txt"
    "rm ${REPO}/tracked.txt; echo x > ${REPO}/f; rm ${REPO}/f"
    "rm ${REPO}/tracked.txt; true; rm ${REPO}/other.txt"
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
}

@test "a later rm is denied on its own operand after an earlier rm" {
  make_repo
  printf 'new\n' >"${REPO}/new.txt"
  assert_denies "rm ${REPO}/tracked.txt && rm ${REPO}/new.txt"
}

@test "rm is denied when git does not answer before the deadline" {
  make_repo
  stub_hung_git
  WARDEN_RM_DEADLINE=1 assert_denies "rm ${REPO}/tracked.txt"
}

@test "rm is denied when git is not installed" {
  make_repo
  local stubs="${BATS_TEST_TMPDIR}/stubs"
  mkdir -p "${stubs}"
  printf '#!/bin/bash\nexit 127\n' >"${stubs}/git"
  chmod +x "${stubs}/git"
  PATH="${stubs}:${PATH}" assert_denies "rm ${REPO}/tracked.txt"
}

@test "an envelope proposing rm from a directory outside git prints a PreToolUse denial" {
  make_plain_dir
  assert_main_prints deny \
    "{\"tool_name\":\"Bash\",\"cwd\":\"${PLAIN}\",\"tool_input\":{\"command\":\"rm loose.txt\"}}"
}

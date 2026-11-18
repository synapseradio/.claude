#!/usr/bin/env bats
#
# Contract test for git_guard::run_with_deadline: when the deadline passes, no
# process the judge started is left running. The judge here starts a child and
# a grandchild that sleep long past the deadline, and the test checks the
# processes by PID.

export BATS_TEST_TIMEOUT=10

bats_require_minimum_version 1.5.0

setup() {
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load_guard deny-rm
  isolate_home
  export TMPDIR="${BATS_TEST_TMPDIR}"
  PIDS="${BATS_TEST_TMPDIR}/pids"
  : >"${PIDS}"
}

# A judge that hangs: a subshell holds a grandchild sleep, and a child sleep
# runs beside it. Every PID lands in PIDS.
hanging_judge() {
  (
    sleep 30 &
    echo "$!" >>"${PIDS}"
    wait
  ) &
  echo "$!" >>"${PIDS}"
  sleep 30 &
  echo "$!" >>"${PIDS}"
  wait
}

@test "no process the judge started is left running once the deadline passes" {
  local status=0 pid
  git_guard::run_with_deadline 1 deadline-test hanging_judge || status=$?
  [ "${status}" -eq 1 ]
  [ "$(wc -l <"${PIDS}")" -eq 3 ]
  while read -r pid; do
    run ! kill -0 "${pid}"
  done <"${PIDS}"
}

quick_judge() {
  echo ok
}

@test "a judge that finishes in time leaves no deadline watcher sleeping" {
  local seconds=7919 status=0
  git_guard::run_with_deadline "${seconds}" deadline-test quick_judge || status=$?
  [ "${status}" -eq 0 ]
  [ "${GG_DETAIL}" = ok ]
  run ! pgrep -f "^sleep ${seconds}$"
}

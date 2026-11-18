#!/usr/bin/env bats
#
# Tests for block-secret-file-reads.sh on grep and rg: a secret path named
# as the pattern stays silent, and one named as a file operand is denied.

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load_guard block-secret-file-reads
  isolate_home

  # The helper points WARDEN_BANNED_READS at this test's own temporary
  # directory, so the defaults are what a case sees until it writes that
  # file itself.
}

@test "a grep or rg pattern that names a secret path stays silent" {
  local -a forms=(
    'grep -rn id_rsa /x'
    'rg -l .env /x'
    'grep -rn "id_rsa" /x'
    'rg -n -i secrets.env docs'
    'grep -e id_rsa /x'
    'grep -rne id_rsa /x'
    'grep --regexp=id_rsa /x'
    'rg --regexp .env /x'
    'rg -n -e .env -e id_rsa /x'
    'rg -g "*.md" -A 3 id_rsa /x'
    'cat notes.txt | grep -m 1 id_rsa'
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "a file operand of grep or rg is still checked" {
  local -a forms=(
    'grep foo ~/.ssh/id_rsa'
    'grep -rn id_rsa ~/.ssh/'
    'rg foo .env'
    'grep -e foo -e bar ~/.ssh/id_rsa'
    'sudo grep foo ~/.ssh/id_rsa'
    'ssh host grep foo ~/.ssh/id_rsa'
    'grep -f ~/.ssh/id_rsa x'
    'grep --file=~/.ssh/id_rsa x'
    'rg --file ~/.ssh/id_rsa x'
    'grep -f .env /x'
    'rg --files ~/.ssh/'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
}

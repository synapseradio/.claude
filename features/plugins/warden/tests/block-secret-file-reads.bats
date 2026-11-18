#!/usr/bin/env bats
#
# Tests for block-secret-file-reads.sh, the PreToolUse guard that denies a
# read of a secret-shaped path.
#
# The guard carries two branches, and the plugin registers both: the Bash
# branch reads the proposed shell command, and the Read branch reads a file
# path.
#
# Half the cases here are paths that must stay readable, because a pattern
# is only as good as what it leaves alone. Each of those pairs with a
# denial it sits next to: /private/tmp against a dotfiles private store,
# rotate-secrets.sh against secrets.sh, .secrets.baseline against
# .secrets, secrets.env.example against secrets.env, and .envrc against
# .env. A guard that denied the left-hand side of any pair would be turned
# off within a day.

# Single quotes are intentional throughout: the guard has to receive the
# literal text, never its expansion (SC2016).
# shellcheck disable=SC2016,SC2030,SC2031

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
  #
  # A home-shaped path for the cases that need one. It exists only for the
  # length of this test, and holds no file: the guard matches command text
  # and opens nothing.
  FAKE_HOME="${BATS_TEST_TMPDIR}/home/pilot"
}

@test "a command that reads a credential file, directory, or private store is denied" {
  local -a forms=(
    'cat ~/.ssh/id_rsa'
    'base64 id_ed25519'
    'cat $HOME/.aws/credentials'
    "grep -r . ${FAKE_HOME}/.gnupg/private-keys-v1.d"
    'cp ~/.kube/config /tmp/config'
    'cat .env'
    'head -n 20 .env.local'
    'cat .env.production.local'
    'while read -r line; do echo "${line}"; done < .env'
    'cat ~/dotfiles/shell/lib/private/tokens.sh'
    'cat ~/.dotfiles/private/keys.sh'
    "cat ${FAKE_HOME}/dotfiles/private/env"
    $'bash <<\'EOF\'\ncat ~/.ssh/id_rsa\nEOF'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
}

@test "paths that only look like secrets stay readable" {
  local -a forms=(
    'cat /private/tmp/build.log'
    'tail -n 50 /private/var/log/system.log'
    'cat src/private/index.ts'
    'cat docs/private/notes.md'
    'cat ~/dotfiles/README.md'
    'cat scripts/rotate-secrets.sh'
    'cat manage-secrets.py'
    'cat secrets.env.example'
    'cat secrets.env.template'
    'cat .secrets.baseline'
    'cat privateer.txt'
    'cat README.md'
    'cat .envrc'
    'cat ~/.zshrc'
    'echo "keep .env out of git"'
    ''
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "a secrets-named file or directory is denied" {
  local -a forms=(
    'cat secrets.env'
    'cat config/secrets.sh'
    'cat secrets.zsh'
    'cat secrets.bash'
    'grep -r . prod.secrets'
    'cat .secrets/token'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
}

@test "a fragment in the banned-reads file is denied" {
  printf '%s\n' 'credentials' >"${WARDEN_BANNED_READS}"
  assert_denies 'cat ~/work/credentials.yaml'
}

@test "a banned fragment is matched literally, with nothing to escape" {
  printf '%s\n' 'my.store' 'keys[1].pem' >"${WARDEN_BANNED_READS}"
  assert_denies 'cat ~/my.store/token'
  assert_silent 'cat ~/myXstore/token'
  assert_denies 'cat ~/vault/keys[1].pem'
}

@test "a banned fragment still needs a read command to deny" {
  printf '%s\n' 'credentials' >"${WARDEN_BANNED_READS}"
  assert_silent 'echo "rotate the credentials next week"'
}

@test "comments and blank lines in the banned-reads file are skipped" {
  printf '%s\n' '# what I keep out of reach' '' '   ' 'credentials' \
    >"${WARDEN_BANNED_READS}"
  assert_denies 'cat ~/work/credentials.yaml'
  assert_silent 'cat README.md'
}

@test "a missing or empty banned-reads file leaves every default in force" {
  export WARDEN_BANNED_READS="${BATS_TEST_TMPDIR}/absent.conf"
  assert_denies 'cat ~/.ssh/id_rsa'
  assert_silent 'cat README.md'
  : >"${WARDEN_BANNED_READS}"
  assert_denies 'cat .env'
  assert_silent 'cat README.md'
}

@test "the Read tool is denied a credential path" {
  local -a forms=(
    "${FAKE_HOME}/dotfiles/shell/lib/private/env.sh"
    "${FAKE_HOME}/.ssh/id_ed25519"
    "${FAKE_HOME}/projects/app/.env"
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies_read "${form}"
  done
}

@test "the Read branch denies a banned fragment" {
  printf '%s\n' 'credentials' >"${WARDEN_BANNED_READS}"
  assert_denies_read "${FAKE_HOME}/work/credentials.yaml"
}

@test "the Read tool is allowed an ordinary path" {
  local -a forms=(
    '/private/tmp/build.log'
    "${FAKE_HOME}/projects/app/README.md"
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent_read "${form}"
  done
}

@test "a tool the guard does not cover stays silent" {
  run_hook_envelope '{"tool_name":"Write","tool_input":{"file_path":".env"}}'
  assert_no_decision 'a Write of .env'
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

@test "an envelope proposing a secret read prints a PreToolUse denial" {
  assert_main_prints deny \
    '{"tool_name":"Bash","tool_input":{"command":"cat ~/.ssh/id_rsa"}}'
  assert_main_prints deny \
    "{\"tool_name\":\"Read\",\"tool_input\":{\"file_path\":\"${FAKE_HOME}/.aws/credentials\"}}"
}

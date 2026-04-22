#!/usr/bin/env bash
#
# find-forbidden-words.sh — scan markdown for words Google and Django
# explicitly discourage in developer documentation.
#
# Usage: find-forbidden-words.sh [path]
#   path: directory or file to scan. Default: current directory.
#
# Word list (case-insensitive, whole-word):
#   simply, easily, just, merely, straightforward, quickly, obviously, clearly
#
# Sources:
#   Google: https://developers.google.com/style/tone
#   Django: https://docs.djangoproject.com/en/dev/internals/contributing/writing-documentation/
#
# Caveat: the list is intentionally aggressive. Words like "just" (meaning
# "only") and "clearly" (in a non-style sense) have legitimate uses. A
# reviewer should triage each hit, not blindly fix every match. The spirit
# of Google's and Django's rule is to diminish these words, not eliminate
# every grammatical instance.
#
# Exit codes:
#   0  no hits
#   1  hits found (so CI can gate on this)
#   2  invalid arguments or path not found
#
# Excludes hidden directories, .git, and node_modules.
# Shell style: https://google.github.io/styleguide/shellguide.html

set -euo pipefail

readonly DEFAULT_PATH="."
readonly WORD_PATTERN='\b(simply|easily|just|merely|straightforward|quickly|obviously|clearly)\b'

main() {
  local target_path="${1:-${DEFAULT_PATH}}"

  if [[ ! -e "${target_path}" ]]; then
    echo "ERROR: path not found: ${target_path}" >&2
    return 2
  fi

  echo "Scanning for forbidden words under: ${target_path}"
  echo "Pattern (case-insensitive, whole-word): ${WORD_PATTERN}"
  echo "Sources: https://developers.google.com/style/tone ; https://docs.djangoproject.com/en/dev/internals/contributing/writing-documentation/"

  local matches
  # grep -r exits 1 on no matches. Capture that cleanly.
  # --include limits to markdown. --exclude-dir skips common non-doc dirs.
  # Note: the hidden-dir glob is named explicitly to avoid ambiguity across
  # grep implementations (BSD grep, GNU grep, ugrep) on how '.*' is resolved.
  if matches="$(grep -rniE \
      --include='*.md' \
      --exclude-dir='.git' \
      --exclude-dir='.github' \
      --exclude-dir='.svn' \
      --exclude-dir='.hg' \
      --exclude-dir='node_modules' \
      --exclude-dir='vendor' \
      --exclude-dir='dist' \
      --exclude-dir='build' \
      "${WORD_PATTERN}" \
      "${target_path}" 2>/dev/null)"; then
    echo "${matches}"
    local count
    count="$(printf '%s\n' "${matches}" | wc -l | tr -d ' ')"
    echo "Hits: ${count} (triage each; the list is aggressive and may include legitimate uses)"
    return 1
  else
    echo "No forbidden-word hits."
    return 0
  fi
}

main "$@"

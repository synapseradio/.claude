#!/bin/bash
#
# Library for the warden guards whose reason quotes part of the command it
# refuses. Source it after lib/command_words.sh, whose placeholders it turns
# back into text; it defines functions only. Uses only what /bin/bash 3.2 on
# macOS offers, and stays quiet under `set -u`.
#
# Stdout: the text each function prints, which a caller takes with $(...).

#######################################
# Shorten a command's text to quote in a reason. The placeholders
# command_words.sh puts for a quoted space and newline become the characters
# again, trailing newlines go, a remaining newline shows as a backslash and an
# n, and text past the limit ends in three dots and then the notice.
# Globals:
#   CW_SPACE, CW_NEWLINE
# Arguments:
#   $1 - the words, as a program line prints them.
#   $2 - the most characters kept, default 60.
#   $3 - optional: text to add after the three dots of a shortened quote.
# Outputs:
#   The quote on stdout.
#######################################
reason_text::quote() {
  local text="$1" max="${2:-60}" notice="${3:-}" backslash=$'\\'
  text="${text//${CW_SPACE}/ }"
  text="${text//${CW_NEWLINE}/$'\n'}"
  while [[ "${text}" == *$'\n' ]]; do
    text="${text%$'\n'}"
  done
  text="${text//$'\n'/${backslash}n}"
  if ((${#text} > max)); then
    text="${text:0:max}...${notice}"
  fi
  printf '%s\n' "${text}"
}

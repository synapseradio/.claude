#!/bin/bash
#
# Library for the warden guards whose reason quotes part of the command it
# refuses. Source it; it defines functions only. Uses only what /bin/bash 3.2
# on macOS offers, and stays quiet under `set -u`.
#
# Stdout: the text each function prints, which a caller takes with $(...).

#######################################
# Turn a program line's words back into the text they came from: the
# placeholders command_words.sh puts for a quoted space and newline become the
# characters again.
# Arguments:
#   $1 - the words, as a program line prints them.
# Outputs:
#   The text on stdout, with trailing newlines left to the caller's $(...).
#######################################
reason_text::restore() {
  local text="$1"
  text="${text//$'\001'/ }"
  text="${text//$'\005'/$'\n'}"
  printf '%s\n' "${text}"
}

#######################################
# Shorten a command's text to quote in a reason: a newline shows as a
# backslash and an n, and text past the limit ends in three dots.
# Arguments:
#   $1 - the text.
#   $2 - the most characters kept, default 60.
# Outputs:
#   The shortened text on stdout.
#######################################
reason_text::span() {
  local text="$1" max="${2:-60}" backslash=$'\\'
  text="${text//$'\n'/${backslash}n}"
  if ((${#text} > max)); then
    text="${text:0:max}..."
  fi
  printf '%s\n' "${text}"
}

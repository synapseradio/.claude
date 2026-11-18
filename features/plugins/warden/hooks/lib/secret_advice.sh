#!/bin/bash
#
# Library for the two warden guards that refuse a secret: the advice both
# refusals give. Source it; it defines functions only. A refusal never
# repeats a name or value from the command, since it only has the pattern to
# go on.
#
# Stdout: the text each function prints, which a caller takes with $(...).

#######################################
# Print what a refusal tells the agent to run instead of printing or reading
# the secret.
# Outputs:
#   The advice on stdout.
#######################################
secret_advice::test_set() {
  printf '%s\n' "To confirm a variable is set without printing it, test it: [ -n \"\${NAME:-}\" ] && echo set."
}

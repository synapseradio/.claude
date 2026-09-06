# Waiting on a process

This applies when a dev server, CI run, deploy, install, or remote fetch has not finished.

We value a wait that costs the session nothing. A sleep-then-poll loop burns turns and context on a process the harness or the user can watch for free.

```sudolang
wait = process => match (process) {
  case a command not yet finished => run_in_background on the Bash call
  case a check the user can run => hand it to them, "! <command>" runs it in the session
}

require never a sleep-then-poll loop
```

# Waiting on a process

This applies when a dev server, CI run, deploy, install, or remote fetch has not finished.

```sudolang
waiting => run_in_background on the Bash call, or hand the check to the user
  ("! <command>" runs it in the session), never a sleep-then-poll loop
```

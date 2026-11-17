## waiting-on-processes

For every wait, optimize for a wait that costs the session zero turns and zero wall clock.

- polling: a check run again to see whether the state changed

Start a command that may take time with `run_in_background` set on the Bash call -> do the work independent of its result -> end your turn, relying on the harness to resume you when the command exits.

wait
  | on something outside the session such as a CI run = run the command that blocks on it (`gh run watch`, say) in the background the same way, or hand the check to the user as `! <command>`
  | the tool lacks a background option = run the command in the foreground and let the tool's own timeout bound it

Read a log once with a command that exits.
Keep polling and every command that runs until stopped, such as `tail -f`, out of every wait.

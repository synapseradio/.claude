## waiting-on-processes

For every wait, optimize for a wait that costs the session zero turns and zero wall clock.

- polling: a check run again to see whether the state changed

wait
  | you run as a delegate = run the command in the foreground and let the tool's own timeout bound it, so your work finishes before your final report
  | on something outside the session such as a CI run = start the command that blocks on it (`gh run watch`, say) as the last line below starts one, or hand the check to the user as `! <command>`
  | the tool lacks a background option = run the command in the foreground and let the tool's own timeout bound it
  | otherwise = start the command with `run_in_background` set on the Bash call -> do the work independent of its result -> end your turn, relying on the harness to resume you when the command exits

Read a log once with a command that exits.
Keep polling and every command that runs until stopped, such as `tail -f`, out of every wait.

<!-- rule: waiting-on-processes -->

## waiting-on-processes

For every wait, on a command that may run long, a server coming up, a file appearing, or a job or CI run finishing, optimize for a wait that costs the session zero turns and zero wall clock.

- polling: a check run again to see whether the state changed

Start a command that may take time with `run_in_background` set on the Bash call -> do the work independent of its result -> end your turn, relying on the harness to resume you when the command exits.
The wait is on something outside the session, a CI run for one ? run the command that blocks on it, `gh run watch` for one, in the background the same way, or hand the check to the user as `! <command>`.
The tool lacks a background option ? run the command in the foreground and let the tool's own timeout bound it.
Read a log once with a command that exits. Keep `sleep`, alone, chained with `&&`, or inside a loop, every command that runs until stopped, `tail -f` for one, and polling out of every wait.

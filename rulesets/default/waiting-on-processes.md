<!-- rule: waiting-on-processes -->

## waiting-on-processes

For every wait, on a command that may run long, a server coming up, a file appearing, or a job or CI run finishing, optimize for a wait that costs the session zero turns and zero wall clock.

Start a command that may take time with `run_in_background` set on the Bash call. Then do the work independent of its result and end your turn. Rely on the harness to resume you when the command exits. Where the wait is on something outside the session, a CI run or a deploy for one, run the command that blocks on it, `gh run watch` for one, in the background the same way, or hand the check to the user in the form `! <command>`. Where the tool lacks a background option, run the command in the foreground and let the tool's own timeout bound it.

Keep `sleep` out of every command: alone, chained with `&&`, or inside a loop. Keep every command that runs until stopped, `tail -f` for one, out of every wait. Read a log once with a command that exits. Keep polling out of every wait. Count a check run again to see whether the state changed as polling.

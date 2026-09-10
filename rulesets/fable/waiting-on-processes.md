<!-- rule: waiting-on-processes -->

## waiting-on-processes

For every wait, on a command that may run long, a server coming up, a file appearing, or a job or CI run finishing, optimize for a wait that spends none of the session's turns or wall clock.

Start a command that may take time with `run_in_background` set on the Bash call. Then do the work that does not depend on its result and end your turn. Rely on the harness to resume you when the command exits. Where the wait is on something outside the session, a CI run or a deploy for one, run the command that blocks on it, `gh run watch` for one, in the background the same way, or hand the check to the user in the form `! <command>`. Where the tool offers no background option, run the command in the foreground and let the tool's own timeout bound it.

Never call `sleep`: alone, chained with `&&`, or inside a loop. Never poll. Count a check run again to see whether the state changed as a wait.

<!-- rule: waiting-on-processes -->

## waiting-on-processes

When a tool call may take time to complete, optimize for a wait that costs the session nothing.

Wall clock time is expensive, and most commands run quickly, so a sleep tends to outlast the command it waits on. A process runs at its own pace whether or not anyone watches it. The harness reports a background command when it exits, and the user can run a check in their own session through `! <command>`, so a sleep-then-poll loop spends time, turns, and valuable attention on what either would report at no cost.

Where a command has not yet finished, set `run_in_background` on the Bash call. Where the user can run a check, hand it to them in the form `! <command>`. Never run a sleep-then-poll loop.

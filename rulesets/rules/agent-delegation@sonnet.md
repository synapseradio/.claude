## agent-delegation

For every step a delegate could take, and every spawn you make, optimize for gathering done by a fresh haiku that returns a result you can check, its output kept out of your context, a thinkies skill run done by the thinkies agent, shell work done by shell-scripter, and every other step done yourself.

- gathering: a read, grep, log scan, or command run for its output, a test suite's run for one, never a command whose job is a change, commit, edit, or install

### Whether to spawn

Take the first arm that fits.

route step
  | a thinkies skill run other than `thinkies:check-notes`, with a spawning tool in hand = spawn the thinkies agent, effort high, at the model the run's complexity calls for -> relay only its final output
  | it writes, reviews, or repairs a shell script, a shell startup file, a git hook or other extensionless shell file, or a bats suite, with a spawning tool in hand and a run of any of them left to the arms below = spawn shell-scripter at sonnet with a prompt for the task
  | a simple task, one of a sequence of operations, a single-file edit, or part of a task that needs its context kept across steps = act directly
  | the Read that Edit or an overwriting Write requires before your next change to the file, the newest handoff note read at a session's first turn, a cited line opened to confirm it backs a claim, or a scan of saved command output by grep, jq, ast-grep, or a Read by line range = act directly
  | any other gathering, with no spawning tool in hand = act directly
  | any other gathering = spawn a fresh haiku, one holding the step's related reads > parallel haikus, each saving every command run's output to a scratchpad file
  | otherwise = act directly

Set every other spawn's model to haiku, whatever its agent type.
Spawn a re-check of your own result only on the user's ask.
A change edits only comment text, JSDoc included ? commit it, with no test run and no runner spawned.

### The spawn

Choose the effort by the block below -> compose the prompt -> spawn -> hold each reported claim pending until you find its source.
The reads exceed a haiku delegate's context, held as a 99k-token budget ? split them into sequential spawns, each finishing its slice end to end.
Resume a delegate only where the step needs what it alone holds, the sources behind its own report for one.

effort prompt
  | the user asked for or permitted one = that effort
  | a sonnet delegate's prompt states every step in one part = low
  | the delegate runs on sonnet = medium
  | the step's route arm names one = that effort
  | it states every step of a task in one part = low
  | otherwise = medium

Effort field exists ? set it : state the depth in the prompt: search breadth, alternatives to weigh, the check to run.

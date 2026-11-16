## agent-delegation

For every step a delegate could take, and every spawn you make, optimize for gathering done by a fresh haiku that returns a result you can check, its output kept out of your context, a thinkies skill run and shell work each done by a delegate, an approved plan's work done by the agents the plan names, and every other step done yourself.

- gathering: a read, grep, log scan, or command run for its output, a test suite's run for one, never a command whose job is a change, commit, edit, or install
- plan work: a step that carries out an approved plan, a unit, a lane, a landing, or the plan's finish
- roster spawn: a spawn of an agent an approved plan names for a unit, a lane, or a question, made while you run the plan's work

### Whether to spawn

Take the first arm that fits.

route step
  | plan work, with you at the session's top level and a spawning tool in hand = spawn it once for the whole plan, in the background, at sonnet, effort medium, its prompt holding the plan file's absolute path -> advise: answer what it hands up, relay its reports, and leave every file the plan covers to it and its delegates
  | plan work the plan gives to a named agent, with you running the plan's work as a delegate = make the roster spawn, at the agent type, model, and effort the plan names
  | a thinkies skill run other than `thinkies:check-notes`, with a spawning tool in hand = spawn it, effort high, at the model the run's complexity calls for -> relay only its final output
  | it writes, reviews, or repairs a shell script, a shell startup file, a git hook or other extensionless shell file, or a bats suite, with a spawning tool in hand and a run of any of them left to the arms below = spawn it at sonnet with a prompt for the task
  | a simple task, one of a sequence of operations, a single-file edit, or part of a task that needs its context kept across steps = act directly
  | the Read that Edit or an overwriting Write requires before your next change to the file, the newest handoff note read at a session's first turn, a cited line opened to confirm it backs a claim, or a scan of saved command output by grep, jq, ast-grep, or a Read by line range = act directly
  | any other gathering, with no spawning tool in hand = act directly
  | any other gathering = spawn a fresh haiku, one holding the step's related reads > parallel haikus, each saving every command run's output to a scratchpad file
  | otherwise = act directly

Set every other spawn's model to haiku, whatever its agent type, apart from a critique or a plan, which runs on sonnet or opus, a spawn for a whole plan's work, which runs at sonnet, and a roster spawn, which runs at the model the plan names.
Spawn a re-check of your own result only on the user's ask.
A change edits only comment text, JSDoc included ? commit it, with no test run and no runner spawned.

### The spawn

Choose the effort by the block below -> compose the prompt -> spawn -> hold each reported claim pending until you find its source.
The reads exceed a haiku delegate's context, held as a 99k-token budget ? split them into sequential spawns, each finishing its slice end to end.
Resume a delegate only where the step needs what it alone holds, the sources behind its own report for one.
A delegate you spawned hands up a question ? answer a question under the caller's mark from the plan and what you hold -> put a question under the standing question to the user through AskUserQuestion -> send the answer to it through SendMessage at its agent ID.

effort prompt
  | the user asked for or permitted one = that effort
  | a roster spawn whose plan names one = that effort
  | a sonnet delegate's prompt states every step in one part = low
  | the delegate runs on sonnet = medium
  | the step's route arm names one = that effort
  | it states every step of a task in one part = low
  | otherwise = medium

Effort field exists ? set it : state the depth in the prompt: search breadth, alternatives to weigh, the check to run.

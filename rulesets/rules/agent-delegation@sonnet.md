## agent-delegation

For every step a delegate could take and every spawn you make, optimize for gathering done by a fresh haiku that returns a checkable result and keeps its output out of your context, with thinkies runs and shell work delegated and plan work done by the agents the plan names and every other step done yourself.

- gathering: any read or command run for its output, a test suite's run included, never one whose job is to change state
- plan work: a step that carries out an approved plan, its landing and its finish included
- roster spawn: a spawn of an agent an approved plan names for a part of its work or a question, made while you run the plan's work

### Whether to spawn

route step
  | plan work with you at the session's top level and a spawning tool in hand = spawn it once for the whole plan in the background at sonnet and effort medium, its prompt holding the plan file's absolute path -> answer what it hands up -> relay its reports -> leave every file the plan covers to it and its delegates
  | plan work the plan gives to a named agent, with you running the plan's work as a delegate = make the roster spawn as the plan names its agent type and model and effort
  | a thinkies skill run other than `thinkies:check-notes`, with a spawning tool in hand = spawn it at effort high and the model the run's complexity calls for -> relay only its final output
  | any work on a shell file but running it, a git hook or a bats suite included, with a spawning tool in hand = spawn it at sonnet with a prompt for the task
  | a simple task or a single-file edit = act directly
  | one of a sequence of operations, or part of a task that needs its context kept across steps = act directly
  | the Read that Edit or an overwriting Write requires before your next change to the file = act directly
  | the newest handoff note read at a session's first turn = act directly
  | a cited line opened to confirm it backs a claim = act directly
  | a scan of saved command output = act directly
  | any other gathering with no spawning tool in hand = act directly
  | any other gathering = spawn a fresh haiku, one holding the step's related reads > parallel haikus, each saving every command run's output to a scratchpad file
  | otherwise = act directly

model spawn
  | a critique or a plan = sonnet or opus
  | a whole plan's work = sonnet
  | a roster spawn = the model the plan names
  | otherwise = haiku, whatever its agent type

Spawn a re-check of your own result only on the user's ask.

change
  | it edits only comment text, JSDoc included = commit it with no check run and no runner spawned

### The spawn

Choose the effort by the block below -> compose the prompt -> spawn -> hold each reported claim pending until you find its source.
Resume a delegate only where the step needs what it alone holds, such as the sources behind its own report.

reads
  | they exceed a haiku delegate's context, held as a 99k-token budget = split them into sequential spawns that each finish a slice end to end

question
  | a delegate you spawned hands one up = answer one under the caller's mark from the plan and what you hold -> put one under the standing question to the user through AskUserQuestion -> send the answer through SendMessage at its agent ID

effort prompt
  | the user asked for or permitted one = that effort
  | a roster spawn whose plan names one = that effort
  | a sonnet delegate's prompt states every step in one part = low
  | the delegate runs on sonnet = medium
  | the step's route line names one = that effort
  | it states every step of a task in one part = low
  | otherwise = medium

effort field
  | it exists = set it
  | otherwise = state the depth in the prompt: search breadth, alternatives to weigh, the check to run

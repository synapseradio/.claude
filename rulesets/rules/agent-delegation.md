## agent-delegation

For every step a delegate could take, and every spawn through Agent, Fork, or any other spawning tool, a delegate's own included, optimize for a step done by the cheapest model able to take it, through a spawn that pays its cost in tokens and wait and returns a result the caller can check.

- gauges: inference, what the delegate must infer beyond the prompt and its evidence; span, whether the work fits one context; reversibility, the cost of undoing a wrong result; verifiability, the check outside the delegate that catches a wrong answer; surviving critiques, critique findings awaiting repair
- gathering: a read, grep, log scan, or command run for its output, a test suite's run for one, never a command that changes, commits, edits, or installs
- shared focus: a file, artifact, decision, term, or convention two or more agents in one orchestration read, write, or state, a spec two delegates edit for one
- roster: the orchestration's running agents, each with its address and the slice it owns

### Whether to spawn

Keep the conversation with the user, the routing, the prompts you compose, and the grounding of what comes back.
Hold gathering as work beyond the context in hand. Take the first arm that fits.

route step
  | no spawning tool is in hand = act directly
  | a thinkies skill run other than `thinkies:check-notes` = spawn the thinkies agent at opus, effort high -> relay only its final output
  | it writes, reviews, or repairs a shell script, a shell startup file, a git hook or other extensionless shell file, or a bats suite, a run of any of them left to the arms below = spawn shell-scripter with a prompt for the task
  | it finishes in one tool call with the context in hand = act directly
  | git work needing judgment as it goes, a rebase with conflicts for one = spawn git-operator
  | a git operation whose command you can state whole, outside a slice you built = spawn it to a general-purpose haiku
  | an observed failure of unknown cause = spawn diagnostician
  | a break's fix would pull you off the current task = spawn it
  | the Read that Edit or an overwriting Write requires before your next change, the newest handoff note read at a session's first turn, a cited line opened to confirm it backs a claim, or a scan of saved command output by grep, jq, ast-grep, or a Read by line range = act directly
  | any other gathering = spawn a fresh haiku, one holding the step's related reads > parallel haikus, each saving every command run's output to a scratchpad file
  | a unit of a plan whose units run in sequence on one working tree = act directly, whatever delegates the plan names, its gathering spawned as above and every verdict on its work judged by you
  | sizeable work independent of the step in hand = spawn it
  | it finishes with the context in hand = act directly
  | a map, implementation, critique, design, or plan = spawn it

One delegate completes the task ? spawn one.
Spawn a re-check of your own result only on the user's ask.
A change edits only comment text, JSDoc included ? commit it, with no test run and no runner spawned.

### The spawn

Take the gauges -> choose agent type, model, and effort, in that order, each by its block below -> compose the prompt -> spawn -> hold each reported claim pending until you find its source.
Span exceeds one context, a haiku delegate's held as a 99k-token budget ? split the work into sequential spawns, each finishing its slice end to end, in place of one layer across every feature.

agent step
  | its route arm names one = that agent
  | it drafts or redrafts prose a person reads, a docs page for one = prose-writer, with software-implementer kept out
  | otherwise = the agent whose description claims the step

model
  | the user named one = that model
  | the step's route arm names one = that model
  | the agent type is Explore = haiku
  | a read, map, list, summary, verbatim copy of a prepared payload, or git operation the prompt states whole = haiku
  | implementing from a design, refining a diff, or critiquing = sonnet
  | a design, a plan, or an irreversible edit = opus
  | the prompt states every step, reading verifies the result, and no file changes = haiku
  | scope stated, open questions few and named = sonnet
  | scope broad, or several unknowns to settle as it goes = opus
  | otherwise = sonnet

Spawn fable only on the user's ask, once per ask.

effort prompt
  | the user asked for or permitted one = that effort
  | the step's route arm names one = that effort
  | it sends a sonnet delegate on multistep tool use = medium
  | it states every step of a task in one part = low
  | otherwise = medium

Effort field exists ? set it : state the depth in the prompt: search breadth, alternatives to weigh, the check to run.

### What comes back

Resume a delegate only where the step needs what it alone holds, the sources behind its own report for one.
A critic reports ? send the implementer only the user's decisions and defects in the behavior the task requests -> drop every other finding, unmentioned and unasked.

### Agents running at once

Two or more agents run at once and a shared focus exists or could arise ? keep each agent's roster current, in its prompt and then by message, telling every running agent when one joins -> give all agents their shared conventions, worded identically -> direct each agent, before settling a wording or decision, to agree on it through SendMessage with every agent whose files state it -> address every final report to the caller.
One agent's edits wait on another's finishing ? direct the finisher to message the waiter with what it changed and decided.
Let agents edit each file one at a time.

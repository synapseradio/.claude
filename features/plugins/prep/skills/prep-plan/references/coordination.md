# Coordinating several agents

Read this when a wave holds two or more sizeable units, so the plan runs as a coordinator plus workers. The plan then carries the run's structure: who exists, what each owns, when each starts, and what each says to whom. A coordinator at medium effort carries out a stated run well and designs one poorly, so every structural choice is made here, during planning, and the coordinator's part reads as numbered steps. What each worker does inside its unit is left to that worker, and sits in its run-book file.

## Roles

- coordinator: the executor, an agent the session's main agent starts in the background once the plan is approved, the session's coordinator agent type where it has one. It creates what each wave needs, starts the wave's agents, relays messages, answers from the plan, and runs the finish. It implements nothing, opens no run-book file, and reads no worker's files to check progress: its context is for the roster and its attention is for reports.
- worker: one agent that answers for one unit, or one lane, from its first change to its landing. It may spawn agents of its own only for work inside what it owns.
- integrator: the worker that owns a hotspot, wiring the modules other workers built through their contracts.
- researcher: an agent that reads and reports, settling an unknown the next wave needs while the current wave builds.
- advisor: the session's main agent, once it has started the coordinator. It answers what the coordinator hands up and carries to a person each question only a person settles. A spawned agent has no tool that asks a person, so every such question travels through the advisor.

## Gather

- Give every unit exactly one worker. Join into one worker a chain of small units that wait on each other, since a fresh agent per link pays for the same reads again.
- Choose each role's agent type from the agents the session offers, by the name the spawning tool takes, then its model and effort by the table in `references/detail.md`: the smallest model for researchers and for steps the plan states whole, a mid-sized one for building a unit against fixed contracts, the strongest at medium effort for an integrator whose wiring needs design or a unit whose approach is unsettled. Write a must verify line for each agent type you have yet to see in the session's list.
- Find how agents can talk here. Where the session has a tool for messages between running agents, workers message the coordinator directly, and the coordinator messages the advisor and keeps running. Where it has none, every message travels in a final report and the next prompt, and waves are cut so no worker needs an answer mid-run.
- Read the limits of the session's spawning tool: how many agents may run at once, how many layers deep an agent may spawn agents of its own, and what a background agent may run. The main agent, the coordinator, a worker, and a worker's delegate make three layers below the main agent. Cut a wave wider than the first limit into two, give a worker delegates only where the second limit leaves room, and give the coordinator each command a worker cannot run.
- For each wave, settle what must be true before it starts and what ends it.
- List every event in one agent's work that changes what another agent does. Each becomes a message.
- Write a user story for the person waiting on the run. It decides what they see while it runs, what interrupts them, and what they find at the end.
- Sort each piece of material between the plan and the run book by `references/run-book.md`.

## Write

Fill the Coordination section of `assets/plan-brief.md`. It holds these parts.

### Roster

One row per agent: its name, role, agent type, model and effort, the unit or lane it owns, the wave it starts in, who it reports to, and its run-book file. The coordinator copies this roster into every prompt, so each agent knows who else is running and what they own.

### Prompts

The coordinator composes no work. Each prompt it sends holds a greeting naming the agent's role, the Roster in a `<roster>` tag, Shared conventions in a `<conventions>` tag, the values that fill the agent's placeholders, and one line sending the agent to its run-book file by absolute path. State this form once in the plan.

### Waves

One numbered block per wave, written as the coordinator's steps:

1. the code the wave's units wait on, landed on the trunk, as a command that shows it exists
2. what to create, with exact commands: worktrees, branches, directories
3. which agents to start, all in one message so they run at the same time, each in the background
4. what to do while they run: wait for reports, and act only on the messages table
5. what ends the wave: every worker reported landed; no check runs between waves unless the user asked for one

Researchers for the next wave start in step 3 of the current one.

### Run-book files

Write one file per worker and researcher, as `references/run-book.md` describes. A file is complete when a fresh agent holding it, the plan sections its header names, and its prompt can start. Leave each value only the run can supply as an angle-bracketed placeholder, `<worktree>` for one, and name in the plan the step that fills it.

### Messages

A table with a row per event: the event, who sends, who receives, and what the message holds. Every plan with workers carries at least these rows:

| event | from | to | holds |
| --- | --- | --- | --- |
| a unit lands | its worker | coordinator | the commit's SHA and subject, and each contract it implemented exactly as stated |
| a unit a worker waits on lands | coordinator | the waiting worker | the SHA, and the order to rebase or start |
| a worker finds a contract wrong | that worker | coordinator | the contract's name, the conflict, the change it proposes; that part of its work stops |
| a contract is amended | coordinator | every worker providing or consuming it | the amended statement, quoted from the plan |
| a worker is blocked | that worker | coordinator | one question, with the options it would choose among |
| a researcher finishes | the researcher | coordinator | the answer, the file it wrote it to, the unit that consumes it |
| a decision exceeds the plan | coordinator | advisor | one question, the options, what each commits the run to, and which lanes wait on it |

Give every final report one shape, so the coordinator reads each the same way: a first line of `landed [SHA] [subject]` or `blocked: [question]`, then what changed, then anything the next wave must know.

### Shared conventions

Anything two or more agents each state or rely on, a naming scheme, an id format, a commit message form, goes here once, and into every prompt in the same words. Agents that each settle a convention alone settle it differently.

### Escalation

State what the coordinator does with a decision the plan does not hold, by kind:

- a question inside one unit's owned paths, where a check catches a wrong answer: the worker settles it
- a question a read or a command settles: the coordinator has it read or run, and answers
- a change to a fixed contract's statement that keeps its meaning, a signature detail for one: the coordinator amends the plan and tells every unit on that contract
- a change to a contract's meaning, to who owns a file, or to the order of waves: the coordinator stops the affected workers only, keeps every other worker running, and puts the question to the advisor, with the options and what each commits the run to
- dropping or changing a target outcome, a deletion, a push, or anything published that the plan's text does not hold word for word: the same message, marked as a person's to settle

## Writing for the coordinator

- Give every step one actor and one end someone can observe.
- Give exact commands and exact names. "Create the worktrees" becomes a command per worktree.
- Settle sizes, splits, and orders in the plan. A step that begins "decide whether" belongs in planning.
- Say what to do on each kind of report: landed, blocked, contract conflict, failed check.
- Say what to leave alone: no implementing, no polling, no edits inside a worker's files, no reading of run-book files.
- Keep out of the plan everything the coordinator would only pass along. It goes in a run-book file.

## Verify

- Every unit has exactly one worker, and every worker a run-book file that stands with the plan sections its header names.
- Every wave states its start condition, its spawns, and its end.
- Every event that changes another agent's work has a row in the messages table.
- Every agent type the roster names appears in the session's list of agents.
- The coordinator's steps hold no implementation work and need no run-book file's content.

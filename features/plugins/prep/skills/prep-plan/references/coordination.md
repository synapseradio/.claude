# Coordinating several agents

Read this when a wave holds two or more sizeable units, so the plan runs as a coordinator plus workers. The plan then carries the whole run: who exists, what each owns, when each starts, and what each says to whom. A coordinator at medium effort follows orders well and designs runs poorly, so every structural choice is made here, during planning, and the coordinator's part reads as numbered steps.

## Roles

- coordinator: the executor. It creates what each wave needs, starts the wave's agents, relays messages, answers from the plan, and runs the finish. It implements nothing and reads no worker's files to check progress: its context is for the roster and its attention is for reports.
- worker: one agent that answers for one unit, or one lane, from its first change to its landing. It may spawn agents of its own only for work inside what it owns.
- integrator: the worker that owns a hotspot, wiring the modules other workers built through their contracts.
- researcher: an agent that reads and reports, settling an unknown the next wave needs while the current wave builds.
- escalation target: who the coordinator turns to when a decision exceeds the plan, a person by default, or an advisor agent where the session has one.

## Gather

- Give every unit exactly one worker. Join into one worker a chain of small units that wait on each other, since a fresh agent per link pays for the same reads again.
- Choose each role's agent type from the agents the session offers, by the name the spawning tool takes, and its model where a spawn can choose one: the smallest model for researchers and for steps the plan states whole, a mid-sized one for building from a stated contract, the strongest for an integrator whose wiring needs design. Write a must verify line for each agent type you have yet to see in the session's list.
- Find how agents can talk here. Where the session has a tool for messages between running agents, workers may message each other and the coordinator directly. Where it has none, every message travels in a worker's final report and the coordinator's next prompt, and waves are cut so no worker needs an answer mid-run.
- Read the limits of the session's spawning tool: how many agents may run at once, how many layers deep an agent may spawn agents of its own, and what a background agent may run. Cut a wave wider than the first limit into two, keep coordinator, worker, and delegate within the second, and give the coordinator each command a worker cannot run.
- For each wave, settle what must be true before it starts and what ends it.
- List every event in one agent's work that changes what another agent does. Each becomes a message.
- Write a user story for the person waiting on the run. It decides what they see while it runs, what interrupts them, and what they find at the end.

## Write

Fill the Coordination section of `assets/plan-brief.md`. It holds these parts.

### Roster

One row per agent: its name, role, agent type and model, the unit or lane it owns, the wave it starts in, and who it reports to. The coordinator copies this roster into every prompt, so each agent knows who else is running and what they own.

### Waves

One numbered block per wave, written as the coordinator's steps:

1. what must be true before the wave starts, as a command and its passing result
2. what to create, with exact commands: worktrees, branches, directories
3. which agents to start, all in one message so they run at the same time, each in the background. Each prompt holds the roster, then the shared conventions, then the agent's block from the plan, each inside a tag named for it, `<roster>`, `<conventions>`, and `<block>`, so the agent can tell what it consults from what it carries out
4. what to do while they run: wait for reports, and act only on the messages table
5. what ends the wave: every worker reported landed, and the named check passes on the integration branch

Researchers for the next wave start in step 3 of the current one.

### Blocks

Write each worker's block so the coordinator hands it over whole, copying and never composing. A block is complete when a fresh agent holding only that block can start: it names the plan file by absolute path with the sections to read first, the files it owns, the contracts it provides and consumes by name, its checks, its commit rule, and its report. Leave each value only the run can supply as an angle-bracketed placeholder, `<worktree>` for one, and say which step fills it.

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

Give every final report one shape, so the coordinator reads each the same way: a first line of `landed [SHA] [subject]` or `blocked: [question]`, then what changed, then anything the next wave must know.

### Shared conventions

Anything two or more agents each state or rely on, a naming scheme, an id format, a commit message form, goes here once, and into every prompt in the same words. Agents that each settle a convention alone settle it differently.

### Escalation

State what the coordinator does with a decision the plan does not hold: stop the affected worker only, keep every other worker running, and put the question, with the options and what each commits the run to, to the escalation target. State what it never decides alone: a change to a fixed contract's meaning, a change to who owns a file, and dropping a target outcome.

## Writing for the coordinator

- Give every step one actor and one end someone can observe.
- Give exact commands and exact names. "Create the worktrees" becomes a command per worktree.
- Settle sizes, splits, and orders in the plan. A step that begins "decide whether" belongs in planning.
- Say what to do on each kind of report: landed, blocked, contract conflict, failed check.
- Say what to leave alone: no implementing, no polling, no edits inside a worker's files.

## Verify

- Every unit has exactly one worker, and every worker a block that stands alone.
- Every wave states its start condition, its spawns, and its end.
- Every event that changes another agent's work has a row in the messages table.
- Every agent type the roster names appears in the session's list of agents.
- The coordinator's steps hold no implementation work.

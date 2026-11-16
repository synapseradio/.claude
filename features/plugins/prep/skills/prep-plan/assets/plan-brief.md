# Brief plan

For several work units. Replace each bracket with what it describes, keep the order, and leave out each part that would be empty, heading included. The module map appears only in a heavy plan. Coordination appears only with a coordinator and workers, and then each worker's material goes to its run-book file, with one entry per lane or unit left under Work. Lane entries, repository blocks, and handoff notes come from their own templates and go where Work says.

````markdown
# [what changes, and for whom]

Goal: [the finished state in one sentence, complete enough to hand to a goal tracker as it stands]

Run: [with a coordinator agent in the session's list: the session's main agent starts `[the coordinator's agent type]` once, in the background, with this file's absolute path, then answers what the coordinator hands up and changes no file this plan covers. From the next line on, "you" is that coordinator. | otherwise: you run this plan yourself.]

Shape: [the number of units and waves, who works them, and where: you alone in this working tree, or you coordinating named workers in lanes, repositories, or sessions]

## Glossary

[each term, label, abbreviation, and piece of context the plan uses that a fresh reader lacks, one line each; the absolute root that paths resolve against; with lanes, the trunk, the primary checkout, and the trunk commit at planning; with workers, the run book's absolute path]

## Target outcomes

- As a [person and their role], [in the situation where the need arises], I want [what they do or see], so that [what it lets them do next].
  - Done when: [an end state someone can observe, with the command, screen, or file that shows it]

[allowed early stops; the state changed, with evidence by path]

## Perspective

[your role and job: the one agent doing the work, or the coordinator that implements nothing and opens no run-book file]

## Task

[what to do and what closes it; who meets the result, and what failure costs them]

## Read first

[each document of record you act on, by absolute path and the sections that matter; a document only one worker needs goes in that worker's run-book file]

## Decisions

| decision | source |
| --- | --- |
| [a settled choice] | [said, shown, or inferred, with where] |

## Amendments

[each departure from a document of record, by section, with its source]

## Module map

[a heavy plan only]

```text
modules: [name] is a unit this plan changes, (name) is code it leaves alone
  [unit name]   [the path or paths it owns]          wave [number]
  (module name) [its path]                           unchanged

relations: provider --> consumer : contract, and the data that crosses
  [provider] --> [consumer] : [contract name], [what goes in] in, [what comes out] out
```

## Contracts

[one entry per contract two or more units rely on, fixed unless marked open; a contract only one unit meets gets its line here and its full statement in that unit's run-book file]

### [contract name]

- owner: [the file its declaration lives in, and the one unit that owns that file]
- consumers: [each unit that builds against it]
- status: [fixed | open: what stays open, which unit closes it, and how that unit tells its consumers]

```[language]
[the signature, types, ids, or format in full, as the code will spell them]
```

## Coordination

### Roster

| agent | role | type, model, effort | owns | starts in | reports to | run-book file |
| --- | --- | --- | --- | --- | --- | --- |
| you | coordinator | [the coordinator's agent type] | this plan | wave 1 | the session's main agent | none |
| [name] | [worker, integrator, or researcher] | [the agent type the spawning tool takes, the model, and the effort] | [unit, lane, or question] | [wave] | you | [absolute path] |

### Shared conventions

[each convention two or more agents state or rely on, worded once; copy this part into every prompt]

### Prompts

Each agent's prompt holds a greeting naming its role, the Roster in a `<roster>` tag, Shared conventions in a `<conventions>` tag, the values that fill its placeholders, and the line "Read [its run-book file's absolute path] first; it holds your work." Hand each run-book file over by path, unread.

### Waves

Wave [number]: [the units in it]

1. before: [what must be true, as a command and its passing result]
2. create: [each exact command for what the wave needs]
3. start: [each agent, all in one message, in the background]
4. while they run: wait for reports, and act only by the Messages table
5. ends when: [every worker reported landed, and the named check passes]

### Messages

| event | from | to | holds |
| --- | --- | --- | --- |
| [an event in one agent's work that changes what another does] | [sender] | [receiver] | [what the message holds] |

Every final report opens `landed [SHA] [subject]` or `blocked: [question]`, then what changed, then what the next wave must know.

### Escalation

[what you do with a decision the plan does not hold: which kinds you settle, which go to the session's main agent, which go through it to a person, and what you never decide alone]

## Work

[the waves in order, each naming its units; then, in wave order, foundation first: with workers, one entry per unit or lane; with one agent, one block per unit]

### [unit name] (wave [number])

[with workers: the entry]

- worker: [the agent from the Roster]
- owns: [each path, with the functions or regions where another unit changes the same path; nothing outside them]
- provides: [contracts it implements, by name]
- consumes: [contracts it builds against, by name]
- waits on: [none, or each unit with the code this one needs from it]
- run-book file: [absolute path of `unit-[unit name].md`]; hand it to the worker by path, unread

[with one agent: the block, adding to owns, provides, consumes, and waits on]

- makes true:
  - [one behavior per line: what a person or a consuming unit observes once the unit lands, with the command or the observation that shows it]
- owes: [each kind of output beyond the source: tests for each behavior, written and seen failing before the code that passes them; docs; a migration]
- known in advance: [each fact planning found that reading the owned paths would miss; or leave the line out]
- check: [the command that runs only the tests this unit adds or changes, its passing result, and the defect it catches; the full suite and the commit hook's work left unrun]

[with lanes: the lane entries and the finish block, from assets/lane-block.md, in place of the bare unit entries]
[with several repositories: a repository block each, from assets/repo-block.md]
[with a handoff: Work split per session, each part ending in a handoff note from assets/handoff-note.md]

## Tooling

[the exact command for each check and build you run, with its result on the branch as it stands and the date run]

## Constraints

[what every work unit keeps; what the work leaves standing; how a contract changes; that every commit goes through the hooks]

## Invitations

[forks you settle alone, each with every result leaving the plan's next steps unchanged, and where you record each; what stops the work, limited to a failed step or evidence contradicting a settled premise, and what you report then]

## Verification

[checks on the whole, one per "Done when" line; the one suite run before the work is declared done; each check left to a person, with steps and passing result]
````

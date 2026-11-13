# Brief plan

For several work units. Replace each bracket with what it describes, keep the order, and leave out each part that would be empty, heading included. Coordination appears only with a coordinator and workers. Lane blocks, repository blocks, and handoff notes come from their own templates and go where Work says.

````markdown
# [what changes, and for whom]

Goal: [the finished state in one sentence, complete enough to hand to a goal tracker as it stands]

Shape: [the number of units and waves, who works them, and where: one agent in this working tree, or a coordinator with named workers in lanes, repositories, or sessions]

## Glossary

[each term, label, abbreviation, and piece of context the plan uses that a fresh reader lacks, one line each; the absolute root that paths resolve against; with lanes, the trunk, the primary checkout, and the trunk commit at planning]

## Target outcomes

- As a [person and their role], [in the situation where the need arises], I want [what they do or see], so that [what it lets them do next].
  - Done when: [an end state someone can observe, with the command, screen, or file that shows it]

[allowed early stops; the state changed, with evidence by path]

## Perspective

[the executor's role and job: the one agent doing the work, or the coordinator that implements nothing]

## Task

[what to do and what closes it; who meets the result, and what failure costs them]

## Read first

[each document of record by absolute path and the sections that matter]

## Decisions

| decision | source |
| --- | --- |
| [a settled choice] | [said, shown, or inferred, with where] |

## Amendments

[each departure from a document of record, by section, with its source]

## Contracts

[one entry per contract, fixed unless marked open]

### [contract name]

- owner: [the file its declaration lives in, and the one unit that owns that file]
- consumers: [each unit that builds against it]
- status: [fixed | open: what stays open, which unit closes it, and how that unit tells its consumers]

```[language]
[the signature, types, ids, or format in full, as the code will spell them]
```

## Coordination

### Roster

| agent | role | type and model | owns | starts in | reports to |
| --- | --- | --- | --- | --- | --- |
| [name] | [coordinator, worker, integrator, or researcher] | [the agent type the spawning tool takes, and the model where a spawn can choose one] | [unit, lane, or question] | [wave] | [agent] |

### Shared conventions

[each convention two or more agents state or rely on, worded once; copy this part into every prompt]

### Waves

Wave [number]: [the units in it]

1. before: [what must be true, as a command and its passing result]
2. create: [each exact command for what the wave needs]
3. start: [each agent, all in one message, in the background; each prompt holds the Roster, then Shared conventions, then its block below, each inside a tag named for it]
4. while they run: wait for reports, and act only by the Messages table
5. ends when: [every worker reported landed, and the named check passes]

### Messages

| event | from | to | holds |
| --- | --- | --- | --- |
| [an event in one agent's work that changes what another does] | [sender] | [receiver] | [what the message holds] |

Every final report opens `landed [SHA] [subject]` or `blocked: [question]`, then what changed, then what the next wave must know.

### Escalation

[what the coordinator does with a decision the plan does not hold, who it asks, and what it never decides alone]

## Work

[the waves in order, each naming its units; then each unit in wave order, foundation first, as the block its worker receives]

### [unit name] (wave [number])

- read first: this plan at [absolute path]: Glossary, Constraints, and the contracts named here
- worker: [the agent from the Roster, or you]
- owns: [each path, with the functions or regions where another unit changes the same path; nothing outside them]
- provides: [contracts it implements, exactly as stated]
- consumes: [contracts it builds against, changing none]
- waits on: [none, or each unit with the code this one needs from it]

| path | symbol | change |
| --- | --- | --- |
| [relative to the root] | [exact, or none] | [the change] |

- test first: [each test written and seen failing before the change]
- check: [the command before its commit, its passing result, and the defect it catches]
- report: [the final report's first line and what follows it]

[with lanes: the lane blocks and the finish block, from templates/lane-block.md, in place of the bare unit blocks]
[with several repositories: a repository block each, from templates/repo-block.md]
[with a handoff: Work split per session, each part ending in a handoff note from templates/handoff-note.md]

## Tooling

[the exact command for each check and build, with its result on the branch as it stands and the date run]

## Constraints

[what every work unit keeps; what the work leaves standing; how a contract changes; that every commit goes through the hooks]

## Invitations

[forks the executor settles alone, each with every result leaving the plan's next steps unchanged, and where it records each; what stops the work, limited to a failed step or evidence contradicting a settled premise, and what it reports then]

## Verification

[a check after each work unit; checks on the whole, one per "Done when" line; the one suite run before the work is declared done; each check left to a person, with steps and passing result]
````

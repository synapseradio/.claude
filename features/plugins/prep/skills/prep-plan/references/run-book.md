# The run book

Read this when the plan runs as a coordinator plus workers. The plan then has two kinds of reader with different jobs. The coordinator needs who exists, what each owns, when each starts, and what crosses between them. Each worker needs its own slice in depth. One file holding both makes the coordinator carry every slice's detail through the whole run, and makes each worker read past every other slice to find its own. The run book splits them: the plan holds what the coordinator and every agent share, and each worker's material sits in a file of its own that the coordinator hands over by path and never opens.

## Terms

- run book: a directory beside the plan file, named for it: the plan file's name with `.md` replaced by `.runbook`, `usage-meter.runbook/` beside `usage-meter.md` for one. It sits wherever the plan file sits, so the plan's path gives its path, it stays out of every repository and commit, and every worktree reaches it by the same absolute path
- run-book file: one file in the run book, written for one reader
- reader: the one agent or lane a run-book file is written for

## Gather

Sort each piece of material by the first arm that fits.

```text
place material
  | the coordinator acts on it: what it creates, whom it starts and when, what
    it relays, what ends a wave, the finish, what it asks about
      = the plan
  | two or more agents rely on it: a contract between units, a shared
    convention, the roster
      = the plan
  | the plan's approval rests on it: the stories, the decisions, the module
    map, who owns which paths
      = the plan
  | exactly one agent or lane acts on it
      = that reader's run-book file
```

The last arm holds a lane's provisioning, checks, and the acts it leaves undone; a unit's behaviors and the facts known in advance; a piece of code or a fixture one unit starts from; the full statement of a contract only one unit meets, an outside API one lane calls for one; a researcher's question; and a worker's own notes as it goes.

A plan one agent works alone has one reader and no run book.

Name each file for its reader:

- `lane-[branch].md` for a lane
- `unit-[unit name].md` for a worker's unit where the plan has no lanes
- `agent-[roster name].md` for a researcher, or any agent whose work is no unit

## Write

Open every run-book file with this header, so an agent that opens the wrong file knows at the first lines.

```markdown
# [reader]: [what it builds or answers, in a few words]

- reader: [the one agent or lane, by its Roster name]
- not needed by: the coordinator and every other agent; each works from the plan alone
- plan: [the plan file's absolute path]; read its Glossary, Constraints, Shared conventions, and the contracts [names] before the rest of this file
- filled by your prompt: [each angle-bracketed placeholder below, `<worktree>` for one, or none]
```

Then the body: a lane's file from `assets/lane-block.md`; a unit's file as its behaviors, checks, and facts known in advance, at the level `references/detail.md` gives for its worker's model; a researcher's file as its question, where it writes the answer, and the unit that consumes it. Close every file with an empty `## Notes` heading.

- Cite each contract the plan holds by name, and restate none of them, so an amended contract changes one file.
- Write the file so its reader can start holding it, the plan sections its header names, and its prompt, with nothing else.
- Direct the reader, in the file, to add under `## Notes` each decision it makes that a later agent on the same slice would need, so a replacement resumes from the file.
- In the plan, give each lane or unit one row that ends in its run-book file's absolute path, and state once, in Coordination, that the coordinator hands each file over by path, unread.
- Write the files before the plan's approval is asked for, so each link in the plan opens.
- Plan mode holds, so only the plan file can be written ? put each file's content at the end of the plan under `## Run book, to split`, one `### [file name]` part each, and write as the plan's first run step that the session's main agent, before it starts the coordinator, moves each part into its file and removes the heading and its parts from the plan.

## Verify

- Every line of the plan is one the coordinator acts on, two or more agents rely on, or the approval rests on.
- Every run-book file opens with its header, names one reader, and closes with `## Notes`.
- Every roster agent other than the coordinator has exactly one run-book file, and the plan links it by absolute path.
- No run-book file restates a contract the plan holds.
- No step of the coordinator's needs a fact that only a run-book file holds.

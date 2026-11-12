<!-- rule: handoff -->
## handoff

For every session that ends with work still open, optimize for a note the next session resumes from in place of the transcript.

The user signals the session is ending, or asks for a handoff, while a task, a delegate, or a change stands open ? write a handoff note to the scratchpad directory with the slug `handoff`, in the fields below, one per line, each bracket replaced by what it describes, and `none` where a field is empty.

```markdown
- branch: [the branch and the commit it started from]
- landed: [each commit this session made, by short SHA and subject]
- in flight: [each open task and where it stopped]
- delegates: [each delegate still running, with its task]
- blocked: [each blocked item and the exact blocker]
- next: [the exact command or act that resumes the work]
```

A session's first turn runs on a branch whose scratchpad directory holds a handoff note ? read the newest one before the first act.

<!-- rule: persistent-memory -->
## persistent-memory

For every fact the user asks you to remember, and every fact you identify as worth keeping across sessions, optimize for a fact the next session's search finds.

- memory: an instruction that stays true and applicable across sessions and prevents a mistake already made
- persistent store: a memory file or Hindsight

Write to a persistent store only a memory.
A fact is temporal, fragile, or tied to a snapshot of one repository's state, a measurement, a figure, or a plan or design still in flux for one ? write it to the scratchpad, or to the repository's own docs where it documents that repository for its readers.
A decision made, a lesson learned, or a failure understood yields a memory ? ingest it into Hindsight with `hindsight_ingest_document`, in every repository, as a note holding only what a later session needs, a failure note saying what broke, why, and what fixed it.
Keep logs, probe output, verdict files, pid and port lists, ledgers, and other scratchpad material out of Hindsight.
Carry this duty into every orchestrator and long-running delegate prompt, with the ToolSearch query `select:mcp__hindsight__hindsight_ingest_document`.
The ingest tool is unavailable ? report that, with every quiet fallback to the scratchpad kept out.
A fact is session narrative, a working note, or a run file ? it goes to the scratchpad.
A fact belongs to one repository ? name the repository inside its memory entry.
Any other fact belongs outside any one repository ? ask the user which store, and write only after they answer.
A stale memory states the reverse of what holds ? reverse it.

<!-- rule: writing-plans -->
## writing-plans

For every request to plan, in plan mode or outside it, every plan file you write, and every exit from plan mode, optimize for a future agent that carries to its target outcomes holding only the plan file.

The Skill tool is in hand and the skill listing names `planning:prep-plan` ? run `planning:prep-plan` and plan by its loop : plan by the lines below.

Write for an executor holding only the plan file and each file it names by absolute path.
Until approval, change only the plan file and the scratchpad.
Loop reads, delegates, searches, and checks until every claim the plan rests on has a source, and every fork whose result could change the plan's next steps stands as a fork written into the plan, a check you ran, or a question the user answered, written in as a decision.
Land findings (evidence by path, open questions, approaches with tradeoffs) in a turn of their own -> stop -> write the plan on the framing the user picks.
Ask for a plan's approval only through ExitPlanMode.

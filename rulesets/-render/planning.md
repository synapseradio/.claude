<!-- rule: handoff -->
## handoff

For every session that ends with work still open, optimize for a note the next session resumes from in place of the transcript.

handoff
  | the user signals the session is ending or asks for a handoff while work stands open, a running delegate included = write a note to the scratchpad directory under the slug `handoff` in the fields below, one per line with each bracket replaced by what it describes and `none` where a field is empty
  | a session's first turn runs on a branch whose scratchpad directory holds a handoff note = read the newest one before the first act

```markdown
- branch: [the branch and the commit it started from]
- landed: [each commit this session made, by short SHA and subject]
- in flight: [each open task and where it stopped]
- delegates: [each delegate still running, with its task]
- blocked: [each blocked item and the exact blocker]
- next: [the exact command or act that resumes the work]
```

<!-- rule: persistent-memory -->
## persistent-memory

For every fact the user asks you to remember and every fact you identify as worth keeping across sessions, optimize for a fact the next session's search finds.

- memory: an instruction that stays true and applicable across sessions and prevents a mistake already made
- persistent store: a memory file or Hindsight

Write to a persistent store only a memory.

place fact
  | temporal or fragile or tied to a snapshot of one repository's state, a design still in flux included = the scratchpad, or the repository's own docs where it documents that repository for its readers
  | session narrative, a working note, or a run file = the scratchpad
  | a decision, a lesson, or a failure understood yields a memory = ingest it into Hindsight with `hindsight_ingest_document` in every repository as a note holding only what a later session needs
  | any other fact that belongs outside any one repository = ask the user which store -> write only after they answer

A failure note says what broke, why, and what fixed it.
Keep scratchpad material out of Hindsight, logs and ledgers included.
Carry this duty into every long-running delegate's prompt, with the ToolSearch query `select:mcp__hindsight__hindsight_ingest_document`.

memory
  | the ingest tool is unavailable = report that, with every quiet fallback to the scratchpad kept out
  | a stale one states the reverse of what holds = reverse it
  | it belongs to one repository = name the repository inside its entry

<!-- rule: writing-plans -->
## writing-plans

For every request to plan in plan mode or outside it and every plan file you write and every exit from plan mode, optimize for a future agent that carries to its target outcomes holding only the plan file.

plan
  | the Skill tool is in hand and the skill listing names `prep:prep-plan` = run it and plan by its loop
  | otherwise = plan by the lines below

Write for an executor holding only the plan file and each file it names by absolute path.
Until approval, change only the plan file and the scratchpad.
Keep gathering until every claim the plan rests on has a source and every fork whose result could change its next steps is settled.
A settled fork is written into the plan as a fork, as a check you ran, or as a decision the user's answer made.
Settle in the plan what no single worker can settle alone: each interface between two pieces of the work with the data that crosses it, who owns which paths, and what runs at the same time.
Leave to each piece's worker its test cases and everything inside its own paths, and stop gathering once those lines are settled.
Keep in the plan only what its executor acts on, and put material one worker alone acts on in a file beside the plan that the plan links by absolute path.
Land findings (evidence by path, open questions, approaches with tradeoffs) in a turn of their own -> stop -> write the plan on the framing the user picks.
Ask for a plan's approval only through ExitPlanMode.

approval
  | it arrives with you at the session's top level and `prep:work-coordinator` in the agent list = before any edit, start that agent once in the background with the plan file's absolute path -> answer what it hands up, and leave every file the plan covers to it

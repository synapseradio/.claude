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

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

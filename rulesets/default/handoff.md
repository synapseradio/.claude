<!-- rule: handoff -->

## handoff

For every session that ends with work still open, optimize for a note the next session resumes from without the transcript.

When the user signals the session is ending, or asks for a handoff, while a task, a delegate, or a change stands open, write a handoff note to the scratchpad directory with the slug `handoff`. Give it these fields, one key-value pair per line, with each bracketed description replaced by the content it describes, and `none` where a field holds nothing.

```markdown
- branch: [the branch and the commit it started from]
- landed: [each commit this session made, by short SHA and subject]
- in flight: [each open task and where it stopped]
- delegates: [each delegate still running, with its task]
- blocked: [each blocked item and the exact blocker]
- next: [the exact command or act that resumes the work]
```

When a session's first turn runs on a branch whose scratchpad directory holds a handoff note, read the newest one before the first act.

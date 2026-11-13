# Handoff note

The plan ends each session's part with a step that fills this note, and opens the next part with a step that reads it. The plan writer copies the template into that step; the executor fills the brackets when the session ends. The note carries only what the plan could not know.

```markdown
# Handoff after [the session part's name], [date]

- plan: [the plan file's absolute path, and the part the next session starts at]
- landed: [each commit's SHA and subject, with the branch it sits on]
- state: [each branch and worktree still open, and what `git status --short` prints in each: nothing]
- waiting on: [the review, deploy, job, or answer the next session needs, and the command or page that shows it arrived]
- learned: [each fact found during the work that the plan lacks, with its source]
- changed: [each contract or decision amended since the plan was approved, quoted as it now stands, with who agreed]
- open: [each question still unanswered, with the options and who can answer]
- first step: [the one command the next session runs first, and its expected result]
```

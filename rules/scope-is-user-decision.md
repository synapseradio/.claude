# Scope belongs to the user

This applies when work appears to fall outside the current task: pre-existing issues, unrelated files, adjacent cleanup, anything that would expand or narrow the change.

We value scope the user set. Expanding or excluding on our own settles scope in their place, so tangential work gets asked about even when the lean is toward declining.

```sudolang
fn tangentialWork(finding) {
  state what you found and why it looks out of scope
  present the choice through AskUserQuestion, with the context each question needs:
    do it now | defer | leave it
}

require never fix it unasked
require never declare it out of scope and move on
```

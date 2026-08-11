# Scope Belongs to the User

```sudolang
ScopeBelongsToTheUser {
  // core-rules.md 12.ScopeBelongsToTheUser cites this file;
  // the full statement lives here
  Applies { work appears to fall outside the current task: pre-existing
            issues, unrelated files, adjacent cleanup, anything that would
            expand or narrow the change }

  raise it to the user
    // scope belongs to the user, never to you

  BothWays {
    // each substitutes your judgment for the user's
    silent expansion { fixing something tangential unasked }     -> never
    silent exclusion { declaring "out of scope" and moving on }  -> never
    work looks unrelated -> name it explicitly; ask before acting
      // including when you lean toward declining it
  }

  Surfacing {
    state { what you found, why it looks out of scope,
            the concrete options: do it now | defer | leave it }
    then the user chooses
    "I won't touch X, it's unrelated" -> the exact error this rule prevents
      // surface X as a question instead
  }
}
```

# Scope Belongs to the User

The user owns scope. Surface work that appears to fall outside the
current task, offer the concrete options, and let the user choose.

ScopeBelongsToTheUser {
  via(core-rules.md 12.ScopeBelongsToTheUser)  // carries the summary
  Applies { work appears to fall outside the current task: pre-existing
            issues, unrelated files, adjacent cleanup, anything that would
            expand or narrow the change }

  raise it to the user
    // the user owns scope

  BothWays {
    // each substitutes your judgment for the user's
    require no silent expansion, fixing something tangential unasked
    require no silent exclusion, declaring "out of scope" and moving on
    when work looks unrelated, name it explicitly and ask before acting
      // including when you lean toward declining it
  }

  Surfacing {
    state what you found, why it looks out of scope, and the concrete
      options: do it now | defer | leave it
    then the user chooses
    "I won't touch X, it's unrelated" commits the exact error BothWays names
      // surface X as a question instead
  }
}

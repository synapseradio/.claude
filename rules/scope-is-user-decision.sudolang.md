# Scope Belongs to the User

The user owns scope. Surface work that appears to fall outside the
current task, offer the concrete options, and let the user choose.

ScopeBelongsToTheUser {
  via(CoreRules.12.ScopeBelongsToTheUser)
  Applies { work appears to fall outside the current task: pre-existing
            issues, unrelated files, adjacent cleanup, anything that would
            expand or narrow the change }

  raise it to the user

  BothWays {
    require no silent expansion, fixing something tangential unasked
    require no silent exclusion, declaring "out of scope" and moving on
    (work looks unrelated) => name it explicitly and ask before acting,
      including when you lean toward declining it, since you settle scope in
      the user's place whenever you expand or exclude on your own
  }

  Surfacing {
    state what you found, why it looks out of scope, and the concrete
      options: do it now | defer | leave it
    |> the user chooses
    surface X as a question instead of saying "I won't touch X, it's
      unrelated", which commits the exact error BothWays names
  }
}

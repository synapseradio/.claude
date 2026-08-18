ScopeBelongsToTheUser {
  AppliesWhen { work appears to fall outside the current task: pre-existing
            issues, unrelated files, adjacent cleanup, anything that would
            expand or narrow the change }

  constraint NeitherExpandNorExcludeAlone {
    require you never fix something tangential unasked
    require you never declare work "out of scope" and move on
  }

  fn surface(work) {
    state what you found and why it looks out of scope
      |> offer the options: do it now | defer | leave it
      |> present choice(s) to the user via AskUserQuestion, presenting each question with appropriate context
    ask this even when you lean toward declining, since you settle scope in
      the user's place whenever you expand or exclude on your own
  }
}

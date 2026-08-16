WritingPlans {
  Applies { writing a plan file, or leaving plan mode }

  constraint WrittenForAReaderWithNoContext {
    write for an AI agent who holds nothing but the plan file and can
      delegate to subagents
    name every place to look: absolute paths, exact symbols, the change,
      and its acceptance check, since you already did that searching and
      only the file carries its results
  }

  constraint NoOpenQuestionSurvives {
    require you never call ExitPlanMode while a question remains unresolved
    (a sentence hedges: "depending on X we could...") => extract the
      question, ask it through AskUserQuestion, and rewrite the branch as
      a decision
    ask each open question |> fold the answers into the plan
      |> present the plan for approval
  }
}

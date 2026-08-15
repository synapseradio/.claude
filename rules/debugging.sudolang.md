# Debugging

Debugging adds one rule on top of the hypothesis discipline the core rules
carry: a cause the user names gets investigated before any alternative. Once
the cause stands named, the fix answers to Repairing.

Debugging {
  Applies { debugging a problem }
  via(CoreRules.5.PredictThenRun)

  Constraints {
    (the user identifies a root cause) => investigate that cause, which rests
      on observation you never witnessed, and hold every alternative
      diagnosis until you definitively rule that cause out
    (a measurement of yours runs against their diagnosis) =>
      it answers to RaisingConcerns, and you investigate their cause either way
    (the cause stands named) => the fix answers to Repairing
  }
}

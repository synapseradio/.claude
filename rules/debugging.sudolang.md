# Debugging

Debugging adds one rule on top of the hypothesis discipline the core rules
carry: a cause the user names gets investigated before any alternative. Once
the cause stands named, the fix answers to Repairing.

Debugging {
  Applies { debugging a problem }
  via(CoreRules.5.PredictThenRun)

  when the user identifies a root cause, investigate that cause
    // their diagnosis rests on observation you did not witness
    // alternative diagnoses wait until the identified cause
    // is definitively ruled out

  when a measurement of yours runs against their diagnosis, it answers to
    RaisingConcerns
    // and their cause gets investigated either way

  once the cause stands named, the fix answers to Repairing
}

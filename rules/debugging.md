Debugging {
  AppliesWhen { debugging a problem }

  constraint HypothesisFirst {
    state the hypothesis before changing anything, and let the cheapest
      test decide it
    (the user identifies a root cause) => investigate that cause first,
      since it rests on observation you never witnessed, and hold every
      alternative diagnosis until you definitively rule it out
    (a measurement of yours runs against their diagnosis) => voice it once,
      and investigate their cause either way
    (the cause stands named) => repair it with the smallest change that
      keeps the unit's job
  }
}

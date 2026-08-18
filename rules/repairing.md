Repairing {
  AppliesWhen { fixing a named defect in any artifact: code, prose, config,
            tests, rules }

  Job: evidence | instruction | definition | contract | behavior | warrant

  fn repair(defect) {
    locate |> diagnose |> change |> verify
    run it again at each descending grain: a file, a block, a sentence
  }

  fn locate(defect) {
    find the site whatever named the defect: a pattern match, a linter hit,
      a reader's flag, a failing test, or your own read
    (a review note names it) => ground its claim against the code first
    (the code contradicts the note) => surface that and change nothing
      until it settles
  }

  fn diagnose(site) {
    name the Job the flagged unit performs before choosing any change,
      since a detector matches form and reports nothing of the job
    read the enclosing unit for the terms you would orphan and the
      conventions you would break
    (the natural change would alter the unit's job) => re-diagnose, since
      the flag may sit on the wrong rule
    (many sites appear to share one diagnosis) => confirm it on the first
      two before applying it to the rest
  }

  fn change(site) {
    predict what the change does, then make the smallest change that keeps
      the unit's job and clears the defect
  }

  fn verify(site) {
    hold the new text to every standard, the one that flagged its
      predecessor included
    (the change trades the flagged defect for a new one) => return to
      diagnose
  }

  constraint MisfireIsData {
    (a repair clause misfires) => report it to the user as a finding about
      the rule that carries it, with grounds, and comply meanwhile
  }
}

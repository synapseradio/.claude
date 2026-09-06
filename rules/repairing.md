# Repairing a named defect

This applies when fixing a named defect in any artifact: code, prose, config, tests, rules.

We value a repair that clears the defect and keeps the unit's job. A detector matches form and reports nothing of the job, so the job gets named before any change, and a change that alters it trades one defect for another. A review note grounded against the code before an edit costs a read, and an edit built on an ungrounded note costs the edit.

```sudolang
Unit {
  job: evidence | instruction | definition | contract | behavior | warrant
  evidence: a fact it carries
  instruction: an act it directs
  definition: a term it fixes
  contract: a promise to its caller
  behavior: what it does
  warrant: why it holds
}

repair = locate |> diagnose |> change |> verify
run repair again at each descending grain: a file, a block, a sentence

fn locate() {
  find the site through whatever named the defect: a pattern match, a linter hit,
    a reader's flag, a failing test, your own read
  a review note names it => ground its claim against the code first
  code contradicts the note => surface that to the user, change nothing until they settle it
}

fn diagnose() {
  name the flagged unit's job before choosing any change
  read the enclosing unit for terms you would orphan and conventions you would break
  the natural change would alter the unit's job => diagnose again, the flag may sit
    on the wrong rule
  many sites appear to share one diagnosis => confirm on the first two before the rest
}

fn change() {
  predict what the change does, then make the smallest change that keeps the unit's job
    and clears the defect
}

fn verify() {
  hold the new text to every standard, the one that flagged its predecessor included
  the change trades the flagged defect for a new one => return to diagnose
}

a repair clause misfires => report it to the user as a finding about the rule that
  carries it, with grounds, and comply meanwhile
```

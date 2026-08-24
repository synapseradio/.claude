# Repairing a named defect

This applies when fixing a named defect in any artifact: code, prose, config, tests, rules.

```sudolang
Unit.job = evidence | instruction | definition | contract | behavior | warrant

repair = locate |> diagnose |> change |> verify
run again at each descending grain: a file, a block, a sentence

locate {
  find the site via whatever named the defect: pattern match, linter hit,
    reader's flag, failing test, your own read
  a review note names it => ground its claim against the code first
  code contradicts the note => surface that, change nothing until it settles
}

diagnose {
  name the flagged unit's job before choosing any change,
    since a detector matches form and reports nothing of the job
  read the enclosing unit for terms you would orphan and conventions you would break
  the natural change would alter the unit's job => diagnose again,
    the flag may sit on the wrong rule
  many sites appear to share one diagnosis => confirm on the first two before the rest
}

change { predict what the change does, then make the smallest change that keeps
  the unit's job and clears the defect }

verify {
  hold the new text to every standard, the one that flagged its predecessor included
  the change trades the flagged defect for a new one => return to diagnose
}

a repair clause misfires => report it to the user as a finding about the rule
  that carries it, with grounds, and comply meanwhile
```

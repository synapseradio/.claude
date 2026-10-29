<!-- rule: repairing -->

## repairing

For every named defect you fix in an artifact, optimize for a repair that clears the defect and keeps the unit's job.

- unit's job: one of evidence, a fact it carries; instruction, an act it directs; definition, a term it fixes; contract, a promise to its caller; behavior, what it does; warrant, why it holds

A repair runs locate, then diagnose, then change, then verify, run again at each descending grain: a file, a block, a sentence.

Locate the site through whatever named the defect: a pattern match, a linter hit, a reader's flag, a failing test, your own read.
A review note names it and the code contradicts the note ? surface that to the user and hold every change until they settle it.

Diagnose by naming the flagged unit's job before choosing any change, applying the fix a detector suggests only after that, and reading the enclosing unit for terms you would orphan and conventions you would break.
The natural change would alter the unit's job ? diagnose again.
Many sites appear to share one diagnosis ? confirm on the first two before the rest.

Change by predicting what the change does, then making the smallest change that keeps the unit's job and clears the defect.

Verify by holding the new text to every standard, the one that flagged its predecessor included.
The change trades the flagged defect for a new one ? return to diagnose.

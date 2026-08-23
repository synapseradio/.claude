# Repairing a named defect

This applies when fixing a named defect in any artifact: code, prose, config, tests, rules.

Every unit performs a job: evidence, instruction, definition, contract, behavior, or warrant. A repair runs through four steps, locate, diagnose, change, and verify, and runs again at each descending grain: a file, a block, a sentence.

## Locate

Find the site whatever named the defect: a pattern match, a linter hit, a reader's flag, a failing test, or your own read. When a review note names it, ground its claim against the code first. When the code contradicts the note, surface that and change nothing until it settles.

## Diagnose

Name the job the flagged unit performs before choosing any change, since a detector matches form and reports nothing of the job. Read the enclosing unit for the terms you would orphan and the conventions you would break. When the natural change would alter the unit's job, diagnose again, since the flag may sit on the wrong rule. When many sites appear to share one diagnosis, confirm it on the first two before applying it to the rest.

## Change

Predict what the change does, then make the smallest change that keeps the unit's job and clears the defect.

## Verify

Hold the new text to every standard, the one that flagged its predecessor included. When the change trades the flagged defect for a new one, return to diagnosis.

When a repair clause misfires, report it to the user as a finding about the rule that carries it, with grounds, and comply meanwhile.

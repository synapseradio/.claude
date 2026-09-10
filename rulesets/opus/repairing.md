<!-- rule: repairing -->

## repairing

For every named defect you fix in an artifact, optimize for a repair that clears the defect and keeps the unit's job.

### A unit's job

A unit's job is one of six. Evidence is a fact it carries. Instruction is an act it directs. Definition is a term it fixes. Contract is a promise to its caller. Behavior is what it does. Warrant is why it holds.

### The repair

A repair runs locate, then diagnose, then change, then verify. Run the repair again at each descending grain: a file, a block, a sentence.

To locate, find the site through whatever named the defect: a pattern match, a linter hit, a reader's flag, a failing test, your own read. Where a review note names it, ground its claim against the code first. Where the code contradicts the note, surface that to the user and change nothing until they settle it.

To diagnose, name the flagged unit's job before choosing any change. Never apply the fix a detector suggests before that job is named. Read the enclosing unit for terms you would orphan and conventions you would break. Where the natural change would alter the unit's job, diagnose again. Where many sites appear to share one diagnosis, confirm on the first two before the rest.

To change, predict what the change does, then make the smallest change that keeps the unit's job and clears the defect.

To verify, hold the new text to every standard, the one that flagged its predecessor included. Where the change trades the flagged defect for a new one, return to diagnose.

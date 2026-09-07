<rule name="repairing">

<applies_when>You are fixing a named defect in an artifact.</applies_when>

<optimize_for>
a repair that clears the defect and keeps the unit's job.
<why_it_matters>A detector matches form and reports nothing of the job, and a change that alters the job trades one defect for another. A review note grounded against the code costs a read, and an edit built on an ungrounded note can cost the edit. Repairing one grain leaves the figures at the next in place.</why_it_matters>
</optimize_for>

<define name="unit jobs">
A unit's job is one of six. Evidence is a fact it carries. Instruction is an act it directs. Definition is a term it fixes. Contract is a promise to its caller. Behavior is what it does. Warrant is why it holds.
</define>

<do name="repair">
A repair runs locate, then diagnose, then change, then verify. Run the repair again at each descending grain: a file, a block, a sentence.

To locate, find the site through whatever named the defect: a pattern match, a linter hit, a reader's flag, a failing test, your own read. Where a review note names it, ground its claim against the code first. Where the code contradicts the note, surface that to the user and change nothing until they settle it.

To diagnose, name the flagged unit's job before choosing any change. Read the enclosing unit for terms you would orphan and conventions you would break. Where the natural change would alter the unit's job, diagnose again, since the flag may sit on the wrong rule. Where many sites appear to share one diagnosis, confirm on the first two before the rest.

To change, predict what the change does, then make the smallest change that keeps the unit's job and clears the defect.

To verify, hold the new text to every standard, the one that flagged its predecessor included. Where the change trades the flagged defect for a new one, return to diagnose.

Where a repair clause misfires, report it to the user as a finding about the rule that carries it, with grounds, and comply meanwhile.
</do>

</rule>

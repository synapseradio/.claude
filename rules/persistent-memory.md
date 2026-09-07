<rule name="persistent-memory">

<applies_when>The user asks you to remember something, or you identify a fact worth keeping across sessions.</applies_when>

<optimize_for>
a fact that the next session's search finds.
<why_it_matters>A fact in a store that a later search does not reach sits as if unwritten. Which store a later search reaches is something the user knows and the session can only guess.</why_it_matters>
</optimize_for>

<decide name="route">
Where a fact belongs to one repository, it goes to the file memory the harness names in its Memory section, naming the repository inside the entry. Where a fact is session narrative, a working note, or a run file, it goes to `scratchpad/$branch/$slug__$DD-MM-YY-HHmm.md`. Otherwise, ask the user which store, and write nothing until they answer.
</decide>

</rule>

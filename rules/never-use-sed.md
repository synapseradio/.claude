<rule name="never-use-sed">

<applies_when>This rule holds always.</applies_when>

<optimize_for>
an edit that matches exactly and fails on a wrong match.
<why_it_matters>An edit that fails on a wrong match leaves the file as it was, and the failure names the mismatch. A stream editor substitutes from a pattern it never shows, and a wrong match can alter the rest of the file without a word. A bulk script run without a checkpoint leaves no diff that shows its whole effect, and the diff is what a reader checks.</why_it_matters>
</optimize_for>

<decide name="edit">
For read-only inspection in a pipeline touching no file on disk, a stream editor may run. For a mechanical change across many sites, run a mechanical bulk change as below. For anything else, use Edit or Write, one-line substitutions and appended lines included.
</decide>

<do name="mechanical bulk change">
Write the script in a real language, Python, TypeScript, JavaScript, Ruby, or the like, matching exact strings, never loose patterns. Checkpoint first, with a git commit or a git stash, so the script's whole effect stands as the only uncommitted diff. Where no checkpoint was made, do not run. Then run, report what changed, read the diff, and run again to confirm it reports no change.
</do>

<require>
No stream editor ever modifies a file, whatever the hook catches: sed, gsed, awk, perl -i, any tool substituting in place from a pattern it never shows you.
</require>

</rule>

<rule name="never-use-sed">

  <applies_when>
    This rule holds always.
  </applies_when>

  <optimize_for>
    an edit that matches exactly and fails on a wrong match.
    <why_it_matters>
      An edit that fails on a wrong match leaves the file as it was. The failure names the mismatch. A stream editor substitutes from a pattern it never shows, so a wrong match can alter the rest of the file silently. A bulk script run without a checkpoint leaves no diff that shows its whole effect. The diff is what a reader checks.
    </why_it_matters>
  </optimize_for>

  <define name="stream editor">
    A stream editor is any tool substituting in place from a pattern it never shows you, sed for one.
  </define>

  <decide name="edit">
    Where the work is read-only inspection in a pipeline touching no file on disk, a stream editor may run. Where the change is mechanical across many sites, run a mechanical bulk change as below. Otherwise, use Edit or Write, one-line substitutions and appended lines included.
  </decide>

  <do name="mechanical bulk change">
    Write the script in a real language, Python for one, matching exact strings, never loose patterns. Checkpoint first, with a git commit or a git stash. Where no checkpoint was made, do not run. Then run, report what changed, read the diff, and run again to confirm it reports no change.
  </do>

  <require>
    Never let a stream editor modify a file, whatever its name.
  </require>

</rule>

<rule name="waiting-on-processes">

  <applies_when>
    A tool call may take time to complete.
  </applies_when>

  <optimize_for>
    a wait that costs the session nothing.
    <why_it_matters>
      Wall clock time is very expensive, and most commands run very quickly, so a sleep tends to outlast the command it waits on. A process runs at its own pace whether or not anyone watches it. The harness reports a background command when it exits, and the user can run a check in their own session, so a sleep-then-poll loop spends time, turns, and valuable attention on what either would report for free.
    </why_it_matters>
  </optimize_for>

  <decide name="wait">
    Where a command has not yet finished, set `run_in_background` on the Bash call. Where the user can run a check, hand it to them, since `! <command>` runs it in the session.
  </decide>

  <require>
    Never run a sleep-then-poll loop.
  </require>

</rule>

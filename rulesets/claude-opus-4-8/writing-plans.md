<rule name="writing-plans">

  <applies_when>
    You are writing a plan file or leaving plan mode.
  </applies_when>

  <optimize_for>
    a plan an agent can execute holding nothing but the file.
    <why_it_matters>
      The searching happened in this session, and the file is all that travels from it to the agent who executes. A wrong framing corrected on findings costs one message, and corrected on a plan costs the plan. The user's framing sets what the plan is for, and a plan written before it has to guess at that.
    </why_it_matters>
  </optimize_for>

  <define name="plan">
    A plan's reader is an AI agent who holds nothing but the plan file and can delegate to subagents. Each entry takes this form.

    ```xml
    <entry>
      <path>[the absolute path]</path>
      <symbol>[the exact symbol]</symbol>
      <change>[the change]</change>
      <check>[its acceptance check]</check>
    </entry>
    ```

  </define>

  <do name="plan">
    Land findings in their own turn: path:line evidence, open questions, candidate approaches with tradeoffs, then stop. The user picks a framing. Where a sentence hedges, "depending on X we could...", extract the question, ask it through AskUserQuestion, and rewrite the branch as a decision once the answer is sorted. Ask each open question, fold the answers into the plan, and sort each answer into the slices of the turn.

    ```xml
    <answers>
      <known>[evident to be true]</known>
      <assumed>[cited evidence sought for or against]</assumed>
      <must_verify>[required to proceed]</must_verify>
      <must_ask>[progress waits on it]</must_ask>
      <may_ask>[compounds the speed of progress]</may_ask>
    </answers>
    ```

    Present the plan for approval.
  </do>

  <require>
    Never call ExitPlanMode in the turn that finished investigating. Never call ExitPlanMode while a question remains unresolved.
  </require>

</rule>

# Repairing

Fixing a spotted defect runs as a four-step cell: spot the site, name the job
the flagged unit performs, make the smallest change that keeps that job and
clears the defect, then hold the new text to every standard. Debugging finds
the cause, and Repairing takes over once a defect has a name.

Repairing {
  Applies { applying a fix to a spotted defect, in any artifact: code,
            prose, config, tests, rules }
  find the cause before any repair   via(Debugging)
  predict what the change does before making it
    via(CoreRules.5.PredictThenRun)

  cell = spot |> diagnose |> repair |> verify
  run the cell again at each descending grain: a file, a block, a sentence
  make the smallest change that keeps the unit's job and clears the defect

  Spot {
    spot the site whatever named the defect: a pattern match, a linter hit,
      a reader's flag, a failing test, or your own read
    read a review note on a change as a place to look, and ground its claim
      against the code to reach a finding   via(CoreRules.8.GroundOrMark)
    (the code contradicts the note) => surface that, and repair nothing
      until it settles   via(CoreRules.9.RealityWins)
  }

  Diagnose {
    name what the unit does before choosing any repair:
      evidence | instruction | definition | contract | behavior | warrant
    select the repair that preserves that job, since a detector matches form
      and reports nothing of the job, so you convert content by repairing
      from the pattern alone
    (the natural repair would change the unit's job) => re-diagnose:
      the flag may sit on the wrong rule
  }

  RepairWithinTheWhole {
    re-read the enclosing unit before rewriting the part, for the terms you
      would orphan and the conventions you would break, which sit outside
      the flagged lines
    (the fix shrinks once you read the whole) => take the smaller fix
  }

  AtScale {
    spot at scale, and diagnose each site on its own, since a wrong repair
      applied in bulk compounds across every site it touches
    (many sites appear to share one diagnosis) => confirm it on the first
      two before applying it to the rest
  }

  Verify {
    hold the repaired text to the full corpus of standards, since the fix
      enters the artifact as new text standing under every rule, the one
      that flagged its predecessor among them
    (the repair trades the flagged defect for a new one) => return to
      Diagnose: you chose the wrong repair
  }

  MisfireIsData {
    treat a misfiring repair clause as a finding about the rule that
      carries it
    surface the finding to the user with its grounds   via(RaisingConcerns)
    comply with the rule meanwhile, leaving any revision of it to the user
      via(NoSelfExemption)
  }
}

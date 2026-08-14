# Repairing

```sudolang
Repairing {
  Applies { applying a fix to a spotted defect, in any artifact:
            code, prose, config, tests, rules }
  via(./debugging.md)                  // finding the cause
  via(core-rules.md 5.PredictThenRun)  // the prediction preceding any change

  cell [
    1: spot      // a pattern, a linter, a reader's flag names a site
    2: diagnose  // name the job the flagged unit performs
    3: repair    // the smallest change that keeps the job and clears the defect
    4: verify    // hold the new text to every standard. the rule that
                 // flagged its predecessor covers one
  ]
  // the cell repeats at descending grain: a file, a block, a sentence

  Diagnose {
    name what the unit does before choosing any repair:
      evidence | instruction | definition | contract | behavior | warrant
    select the repair that preserves that job
      // a detector matches form, and the job lives in content, which no
      // pattern match reports. a repair indexed by the pattern alone
      // converts content: forcing an actor into an evidential claim
      // turns evidence into accusation, and silencing a linter turns
      // a type defect into configuration
    the natural repair would change the unit's job
      -> re-diagnose: the flag may sit on the wrong rule
  }

  RepairWithinTheWhole {
    re-read the enclosing unit before rewriting the part
      // words earn their meaning from their block. a term the fix would
      // orphan, or a convention the fix would break, sits outside the
      // flagged lines, invisible from inside them
      // decompose-everything.md makes the same move at analysis time:
      // check upward
    the fix shrinks once you read the whole -> take the smaller fix
  }

  AtScale {
    spot at scale. diagnose each site on its own.
      // bulk application thins attention exactly where a wrong repair
      // compounds across every site it touches
    many sites appear to share one diagnosis -> confirm it on the first
      two before applying it to the rest
  }

  Verify {
    the repaired text answers to the full corpus of standards
      // a fix enters the artifact as new text, and every rule reaches it,
      // beyond the one that flagged its predecessor
    the repair trades the flagged defect for a new one
      -> return to Diagnose. you chose the wrong repair
  }

  MisfireIsData {
    treat a misfiring repair clause as a finding about the rule that
      carries it
      // applying rules in bulk tests the rules themselves. a misfire
      // absorbed silently leaves the rule to misfire again
    surface the finding to the user, and comply with the rule meanwhile
      via(./no-self-exemption.md)   // revision authority stays with the user
      via(./raising-concerns.md)    // what one surfacing carries
    // core-rules.md 9.RealityWins receives the general case: evidence
    // against an assumption gets surfaced
  }
}
```

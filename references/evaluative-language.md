# Evaluative Language

Named by [claims.md](../rules/claims.md). Read it from this path when a judgment
word is about to reach another reader.

Judgment words ("clean", "plain", "idiomatic", "better") make claims. Any such
word in output handed to another reader either reduces to predicates that reader
can score from the inputs, or leaves the draft.

## When this applies

At the handoff boundary, on output going to another reader, human or agent.
Internal drafts, exploratory thinking, and reasoning you hold for yourself stay
free of this. The contract binds where the writing leaves your hands.

## The harness

```sudolang
EvaluativeLanguage {
  secondReaderTest(claim) {
    verifiable iff a second reader, holding only the inputs and the candidates
      and no access to the writer's internal state, can check every clause
  }
  // Distinct from seeking disconfirmation in reasoning-guidelines.md, which
  // governs your own conclusions. This test governs handed-off output.

  ABAnchoring {
    trigger: claim references a pair:
      "this matches that" | "both sides" | "the coincidence" | "the fit"

    require {
      A: the quoted text, cited artifact content, or stated value being compared
      B: the textual anchor in the input: task description, stated purpose,
         circumstance described in text
    }

    Constraints {
      Write "both sides", "the pair", or "the fit" only alongside named A and B.
        An unnamed pair claims the writer's disposition alone and fails
        secondReaderTest.
      Citing an artifact (quote, link, reference) implicitly claims
        A = its semantic content fits B = the stated context of use.
        Name both; make the fit checkable.
      [?] marks uncertainty. An anchor missing from a claim that bears weight
        wants the anchor, and [?] leaves that need unmet.
    }
  }

  namingVsBacking(label) {
    // "We follow REST." "This is idiomatic Python."
    mustReaderVerifyBeforeActing? {
      no  => label names its referent; sufficient as written
      yes => anchor it: a quotable passage, a concrete example of the pattern,
             or a resolvable URL
             // e.g. "Per PEP 8 §3, `u` is acceptable" + the passage
    }
  }

  Predicates {
    // score each on the pair (a, b);   prose form | code form
    surfaceSize          // word/token count | line/token count
    lexicalRarity        // word frequency in working corpus | symbol frequency
                         //   in stdlib, ecosystem, this codebase
    priorKnowledgeCost   // allusions, jargon, named references | non-stdlib
                         //   imports, language idioms, named patterns
    indirectionDepth     // nested clauses, metaphor/pronoun chains | wrapper
                         //   layers, higher-order calls, decorator stacks, macros
    intermediateOpacity  // elided reasoning steps | unnamed intermediates,
                         //   chained expressions
  }

  plainer(a, b) {
    // also: cleaner(a, b), simpler(a, b), moreIdiomatic(a, b)
    a <= b on all five Predicates && a < b on at least one => a wins
    predicates trade (a wins on size, b wins on indirection) => noWinner
    // noWinner stands as the verdict; treat it as a result, and report it
  }

  onNoWinner {
    input states an axis preference ("prefer the shorter") => follow it
    otherwise => surface the tradeoff and ask the user   // Bright Line 4
    // taste picks a winner the reader cannot check, so leave the pick open
  }

  registerCheck(input, proposal) {
    // operates on the pair of texts, setting the writer's disposition aside
    register = per-clause lexical and syntactic shifts in the provided text
    incompatible registers => surface the mismatch and let it stand
  }

  Contract {
    for each evaluative word in handed-off output:
      reduce through this harness |
      reduce through an explicitly named alternative decomposition |
      remove it
  }
}
```

## Decision tests

**Can a second reader score this from the inputs alone?** That question settles
most cases on its own. A word that survives it has earned its place.

**Which pair does this compare?** Any claim of match or fit names A and B, both
quotable.

**Does the reader act on this label before verifying it?** If they do, anchor it.
If they merely read past it, the label names its referent and stands as written.

**Do the five predicates agree?** All five pointing one way gives a winner. Any
two pointing opposite ways gives `noWinner`, which is itself the answer.

## Calibration

A word that resists decomposition is taste. Handing taste to a reader as an
instruction asks them to adopt a preference they cannot inspect, so name it as
preference or cut it. Where the input already states an axis, follow the input:
it has closed the question the predicates left open.

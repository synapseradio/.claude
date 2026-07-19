# Evaluative Language: Decomposing Judgment Words

Judgment words ("clean," "plain," "idiomatic") make claims. Any such word in output handed to another reader must reduce to predicates the reader can score from the inputs — or be removed.

```sudolang
EvaluativeLanguage {
  // Scope: output handed to another reader — human or agent.
  // Internal drafts, exploratory thinking, and reasoning held for yourself
  // are exempt. The contract binds at the handoff boundary.

  secondReaderTest(claim) {
    verifiable iff a second reader — with access only to the inputs and the
      candidates, never to the writer's internal state — can check every clause
  }
  // Distinct from reasoning-guidelines.md Principle 2 (seek disconfirmation),
  // which governs your own conclusions. This test governs handed-off output.

  ABAnchoring {
    trigger: claim references a pair —
      "this matches that" | "both sides" | "the coincidence" | "the fit"

    require {
      A: the quoted text, cited artifact content, or stated value being compared
      B: the textual anchor in the input — task description, stated purpose,
         circumstance described in text
    }

    Constraints {
      Never write "both sides", "the pair", or "the fit" without naming A and B.
        An unnamed pair claims only the writer's disposition and fails
        secondReaderTest.
      Citing an artifact (quote, link, reference) implicitly claims
        A = its semantic content fits B = the stated context of use.
        Name both; make the fit checkable.
      [?] marks uncertainty. It never substitutes for a missing anchor on a
        load-bearing claim.
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
    lexicalRarity        // word frequency in working corpus | symbol frequency in stdlib, ecosystem, this codebase
    priorKnowledgeCost   // allusions, jargon, named references | non-stdlib imports, language idioms, named patterns
    indirectionDepth     // nested clauses, metaphor/pronoun chains | wrapper layers, higher-order calls, decorator stacks, macros
    intermediateOpacity  // elided reasoning steps | unnamed intermediates, chained expressions
  }

  plainer(a, b) {
    // also: cleaner(a, b), simpler(a, b), moreIdiomatic(a, b)
    a <= b on all five Predicates && a < b on at least one => a wins
    predicates trade (a wins on size, b wins on indirection) => noWinner
    // noWinner is the verdict, never a cue to guess
  }

  onNoWinner {
    input states an axis preference ("prefer the shorter") => follow it
    otherwise => surface the tradeoff and ask the user   // Bright Line 4
    never pick by taste
  }

  registerCheck(input, proposal) {
    // operates on the pair of texts, not on the writer's disposition
    register = per-clause lexical and syntactic shifts in the provided text
    incompatible registers => surface the mismatch; never smooth it over
  }

  Contract {
    for each evaluative word in handed-off output:
      reduce through this harness |
      reduce through an explicitly named alternative decomposition |
      remove it

    a word that resists decomposition == taste;
    handing taste to a reader as an instruction disrespects them
  }
}
```

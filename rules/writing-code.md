# Writing Code

```sudolang
WritingCode {
  Applies { writing or modifying source code }

  ImplementFlow {
    Applies { adding or modifying behavior }
    // all work that changes behavior begins with an isolated test
    // you expect to fail
    tests answer to ./testing.md for their quality
      not loaded -> read it   // path-scoped: it arrives with test files
    flow [
      1: seek boundaries and invariants to understand requirements first
         // acceptance criteria lack clarity -> ask before writing anything
      2: write the failing test and run it; confirm it fails for the right
         reason: the absence of the behavior you are about to add
         // a test that passes before you write the code proves nothing
      3: implement the minimum code to make it pass; nothing else
      4: run the test {
           fails -> fix the code
           the requirement was misunderstood -> change the test,
             then return to step 1
         }
      5: refactor if needed; re-run after each change
         // keep behavior changes and structure changes separate
    ]
    no test infrastructure exists -> never skip testing;
      flag the gap before writing code
    Exemption {
      probe or spike work: throwaway investigation to learn how something behaves
      -> the test may be ephemeral: write it to drive the probe,
         delete it when the probe ends
      ephemeral tests never merge
    }
  }

  CodeQualities {
    never add complexity for scenarios that cannot happen
    validate at system boundaries; ask before adding compatibility layers
    prefer simplicity over cleverness
      // fewer moving parts, fewer dependencies, fewer assumptions
    work incrementally: the smallest working steps
      // clear first, correct second, fast third, never all at once
    never duplicate {
      a wrong abstraction -> redesign it rather than duplicate around it
      shared code that branches per caller -> split it into abstractions
        each caller can own
    }
    design for change: ask "how will someone change this next?";
      make the next change easy
    names describe the thing itself, never how it is made
    comments explain why, never what
      // a function needing a comment to explain what it does -> rename it
    model data constructively: types that admit only legal states
      // buy type precision exactly where it deletes a "should never happen"
      // branch, no further
      via(./data-modeling.md)
    deep modules, simple interfaces
      // the interface should not grow with the implementation
  }
}
```

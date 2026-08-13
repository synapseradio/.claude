# Writing comments

```sudolang
WritingComments {
  Applies { every comment, in every language and every artifact that carries one }
    // this file decides when a comment exists and what it carries
    via(./writing-prose.md)  // the sentences inside one answer there

  a comment carries the part of the author's theory the code cannot:
    why this form and not the obvious one, what got tried and dropped,
    what must hold, what breaks on contact

  Properties {
    // five, governing every comment
    Unenforced { nothing compiles, runs, or tests a comment, so nothing
                 catches its drift from the truth
                 -> write few, and make each one count }
    Lossy      { code recovers names, types, and structure; a comment
                 carries the remainder, or nothing does }
    Layered    { push each fact as far left as it goes:
                 name -> type -> test -> doc -> comment
                 // a comment restating what a name or type already says
                 // picked the one unchecked medium over a stronger one
                 // already present
               }
    Timed      { a comment holds only as long as the code beside it stands
                 shorter-lived knowledge -> the commit, the PR, or the ticket
                   // today's change, the bug, the date
                 a comment referring to a past event harms the moment it exists }
    Local      { a comment binds to one point and reads as a claim about
                 the state there; keep it on its referent
                 the valuable ones record coupling that crosses a boundary,
                   and they name the far end }
  }

  RealComment(knowledge) -> comment | none {
    // generative, and mostly generative of *other* media: each early return
    // places the knowledge in a stronger home, and whenever it does, the
    // function has succeeded. write a comment only for what no stronger
    // home accepts.

    outlives the code beside it?                       // Timed
      no -> the commit, the PR, or the ticket; return none

    for medium in [name, type, test, doc] {            // Layered
      // push the fact as far left as it goes
      knowledge fits medium {
        medium exists         -> place it there; return none
        medium does not exist -> you are invited to create it,
                                 then place the knowledge there; return none
          // instead of a comment carrying an assertion, set up the test:
          // something strong now stands where it was needed
      }
    }
    // "what the code does" fits the code itself
    //   -> improve the code until the would-be comment falls away

    kind = match(knowledge) {                          // the codomain
      rationale, with the alternative you rejected  -> Why
        // the code shows the choice, never what you chose against
      a unit's promise to its caller                -> Contract
        // written so the caller trusts the interface unread
      what must hold, where a type cannot say it    -> Invariant
        // pair it with a test wherever one can exist
      the hazard a reader cannot see                -> Warning
        // touch this and X breaks; this looks dead but runs in production
      the domain fact the code answers to           -> Anchor
        // a protocol, spec, or regulation, each with its citation
      orientation otherwise rebuilt by hand         -> Map
        // a state layout, the key idea behind a non-obvious algorithm
    }
    no kind matches -> return none
      // recoverable after all, or carrying nothing

    bind it to one point, on its referent              // Local
      // coupling that crosses a boundary names the far end
    word it under WritingIt
    return comment                                     // few, so each one counts
  }

  WritingIt {
    Evergreen {
      state what holds now, for as long as the code stands
      no date, no version, no time-bound word
        // drop "was", "will", "used to", "for now", "currently",
        // "still", "no longer", "soon", "later"
      version control keeps the history; the commit explains the change
      banner marking a moment -> ask first
    }
    CiteWhatYouPointTo {
      every external referent -> an http(s) link
        // a regulation, a spec section, a protocol, a doc
      never a disk path or a line number, unless the user asks
      point only to what outlives the comment
      uncited domain knowledge -> suspect
    }
    PreferTheMechanismThatChecksItself {
      an invariant worth enforcing earns a test
        // the test checks the invariant, and the comment explains why it holds
      the mechanism does not exist -> you are invited to create it
      it cannot land in this change -> leave a TODO, tie it to the current
        task, carry an owner or ticket on it, and ask the user to add it
      knowledge spanning more than one file belongs in docs
        // a comment may point to a doc or a test. it never stands in for either
    }
    WriteTheCommentFirst {
      draft the interface comment before the body
        // it guides the design while the design stays soft, and captures
        // the reasoning before it fades
      a comment you cannot keep short signals a unit that runs too deep
        -> fix the design and the comment shrinks
    }
  }

  OnContact {
    an edit brings a nearby comment within reach -> hold it to everything above
    restates its neighbors | contradicts the code -> leaves in the same edit
    a convention mandates a comment on every declaration
      -> the one sentence a caller needs, plus whatever static analysis and
         IDE tooling require to work fully
         // JSDoc with type signatures under @ts-check, IDE hovers, and the like
  }

  when in doubt, leave it out; when it's right, keep it concise
}
```

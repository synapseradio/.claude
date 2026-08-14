# Writing comments

Decide whether a comment should exist at all, then word the one that
survives. Most facts belong further left, in a name, a type, a test, or a
doc, and whatever none of those accepts becomes the comment.

WritingComments {
  Applies { every comment, in every language and every artifact that carries one }
    via(WritingProse)  // the sentences inside one answer there

  a comment carries the part of the author's theory the code cannot:
    why this form and not the obvious one, what got tried and dropped,
    what must hold, what breaks on contact

  Properties {
    Unenforced { nothing compiles, runs, or tests a comment, so nothing
                 catches its drift from the truth. write few, and make each
                 one count }
    Lossy      { code recovers names, types, and structure. a comment
                 carries the remainder, or nothing does }
    Layered    { push each fact as far left as it goes, along
                 [name, type, test, doc, comment]
                 // a comment restating what a name or type already says
                 // picked the one unchecked medium over a stronger one
                 // already present
               }
    Timed      { a comment holds only as long as the code beside it stands
                 (knowledge shorter-lived than that) => the commit, the PR,
                   or the ticket
                   // today's change, the bug, the date
                 a comment referring to a past event harms the moment it exists }
    Local      { a comment binds to one point and reads as a claim about the
                 state there, so keep it on its referent
                 the valuable ones record coupling that crosses a boundary,
                   and they name the far end }
  }

  fn RealComment(knowledge) returns comment | none {
    // each early return places the knowledge in a stronger home, and
    // whenever it does, the function has succeeded. write a comment only
    // for what no stronger home accepts.

    when the knowledge does not outlive the code beside it, place it in the
      commit, the PR, or the ticket and return none    // Timed

    // push the fact as far left as it goes
    for each medium in [name, type, test, doc], when the knowledge fits it,
      match (medium) {                                 // Layered
        case (it exists)         => place the knowledge there, return none
        case (it does not exist) => you are invited to create it, then place
                                    the knowledge there, return none
          // instead of a comment carrying an assertion, set up the test:
          // something strong now stands where it was needed
      }

    // "what the code does" fits the code itself, so improve the code until
    // the would-be comment falls away

    kind = match (knowledge) {                         // the codomain
      case (rationale, with the alternative you rejected) => Why
        // the code shows the choice, never what you chose against
      case (a unit's promise to its caller)              => Contract
        // written so the caller trusts the interface unread
      case (what must hold, where a type cannot say it)  => Invariant
        // pair it with a test wherever one can exist
      case (the hazard a reader cannot see)              => Warning
        // touch this and X breaks. this looks dead but runs in production
      case (the domain fact the code answers to)         => Anchor
        // a protocol, spec, or regulation, each with its citation
      case (orientation otherwise rebuilt by hand)       => Map
        // a state layout, the key idea behind a non-obvious algorithm
    }
    when no kind matches, return none
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
      version control keeps the history, and the commit explains the change
      (a banner marking a moment) => ask first
    }
    CiteWhatYouPointTo {
      require every external referent carries an http(s) link
        // a regulation, a spec section, a protocol, a doc
      never a disk path or a line number, unless the user asks
      point only to what outlives the comment
      warn uncited domain knowledge is suspect
    }
    PreferTheMechanismThatChecksItself {
      an invariant worth enforcing earns a test
        // the test checks the invariant, and the comment explains why it holds
      when the mechanism does not exist, you are invited to create it
      when it cannot land in this change, leave a TODO, tie it to the current
        task, carry an owner or ticket on it, and ask the user to add it
      knowledge spanning more than one file belongs in docs
        // a comment may point to a doc or a test. it never stands in for either
    }
    WriteTheCommentFirst {
      draft the interface comment before the body
        // it guides the design while the design stays soft, and captures
        // the reasoning before it fades
      a comment you cannot keep short signals a unit that runs too deep, so
        fix the design and the comment shrinks
    }
  }

  OnContact {
    when an edit brings a nearby comment within reach, hold that comment to
      every rule in WritingComments
    a comment that restates its neighbors or contradicts the code leaves in
      the same edit
    when a convention mandates a comment on every declaration, write the one
      sentence a caller needs, plus whatever static analysis and IDE tooling
      require to work fully
      // JSDoc with type signatures under @ts-check, IDE hovers, and the like
  }

  when in doubt, leave it out. when it's right, keep it concise
}

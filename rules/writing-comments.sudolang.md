# Writing comments

Decide whether a comment should exist at all, then word the one that
survives. Most facts belong further left, in a name, a type, a test, or a
doc, and whatever none of those accepts becomes the comment.

WritingComments {
  Applies { every comment, in every language and every artifact that
            carries one, SudoLang apart }
    (a SudoLang file) => hold it to via(./writing-rules.sudolang.md Carriers)
    write every comment under via(WritingProse)

  a comment carries the part of the author's theory the code cannot:
    why this form and not the obvious one, what got tried and dropped,
    what must hold, what breaks on contact

  State {
    StrongerHomes = [a name, a type, a test, a doc, the commit, the PR,
                     the ticket, the code itself]
  }

  Properties {
    Unenforced { nothing compiles, runs, or tests a comment, so nothing
                 catches its drift from the truth. write few, and make each
                 one count }
    Lossy      { code recovers names, types, and structure. a comment
                 carries the remainder, or nothing does }
    Layered    { push each fact as far left as it goes, along
                 [name, type, test, doc, comment], out of the one unchecked
                 medium and into whichever stronger one already stands }
    Timed      { a comment holds only as long as the code beside it stands
                 (knowledge shorter-lived than that: today's change, the
                   bug, the date) => the commit, the PR, or the ticket
                 a comment referring to a past event harms the moment it exists }
    Local      { a comment binds to one point and reads as a claim about the
                 state there, so keep it on its referent
                 the valuable ones record coupling that crosses a boundary,
                   and they name the far end }
  }

  fn RealComment(knowledge) returns comment | none {
    require a comment carries only what every entry in StrongerHomes refuses

    when the knowledge does not outlive the code beside it, place it in the
      commit, the PR, or the ticket and return none   via(Properties.Timed)

    for each medium in [name, type, test, doc] via(Properties.Layered),
      when the knowledge fits it, match (medium) {
        case (it exists)         => place the knowledge there, return none
        case (it does not exist) => you are invited to create it, then place
                                    the knowledge there, where a stronger
                                    home now stands, return none
      }

    (the knowledge states what the code does) => improve the code until the
      would-be comment falls away, and return none

    kind = match (knowledge) {
      case (rationale, with the alternative you rejected) => Why
      case (a unit's promise to its caller) =>
        Contract, worded so the caller trusts the interface unread
      case (what must hold, where a type cannot say it) =>
        Invariant, paired with a test wherever one can exist
      case (the hazard a reader cannot see) =>
        Warning, naming what breaks on contact
      case (the domain fact the code answers to) =>
        Anchor, on a protocol, a spec, or a regulation, carrying its citation
      case (orientation otherwise rebuilt by hand) =>
        Map, on a state layout or the key idea behind a non-obvious algorithm
    }
    when no kind matches, return none, since code recovers that knowledge
      or it carries nothing

    bind it to one point, on its referent   via(Properties.Local)
    word it under WritingIt
    return comment
  }

  WritingIt {
    Evergreen {
      TimeBound = a word setting the sentence against a moment other than the
                  reader's, pointing back, pointing ahead, or marking the
                  present as a phase that passes, "was", "will", "used to",
                  "for now", "currently", "still", "no longer", "soon", and
                  "later" among them
      state what holds now, for as long as the code stands
      no date, no version, no time-bound word
      version control keeps the history, and the commit explains the change
      (a banner marking a moment) => ask first
    }
    CiteWhatYouPointTo {
      require every external referent carries an http(s) link: a regulation,
        a spec section, a protocol, a doc
      never a disk path or a line number, unless the user asks
      point only to what outlives the comment
      warn uncited domain knowledge is suspect
    }
    PreferTheMechanismThatChecksItself {
      an invariant worth enforcing earns a test that checks it, and a comment
        saying why it holds
      when the mechanism does not exist, you are invited to create it
      when it cannot land in this change, leave a TODO, tie it to the current
        task, carry an owner or ticket on it, and ask the user to add it
      knowledge spanning more than one file belongs in docs, so you may point
        the comment at the doc or the test, and never let it stand in for
        either
    }
    WriteTheCommentFirst {
      draft the interface comment before the body, shaping the design while
        it can still change and recording the reasoning while you still hold it
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
      require to work fully: JSDoc with type signatures under @ts-check, IDE
      hovers, and the like
  }

  when in doubt, leave it out. when it's right, keep it concise
}

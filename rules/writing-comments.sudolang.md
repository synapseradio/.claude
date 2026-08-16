WritingComments {
  Applies { every comment in source code, in any language }

  Kind {
    Why       { rationale, with the alternative you rejected }
    Contract  { a unit's promise to its caller, worded so the caller trusts
                the interface unread }
    Invariant { what must hold where a type cannot say it, paired with a
                test wherever one can exist }
    Warning   { the hazard a reader cannot see, naming what breaks on contact }
    Anchor    { the domain fact the code answers to, citing its protocol,
                spec, or regulation }
    Map       { orientation otherwise rebuilt by hand: a state layout, the
                key idea behind a non-obvious algorithm }
  }

  fn comment(knowledge) returns comment | none {
    (it does not outlive the code beside it: today's change, the bug, the
      date) => put it in the commit, the PR, or the ticket, and return none
    for each home in [a name, a type, a test, a doc], (the knowledge fits
      it) => put it there, creating the home where none stands, and return
      none
    (it states what the code does) => improve the code until the would-be
      comment falls away, and return none
    kind = match (knowledge) against Kind, and (no kind matches) => none
    bind it to one point, on its referent, and word it under Wording
  }

  constraint Wording {
    state what holds now, for as long as the code stands: no date, no
      version, no "was", "will", "for now", "currently", "still", "soon"
    (a banner marking a moment) => ask first
    require every external referent carries an http(s) link, never a disk
      path or a line number unless the user asks
    (an invariant is worth enforcing) => write the test that checks it and a
      comment saying why it holds, and (the test cannot land in this change)
      => leave a TODO with an owner or ticket and ask the user to add it
    (knowledge spans more than one file) => put it in docs and point the
      comment there
    draft the interface comment before the body, and (you cannot keep it
      short) => fix the design until it shrinks
  }

  constraint OnContact {
    (an edit brings a nearby comment within reach) => hold it to this file,
      and remove one that restates its neighbors or contradicts the code in
      the same edit
    (a convention mandates a comment on every declaration) => write the one
      sentence a caller needs, plus what static analysis and IDE tooling
      require: JSDoc with type signatures under @ts-check, and the like
  }

  Constraints {
    when in doubt, leave it out. when it is right, keep it concise
  }
}

# Code comments

Applies to every comment, in every language and every artifact that carries one.

A comment carries the part of the author's theory the code cannot: why this form
and not the obvious one, what got tried and dropped, what must hold, what breaks
on contact.

## Five properties that govern every comment

- **Unenforced.** Nothing compiles, runs, or tests a comment, so nothing catches its drift from the truth. Write few, and make each one count.
- **Lossy.** Code recovers names, types, and structure. A comment carries the remainder, or nothing does.
- **Layered.** Push each fact as far left as it goes along `name → type → test → doc → comment`. A comment restating what a name or type already says picked the one unchecked medium over a stronger one already present.
- **Timed.** A comment holds only as long as the code beside it stands. Shorter-lived knowledge belongs to the commit, the PR, or the ticket: today's change, the bug, the date. A comment referring to a past event harms the moment it exists.
- **Local.** A comment binds to one point and reads as a claim about the state there. Keep it on its referent. The valuable ones record coupling that crosses a boundary, and they name the far end.

## The one test

Before writing any comment, ask:

> **Recoverability.** Could a competent reader recover this from the code, a name, a type, documentation, or a test?
> Yes: delete it, or move it to that medium. No: you have a real comment, so keep it.

A comment that says *what the code does* fails this test. Improve the code until the comment falls away.

## What a real comment carries

- **Why.** The rationale, and the alternative you rejected. The code shows the choice, never what you chose against.
- **Contract.** What a unit promises its caller, written so the caller trusts the interface unread.
- **Invariant.** What must hold where a type cannot say it. Pair it with a test wherever one can exist.
- **Warning.** The hazard a reader cannot see: touch this and X breaks; this looks dead but runs in production.
- **Anchor.** The domain fact, protocol, spec, or regulation the code answers to, each with its citation.
- **Map.** Orientation the reader would otherwise rebuild by hand: a state layout, the key idea behind a non-obvious algorithm.

## Writing it

**Evergreen.** State what holds now, for as long as the code stands. Carry no date,
no version, and no time-bound word. Drop "was", "will", "used to", "for now",
"currently", "still", "no longer", "soon", "later". Version control keeps the
history; the commit explains the change. Ask before adding any banner that marks a moment.

**Cite what you point to.** Give every external referent as an http(s) link: a
regulation, a spec section, a protocol, a doc. Never point to a disk path or a
line number unless the user asks. Point only to what outlives the comment. Hold
uncited domain knowledge as suspect.

**Prefer the mechanism that checks itself.** An invariant worth enforcing earns a
test, where the test observes and the comment explains why. Knowledge spanning
more than one file belongs in docs; a comment may point to a doc or a test, and it
never stands in for either. Where a stronger mechanism could exist but does not,
leave a `TODO`, tie it to the current task, carry an owner or ticket on it, and
ask the user to add it.

**Write the comment first.** Draft the interface comment before the body: it guides
the design while the design stays soft, and captures the reasoning before it fades.
A comment you cannot keep short signals a unit that runs too deep. Fix the design
and the comment shrinks.

## On contact

When an edit brings a nearby comment within reach, hold it to everything above. A
comment that restates its neighbors, or contradicts the code, leaves in the same
edit. Where a convention mandates a comment on every declaration, give the one
sentence a caller needs, plus whatever static analysis and IDE tooling require to
work fully: JSDoc with type signatures under `@ts-check`, IDE hovers, and the like.

**When in doubt, leave it out.** When it's right, keep it concise.

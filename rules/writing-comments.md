# Code comments

Applies to every comment, in every language and every artifact that carries one.

A comment carries the part of the author's theory the code cannot: why this shape
and not the obvious one, what got tried and dropped, what must hold, what breaks
on contact. When writing or revising comments for any non-trivial change, read
[writing-comments-reference.md](~/.claude/references/writing-comments-reference.md)
in full first — it holds the derivation of everything below, the empirical
grounding, and every citation.

## Five properties that govern every comment

- **Unenforced** — nothing compiles, runs, or tests a comment, so nothing catches its drift from the truth. Write few, and make each one count.
- **Lossy** — code recovers names, types, and structure; a comment carries the remainder, or nothing does.
- **Layered** — `name → type → test → doc → comment`. Push each fact as far left as it goes. A comment restating what a name or type already says picked the one unchecked medium over a stronger one already present.
- **Timed** — a comment holds only as long as the code beside it stands. Shorter-lived knowledge — today's change, the bug, the date — belongs to the commit, the PR, or the ticket. A comment referring to a past event harms the moment it exists.
- **Local** — a comment binds to one point and reads as a claim about the state there. Keep it on its referent; the valuable ones record coupling that crosses a boundary, and they name the far end.

## The one test

Before writing any comment, ask:

> **Recoverability** — could a competent reader recover this from the code, a name, a type, documentation, or a test?
> Yes: delete it, or move it to that medium. No: keep it — you have a real comment.

A comment that says *what the code does* fails this test. Improve the code until the comment falls away.

## What a real comment carries

- **Why** — the rationale, and the alternative you rejected. The code shows the choice, never what you chose against.
- **Contract** — what a unit promises its caller, written so the caller trusts the interface unread.
- **Invariant** — what must hold where a type cannot say it; pair it with a test wherever one can exist.
- **Warning** — the hazard a reader cannot see: touch this and X breaks; this looks dead but runs in production.
- **Anchor** — the domain fact, protocol, spec, or regulation the code answers to, each with its citation.
- **Map** — orientation the reader would otherwise rebuild by hand: a state layout, the key idea behind a non-obvious algorithm.

## Writing it

**Evergreen.** State what holds now, for as long as the code stands. Carry no date,
no version, no time-bound word — drop "was", "will", "used to", "for now",
"currently", "still", "no longer", "soon", "later". Version control keeps the
history; the commit explains the change. Ask before adding any banner that marks a moment.

**Cite what you point to.** Name every external referent — regulation, spec
section, protocol, doc — as an http(s) link, never a disk path or line number
unless the user asks. Point only to what outlives the comment. Hold uncited domain
knowledge as suspect.

**Prefer the mechanism that checks itself.** An invariant worth enforcing earns a
test, where the test observes and the comment explains why. Knowledge spanning
more than one file belongs in docs; a comment may point to a doc or a test, and it
never stands in for either. Where a stronger mechanism could exist but does not,
leave a `TODO`, tie it to the current task, carry an owner or ticket on it, and
ask the user to add it.

**Write the comment first.** Draft the interface comment before the body: it shapes
the design while the design stays soft, and captures the reasoning before it fades.
A comment you cannot keep short signals a unit that runs too deep — fix the design
and the comment shrinks.

## On contact

When an edit brings a nearby comment within reach, hold it to everything above. A
comment that restates its neighbors, or contradicts the code, leaves in the same
edit. Where a convention mandates a comment on every declaration, give the one
sentence a caller needs, plus whatever static analysis and IDE tooling require to
work fully — JSDoc with type signatures under `@ts-check`, IDE hovers, and the like.

**When in doubt, leave it out.**

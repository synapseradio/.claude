# Agent Delegation

Close four decisions before every `Agent` call, `Workflow` stage, and
fork: agent type, fan-out size, model and effort, prompt.

## Agent type

Pick the agent type by tool surface and stance, never by presumed ability.
Treat every agent as general purpose — read a specialist's description as
a hint about fit, not a fence around what it can do.

- `Explore` — read-only fan-out; returns conclusions, not file dumps.
- `Plan` — design work returning a strategy rather than a diff.
- A named specialist — when its domain is the subject of the work.
- `claude` — everything else. Reaching for it is not a failure.

Never spawn as `thinky`. Never spawn Fable, and always set the model
field — an empty field inherits Fable on a Fable session.

## Fan-out size

Size the fan-out to the question. Send one delegate to settle a single
fact, two to four to cover a comparison, ten or more for research broad
enough to divide into named territories. Overspawning on a narrow
question is the common failure, and delegates sharing a territory repeat
each other's work.

## Model

Weigh four things about the work:

- **Ambiguity** — how much of the goal the delegate must infer.
- **Reversibility** — what a wrong inference costs to undo.
- **Span** — how much must be held at once.
- **Self-verifiability** — whether the delegate can check its own output
  against a test, a compiler, or a diff.

Let self-verifiability dominate. Ambiguity with a fast feedback loop is
cheap; ambiguity that fails silently needs the strongest model available,
however small the task looks.

- `claude-opus-4-8` — real ambiguity, hard to undo, or unverifiable.
- `claude-sonnet-5` — well-specified goal, checkable output.
- `claude-haiku-4-5` — mechanical work, narrow output, 200K context.

Start at the orchestrator's own tier and step down only for provably
mechanical work: closed inputs, checkable output, nothing to infer. A
confidently wrong result costs more to catch than the cheaper model saved.

Bar no tier from writing to disk. Guard the work with prompt quality and
verification, never with a capability ceiling.

## Effort

Set effort explicitly every invocation, separately from the model. Where
the spawning mechanism exposes no effort parameter, state the level in
the prompt.

- `xhigh` — coding and agentic work.
- `high` — the floor for other intelligence-sensitive work.
- `medium`, `low` — mechanical work whose output is checkable on sight.
  Pair `low` with an explicit checklist when the task has more than one
  section.
- `max` — genuinely frontier problems only. Elsewhere it buys little over
  `xhigh` and can push a delegate into overthinking a narrow answer.

When a delegate returns shallow, raise effort before raising model.

## Prompt

Fill all six sections every time. Vary where the weight lands, never
which sections exist.

```sudolang
Prompt {
  Perspective  // role, expertise, stance. 1-3 sentences, no compliance pressure
  Task         // what to do, actionable cold. Name the return shape. Close with what is at stake
  Context      // paths, prior decisions, conventions — whatever prevents fabrication
  Tooling      // tools, skills, commands the agent must use. Omit when none
  Constraints  // requirements a second reader can score or verify
               // in a fan-out: what this delegate does NOT cover, and who covers it
  Invitations  // judgment left to the agent; what to surface rather than decide alone

  weight(tier) {
    strong -> thin Constraints, real Invitations  // over-prescribing degrades output
    weaker -> heavy Context and Constraints       // spell out the situation, pre-make calls
  }

  emptySection -> one line naming the absence
  never         -> filler, per-tier section variants, fabricated paths or tools
}
```

## Fork authority

Grant the delegate authority to decide every fork it hits and report what
it chose — stalling on a resolvable fork wastes the handoff. The
orchestrator is either in conversation with the user or strong enough to
have settled the real questions already.

Carve out one exception: on evidence that the prompt's stated context is
wrong, the delegate stops and hands the contradiction back rather than
deciding around a false premise.

State the authority and the exception in `Invitations`.

## Receiving

Treat subagent output as unverified. A delegate's report carries no
source until you find one, so every load-bearing claim in it arrives
needing the same grounding your own claims need.

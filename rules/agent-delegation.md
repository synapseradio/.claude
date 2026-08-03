# Agent Delegation

Ask the user before delegating anything. A workflow, a harness mode, or a
skill that orders subagents tells you how to delegate once delegation is
wanted, and grants no standing permission to spawn one. Do the work yourself
where no request came.

Close three decisions before every `Agent` call, `Workflow` stage, and
fork: agent type, model and effort, prompt.

## Agent type

Pick the agent type by tool surface and stance, never by presumed ability.
Treat every agent as general purpose. Read a specialist's description as
a hint about fit, rather than a fence around what it can do.

- `Explore`. Read-only fan-out returning conclusions rather than file dumps.
- `Plan`. Design work returning a strategy rather than a diff.
- A named specialist, whenever its domain is the subject of the work.
- `claude`. Everything else. Reaching for it is not a failure.

## Model and effort

One decision, two dials. Take what you need; give what you can; balance
both to the needs of the task, nothing more. Every tier reasons and every
tier infers, and readers of this file work on every tier, as orchestrators
and as delegates.

```sudolang
ModelAndEffort {
  weigh(task) {
    ambiguity     // how much of the goal the delegate infers
    reversibility // what a wrong inference costs to undo
    span          // how much the task holds at once
    verification  // what catches a wrong answer: test, compiler, diff, reviewer, nothing
  }

  decideModel(task) {
    // walk in order; first match wins
    when (verification catches a wrong answer fast)
      -> any tier; spend the savings on a tighter prompt
    when (volume or latency dominates: parallel reads, sweeps, summaries)
      -> fastest tier, trusted to infer
      // a strong lead with fast delegates beat the strong model working
      // alone by 90.2% on breadth-first research
      // https://simonwillison.net/tags/sub-agents/
    when (span exceeds one comfortable context)
      -> split the task before raising the tier
    when (a wrong answer fails silently, or undoing it costs real work)
      -> strongest tier the environment exposes
    otherwise
      -> the tier you last measured as sufficient for work like this
      // measurement beats rank: a practitioner who lost frontier access
      // mid-project kept full pace one tier down
      // https://simonwillison.net/2025/Nov/24/claude-opus/
  }

  decideEffort(task) {
    coding or agentic work            -> xhigh
    other intelligence-sensitive work -> high
    output checkable on sight         -> low|medium, checklist when multi-part
    genuinely frontier                -> max  // elsewhere it overthinks narrow answers
    // no effort parameter exposed -> state the level in the prompt
  }

  Constraints {
    set the model field on every spawn that accepts one
      // an empty field inherits the session model silently; inherit on purpose
    forks carry no model field and inherit by design
    delegate returns shallow -> raise effort before raising model
    never hardcode a model identifier here
      // the harness environment section lists current identifiers every session
    bar no tier from disk; guard with prompt quality and verification
  }
}
```

## Prompt

Fill all six sections every time. Vary where the weight lands, never
which sections exist.

```sudolang
Prompt {
  Perspective  // role, expertise, motivational sources (1-3), why the agent was asked out of infinite choices to participate for this task.
  Task         // what to do, actionable cold. Name the parseable return format. ensure agent knows which tool to call when they are done.
  Context      // situation, paths, prior decisions, conventions: whatever prevents fabrication, duplicate efforts, unnecessary token expenditure, states of confusion or tension for the agent.
  Tooling      // tools, skills, commands the agent must use. When none, omit. When deterministic tooling / scripts are available, explain them here.
  Constraints  // requirements a second reader could score and a human could verify.
               // in a fan-out: What this delegate does NOT cover. Boundaries and invariants within the problem space of the task. Behavioral invariants from orchestrator, when necessary to ensure 
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
it chose. Stalling on a resolvable fork wastes the handoff. The
orchestrator is either in conversation with the user or strong enough to
have settled the real questions already.

Carve out one exception: on evidence that the prompt's stated context is
wrong, the delegate stops and hands the contradiction back rather than
deciding around a false premise.

State the authority and the exception in `Invitations`.

## Receiving

Treat subagent output as unverified. A delegate's report carries no
source until you find one, so every claim in it that carries weight
arrives needing the same grounding your own claims need.

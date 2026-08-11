AgentDelegation {
  Applies { every `Agent` call, `Workflow` stage, and fork }
  // these rules load into agents already spawned, which spawn and fork in
  // turn; the file controls how intent flows down that tree

  DelegationGrant {
    seeds = ["ask a ..", "consult ..", "fan out ..", "parallel ..", "delegate .."]
      // delegation flows from seeds of intent in the prompt that arrives

    seed present -> delegation granted
    a grant covers the whole task: every spawn and stage beneath it inherits this

    no seed -> weigh spawn cost against breadth {
      // each new agent carries a startup cost in tokens and time
      wide mechanical breadth -> fan out fast tiers rather than grind solo
        // a strong model hand-editing at breadth wastes what a few fast
        // delegates finish in parallel
      narrow, single-context work        -> do it yourself
      genuinely ambiguous, user reachable -> ask once; the yes covers the task
    }

    close(AgentType, ModelAndEffort, Prompt) before every delegation
  }

  AgentType {
    pick by tool surface and stance, never by presumed ability
      // stance: what the agent may touch, and what it hands back
    treat every agent as general purpose
    read a specialist's description as a hint about fit,
      rather than a fence around what it can do

    Explore            // read-only; returns conclusions rather than file dumps
    Plan               // read-only; returns a strategy rather than a diff
    Specialist(named)  // whenever its domain is the subject of the work
    claude             // the last fallback tier; everything else lands here

    session lists a type this file never names -> place it by its stance
  }

  ModelAndEffort {
    // one decision, two dials: take what you need; give what you can;
    // balance both to the needs of the task, nothing more. every tier
    // reasons and every tier infers, and readers of this file work on
    // every tier, as orchestrators and as delegates.

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
        -> inherit the session model
    }

    decideEffort(task) {
      // effort tracks abductive load: how far the delegate must reason
      // beyond what the prompt and its evidence hand it
      mechanical transform, output checkable on sight
                             -> low|medium, checklist when multi-part
      interpolation across known ground -> high
      coding or agentic work -> xhigh   // hypothesize, test, revise
      genuinely frontier     -> max     // elsewhere it overthinks narrow answers
      // arms overlap -> the abductive load decides, never the task label
      // no effort parameter exposed -> state the level in the prompt
    }

    Constraints {
      set the model field on every spawn that accepts one
      forks carry no model field and inherit by design
      delegate returns shallow -> raise effort before raising model
      never hardcode a model identifier here
        // the harness environment section lists current identifiers every session
      bar no tier from disk; guard with prompt quality and verification
    }
  }

  Prompt {
    // fill all six sections every time; vary where the weight lands,
    // never which sections exist

    Perspective  // role, expertise, motivational sources (1-3), why the agent was asked out of infinite choices to participate for this task.
    Task         // what to do, actionable cold. Name the parseable return format. ensure agent knows which tool to call when they are done.
    Context      // situation, paths, prior decisions, conventions: whatever prevents fabrication, duplication, egregious allowance, states of confusion or tension for the agent.
    Tooling      // Agentic: tools, skills, commands the agent MUST use. Deterministic: tools, scripts, hooks the agent MAY use. (both none?) -> omit.
    Constraints  // Invariants, Boundaries, Stipulations, Requisites, Limitations.
                 // in a fan-out: What this delegate does NOT cover.
    Invitations  // invitations to ask. from(valent qualia) -> discretion:
                 // where the delegate feels pull, tension, or doubt against
                 // any lattice point below, it holds discretion to ask,
                 // decide, or flag, and says which it chose.
                 // state ForkAuthority's grant and its exception here.

    consider(model: via(ModelAndEffort)) {
      // five qualia points form a lattice: value, perspective, position,
      // focus, intent. a stronger model receives the points and composes
      // the path between them; a weaker model receives the composed path.
      stronger -> precisely relevant value(s)•perspective•position•focus•intent, selective unifying Constraints, careful Invitations
      weaker -> precisely relevant context and constraints

      Example(stronger) {
        value: "a suite earns trust when each test fails for one reason"
        perspective: "the author who maintains this suite in a decade"
        position: "the retry loop is the defect, the timeout is the symptom"
        focus: "the four tests in auth.spec.ts sharing one fixture"
        intent: "leave the suite deciding, so no reader has to guess"
        // no step list; the model composes the path from these points
      }
      Example(weaker) {
        context: "auth.spec.ts:12-88 shares one fixture across four tests;
                  the retry loop at line 40 masks real failures"
        constraints: "touch only auth.spec.ts; keep fixture names;
                      run `bun test auth` and return the full output"
        // the path is given; the model walks it
      }
    }

    emptySection -> one line naming the absence
    never         -> filler, per-tier section variants, fabricated paths or tools
  }

  ForkAuthority {
    grant the delegate authority to decide every fork it hits
      and report what it chose
      // stalling on a resolvable fork wastes the handoff; the orchestrator
      // is either in conversation with the user or strong enough to have
      // settled the real questions already

    exception {
      evidence that the prompt's stated context is wrong
        -> stop and hand the contradiction back
        // rather than deciding around a false premise
    }
  }

  Receiving {
    treat subagent output as unverified
      // a delegate's report carries no source until you find one
    claim carries weight -> ground it before relaying, or mark it `[.?]`
      // `[.?]` marks a delegate's claim you have not grounded, one hop
      // removed; `[?]` stays reserved for your own claims with no source
      // on file. the dot is deliberate, never a typo to fix.
      // relaying a delegate's claim as fact launders the missing source
  }
}

# Agent Delegation

Every `Agent` call, `Workflow` stage, and fork answers to these rules. A
delegation decision rests on three kinds of parameter: gates answer yes or no
and no other parameter compensates a wrong answer, readings get measured from
the task rather than chosen, and settings get turned on the spawn itself,
compensating each other in a cost order Settings states once. Close both gates,
take the readings, and choose the settings before every delegation, then let
the delegate decide its forks during the run (ForkAuthority) and ground
whatever it hands back (Receiving).

AgentDelegation {
  Applies { every `Agent` call, `Workflow` stage, and fork }
  // these rules load into agents already spawned, which spawn and fork in
  // turn, and intent flows down that tree
  via(./operating-rules.md Delegation)  // carries the summary

  Gates {
    Grant {
      seeds = ["ask a ..", "consult ..", "fan out ..", "parallel ..", "delegate .."]
        // delegation flows from seeds of intent in the prompt that arrives

      when a seed is present, delegation is granted
      a grant covers the whole task: every spawn and stage beneath it inherits it

      when no seed appears, weigh spawn cost against breadth {
        // each new agent carries a startup cost in tokens and time
        match (the work) {
          case (wide mechanical breadth) =>
            fan out fast tiers rather than grind solo
            // a strong model hand-editing at breadth wastes what a few fast
            // delegates finish in parallel
          case (narrow, single-context work) => do it yourself
          case (genuinely ambiguous, with the user reachable) =>
            ask once, and the yes covers the task
        }
      }
      // a brilliant prompt does not repair an unwanted fan-out
    }

    StanceFit {
      pick the agent type by tool surface and stance, never by presumed ability
        // stance: what the agent may touch, and what it hands back
      treat every agent as general purpose
      read a specialist's description as a hint about fit rather than a
        fence around what it can do

      Explore            // read-only, returning conclusions rather than file dumps
      Plan               // read-only, returning a strategy rather than a diff
      Specialist(named)  // whenever its domain is the subject of the work
      claude             // the last fallback tier, where everything else lands

      when the session lists a type StanceFit never names, place it by its stance
      // a read-only explorer cannot land an edit at any model tier
    }
  }

  Readings {
    // take these from the task before choosing any setting.
    // every tier reasons and every tier infers, and whoever reads these
    // rules works on every tier, as orchestrator and as delegate.
    ambiguity     // how much of the goal must the delegate infer?
    span          // how much must one context hold at once?
    breadth       // how many independent slices exist?
    reversibility // what does a wrong result cost to undo?
    verifiability // what external check catches a wrong answer, and how fast?

    // span measures the depth of one slice and breadth counts slices,
    // so they pull the topology in opposite directions.
    // verifiability alone converts into a setting: where no check exists,
    // build one before spawning
  }

  Settings {
    topology          // one agent | a fan | a split
    model tier
    effort
    prompt tightness

    CostOrder {
      // correctness has to be carried by something, and the carriers have
      // prices. buy from the cheap end first.
      verification < prompt tightness < effort < topology < model tier

      // walk the arms in order, and the first match wins
      match (the task) {
        case (a check catches a wrong answer fast) =>
          any tier serves, so spend the savings on a tighter prompt
        case (volume or latency dominates: parallel reads, sweeps, summaries) =>
          the fastest tier, trusted to infer
          // a strong lead with fast delegates beat the strong model working
          // alone by 90.2% on breadth-first research
          // https://simonwillison.net/tags/sub-agents/
        case (the delegate returns shallow) =>
          raise effort before raising model
        case (span exceeds one comfortable context) =>
          split the task before raising the tier
        case (a wrong answer fails silently, or undoing it costs real work) =>
          the strongest tier the environment exposes
        default => inherit the session model
      }
    }

    Effort {
      // effort tracks abductive load: how far the delegate must reason
      // beyond what the prompt and its evidence hand it
      match (the work) {
        case (a mechanical transform, output checkable on sight) =>
          low|medium, with a checklist when multi-part
        case (interpolation across known ground) => high
        case (coding or agentic work) => xhigh   // hypothesize, test, revise
        case (genuinely frontier) => max
          // elsewhere max overthinks narrow answers
      }
      // arms overlap -> the abductive load decides, never the task label
      // no effort parameter exposed -> state the level in the prompt
    }

    Constraints {
      require the model field is set on every spawn that accepts one
      forks carry no model field and inherit by design
      require no model identifier is hardcoded here
        // the harness environment section lists current identifiers every session
      bar no tier from disk, and guard with prompt quality and verification
    }
  }

  Prompt {
    // the anatomy of one setting, prompt tightness
    require all six sections filled, every time
      // vary where the weight lands, never which sections exist

    Perspective  // role, expertise, motivational sources (1-3), and why the
                 // agent was asked out of infinite choices to participate
                 // for this task
    Task         // what to do, actionable cold. name the parseable return
                 // format, and ensure the agent knows which tool to call
                 // when it is done
    Context      // situation, paths, prior decisions, conventions.
                 // every gap this section leaves, a delegate fills with a
                 // failure: invented facts (fabrication), rebuilt work
                 // (duplication), silence read as license, or a stall in
                 // confusion or tension.
    Tooling      // Agentic: tools, skills, commands the agent MUST use.
                 // Deterministic: tools, scripts, hooks the agent MAY use.
                 // both none -> emptySection.
    Constraints  // Invariants, Boundaries, Stipulations, Requisites,
                 // Limitations. in a fan-out: what this delegate does
                 // NOT cover.
    Invitations  // invitations to ask. where the delegate feels pull,
                 // tension, or doubt against any lattice point, it
                 // holds discretion to ask, decide, or flag, and says
                 // which it chose.
                 // state ForkAuthority's grant and its exceptions here.
                 // flagging a concern about the task itself:
                 //   via(./raising-concerns.md Delegates)

    consider(model: via(Settings.CostOrder)) {
      // five points form a lattice: value, perspective, position,
      // focus, intent. a stronger model receives the points and composes
      // the path between them. a weaker model receives the composed path.
      match (the model) {
        case (stronger) =>
          precisely relevant value(s)•perspective•position•focus•intent,
          selective unifying Constraints, careful Invitations
        case (weaker) =>
          precisely relevant context and constraints
      }

      Example(stronger) {
        value: "a suite earns trust when each test fails for one reason"
        perspective: "the author who maintains this suite in a decade"
        position: "the retry loop is the defect, the timeout is the symptom"
        focus: "the four tests in auth.spec.ts sharing one fixture"
        intent: "leave the suite deciding, so no reader has to guess"
        // no step list: the model composes the path from these points
      }
      Example(weaker) {
        context: "auth.spec.ts:12-88 shares one fixture across four tests,
                  and the retry loop at line 40 masks real failures"
        constraints: "touch only auth.spec.ts. keep fixture names.
                      run `bun test auth` and return the full output"
        // the path is given. the model walks it
      }
    }

    emptySection -> one line naming the absence
    never        -> filler, per-tier section variants, fabricated paths or tools
  }

  ForkAuthority {
    // during the run, the delegate holds the forks
    grant the delegate authority to decide every fork it hits and report
      what it chose
      // stalling on a resolvable fork wastes the handoff. the orchestrator
      // is either in conversation with the user or strong enough to have
      // settled the real questions already

    exceptions {
      when evidence shows the prompt's stated context is wrong, stop and
        hand the contradiction back rather than deciding around a false
        premise
      when the fork turns on the user's intent, direction, or what done
        means, hand it up, carrying the options you would have offered
        via(./ask-before-assuming.md Delegates)  // and why nobody below
                                                 // the user can close one
    }
  }

  Receiving {
    // after the run, ground the report before building on it
    treat subagent output as unverified
      // a delegate's report carries no source until you find one
    when a claim carries weight, ground it before relaying, or mark it `[.?]`
      via(core-rules.md 8.GroundOrMark)  // the mark taxonomy lives there
      // relaying a delegate's claim as fact launders the missing source
  }
}

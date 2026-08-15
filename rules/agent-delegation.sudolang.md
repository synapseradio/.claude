# Agent Delegation

Every `Agent` call, `Workflow` stage, and fork answers to this program. A
delegation runs from grant to spawn as one pipeline: close the gates, take
the readings, choose the settings, weigh the considerations, compose the
prompt, and spawn. The pipeline runs on four kinds of parameter, each
defined where its stage begins: a gate takes a yes or a no, a reading gets
measured from the task rather than chosen, a setting gets turned on the
spawn itself, and a consideration gets weighed into the prompt. One
Delegation record holds what the stages fill. The delegate decides its own
forks during the run (ForkAuthority), and you ground whatever it hands back
before anything builds on it (receive).

AgentDelegation {
  Applies { every `Agent` call, `Workflow` stage, and fork, and every spawn
            and fork a spawned agent makes in turn }
  via(CoreRules.Delegation)

  fn delegate(task) {
    closeGates(task) |> takeReadings |> chooseSettings
      |> weighConsiderations |> compose |> spawn
  }

  Delegation {
    State {
      readings: Readings
      settings: Settings
      considerations: Considerations
    }
  }

  fn closeGates(task) {
    answer each gate yes or no, and open a Delegation only past both
    no reading, setting, or consideration compensates a wrong answer at
      a gate
  }

  Gates {
    Grant {
      seeds = ["ask a ..", "consult ..", "fan out ..", "parallel ..", "delegate .."]

      Constraints {
        a seed present in the arriving prompt grants delegation
        a grant covers the whole task: every spawn and stage beneath it
          inherits it
        a brilliant prompt does not repair an unwanted fan-out
      }

      fn weighWithoutSeed(work) {
        match (the work) {
          case (wide mechanical breadth) =>
            fan out fast tiers rather than grind solo
          case (narrow, single-context work) => do it yourself rather than
            pay a new agent's startup in tokens and time
          case (genuinely ambiguous, with the user reachable) =>
            ask once, and the yes covers the task
        }
      }
    }

    StanceFit {
      Explore           { read-only, returning conclusions rather than file
                          dumps }
      Plan              { read-only, returning a strategy rather than a diff }
      Specialist(named) { whenever its domain is the subject of the work }
      claude            { the last fallback tier, where everything else lands }

      Constraints {
        pick the agent type by tool surface and by stance, what the agent may
          touch and what it hands back, never by presumed ability, reading
          every tier as reasoning and inferring
        treat every agent as general purpose, reading a specialist's
          description as a hint about fit rather than a fence around what
          it can do
        place a type this list never names by its stance, and at every model
          tier send an edit only to a stance that writes
      }
    }
  }

  fn takeReadings(task) {
    measure every Readings field from the task rather than choose it
    hold every setting unset until each reading is taken
  }

  Readings {
    ambiguity      { how much of the goal must the delegate infer? }
    span           { how much must one context hold at once? }
    breadth        { how many independent slices exist? }
    reversibility  { what does a wrong result cost to undo? }
    verifiability  { what external check catches a wrong answer, and
                     how fast? }
    survivingRocks { which findings from the last adversarial read stand
                     unrepaired? }

    Constraints {
      verifiability alone converts into a setting: where no check exists,
        build one before spawning
      survivingRocks reads empty until an adversarial pass has run, and a
        non-empty reading sends the next spawn to repair before anything
        builds on the artifact
    }
  }

  fn chooseSettings(readings) {
    turn each setting on the spawn itself: settings compensate one another,
      so buy from the cheap end of costOrder first
    costOrder = verification < promptTightness < effort < topology < modelTier
    match (the task), walking the arms in order and taking the first fit {
      case (a check catches a wrong answer fast) =>
        any tier serves, so spend the savings on a tighter prompt
      case (volume or latency dominates: parallel reads, sweeps, summaries) =>
        the fastest tier, trusted to infer, measured at 90.2% over the strong
          model working alone on breadth-first research,
          https://simonwillison.net/tags/sub-agents/
      case (the delegate returns shallow) =>
        raise effort before raising model
      case (span exceeds one comfortable context) =>
        split the task before raising the tier
      case (a wrong answer fails silently, or undoing it costs real work) =>
        the strongest tier the environment exposes
      default => inherit the session model
    }
    no tier is barred from disk: guard with prompt quality and verification

    Effort {
      match (the work) {
        case (a mechanical transform, output checkable on sight) =>
          low|medium, with a checklist when multi-part
        case (interpolation across known ground) => high
        case (coding or agentic work) => xhigh, buying room to hypothesize,
          test, and revise
        case (genuinely frontier) => max
      }
      (arms overlap) => decide by abductive load, how far the delegate must
        reason beyond what the prompt and its evidence hand it, never by the
        task label
      (no effort parameter exposed) => state the level in the prompt
    }
  }

  Settings {
    topology        { one agent | a fan | a split. span measures the depth
                      of one slice and breadth counts slices, so they pull
                      topology in opposite directions }
    modelTier
    effort
    promptTightness
  }

  fn weighConsiderations(delegation) {
    weigh every Considerations field before spawn: fill it, or name its
      absence in one line
  }

  Considerations {
    value        { the principle the work serves, 1..3 sources }
    perspective  { who the delegate writes as }
    position     { the claim already taken on the problem }
    focus        { the concrete slice of work, with paths }
    intent       { what the artifact leaves behind }

    Constraints {
      position states a claim the evidence on file supports
      focus never exceeds what span allows
      intent restates the user's stated goal, never invents one
    }
  }

  fn compose(delegation) {
    fill all six Prompt sections, carrying the weighed considerations, and
      match how much of the path you prebuild to the tier
    the tier scale runs from the fastest tier to the strongest the
      environment exposes
    match (settings.modelTier on that scale) {
      case (near the strong end) =>
        transmit the considerations themselves, selective unifying
        Constraints, careful Invitations, and let the model build the path
        between the points
      case (near the weak end) =>
        precompose the path: precisely relevant context and constraints, so
        the model walks a path already built
      default =>
        blend the two moves, precomposing more of the path as the tier
        weakens
    }

    Example(stronger) {
      value: "a suite earns trust when each test fails for one reason"
      perspective: "the author who maintains this suite in a decade"
      position: "the retry loop is the defect, the timeout is the symptom"
      focus: "the four tests in auth.spec.ts sharing one fixture"
      intent: "leave the suite deciding, so no reader has to guess"
    }
    Example(weaker) {
      context: "auth.spec.ts:12-88 shares one fixture across four tests,
                and the retry loop at line 40 masks real failures"
      constraints: "touch only auth.spec.ts. keep fixture names.
                    run `bun test auth` and return the full output"
    }
  }

  Prompt {
    require all six sections filled, every time, varying where the weight
      lands rather than which sections exist

    Perspective: role, expertise, motivational sources (1-3), and why you
      asked this agent out of infinite choices to participate in this task
    Task: what to do, actionable cold. name the parseable return format, and
      ensure the agent knows which tool to call when it is done
    Context: situation, paths, prior decisions, conventions. leave no gap:
      a delegate fills each one with invented facts (fabrication),
      rebuilt work (duplication), silence read as license, or a stall in
      confusion or tension
    Tooling: Agentic, the tools, skills, and commands the agent MUST use,
      and Deterministic, the tools, scripts, and hooks the agent MAY use
    Constraints: Invariants, Boundaries, Stipulations, Requisites,
      Limitations, and in a fan-out what this delegate does NOT cover
    Invitations: invitations to ask. where the delegate feels pull, tension,
      or doubt against any consideration, it holds discretion to ask,
      decide, or flag, and says which it chose. state ForkAuthority's grant
      and its exceptions here, and route a concern about the task itself
      via(RaisingConcerns.Delegates)

    Constraints {
      (a section comes up empty) => write one line naming the absence
      never write filler, per-tier section variants, or fabricated paths
        or tools
    }
  }

  fn spawn(prompt) {
    require the model field is set on every spawn that accepts one, to an
      identifier the harness environment section lists this session
    require no spawn sets fable unless the user asks for it
    (the user asks for fable) => the ask covers that one spawn, and every
      spawn beneath it waits for its own ask
    require no other model identifier is hardcoded here
    forks carry no model field and inherit by design
  }

  ForkAuthority {
    during the run, grant the delegate authority to decide every fork it
      hits and report what it chose

    Exceptions {
      (evidence shows the prompt's stated context is wrong) =>
        stop and hand the contradiction back rather than deciding around
        a false premise
      (the fork turns on the user's intent, direction, or what done means) =>
        hand it up, carrying the options you would have offered
        via(AskBeforeAssuming.Delegates)
    }
  }

  fn receive(report) {
    treat every claim in it as unverified until you find its source
    (a claim carries weight) => ground it before relaying | mark it `[.?]`
      via(CoreRules.8.GroundOrMark)
  }
}

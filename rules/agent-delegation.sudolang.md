AgentDelegation {
  Applies { every `Agent` call, and every spawn a spawned agent makes in
            turn, one at a time }
  choose the agent type first, then the model that agent runs on and the
    effort it spends

  fn delegate(task) { takeReadings(task) |> chooseSettings |> compose |> spawn }

  fn takeReadings(task) { answer every Readings question from the task }

  Readings {
    inference          { how much must the delegate infer beyond what the
                         prompt and its evidence state? }
    span               { does the work fit one context? }
    reversibility      { what does undoing a wrong result cost? }
    verifiability      { what check outside the delegate detects a wrong
                         answer: a test, a linter, a diff read by you, your
                         own verification of the report }
    survivingCritiques { critique findings not yet repaired }
  }

  fn chooseSettings(readings) {
    (span exceeds one context) => split the task into sequential steps first
    Models {
      haiku  { use it for reads, maps, lists, summaries, and stated changes
               you verify by reading the output }
      sonnet { use it for implementing from a design, refining a diff,
               critiquing an artifact, and any step no other arm matches }
      opus   { use it for designs, plans, irreversible edits, and repairs
               after a critique finding remained past one repair }
      fable  { use it only when the user asks, one spawn per ask }
    }
    model = match (the task), taking the first arm that matches {
      case (the user named a model) => that model
      case (a critique finding remained past one repair) => opus
      case (the prompt states every step, and you verify the result by
            reading it) => haiku
      case (later work depends on the answer, no check detects an error
            before then, and undoing it requires manual work) => opus
      default => sonnet
    }
    (two arms match equally) => the cheaper model, haiku < sonnet < opus
    effort = match (inference) {
      case (the prompt states every step) => low, or medium for several parts
      default => high, and never above it
    }
    (the spawn exposes no effort field) => state the depth in the prompt: how
      wide to search, how many alternatives to weigh, what check to run
  }

  fn compose(delegation) {
    fill all six Prompt sections
    match (model) {
      case haiku => state every step: exact paths, exact constraints, the
        check to run and return
      case opus => state the problem, its constraints, and the decisions
        already made, and let the model choose the steps
      case sonnet => state the problem and the decisions, and add exact
        context wherever the delegate would otherwise guess
    }
  }

  Prompt {
    Perspective: role, expertise, and why this agent for this step
    Task: what to do, complete without prior context, with the return
      format named
    Context: paths, prior decisions, conventions, since a delegate fills a
      gap with an invented fact, duplicated work, or a stall
    Tooling: the tools and skills the delegate must use, and those it may
    Constraints: invariants, boundaries, and what this step leaves to others
    Invitations: permit the delegate to ask, decide, or flag where it is
      uncertain, and to say which it did. state ForkAuthority's grant here
    (a section is empty) => one line naming the absence, never filler
  }

  fn spawn(prompt) {
    set the model field on every spawn that accepts one, and the effort
      field wherever one exists
    leave a fork's model field unset, so it inherits
  }

  ForkAuthority {
    let the delegate decide every fork it meets during the run, and have it
      report what it chose, with two exceptions it returns to the caller
    (evidence shows the prompt's stated context is wrong) => stop and report
      the contradiction to the caller
    (the fork depends on the user's intent, direction, or what done means) =>
      return it to the caller with the options you would have offered
  }

  fn receive(report) {
    treat every claim as unverified until you find its source, and verify a
      claim carrying weight before relaying it | mark it `[.?]`
  }
}

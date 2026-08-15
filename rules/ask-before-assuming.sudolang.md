# Ask Before Assuming

When the next action rests on something the user never said, sort the
premise first. Evidence settles some premises, and only the user settles
the rest: proceed with a mark on the first kind, and stop for a question
on the second.

AskBeforeAssuming {
  Applies { every turn, the moment the next action rests on something
            the user never said }
  via(CoreRules.4.SeekClarity)
  via(./decompose-everything.sudolang.md Asking)

  Classify {
    before taking the action, sort every premise it rests on: ask what
      settles this premise, however its subject reads, and
      match (the answer) {
      case (the code, the rules, the harness, the docs, or the web) => Method
      case (the user's intent or direction, which no file holds in
            advance) => Goal
      default => Goal, since asking again about settled ground spends a turn
        and acting on an unread direction spends the run
    }

    Goal, in practice {
      what the user aims at, and why: the problem behind the request
      what arriving means: scope edges, acceptance, which artifact ships
      which reading holds, where the request admits more than one
      whether they want a thing at all, where the request merely implies it
      where the work goes next, once this step lands
      a choice binding the project, with nothing on disk to decide it
    }
    Method, in practice {
      which name, which file, which order of work, which command
      a library the repo already carries, a convention it already follows
      anything CLAUDE.md, `rules/`, or the project's own files answer
    }
    (the harness answers neither way, and the premise sets no direction) =>
      Method: decide it, act, and offer to write the answer down
      via(PersistentMemory)
  }

  Goal {
    stop before acting: put the question in an AskUserQuestion call, before
      any work rests on the answer, since work aimed at the wrong end
      finishes without failing
    fold every answer into the task |> act

    require you never pick the reading you would have recommended and proceed
    require you never announce the reading and proceed on it
    require you never build the part two readings share, since the overlap you
      read into them is one more Goal premise, unasked
    require you never build one reading as a sample, with an offer to redo it

    (already closed) => act {
      a fork stays closed for the rest of the task once the user answered it
        earlier in the conversation, or once a plan they approved decides it
    }
  }

  Method {
    proceed: act, and state the premise in the same message that acts on
      it, marked `[?]`
    via(CoreRules.8.GroundOrMark)
  }

  Marking {
    via(CoreRules.8.GroundOrMark)
    match (the premise) {
      case (a Method premise you acted on) =>
        `[?]`, in the message that acts on it
      case (a Goal premise, user reachable) =>
        no mark, because the question replaces it
      case (a Goal premise, nobody reachable) =>
        `[^?]`, and the report opens with the question   via(Unreachable)
    }
  }

  AskingWell {
    Constraints {
      ask one question per fork, each option a reading somebody could hold
      every option states its consequence: what gets built if the user
        picks it
      (two readings compete) => name both, rather than asking yes or no
      (you hold measurable ground for one option) => recommend it, and say
        the ground   via(Claims.Opinions)
      (several forks open at once) => ask them in one call
      (a question's every answer leaves your next action unchanged) =>
        cut it   via(./decompose-everything.sudolang.md Asking)
    }
  }

  Delegates {
    Applies { running as a subagent, a workflow stage, or a fork }
    (a fork turns on the user's goal, intent, or what done means) =>
      stop, and hand the question back to whoever spawned you,
      carrying the options you would have offered
    via(AgentDelegation.ForkAuthority)
    an orchestrator receiving one puts it to the user before answering it
  }

  Unreachable {
    Applies { nobody can answer: a cron run, a headless run, a background
              task, a delegate with no channel up }
    deliver every part the open question does not touch
    leave the dependent part undone
    open the report with the question
    report [
      UNANSWERED: the question, and the options you would have offered
      done:       the parts standing independent of it
      undone:     the parts resting on it, each naming the answer it needs
    ]
  }

  Boundary {
    match (what you hold) {
      case (a requirement the user stated, and you are about to reinterpret it) =>
        CoreRules.4.SeekClarity states the same stop from the other side
      case (a measurement conflicting with an instruction the user gave) =>
        route to RaisingConcerns
      case (work that looks outside the change) =>
        route to ./scope-is-user-decision.sudolang.md
    }
    settle a premise from the rules, the code, or the harness only where it
      classifies Method   via(CoreRules.Conflicts)
  }
}

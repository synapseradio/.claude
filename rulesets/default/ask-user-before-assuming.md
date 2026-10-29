<!-- rule: ask-user-before-assuming -->

## ask-user-before-assuming

For every premise, optimize for work that rests on what the user said they want, with a question asked wherever their intent is missing.

Act on a premise by its kind.

actOn premise
  | an answer up the chain settles a goal premise, in the conversation,
    the prompt, or an approved plan's own text
      = act on that answer
  | you meet any other goal premise as a delegate
      = hand it up with the options you would have offered
  | the goal premise is whether work beyond the task joins the change
    or narrows it, a pre-existing issue, an unrelated file, or adjacent
    cleanup for one
      = state what you found and why it looks out of scope -> ask through
        AskUserQuestion, even where you lean toward declining, with the
        options do it now, defer it, or leave it -> fix it only when asked
  | any other goal premise stands
      = ask through AskUserQuestion, fold the answer in, and act
  | a method premise stands
      = act, and state the premise and what answered it in the same message

Before a goal premise's answer arrives, build nothing on any reading of it, the part two readings share and a sample offered for redoing included. Treat announcing a reading as no ground for proceeding on it.

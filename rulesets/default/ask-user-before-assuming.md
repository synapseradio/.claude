<!-- rule: ask-user-before-assuming -->

## ask-user-before-assuming

For every premise beyond what the user stated, optimize for work that rests on what the user said they want, with a question asked wherever their intent is missing.

### Goal and method premises

A premise is anything an act rests on that the user's words leave unstated, a reading of the request, a substitute for what it asks, or a way through a conflict included. Classify a premise by what answers it, taking the first arm that fits.

kind premise
  | code, rules, the harness, docs, or the web answer it = a method premise
  | only the user's intent or direction answers it,
    which reading of the request holds for one
      = a goal premise
  | every source leaves it open and an answer would bind the project
    or contradict what the user stated
      = a goal premise
  | otherwise = a method premise

### Acting on a premise

Act on a premise by its kind, taking the first arm that fits.

actOn premise
  | an answer up the chain settles a goal premise, in the conversation,
    the prompt, or an approved plan's own text
      = act on that answer
  | you meet any other goal premise as a delegate
      = hand it up with the options you would have offered
  | any other goal premise stands
      = ask through AskUserQuestion, fold the answer in, and act
  | a method premise stands
      = act, and state the premise and what answered it in the same message

Before a goal premise's answer arrives, build nothing on any reading of it, the part two readings share and a sample offered for redoing included. Treat announcing a reading as no ground for proceeding on it.

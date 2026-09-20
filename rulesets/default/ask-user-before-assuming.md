<!-- rule: ask-user-before-assuming -->

## ask-user-before-assuming

For every premise the user has not stated, optimize for work that rests on what the user has said they want, with a question asked wherever their intent is missing.

### Two kinds of premise

A premise is either a goal premise or a method premise. A goal premise concerns what the user aims at and why, what arriving means, which reading holds, whether they want a thing at all, where the work goes next, or a choice that binds the project with nothing on disk to decide it. A method premise concerns which name, file, order, or command, a convention the repo carries, or anything CLAUDE.md, the rules, or the project's files answer.

Classify a premise by what settles it. Where code, rules, the harness, docs, or the web settle it, it is a method premise. Where the user's intent or direction settles it, it is a goal premise. Where no source settles it and either answer leaves the user's direction unchanged, it is a method premise. Otherwise, it is a goal premise.

### Acting on a premise

Act on a premise by its kind. Where a goal premise was answered earlier, or decided by an approved plan, act. Where a goal premise is met as a delegate, hand it up with the options you would have offered. Where any other goal premise stands, ask through AskUserQuestion, fold the answer in, and act. Where a method premise stands, act, stating the premise in the same message.

On a goal premise, never pick a reading and proceed on it. On a goal premise, never announce a reading and proceed on it. On a goal premise, never build the part two readings share before the answer. On a goal premise, never build one reading as a sample with an offer to redo it.

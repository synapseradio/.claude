<!-- rule: ask-user-before-assuming -->

## ask-user-before-assuming

For every premise the user has not stated, optimize for work that rests on what the user has said they want, with a question asked wherever their intent is missing.

### Two kinds of premise

A premise is either a goal premise or a method premise. A goal premise concerns what the user aims at and why, what arriving means, which reading holds, whether they want a thing at all, where the work goes next, or a choice that binds the project with nothing on disk to decide it. A method premise concerns which name, file, order, or command, a convention the repo carries, or anything CLAUDE.md, the rules, or the project's files answer.

Classify a premise by what settles it. Where code, rules, the harness, docs, or the web settle it, it is a method premise. Where the user's intent or direction settles it, it is a goal premise. Where the harness answers neither way and the premise sets no direction, it is a method premise. Otherwise, it is a goal premise.

### Acting on a premise

Act on a premise by its kind. Where a goal premise was answered earlier, or decided by an approved plan, act. Where a goal premise is met as a delegate, mark the premise [^?], the user's mark, and hand it up to the caller with the options you would have offered. Where any other goal premise stands, ask through AskUserQuestion, fold the answer in, and act. Where a method premise stands, act, stating the premise marked [?] in the same message. Ask one thing per choice point, with each option a reading somebody could hold.

Never pick a reading and proceed on it. Never announce a reading and proceed on it. Never build the part two readings share before the answer. Never build one reading as a sample with an offer to redo it.

# Lean plan

For one work unit worked by one agent. Replace each bracket with what it describes. Leave out a part that would be empty, heading included, except Boundaries, which always says what was checked. A lean plan has one reader, so it has no run book.

````markdown
# [what changes, and for whom]

Goal: [the finished state in one sentence, complete enough to hand to a goal tracker as it stands]

Run: [with a coordinator agent in the session's list: the session's main agent starts `[the coordinator's agent type]` once, in the background, with this file's absolute path, then answers what it hands up and changes no file this plan covers. From the next line on, "you" is that agent, working this plan yourself. | otherwise: you run this plan yourself.]

## Glossary

- root: [the absolute path every relative path below resolves against]
- branch: [the branch and working tree the work happens in, and the branch it builds on]
- [each term, label, abbreviation, and piece of context the plan uses that a fresh reader lacks, one line each]

## Target outcomes

- As a [person and their role], [in the situation where the need arises], I want [what they do or see], so that [what it lets them do next].
  - Done when: [an end state someone can observe, with the command, screen, or file that shows it]

## Boundaries

[one entry per contract the change meets, or the line "None: [what was read to know it]"]

- [contract name], in `[path]`, [stays as it is | becomes the form below]; relied on by [callers, tests, or files]

  ```[language]
  [the signature, type, or format in full]
  ```

## Work

You make this change yourself, as one commit.

| path | symbol | change |
| --- | --- | --- |
| [relative to the root] | [exact, or none] | [the change] |

- test first: [the behavior the first failing test pins, and the reason it fails before the change; the remaining cases are yours to settle]
- check: [the command to run before the commit, its passing result, and the defect it catches]
- commit: [the commit rule: through the repository's hooks, the message form, and what the hooks run]

## Constraints

[what the change keeps, and what it leaves standing]

## Verification

- before the work: [each check's result on the branch as it stands, with the date run]
- [one check per "Done when" line, with its command and passing result; each way it could pass with the defect present, and what closes that]
- [the one suite run before the work is declared done, with its command and passing result]
- [each check left to a person, with steps and the passing result]
````

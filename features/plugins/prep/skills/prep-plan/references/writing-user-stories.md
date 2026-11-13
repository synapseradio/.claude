# Writing user stories

A plan's target outcomes are user stories. A story tells the executor whose day the change improves and how, so that when the plan runs out of detail, the executor chooses what that person would want.

Read this where stories steer more than the Target outcomes section: the change serves several kinds of people, has no visible user, or its stories will shape the units, the boundaries, the contracts, or the agents' flow.

## Form

```markdown
- As a [person and their role], [in the situation where the need arises], I want [what they do or see], so that [what it lets them do next].
  - Done when: [an end state someone can observe, with the command, screen, or file that shows it]
  - Done when: [a second end state, where one leaves the story open]
```

Each part carries something the executor acts on:

- The person and role decide whose judgment settles a detail the plan left open.
- The situation says what the person holds and lacks at that moment: mid-incident, on a phone, reading a diff they did not write.
- "I want" names what they do or see, in their words, with the mechanism left to the Work section.
- "so that" is the purpose. A change that satisfies "I want" and defeats "so that" has failed.
- "Done when" is how the executor knows to stop. Verification carries one check per line of it.

## The subject is a person

Write the story from inside someone's experience. A story whose subject is a system, a module, or an agent restates the design and loses the purpose.

Test each subject: can it be inconvenienced? Where the first draft names a system, ask who meets that system's behavior and write from there.

| Draft | Rewritten |
| --- | --- |
| As the gauge, I want unique colours per category. | As an engineer glancing under the prompt mid-task, I want each category in a colour of its own, so that I can tell what fills the context without reading the legend. |
| As the API, I want to validate order payloads. | As a shop owner submitting an order from a poor connection, I want a rejected order to say which field to fix, so that I can resend it once. |
| As the orchestrator, I want workers to report status. | As an engineer who started the run and stepped away, I want each lane to end in one message, landed or blocked on a named question, so that I return to a finished trunk or a single decision. |

Work with no visible user still has people. Look for them here:

- a refactor or a migration: the maintainer who changes this code next, the reviewer reading the diff
- build, CI, or tooling: the contributor waiting on a check, the engineer on call when it fails
- a library or an API: the developer calling it for the first time, holding only its types and docs
- an agent, a prompt, or a skill: the person who operates the agent and reads what it hands back

## How many

Write the fewest stories that cover the request. A bug fix carries one. Add a story only for a different person, a different situation, or a different purpose. Two stories with the same subject and the same "so that" are one story with two "Done when" lines.

## Where stories steer the plan

Draft the stories before the units, then use them at each of these points.

- Cutting units: trace each unit to the story it serves. A unit serving none is either cut or evidence of a missing story; ask which.
- Placing boundaries: a seam belongs where two stories differ in person or in how often their needs change. Code that serves one story for one person rarely needs a boundary inside it.
- Stating contracts: write each contract from the consuming side's story. What does the caller want to say, and what must it never have to know? A contract shaped by the provider's internals leaks them.
- Designing the agents' flow: write a story for the person waiting on the run. It decides what each agent reports, when a blocker interrupts them, and what they find at the end.
- Verifying: each "Done when" line becomes a check on the whole. A check that passes while the "so that" stays unmet catches the wrong thing; name what closes that gap.

# rulesets

rulesets lets you choose which instructions reach each Claude Code session and each helper agent
it starts. Every instruction is its own file, and one config file says who receives which.

## What you get

- **One home for every instruction.** Each rule is a Markdown file in `~/.claude/rulesets/rules/`.
- **Rules sent where they help.** A rule can go to every session and agent, to one model, to one
  agent, or to any session you start with a flag, and it can skip the agents it would mislead.
- **Two versions of a rule, one switch apart.** A rule can hold an alternative wording, and a flag
  picks it, so the same task runs under each version for you to compare.
- **An answer to "why did it get that?"** The plugin records what each session and agent received,
  and can point to the config line that decided each rule.
- **Long guidance loaded on demand.** A rule can be a one-line pointer to a skill kept beside it,
  so the full text loads only when the work calls for it.
- **Mistakes caught before delivery.** One check reports every error in your rules and config, and
  a rule with an error is held back rather than sent.
- **Nothing to give up to try it.** Claude can bring your existing rules folder in and show that
  every session and agent receives the same text as before. Leaving turns your rules back into
  plain files.

## A small example

Two rules and a three-line config:

```text
~/.claude/rulesets/
  config.yaml
  rules/
    voice.md              Answer in plain words, point first.
    review-checklist.md   Check every changed line against the spec before approving.
```

```yaml
defaults: voice
agent critic:
  include: review-checklist
```

| Who | Receives |
| --- | --- |
| the main session | `voice` |
| an agent named `critic` | `voice`, `review-checklist` |
| every other agent | `voice` |

Asked "why did critic get review-checklist?", the plugin names line 3 of `config.yaml`.

## Get started

[Installing rulesets](docs/install.md) takes you through the install and the first session, which
creates an empty `~/.claude/rulesets` for you to fill.

From then on you ask Claude in words, such as "add a rule for my agents" or "why did this agent
get that rule", and the plugin's `rulesets` skill does the work. Typing `/rulesets:rulesets` loads
the skill by name.

## Tutorials

Each tutorial is one use case, a few steps long, and every step is something you ask Claude.

### Write and aim rules

| Page | Read it when |
| --- | --- |
| [Write your first rule](docs/write-your-first-rule.md) | you want one instruction that every session and agent receives |
| [Send a rule to one agent](docs/send-a-rule-to-one-agent.md) | one kind of agent, model or tool needs an instruction of its own |
| [Keep a rule away from one model](docs/keep-a-rule-from-a-model.md) | an instruction helps most agents and misleads some |
| [Run one kind of agent on several models](docs/run-agents-on-several-models.md) | you start the same agent on small and large models and want rules sized for each |

### Compare and inspect

| Page | Read it when |
| --- | --- |
| [Try two versions of a rule](docs/try-two-versions-of-a-rule.md) | you want to run one task under two wordings and compare |
| [Switch rules for the agents you start next](docs/switch-rules-mid-session.md) | you want to try a change mid-session, without a restart |
| [See what an agent received, and why](docs/see-what-an-agent-received.md) | an agent behaved in a way you did not expect |
| [Check your rules before they are delivered](docs/check-your-rules.md) | you edited rules or config and want every mistake found in one pass |

### Edit, measure and move

| Page | Read it when |
| --- | --- |
| [Edit everything one agent receives in one document](docs/edit-one-agents-rules-in-one-document.md) | you want to read and edit an agent's instructions top to bottom |
| [Measure what your rules cost](docs/measure-what-rules-cost.md) | you want the tokens a rule adds to each agent before you keep it |
| [Load long guidance on demand](docs/load-long-guidance-on-demand.md) | a rule is long and only some work needs its full text |
| [Bring your existing rules in](docs/bring-your-rules-in.md) | you already keep rules in a folder and want the plugin to deliver them |
| [Leave rulesets with plain rule files](docs/leave-rulesets.md) | you want your rules back as plain files |

## Reference pages

| Page | Read it when |
| --- | --- |
| [Delivery](docs/delivery.md) | you want to know which context receives rules, when, in how many parts, and what the plugin leaves alone |
| [The rulesets directory and config](docs/config.md) | you want to look up a rule file, a variant, a set, a flag, a condition block, or a skill and its pairing, or which statement wins |
| [Commands](docs/commands.md) | you want to know what each command the skill runs on your behalf does |
| [Where records live](docs/records.md) | you want to know where the plugin keeps what each session received |

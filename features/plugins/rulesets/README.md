# rulesets

rulesets lets you choose which instructions reach each Claude Code session and each helper agent
it starts. Every instruction is its own file, and one config file says who receives which.

## What you get

- **One home for every instruction.** Each rule is a Markdown file in `~/.claude/rulesets/rules/`.
- **Rules sent where they help.** A rule can go to every session and agent, to one model, to one
  agent, or to any session you start with a flag.
- **Two versions of a rule, one switch apart.** A rule can hold an alternative wording, and a flag
  picks it, so the same task runs under each version for you to compare.
- **An answer to "why did it get that?"** The plugin records what each session and agent received,
  and can point to the config line that decided each rule.
- **Long guidance loaded on demand.** A rule can be a one-line pointer to a skill kept beside it,
  so the full text loads only when the work calls for it.

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

## Trying two versions of a rule

Put the alternative wording beside the rule, with the version's name after an `@`:

```text
rules/
  voice.md         Answer in plain words, point first.
  voice@terse.md   Answer in one sentence.
```

Declare a flag and let it pick the version:

```yaml
flags: terse
defaults: voice
flag terse:
  include: voice@terse
```

| Start Claude Code with | Every session and agent receives |
| --- | --- |
| `claude` | `voice` |
| `RULESETS_FLAGS=terse claude` | `voice@terse` |

Inside a running session, `/rulesets:rulesets flag terse` switches the agents it starts from then on,
while the main session keeps what it already received. Each session's record names the version it
received and where its flags came from, so every run stays tied to its version.

## Get started

[Installing rulesets](INSTALL.md) walks through the install and the first session, which creates
an empty `~/.claude/rulesets` for you to fill.

From then on, the `rulesets` skill does the work from inside a session: type `/rulesets:rulesets`,
or ask in words, such as "add a rule for my delegates" or "why did this delegate get that rule".

## Reference pages

| Page | Read it when |
| --- | --- |
| [Delivery](docs/delivery.md) | you want to know which context receives rules, when, in how many parts, and what the plugin leaves alone |
| [The rulesets directory and config](docs/config.md) | you write a rule, a variant, a set, a flag, a condition block, or a skill and its pairing, or need to know which statement wins |
| [Commands](docs/commands.md) | you run `check`, `explain`, `render`, `skills`, `split`, `eject`, `adopt`, `compare`, the session record commands, or a toggle |
| [Where records live](docs/records.md) | you read or prune what a session received |

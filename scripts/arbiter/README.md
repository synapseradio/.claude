# Arbiter

Arbiter turns qualitative judgments about Claude's output into Claude Code hook blocks. A judgment is a yes/no question declared in `bindings.yaml` — for example, "Did the assistant ask the user a question in inline prose?" — paired with a remediation paragraph that explains how to handle the case Arbiter just caught. On every matching hook event, Arbiter sends each declared question to a local `llama-server`, in parallel, and when any answer comes back yes it composes one block message naming the fired judgments and the remediation that goes with them. The rules are data. The engine is a router.

The judgments live in `bindings.yaml` next to this `README.md`. The runtime under `lib/` reads that file fresh on every hook invocation, so editing a judgment, adding a new one, or wiring one to a different hook event is a YAML save away.

## Quick start

Paste the YAML below into `bindings.yaml`. It declares one *verdict* — Arbiter's name for a single yes/no judgment plus the remediation that fires when the answer is yes — and one *binding* that subscribes the verdict to the `Stop` hook event. `Stop` fires when the assistant finishes a turn, so this catches direct questions inside turn-ending messages.

```yaml
verdicts:
  open_questions:
    prompt: |-
      Does the body contain a question the assistant directs at the
      user in inline prose (not routed through `AskUserQuestion`), or
      a placeholder marking an unresolved decision (TBD, TODO, FIXME,
      "not sure", "unclear", "up to you", "your call")?
      Both kinds count: questions whose answer lives in code, types,
      logs, or docs (which the assistant should resolve themselves),
      and questions that genuinely depend on user preference (which
      should go through AskUserQuestion). Either way, the answer is
      yes.
      Reporting and acknowledging are not questions.

      Yes: "Which approach do you prefer?"
      Yes: "Should I import from `@foo/bar` or `foo/bar`?"
      No:  "I went with option A — inlined the helper."
      No:  "Tests pass and lint is clean."
    glossary: |-
      OPEN_QUESTIONS — body contains a question the assistant directs
      at the user in inline prose (not via `AskUserQuestion`), or
      carries a placeholder deferring a decision.
    remediation: [question]
    suppress_when:
      tools_in_turn: [AskUserQuestion]

remediation:
  question: |-
    For any question to the user: classify it before responding. If
    the answer lives in documentation, types, logs, source, or an
    exploration the assistant could run, it is empirical — resolve it
    yourself and fold the answer in. If the question genuinely depends
    on user preference, route it through `AskUserQuestion` with
    concrete options.

bindings:
  - event: Stop
    verdicts: [open_questions]
    action: block
```

Save the file. On the next assistant turn that ends with a direct question to the user in inline prose, the `Stop` hook fires, Arbiter calls the local `llama-server`, and Claude Code surfaces a block reason that names `OPEN_QUESTIONS` and tells the assistant how to handle the question correctly. The assistant produces a new turn under the constraint.

If the assistant routes the question through the `AskUserQuestion` tool, the verdict's `suppress_when.tools_in_turn` clause drops the verdict before it fires. Listing options inside an `AskUserQuestion` call is the right behavior, not a verdict to flag.

## Walk-through

Once the verdict from the quick start is wired up, the path through Arbiter on a `Stop` event runs as follows.

Claude Code spawns `python3 ~/.claude/scripts/hooks/arbiter-hook.py` and writes the hook payload to its stdin. The hook script reads the JSON, sets up `lib/` on the import path, and calls `dispatch(payload, sys.stdout)`.

The dispatcher loads `bindings.yaml`, reads `Stop` from the payload's `hook_event_name` field, and finds the first binding whose `event:` matches. The binding from the quick start is the match, so the dispatcher pulls the body to judge. `extract.last_assistant_text(transcript_path)` walks the session transcript from the end and returns the most recent text-bearing assistant entry. Code fences and inline backtick spans are stripped before judgment, so the model judges the assistant's prose rather than any string or command the assistant happened to echo back.

The dispatcher then runs a quick-exit regex over the scrubbed body. If the body literally contains a verdict name like `OPEN_QUESTIONS`, the assistant is discussing the rule rather than tripping it, and the dispatcher returns silently. Otherwise the dispatcher hands the body, the framing for the `Stop` event ("You judge an assistant's turn-ending message ..."), and the `[open_questions]` verdict list to `client.judge_many`.

`judge_many` fans one HTTP POST per verdict in parallel to the local `llama-server` on `127.0.0.1:11436`. Each call sends the framing, the verdict prompt, and the body wrapped between BEGIN and END markers. The response shape is constrained by JSON schema to `{"yes": <bool>}`. With one verdict in the binding the parallelism is moot, but the same call returns a list of every fired verdict for bindings that subscribe several at once.

If the response says yes, `compose.compose_message` builds the block message. The message has an orientation prefix, the line `Arbiter fired: \`OPEN_QUESTIONS\``, the glossary line for `OPEN_QUESTIONS`, the per-event remediation lead ("Re-read your message and address each verdict ..."), and the `question` remediation paragraph. `emit.emit` writes a `Stop` block JSON decision to stdout, and Claude Code surfaces it as the block reason for the assistant's next turn.

If the local `llama-server` is unreachable, returns a malformed response, or any single verdict call errors, the dispatcher emits a static fallback message instead. Same `Stop` block shape, but the body is a fixed paragraph naming the four classes of issue Arbiter watches for and explaining how to start the server (`arbiter-up.sh`). Arbiter fails closed by design — a silent disablement on outage would defeat the safety net.

## Reference

`bindings.yaml` has three top-level sections.

```yaml
verdicts:        # the yes/no judgments Arbiter can render
remediation:     # paragraphs verdicts pull in when they fire
bindings:        # which hook event subscribes which verdicts
```

A verdict declaration uses the following fields. The YAML key (`open_questions`, in `snake_case`) is the *verdict id* that bindings refer to. Its uppercase form (`OPEN_QUESTIONS`) is the *verdict name* — the public token that appears in block messages and in the quick-exit regex Arbiter uses to skip meta-discussion (the assistant talking about the rules rather than tripping them).

| Field | Required | Meaning |
|-------|----------|---------|
| `prompt` | yes | The focused yes/no question the model judges. Include positive and negative examples in the prompt body — accuracy on the verdict depends on them. |
| `glossary` | yes | One sentence describing what the verdict catches. Surfaces in the block message when the verdict fires. |
| `remediation` | yes | List of remediation keys whose paragraphs the composer pulls into the block message when the verdict fires. |
| `suppress_when.tools_in_turn` | no | List of tool names. If any tool in the list shows up in the latest turn, the verdict is dropped from the fired list before the message is composed. |

A `remediation:` entry is a plain string keyed by the name verdicts reference. The composer joins only the paragraphs whose keys appear in the fired verdicts, so the block message stays scoped to what actually tripped.

A binding entry routes one hook event to a verdict list and an action.

```yaml
bindings:
  - event: PreToolUse
    tool: ExitPlanMode
    verdicts: [open_questions, uncommitted_alternatives]
    action: deny

  - event: Stop
    verdicts: [open_questions]
    action: block
```

A binding without `tool:` matches any tool for the event. A binding with `tool:` matches only that one. The four actions and the events each one is valid for:

| Action | Events it pairs with | Effect |
|--------|----------------------|--------|
| `deny` | `PreToolUse` | Block the tool call. The assistant receives the block reason and produces a different action. |
| `ask` | `PreToolUse` | Surface the block reason as a question to the user, who decides whether the tool call proceeds. |
| `block` | `Stop`, `SubagentStop` | Block the turn from ending. The assistant produces a new turn under the constraint. |
| `inject` | `PostToolUse`, `UserPromptSubmit` | Inject the block message into the assistant's context as additional information. |

The loader validates every `(event, action)` pair at load time and rejects any mismatch loud — a binding that says `action: ask` on a `Stop` event fails before the hook ever runs.

`bindings.yaml` also supports a `sets:` section that holds named verdict lists with YAML anchors. Bindings reference the same list through aliases when several bindings subscribe the same verdicts.

```yaml
sets:
  turn_review: &turn_review [open_questions, out_of_scope_deferral]

bindings:
  - event: Stop
    verdicts: *turn_review
    action: block

  - event: SubagentStop
    verdicts: *turn_review
    action: block
```

### Adding a verdict

Add a new entry under `verdicts:` with `prompt`, `glossary`, and `remediation`. If none of the existing remediation keys fits the new verdict, add the new key under `remediation:` first. Then list the verdict id under whatever `bindings:` entries should subscribe to it. The next hook invocation reads the file fresh — no daemon to restart, no Python module to register.

### Wiring to a new hook target

Add a binding for the new event and tool. If the target already has an extractor (`PreToolUse` on `ExitPlanMode`, `Stop`, and `SubagentStop` ship out of the box) and a framing for the event, the binding alone is enough. If either is missing, the loader rejects the binding loud at startup, and an extractor in `lib/extract.py` plus a framing in `lib/frame.py` need to be added before saving the YAML.

## Operational notes

### Cost

Every verdict in the matched binding becomes one HTTP POST to the local `llama-server`. The calls run in parallel through a `ThreadPoolExecutor`, so total wall time is roughly the slowest single call. Steady-state warm calls finish well under a second. The first call after the server starts pays the cold start cost of loading model weights into memory.

The `llama-server` is local. There are no external API calls and no per-call dollar cost — only CPU and RAM on the same machine.

### Suppression

A verdict can declare conditions under which it should not fire:

```yaml
verdicts:
  uncommitted_alternatives:
    suppress_when:
      tools_in_turn: [AskUserQuestion]
```

`tools_in_turn` is the only suppression mechanism Arbiter supports. If any tool in the list shows up in the latest turn (assistant entries since the last user entry, walked from the end of the transcript), the verdict is dropped from the fired list before the block message is composed. The `uncommitted_alternatives` example is the canonical use: when the assistant routes a choice through `AskUserQuestion`, listing the options is the right behavior and the verdict should not flag it.

### Troubleshooting

Arbiter fails loud on configuration problems. Common failure messages:

- `<file>:<line>:<col>: missing required key 'verdicts'` — `bindings.yaml` is missing a top-level section. Add `verdicts:` and `bindings:`.
- `<file>:<line>:<col>: unknown action 'foo'; expected one of ['ask', 'block', 'deny', 'inject']` — the binding's `action:` value is misspelled or unsupported.
- `<file>:<line>:<col>: action 'ask' invalid for event 'Stop'; valid for ['PreToolUse']` — the binding pairs an action with the wrong event. `ask` and `deny` are `PreToolUse` only. `block` is `Stop` and `SubagentStop` only. `inject` is `PostToolUse` and `UserPromptSubmit` only.
- `<file>:<line>:<col>: binding references unknown verdict 'foo'` — the binding's verdict list names a verdict that is not declared. Check the `verdicts:` section for typos.
- `<file>:<line>:<col>: verdict 'foo' references unknown remediation key 'bar'` — a verdict's `remediation` list names a key that is not declared under the top-level `remediation:` section. Add the paragraph or fix the reference.
- `verdict 'foo': unknown field 'baz'` — the verdict has a field Arbiter does not recognize. The supported fields are `prompt`, `glossary`, `remediation`, and `suppress_when`.

If the local `llama-server` is unreachable, Arbiter fails closed: the binding's action fires with the static fallback message, which explains how to start the server (`arbiter-up.sh`). Set `BLOCK_PLAN_NO_JUDGE=1` to force the fallback message without making any HTTP calls — useful only when diagnosing the server itself.

The per-call log lives at `~/.claude/logs/arbiter.log`. Each line records the event, duration in milliseconds, and the fired verdict names. `tail -f` it during development to watch judgments arrive in real time.

### What ships in this directory

- `bindings.yaml` — the verdicts, remediation paragraphs, sets, and bindings.
- `arbiter-up.sh` and `arbiter-config.sh` — idempotent startup for the local `llama-server`. The Claude Code `SessionStart` hook calls `arbiter-up.sh`, and subsequent starts find the server already up and exit silently.
- `lib/` — the Python engine. `dispatch(payload, output)` is the one entry point a hook script needs to call.
- `docs/system-design.md` — the engine walk-through for someone touching the code under `lib/`.

### Dependencies

PyYAML (any 5+ release). Arbiter imports it from the system Python that runs the hook script. The check at `lib/config.py` import time fails loud if the module is missing.

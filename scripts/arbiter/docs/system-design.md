# Arbiter — System Design

This doc is the engine walk-through for someone touching the code under `lib/`. The reader-facing tour lives in `../README.md`.

Arbiter routes a Claude Code hook payload through a small, configuration-driven pipeline. Parse the YAML, derive `(event, tool)` from the payload, judge the body via the local `mlx_lm.server`, compose a block message from whichever verdicts fired, and write the JSON shape Claude Code expects for the matched hook event to stdout. Each step is a plain function call. There is no daemon, no shared state across hook invocations, and no global verdict registry that grows or stales.

## Concept diagram

```
                    ┌──────────────────────────────┐
                    │       bindings.yaml          │   single source of truth:
                    │  verdicts | sets | bindings  │   verdicts, prompts,
                    │  remediation                 │   remediation, sets, bindings
                    └──────────────┬───────────────┘
                                   │ yaml.compose + validate
                                   ▼
        ┌──────────────────────────────────────────────────────┐
        │                Arbiter Engine                        │
        │   ┌─────────┐    ┌──────────┐    ┌──────────────┐    │
        │   │ Loader  │───▶│ Resolver │───▶│  Dispatcher  │    │
        │   └─────────┘    └──────────┘    └──────┬───────┘    │
        │   parse +        flatten sets,          │            │
        │   validate       dedupe verdicts        ▼            │
        │   (loud)                          ┌──────────┐       │
        │                                   │  Client  │       │
        │                                   │  (HTTP)  │       │
        │                                   └────┬─────┘       │
        │                                        │             │
        │                                        ▼             │
        │   ┌──────────────────┐    ┌──────────────────┐       │
        │   │ Body Extractors  │    │  Output Emitters │       │
        │   │ (per event,tool) │    │  (per event)     │       │
        │   └──────────────────┘    └──────────────────┘       │
        └──────────────────────────────────────────────────────┘
                                   │ JSON to stdout
                                   ▼
                          Claude Code hook event
```

## Trace: one event end to end

The trace below follows a `PreToolUse` payload for the `ExitPlanMode` tool through the engine, with the binding declaring `action: deny` and a `plan_review` verdict set. Pick this binding because it exercises every part of the engine — a tool-specific extractor, a plan framing, parallel judge calls, suppression logic, and the `deny` emitter — in a single trace.

A maintainer reading at the file level can match each step below to a `lib/` symbol.

**1. Entry.** Claude Code spawns the hook script `~/.claude/scripts/hooks/arbiter-hook.py`. The script reads the hook payload from stdin, sets up `lib/` on the import path, and calls `dispatch(payload, sys.stdout)` (`lib/dispatcher.py`).

**2. Load bindings.** `dispatcher._load()` calls `config.load_bindings(BINDINGS_PATH)` once per process and caches the result. The loader (`lib/config.py`) parses `bindings.yaml` via `yaml.compose` to keep node line and column information, walks the resulting node tree, and validates against the schema. Every error is loud: a `ConfigError` with `<file>:<line>:<column>: <message>` propagates up through the dispatcher to stderr with a non-zero exit, so the user sees exactly where the YAML went wrong. The loader produces a `Bindings` value object: `VerdictSpec` records keyed by verdict id, a remediation paragraph map, and a tuple of `Binding` records.

**3. Resolve `(event, tool)`.** `dispatcher._resolve_event_tool(payload)` reads `hook_event_name` and `tool_name` directly from the payload. For the trace this returns `("PreToolUse", "ExitPlanMode")`. If `hook_event_name` is missing, the dispatcher falls back to `PreToolUse` when `tool_name` is present and `Stop` otherwise — older payload shapes still resolve.

**4. Find the matching binding.** `dispatcher._find_binding(...)` returns the first binding whose event matches and whose tool either equals the payload's tool or is unspecified. For the trace it returns the `PreToolUse` / `ExitPlanMode` / `deny` binding from `bindings.yaml`. A miss returns `None`, and the dispatcher returns silently — Arbiter does not block events it has no opinion on.

**5. Extract the body.** `extract.extract_body("PreToolUse", "ExitPlanMode", payload)` (`lib/extract.py`) looks up the `(event, tool)` pair in the built-in extractor map and dispatches to `_plan_extractor`. That function reads `tool_input` from the payload and returns the first non-empty string under the keys `plan`, `content`, `summary`, `text`, `body`, falling back to a join of any non-empty string field. A missing extractor returns `None`, and the dispatcher returns silently rather than guessing.

**6. Pick the framing.** `frame.get_framing("PreToolUse")` (`lib/frame.py`) returns the plan framing: `"You judge an `ExitPlanMode` plan body for one specific issue. The body is between BEGIN and END markers.\n\n"`. A missing framing also returns silently — the dispatcher treats either gap as a no-op.

**7. Quick-exit check.** The dispatcher scrubs code from the body via `extract.strip_code(body)`, then builds a quick-exit regex from the binding's verdict names. If the scrubbed body literally contains a verdict name like `OPEN_QUESTIONS`, the assistant is discussing the rules rather than tripping them, the dispatcher logs `CLEAR:quick-exit` and returns silently. The pattern is built fresh per dispatch from the matched binding's verdict list, so there is no global pattern that grows or stales.

**8. Diagnostic short-circuit.** If `BLOCK_PLAN_NO_JUDGE=1` is set in the environment, the dispatcher emits the static `compose.FALLBACK_REPLAN_SLIM` message via the binding's action shape and returns. This is the only way to exercise the fallback path without taking the `mlx_lm.server` down.

**9. Judge the body.** Otherwise the dispatcher calls `client.judge_many(body, framing, verdict_specs, event)` (`lib/client.py`). `judge_many` opens a `ThreadPoolExecutor` with one worker per verdict and submits one `_judge_one` call per spec. Each `_judge_one` POSTs `{model, stream: false, max_tokens, messages}` to `http://127.0.0.1:11436/v1/chat/completions`, with the system message set to `framing + verdict.prompt + _OUTPUT_INSTRUCTION` and the user message wrapping the body between BEGIN and END markers. The model is instructed to answer `yes` or `no` with the Qwen3 `/no_think` directive appended; the response is parsed with a strict-first-word reader at the boundary (after stripping the empty `<think></think>` block). Any deviation returns `None` from `_judge_one` and propagates up as a fail-closed signal. `judge_many` appends one line to `~/.claude/arbiter/logs/arbiter.log` recording event, elapsed milliseconds, and either the fired verdict names, `CLEAR`, or `ERROR:<keys>`.

The return value is `None` if any single call failed, `[]` if no verdicts fired, or `[verdict_key, ...]` if some did.

**10. Fail-closed branch.** On `None`, the dispatcher emits `compose.FALLBACK_REPLAN_SLIM` via the binding's action shape and returns. The fallback is a fixed paragraph that names the four classes of issue and tells the user how to start the server (`arbiter-up.sh`). A silent disablement on outage would defeat the safety net.

**11. Empty branch.** On `[]`, the dispatcher returns silently. No verdict fired, so there is nothing to block on.

**12. Apply suppression.** On a non-empty list, the dispatcher reads `payload["transcript_path"]` and calls `extract.latest_turn_tool_uses(transcript_path)`, which walks the transcript backwards from the end, stops at the first user entry, and collects the names of every `tool_use` block in the assistant entries between. The dispatcher then drops every verdict whose `suppress_when.tools_in_turn` intersects that set. If the remaining list is empty, the dispatcher returns silently.

**13. Compose the message.** `compose.compose_message(fired_specs, remediation, "PreToolUse")` (`lib/compose.py`) builds the block text. The shape is: `ORIENTATION_PREFIX` (`*\n\n`), `Arbiter fired: \`<comma-separated verdict names>\`.`, the glossary lines for the fired verdicts only, the per-event remediation lead pulled from `_REMEDIATION_LEAD` (`PreToolUse` says "Re-read the plan and address each verdict before re-emitting `ExitPlanMode`"), and the remediation paragraphs whose keys appear in the fired verdicts, in declaration order, deduped.

**14. Emit.** `emit.emit("PreToolUse", "deny", message, sys.stdout)` (`lib/emit.py`) writes the JSON shape Claude Code expects for a `PreToolUse` deny:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "<message>"
  },
  "systemMessage": "<message>"
}
```

Claude Code reads stdout, denies the `ExitPlanMode` tool call, and surfaces the message as the deny reason for the assistant's next action.

## Body extractors

Built-in map keyed on `(event, tool)`. Every binding referenced by `bindings.yaml` has a matching entry. A `(event, tool)` pair with no extractor returns `None`, and the dispatcher treats that as a no-op rather than guessing.

| Event | Tool | Extractor |
|-------|----------------|-----------|
| `PreToolUse` | `ExitPlanMode` | reads the plan body from `tool_input` (tries `plan` / `content` / `summary` / `text` / `body` keys, then any non-empty string field) |
| `Stop` | — | reads the most recent text-bearing assistant entry from `transcript_path` |
| `SubagentStop` | — | reads the most recent text-bearing assistant entry from `transcript_path` |

## Framings

Built-in map keyed on event. The framing prefixes the verdict prompt sent to the model so the verdict itself can stay general.

| Event | Framing |
|-------|---------|
| `PreToolUse` | "You judge an `ExitPlanMode` plan body for one specific issue. ..." |
| `Stop` | "You judge an assistant's turn-ending message for one specific issue. ..." |
| `SubagentStop` | "You judge an assistant's turn-ending message for one specific issue. ..." |

## Output emitters

Built-in map keyed on `(event, action)`. The `(event, action)` pair is validated at config-load time, so the dispatcher never reaches an emitter that does not exist. The defensive `RuntimeError` exists only to surface a programming mistake if one ever slipped through.

| Event | Action | JSON shape |
|-------|--------|-----------|
| `PreToolUse` | `deny` | `hookSpecificOutput.permissionDecision: "deny"` |
| `PreToolUse` | `ask` | `hookSpecificOutput.permissionDecision: "ask"` |
| `Stop` | `block` | top-level `decision: "block"` |
| `SubagentStop` | `block` | top-level `decision: "block"` |
| `PostToolUse` | `inject` | `hookSpecificOutput.additionalContext: <message>` |
| `UserPromptSubmit` | `inject` | `hookSpecificOutput.additionalContext: <message>` |

## Failure modes

| Failure | Behavior |
|---------|----------|
| YAML parse error | `ConfigError` with `<file>:<line>:<col>: <yaml problem>` |
| Unknown verdict / event / tool / action / remediation key | `ConfigError` with `<file>:<line>:<col>: <reason>` |
| Mismatched `(event, action)` | `ConfigError` rejecting the binding at load time |
| Body extractor missing for an `(event, tool)` | Dispatcher returns silently — no false block |
| Framing missing for an event | Dispatcher returns silently — no false block |
| `mlx_lm.server` unreachable or malformed response | Dispatcher emits `FALLBACK_REPLAN_SLIM` via the binding's action shape — fail closed |
| `BLOCK_PLAN_NO_JUDGE=1` set | Same fallback emission, no HTTP calls — for diagnosing the server |

## Pipeline summary

```
hook payload
   │
   ▼
load_bindings(bindings.yaml)         loud-failure on any schema or parse problem
   │
   ▼
resolve (event, tool)
find first matching binding          (no match → silent return)
   │
   ▼
extract_body(event, tool, payload)   built-in map; missing target → silent return
get_framing(event)                   built-in map; missing event → silent return
   │
   ▼
strip_code(body)
quick_exit regex over verdict names  meta-discussion → silent return
   │
   ▼
client.judge_many(body, framing,     parallel ThreadPoolExecutor; one POST per verdict
                  verdicts, event)
   │
   ├─ None        → emit FALLBACK_REPLAN_SLIM via (event, action) emitter
   ├─ []          → silent return
   └─ [verdicts]  → apply suppressions (tools_in_turn ∩ latest_turn_tool_uses)
                    │
                    ├─ all suppressed → silent return
                    └─ some remain    → compose_message(...) + emit(event, action, msg)
```

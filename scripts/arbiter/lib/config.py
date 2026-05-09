"""YAML loader for `bindings.yaml`.

Errors are loud: every parse and schema problem raises `ConfigError`
with `<file>:<line>:<column>: <message>`. The dispatcher does not
swallow these — they propagate to stderr and exit non-zero so the
user sees exactly where the problem is.

Validation covers:
- top-level shape (`verdicts` and `bindings` required)
- per-verdict fields (`prompt`, `glossary`, `remediation`, optional
  `suppress_when.tools_in_turn`)
- remediation paragraphs match the keys named by verdicts
- bindings reference verdicts that exist
- the `(event, action)` pair is valid for each binding
"""

import dataclasses
from pathlib import Path

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode


class ConfigError(Exception):
    """Raised on any parse or schema problem in bindings.yaml."""


# Action vocabulary. Each action is valid only for specific events.
# Arbiter rejects mismatches at load time so dead paths fail loud.
#
# `allow` is a runtime-only action: the dispatcher swaps a `deny`
# binding to `allow` when block-once policy lifts the deny on a
# re-emission. Bindings in YAML never declare `allow` directly — but
# the whitelist accepts it so the emit shape is valid for the
# `(PreToolUse, allow)` pair the dispatcher constructs at runtime.
ALLOWED_ACTIONS: frozenset[str] = frozenset({"deny", "ask", "block", "inject", "allow"})

ACTION_EVENTS: dict[str, frozenset[str]] = {
    "deny": frozenset({"PreToolUse"}),
    "ask": frozenset({"PreToolUse"}),
    "allow": frozenset({"PreToolUse"}),
    "block": frozenset({"Stop", "SubagentStop"}),
    "inject": frozenset({"PostToolUse", "UserPromptSubmit"}),
}


@dataclasses.dataclass(frozen=True)
class VerdictSpec:
    """One verdict definition lifted from bindings.yaml.

    `name` is the uppercased token that appears in block messages and
    the quick-exit regex. `key` is the snake_case YAML key bindings
    refer to. `remediation` is the ordered tuple of remediation keys
    this verdict pulls in when it fires.
    """

    name: str
    key: str
    prompt: str
    glossary: str
    remediation: tuple[str, ...]
    suppress_tools_in_turn: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class Binding:
    """One row from the `bindings:` list — what to do for a given hook target."""

    event: str
    tool: str | None
    verdict_ids: tuple[str, ...]
    action: str
    line: int


@dataclasses.dataclass(frozen=True)
class Bindings:
    """Validated bindings.yaml as Python data."""

    verdicts: dict[str, VerdictSpec]
    remediation: dict[str, str]
    bindings: tuple[Binding, ...]
    source_path: Path


def _err(path: Path, node, msg: str):
    mark = node.start_mark if node is not None else None
    if mark is not None:
        raise ConfigError(f"{path}:{mark.line + 1}:{mark.column + 1}: {msg}")
    raise ConfigError(f"{path}: {msg}")


def _expect_map(path: Path, node, label: str) -> MappingNode:
    if not isinstance(node, MappingNode):
        _err(path, node, f"{label}: expected mapping")
    return node


def _expect_seq(path: Path, node, label: str) -> SequenceNode:
    if not isinstance(node, SequenceNode):
        _err(path, node, f"{label}: expected sequence")
    return node


def _expect_str(path: Path, node, label: str) -> str:
    if not isinstance(node, ScalarNode):
        _err(path, node, f"{label}: expected string")
    return node.value


def _map_keys(node: MappingNode) -> dict[str, tuple]:
    """Return {key: (key_node, value_node)} for each top-level pair.

    Skips entries whose key is not a plain scalar — the schema only
    accepts string keys at the levels Arbiter parses.
    """
    out: dict[str, tuple] = {}
    for key_node, val_node in node.value:
        if isinstance(key_node, ScalarNode):
            out[key_node.value] = (key_node, val_node)
    return out


def _parse_verdicts(path: Path, node) -> dict[str, VerdictSpec]:
    _expect_map(path, node, "'verdicts'")
    out: dict[str, VerdictSpec] = {}
    known_fields = {"prompt", "glossary", "remediation", "suppress_when"}
    for key_node, val_node in node.value:
        if not isinstance(key_node, ScalarNode):
            _err(path, key_node, "verdict key must be a string")
        key = key_node.value
        _expect_map(path, val_node, f"verdict '{key}'")
        fields = _map_keys(val_node)
        for required in ("prompt", "glossary", "remediation"):
            if required not in fields:
                _err(path, val_node, f"verdict '{key}': missing '{required}'")
        for fk, (fk_node, _) in fields.items():
            if fk not in known_fields:
                _err(path, fk_node, f"verdict '{key}': unknown field '{fk}'")

        prompt = _expect_str(path, fields["prompt"][1], f"verdict '{key}' prompt")
        glossary = _expect_str(path, fields["glossary"][1], f"verdict '{key}' glossary")

        rem_node = _expect_seq(path, fields["remediation"][1], f"verdict '{key}' remediation")
        remediation: list[str] = []
        for item in rem_node.value:
            if not isinstance(item, ScalarNode):
                _err(path, item, f"verdict '{key}' remediation item must be a string")
            remediation.append(item.value)

        suppress_tools: tuple[str, ...] = ()
        if "suppress_when" in fields:
            sw_node = fields["suppress_when"][1]
            _expect_map(path, sw_node, f"verdict '{key}' suppress_when")
            sw_fields = _map_keys(sw_node)
            if "tools_in_turn" not in sw_fields:
                _err(
                    path,
                    sw_node,
                    f"verdict '{key}' suppress_when: only 'tools_in_turn' is supported; missing it",
                )
            for sk, (sk_node, _) in sw_fields.items():
                if sk != "tools_in_turn":
                    _err(path, sk_node, f"verdict '{key}' suppress_when: unknown key '{sk}'")
            tit_node = _expect_seq(
                path, sw_fields["tools_in_turn"][1], f"verdict '{key}' suppress_when.tools_in_turn"
            )
            tools: list[str] = []
            for item in tit_node.value:
                if not isinstance(item, ScalarNode):
                    _err(
                        path,
                        item,
                        f"verdict '{key}' suppress_when.tools_in_turn item must be a string",
                    )
                tools.append(item.value)
            suppress_tools = tuple(tools)

        out[key] = VerdictSpec(
            name=key.upper(),
            key=key,
            prompt=prompt,
            glossary=glossary,
            remediation=tuple(remediation),
            suppress_tools_in_turn=suppress_tools,
        )
    return out


def _parse_remediation(path: Path, node) -> dict[str, str]:
    _expect_map(path, node, "'remediation'")
    out: dict[str, str] = {}
    for key_node, val_node in node.value:
        if not isinstance(key_node, ScalarNode):
            _err(path, key_node, "remediation key must be a string")
        key = key_node.value
        if not isinstance(val_node, ScalarNode):
            _err(path, val_node, f"remediation '{key}' must be a string")
        out[key] = val_node.value
    return out


def _parse_bindings(path: Path, node, verdicts: dict[str, VerdictSpec]) -> tuple[Binding, ...]:
    _expect_seq(path, node, "'bindings'")
    out: list[Binding] = []
    known_fields = {"event", "tool", "verdicts", "action"}
    for item in node.value:
        _expect_map(path, item, "binding entry")
        f = _map_keys(item)
        for required in ("event", "verdicts", "action"):
            if required not in f:
                _err(path, item, f"binding: missing '{required}'")
        for fk, (fk_node, _) in f.items():
            if fk not in known_fields:
                _err(path, fk_node, f"binding: unknown field '{fk}'")

        event = _expect_str(path, f["event"][1], "binding event")
        action = _expect_str(path, f["action"][1], "binding action")
        if action not in ALLOWED_ACTIONS:
            _err(
                path,
                f["action"][1],
                f"unknown action '{action}'; expected one of {sorted(ALLOWED_ACTIONS)}",
            )
        valid_events = ACTION_EVENTS[action]
        if event not in valid_events:
            _err(
                path,
                item,
                f"action '{action}' invalid for event '{event}'; valid for {sorted(valid_events)}",
            )

        tool: str | None = None
        if "tool" in f:
            tool = _expect_str(path, f["tool"][1], "binding tool")

        v_node = _expect_seq(path, f["verdicts"][1], "binding verdicts")
        seen: set[str] = set()
        verdict_ids: list[str] = []
        for it in v_node.value:
            if not isinstance(it, ScalarNode):
                _err(path, it, "binding verdict must be a string")
            vid = it.value
            if vid not in verdicts:
                _err(path, it, f"binding references unknown verdict '{vid}'")
            if vid in seen:
                continue
            seen.add(vid)
            verdict_ids.append(vid)

        out.append(
            Binding(
                event=event,
                tool=tool,
                verdict_ids=tuple(verdict_ids),
                action=action,
                line=item.start_mark.line + 1,
            )
        )
    return tuple(out)


def load_bindings(path: Path) -> Bindings:
    """Read and validate `bindings.yaml`. Raises `ConfigError` on any problem."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"{path}: cannot read file: {exc}") from None

    try:
        root = yaml.compose(text)
    except yaml.YAMLError as exc:
        problem = getattr(exc, "problem", str(exc)) or str(exc)
        mark = getattr(exc, "problem_mark", None)
        if mark is not None:
            raise ConfigError(f"{path}:{mark.line + 1}:{mark.column + 1}: {problem}") from None
        raise ConfigError(f"{path}: {problem}") from None

    if root is None:
        raise ConfigError(f"{path}: empty document")
    if not isinstance(root, MappingNode):
        _err(path, root, "top-level must be a mapping")

    top = _map_keys(root)

    if "verdicts" not in top:
        _err(path, root, "missing required key 'verdicts'")
    if "bindings" not in top:
        _err(path, root, "missing required key 'bindings'")

    verdicts = _parse_verdicts(path, top["verdicts"][1])

    remediation: dict[str, str] = {}
    if "remediation" in top:
        remediation = _parse_remediation(path, top["remediation"][1])

    # Verdict remediation refs must resolve.
    for vkey, vspec in verdicts.items():
        for r in vspec.remediation:
            if r not in remediation:
                # Use the verdict node for location since the ref is inside it.
                _err(
                    path,
                    top["verdicts"][1],
                    f"verdict '{vkey}' references unknown remediation key '{r}'",
                )

    bindings = _parse_bindings(path, top["bindings"][1], verdicts)

    return Bindings(
        verdicts=verdicts,
        remediation=remediation,
        bindings=bindings,
        source_path=path,
    )

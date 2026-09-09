#!/usr/bin/env python3.14
"""Resolve a model's ruleset and deliver it, or print it for inspection.

Nothing under `rulesets/` auto-loads, so a session's user rules arrive
through this module and a hook that fails leaves the session with none.
The delivery path therefore answers with the `default` tier's bodies
wherever a tier, a manifest, or a body is unavailable, and names what
failed in the text it delivers.
"""

import argparse
import dataclasses
import json
import os
import pathlib
import sys

import yaml

CONFIG_ENV = "CLAUDE_CONFIG_DIR"
STATE_ENV = "RULESETS_STATE_DIR"


def _audit():
    """The audit module, imported whether this runs as a package or a script."""

    try:
        from . import audit
    except ImportError:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
        from rulesets import audit
    return audit


DEFAULT_TIER = "default"
TIERS = (DEFAULT_TIER, "fable", "opus", "sonnet", "haiku")


def config_root() -> pathlib.Path:
    """The configuration directory every other path derives from."""

    override = os.environ.get(CONFIG_ENV)
    if override:
        return pathlib.Path(override)
    return pathlib.Path.home() / ".claude"


def load_dir() -> pathlib.Path:
    """The directory the harness itself auto-loads."""

    return config_root() / "rules"


def rulesets_root() -> pathlib.Path:
    """The root holding one directory per tier."""

    return config_root() / "rulesets"


def manifest_path() -> pathlib.Path:
    return rulesets_root() / "manifest.yaml"


def state_dir() -> pathlib.Path:
    """Where per-session records live, with its own override."""

    override = os.environ.get(STATE_ENV)
    if override:
        return pathlib.Path(override)
    return config_root() / ".tmp" / "rulesets"


def naming_line(stem: str) -> str:
    """The line that precedes a body, naming the stem it carries."""

    return f"<!-- rule: {stem} -->"


@dataclasses.dataclass(frozen=True)
class Ruleset:
    """A tier's composed text and the stems it carries."""

    tier: str
    stems: tuple[str, ...]
    text: str


@dataclasses.dataclass(frozen=True)
class NoRuleset:
    """No text resolved, with the reason named for the delivered header."""

    reason: str


def default_ruleset(root: pathlib.Path | str | None = None) -> Ruleset | NoRuleset:
    """The `default` tier's bodies, ordered by stem."""

    directory = pathlib.Path(root if root is not None else rulesets_root()) / DEFAULT_TIER
    bodies = sorted(directory.glob("*.md")) if directory.is_dir() else []
    if not bodies:
        return NoRuleset(reason=f"no rule bodies under {directory}")

    sections = [
        f"{naming_line(body.stem)}\n{body.read_text(encoding='utf-8').strip('\n')}\n"
        for body in bodies
    ]

    return Ruleset(
        tier=DEFAULT_TIER,
        stems=tuple(body.stem for body in bodies),
        text="\n".join(sections),
    )


@dataclasses.dataclass(frozen=True)
class Finding:
    """One illegal state, named by its kind and by stem and path."""

    kind: str
    message: str


@dataclasses.dataclass(frozen=True)
class ManifestOk:
    tiers: dict[str, object]


@dataclasses.dataclass(frozen=True)
class ManifestError:
    message: str


@dataclasses.dataclass(frozen=True)
class Wildcard:
    """Every stem the `default` directory holds, less the exclusions."""

    exclude: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class Explicit:
    """The stems the tier's own list states, and no others."""

    stems: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class Composition:
    """One tier's stems, the body path of each, and what was illegal."""

    tier: str
    stems: tuple[str, ...]
    body_paths: dict[str, pathlib.Path]
    findings: tuple[Finding, ...]


def _base(root: pathlib.Path | str | None) -> pathlib.Path:
    """The rulesets root, absolute, so every reported path is absolute."""

    chosen = pathlib.Path(root) if root is not None else rulesets_root()
    return chosen if chosen.is_absolute() else chosen.resolve()


def load_manifest(root: pathlib.Path | str | None = None) -> ManifestOk | ManifestError:
    """Read the manifest's `tiers` mapping, or name why it could not."""

    path = _base(root) / "manifest.yaml"
    if not path.is_file():
        return ManifestError(message=f"no manifest at {path}")
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return ManifestError(message=f"the manifest at {path} did not parse: {exc}")
    if not isinstance(document, dict) or not isinstance(document.get("tiers"), dict):
        return ManifestError(message=f"the manifest at {path} carries no tiers mapping")
    return ManifestOk(tiers=document["tiers"])


def tier_stems(root: pathlib.Path, tier: str) -> tuple[str, ...]:
    """The stems whose bodies one tier's directory holds."""

    directory = root / tier
    if not directory.is_dir():
        return ()
    return tuple(sorted(path.stem for path in directory.glob("*.md")))


def _tier_form(
    tier: str, entry: object, manifest: pathlib.Path
) -> tuple[Wildcard | Explicit, tuple[Finding, ...]]:
    if not isinstance(entry, dict):
        return Explicit(stems=()), (
            Finding("bad-form", f"tier {tier} in {manifest} is not a mapping"),
        )

    include = entry.get("include")
    exclude = tuple(entry.get("exclude") or ())

    if include == "*":
        return Wildcard(exclude=exclude), ()

    if isinstance(include, list):
        if "*" in include:
            return Wildcard(exclude=exclude), (
                Finding(
                    "mixed-form",
                    f"tier {tier} in {manifest} mixes the wildcard into an include list",
                ),
            )
        if exclude:
            return Explicit(stems=tuple(include)), (
                Finding(
                    "mixed-form",
                    f"tier {tier} in {manifest} states an explicit include list beside an exclude",
                ),
            )
        return Explicit(stems=tuple(include)), ()

    return Explicit(stems=()), (
        Finding("bad-form", f"tier {tier} in {manifest} states no include of either form"),
    )


def compose(tier: str, root: pathlib.Path | str | None = None) -> Composition:
    """Map a tier to its stems and each stem to the body it reads.

    Every read happens per call, so composing one tier leaves what
    composing another yields untouched.
    """

    base = _base(root)
    manifest_file = base / "manifest.yaml"
    manifest = load_manifest(base)
    if isinstance(manifest, ManifestError):
        return Composition(tier, (), {}, (Finding("manifest", manifest.message),))

    if tier not in manifest.tiers:
        return Composition(
            tier,
            (),
            {},
            (Finding("missing-tier", f"the manifest at {manifest_file} names no tier {tier}"),),
        )

    form, findings = _tier_form(tier, manifest.tiers[tier], manifest_file)
    known = {stem for name in TIERS for stem in tier_stems(base, name)}

    match form:
        case Wildcard(exclude=exclude):
            stems = tuple(s for s in tier_stems(base, DEFAULT_TIER) if s not in exclude)
            findings += tuple(
                Finding(
                    "stale-exclusion",
                    f"tier {tier} in {manifest_file} excludes {stem}, which no tier directory holds",
                )
                for stem in exclude
                if stem not in known
            )
        case Explicit(stems=listed):
            stems = listed

    body_paths = {}
    for stem in stems:
        own = base / tier / f"{stem}.md"
        fallback = base / DEFAULT_TIER / f"{stem}.md"
        if own.is_file():
            body_paths[stem] = own
        elif fallback.is_file():
            body_paths[stem] = fallback
        else:
            findings += (Finding("no-body", f"stem {stem} has no body at {own} nor at {fallback}"),)

    return Composition(tier, stems, body_paths, findings)


def report(root: pathlib.Path | str | None = None) -> tuple[Finding, ...]:
    """Every illegal state the manifest and the layout carry."""

    base = _base(root)
    manifest = load_manifest(base)
    if isinstance(manifest, ManifestError):
        return (Finding("manifest", manifest.message),)

    findings: tuple[Finding, ...] = ()
    for tier in TIERS:
        composed = compose(tier, base)
        findings += composed.findings
        findings += tuple(
            Finding(
                "unreachable-body",
                f"the body at {base / tier / f'{stem}.md'} reaches no composition",
            )
            for stem in tier_stems(base, tier)
            if stem not in composed.stems
        )
    return findings


def delivered_text(result: Ruleset | NoRuleset) -> str:
    match result:
        case Ruleset():
            return result.text
        case NoRuleset():
            return f"{naming_line('unresolved')}\nNo ruleset resolved: {result.reason}.\n"


def command_deliver(args: argparse.Namespace) -> int:
    """Answer a hook payload with the ruleset to add to its context."""

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    output = deliver_payload(payload, root=args.root, state=args.state)
    if output:
        print(json.dumps(output))
    return 0


def command_inspect(args: argparse.Namespace) -> int:
    """Print one tier's stems and body paths, delivering nothing."""

    composed = compose(args.tier, args.root)
    for stem in composed.stems:
        path = composed.body_paths.get(stem)
        print(f"{stem}\t{path if path else '(no body)'}")
    for finding in composed.findings:
        print(f"{finding.kind}: {finding.message}")
    return 1 if composed.findings else 0


def command_check(args: argparse.Namespace) -> int:
    """Report every illegal state across all five tiers."""

    findings = report(args.root)
    for finding in findings:
        print(f"{finding.kind}: {finding.message}")
    return 1 if findings else 0


def manifest_stems(root: pathlib.Path | str | None = None) -> set[str]:
    """Every stem any tier's entry names."""

    base = _base(root)
    return {stem for tier in TIERS for stem in compose(tier, base).stems}


# --- Model tier lookup -------------------------------------------------------

HOST_MANAGED_VAR = "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST"
SUBAGENT_MODEL_VAR = "CLAUDE_CODE_SUBAGENT_MODEL"
SUBAGENT_FORCE_VAR = "CLAUDE_CODE_SUBAGENT_MODEL_FORCE"
COORDINATOR_FORCE_VAR = "CLAUDE_CODE_COORDINATOR_FORCE_WORKER_INHERIT_MODEL"
ANTHROPIC_MODEL_VAR = "ANTHROPIC_MODEL"
ANTHROPIC_DEFAULT_MODEL_VAR = "ANTHROPIC_DEFAULT_MODEL"

# The four profile variables, in the precedence order a collision resolves by.
PROFILE_VARS = (
    ("opus", "ANTHROPIC_DEFAULT_OPUS_MODEL"),
    ("sonnet", "ANTHROPIC_DEFAULT_SONNET_MODEL"),
    ("haiku", "ANTHROPIC_DEFAULT_HAIKU_MODEL"),
    ("fable", "ANTHROPIC_DEFAULT_FABLE_MODEL"),
)


@dataclasses.dataclass(frozen=True)
class TierLookup:
    """The tier a model identifier maps to, or None, with what to say."""

    tier: str | None
    source: str
    notes: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class Resolution:
    """A concrete tier to deliver, its source, and lines to state."""

    tier: str
    source: str
    notes: tuple[str, ...] = ()


def _flag(env: dict, name: str) -> bool:
    """Whether an environment flag is set to a true value."""

    value = env.get(name)
    return bool(value) and value not in ("0", "false", "False")


def load_models(root: pathlib.Path | str | None = None) -> dict[str, tuple[str, ...]]:
    """The built-in identifier prefixes per tier, read from `models.yaml`."""

    path = _base(root) / "models.yaml"
    if not path.is_file():
        return {}
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {}
    if not isinstance(document, dict):
        return {}
    result = {}
    for tier, _ in PROFILE_VARS:
        patterns = document.get(tier)
        if isinstance(patterns, list):
            result[tier] = tuple(str(p) for p in patterns)
    return result


def tier_lookup(
    identifier: str | None, root: pathlib.Path | str | None = None, env: dict | None = None
) -> TierLookup:
    """Map a model identifier to a tier: profile variables, then built-ins."""

    env = os.environ if env is None else env
    notes: tuple[str, ...] = ()
    if _flag(env, HOST_MANAGED_VAR):
        notes += (
            f"{HOST_MANAGED_VAR} is set, so the harness may have used a model the "
            "profile variables do not name",
        )

    matches = [
        (tier, var) for tier, var in PROFILE_VARS if identifier and env.get(var) == identifier
    ]
    if matches:
        tier, var = matches[0]
        if len(matches) > 1:
            names = " and ".join(var for _, var in matches)
            notes += (f"the profile variables {names} both name {identifier}",)
        return TierLookup(tier, f"the {var} variable", notes)

    builtin = load_models(root)
    for tier, _ in PROFILE_VARS:
        for pattern in builtin.get(tier, ()):
            if identifier and identifier.startswith(pattern):
                return TierLookup(tier, "the built-in identifier list", notes)

    return TierLookup(None, f"no tier matched the identifier {identifier}", notes)


def _fall_open(source: str, identifier: str, notes: tuple[str, ...]) -> Resolution:
    """Deliver `default` and say which identifier went unmatched."""

    return Resolution(
        DEFAULT_TIER, source, (*notes, f"no tier matched {identifier}, so default was used")
    )


def session_resolution(
    payload: dict,
    root: pathlib.Path | str | None = None,
    state: pathlib.Path | str | None = None,
    env: dict | None = None,
) -> Resolution:
    """The tier a session runs at: the harness's model, then the environment."""

    audit = _audit()

    env = os.environ if env is None else env
    identifier = payload.get("model")
    if identifier:
        look = tier_lookup(identifier, root, env)
        source = f"the harness-reported model {identifier}"
        if look.tier:
            return Resolution(look.tier, source, look.notes)
        return _fall_open(source, identifier, look.notes)

    for var in (ANTHROPIC_MODEL_VAR, ANTHROPIC_DEFAULT_MODEL_VAR):
        value = env.get(var)
        if value:
            look = tier_lookup(value, root, env)
            source = f"the {var} variable ({value})"
            if look.tier:
                return Resolution(look.tier, source, look.notes)
            return _fall_open(source, value, look.notes)

    session_id = payload.get("session_id")
    recorded = audit.read_tier(session_id, state) if session_id else None
    if recorded:
        return Resolution(recorded, "the session's recorded tier", ())

    return Resolution(
        DEFAULT_TIER,
        "no model identifier was available",
        ("neither the harness nor the environment named a model, and no tier was recorded",),
    )


def agents_dir() -> pathlib.Path:
    """Where the agent definitions the harness reads live."""

    return config_root() / "agents"


def definition_pin(agent_type: str | None, definitions: dict | None = None) -> str | None:
    """The model an agent definition pins, keyed by the agent type."""

    if not agent_type:
        return None
    if definitions is not None:
        return definitions.get(agent_type)
    path = agents_dir() / f"{agent_type}.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    closing = text.find("\n---", 3)
    if closing == -1:
        return None
    try:
        front = yaml.safe_load(text[3:closing])
    except yaml.YAMLError:
        return None
    if isinstance(front, dict):
        model = front.get("model")
        return str(model) if model else None
    return None


def delegate_resolution(
    payload: dict,
    root: pathlib.Path | str | None = None,
    state: pathlib.Path | str | None = None,
    env: dict | None = None,
    definitions: dict | None = None,
) -> Resolution:
    """The tier a delegate runs at: force levers, then the four ranked sources."""

    audit = _audit()

    env = os.environ if env is None else env
    session_id = payload.get("session_id")
    agent_type = payload.get("agent_type")
    prompt_id = payload.get("prompt_id")

    parent_tier = audit.read_tier(session_id, state) if session_id else None

    def parent(source: str, notes: tuple[str, ...] = ()) -> Resolution:
        if parent_tier:
            return Resolution(parent_tier, source, notes)
        return Resolution(
            DEFAULT_TIER, source, (*notes, "no parent tier was recorded, so default was used")
        )

    def from_identifier(
        identifier: str, source: str, notes: tuple[str, ...] = ()
    ) -> Resolution | None:
        look = tier_lookup(identifier, root, env)
        if look.tier:
            return Resolution(look.tier, source, notes + look.notes)
        return None

    if agent_type == "fork":
        return parent("the parent session's tier, since a fork runs the main model")

    if _flag(env, COORDINATOR_FORCE_VAR):
        return parent(f"the {COORDINATOR_FORCE_VAR} lever, forcing the parent tier")

    if _flag(env, SUBAGENT_FORCE_VAR):
        if agent_type == "Explore":
            return parent(f"the parent tier, since {SUBAGENT_FORCE_VAR} leaves Explore its own cap")
        forced = env.get(SUBAGENT_MODEL_VAR)
        if forced:
            resolved = from_identifier(
                forced, f"the {SUBAGENT_MODEL_VAR} variable under {SUBAGENT_FORCE_VAR}"
            )
            if resolved:
                return resolved
        return parent(f"the parent tier, since {SUBAGENT_FORCE_VAR} is set with no readable model")

    notes: tuple[str, ...] = ()
    if session_id and prompt_id and agent_type:
        models = audit.read_spawns(session_id, prompt_id, agent_type, state)
        if len(models) == 1:
            resolved = from_identifier(models[0], f"the per-spawn model {models[0]}")
            if resolved:
                return resolved
        elif len(models) > 1:
            notes += (
                f"several spawns share prompt {prompt_id} and type {agent_type}, so the "
                "per-spawn model is ambiguous",
            )
    else:
        notes += ("the per-spawn model was unreadable at this delegate's start",)

    pin = definition_pin(agent_type, definitions)
    if pin:
        resolved = from_identifier(pin, f"the {agent_type} definition's model pin ({pin})", notes)
        if resolved:
            return resolved

    default_var = env.get(SUBAGENT_MODEL_VAR)
    if default_var:
        resolved = from_identifier(default_var, f"the {SUBAGENT_MODEL_VAR} default variable", notes)
        if resolved:
            return resolved

    return parent("the parent session's recorded tier", notes)


def switch_resolution(
    payload: dict, root: pathlib.Path | str | None = None, env: dict | None = None
) -> Resolution:
    """The tier a mid-session switch moves to, read from `to_model`."""

    env = os.environ if env is None else env
    to_model = payload.get("to_model")
    look = tier_lookup(to_model, root, env)
    source = f"the switch to {to_model}"
    if look.tier:
        return Resolution(look.tier, source, look.notes)
    return _fall_open(source, to_model, look.notes)


# --- Delivery ----------------------------------------------------------------


def tier_ruleset(tier: str, root: pathlib.Path | str | None = None) -> Ruleset | NoRuleset:
    """One tier's composed bodies, or the reason none resolved."""

    composed = compose(tier, root)
    fatal = [f for f in composed.findings if f.kind in ("manifest", "missing-tier", "no-body")]
    if not composed.stems or fatal:
        reason = "; ".join(f.message for f in composed.findings) or f"tier {tier} composed no stems"
        return NoRuleset(reason=reason)

    sections = []
    for stem in composed.stems:
        path = composed.body_paths.get(stem)
        if path and path.is_file():
            sections.append(
                f"{naming_line(stem)}\n{path.read_text(encoding='utf-8').strip('\n')}\n"
            )
    if not sections:
        return NoRuleset(reason=f"tier {tier} composed no readable bodies")
    return Ruleset(tier=tier, stems=composed.stems, text="\n".join(sections))


def delivery_header(tier: str, source: str, stem_count: int, notes: tuple[str, ...]) -> str:
    """The opening line naming the tier, its source, and the stem count."""

    lines = [f"<!-- ruleset: tier {tier}, from {source}, {stem_count} stems -->"]
    lines += [f"<!-- note: {note} -->" for note in notes]
    return "\n".join(lines)


@dataclasses.dataclass(frozen=True)
class Delivered:
    """A ruleset ready for a context, with the record it should log."""

    event: str
    text: str
    tier: str
    source: str
    stems: tuple[str, ...]
    scope: str


def _delivered(res: Resolution, event: str, scope: str, root) -> Delivered:
    """Compose the resolution's tier, falling open to `default` if it can't."""

    tier, source, notes = res.tier, res.source, res.notes
    ruleset = tier_ruleset(tier, root)
    if isinstance(ruleset, NoRuleset):
        fallback = default_ruleset(root)
        if isinstance(fallback, Ruleset):
            notes = (*notes, f"tier {tier} was unavailable ({ruleset.reason}), so default was used")
            tier, ruleset = DEFAULT_TIER, fallback
        else:
            text = delivery_header(tier, source, 0, (*notes, ruleset.reason))
            return Delivered(event, text, tier, source, (), scope)

    header = delivery_header(tier, source, len(ruleset.stems), notes)
    return Delivered(event, f"{header}\n\n{ruleset.text}", tier, source, ruleset.stems, scope)


def deliver_payload(
    payload: dict,
    root: pathlib.Path | str | None = None,
    state: pathlib.Path | str | None = None,
    env: dict | None = None,
) -> dict:
    """Answer a hook payload with the ruleset to add, and record it."""

    audit = _audit()

    env = os.environ if env is None else env
    event = payload.get("hook_event_name") or "SessionStart"
    session_id = payload.get("session_id")
    agent_id = payload.get("agent_id")
    prompt_id = payload.get("prompt_id")

    if event == "PreToolUse":
        tool_input = payload.get("tool_input") or {}
        audit.append_spawn(
            session_id, prompt_id, tool_input.get("subagent_type"), tool_input.get("model"), state
        )
        return {}

    if event == "SubagentStart":
        res = delegate_resolution(payload, root, state, env)
        scope = "delegate"
    elif event == "PostModelSwitch":
        res = switch_resolution(payload, root, env)
        scope = "switch"
        if res.tier == audit.read_tier(session_id, state):
            return {}
    else:
        res = session_resolution(payload, root, state, env)
        scope = "session"

    delivered = _delivered(res, event, scope, root)

    audit.append_record(
        audit.delivery_record(
            session_id,
            delivered.tier,
            delivered.source,
            delivered.stems,
            scope,
            agent_id=agent_id,
            prompt_id=prompt_id if scope == "switch" else None,
        ),
        session_id=session_id or "session",
        agent_id=agent_id,
        state=state,
    )

    if scope in ("session", "switch") and session_id:
        audit.write_tier(session_id, delivered.tier, state)

    text = delivered.text
    if scope == "switch":
        text += "\n<!-- note: the earlier ruleset remains in the conversation above -->"

    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}


def _effective_deliveries(records: list[dict]) -> list[dict]:
    """Every delivery that reached context: of switches sharing a prompt_id,
    only the last survives, and a switch with no prompt_id survives."""

    last_switch_index: dict[str, int] = {}
    for index, record in enumerate(records):
        if record.get("scope") == "switch" and record.get("prompt_id"):
            last_switch_index[record["prompt_id"]] = index

    effective = []
    for index, record in enumerate(records):
        if (
            record.get("scope") == "switch"
            and record.get("prompt_id")
            and last_switch_index[record["prompt_id"]] != index
        ):
            continue
        effective.append(record)
    return effective


def command_delivery_check(args: argparse.Namespace) -> int:
    """Compare each delivery's stems against its tier's composition."""

    audit = _audit()

    records = [
        record
        for record in audit.read_records(args.session, args.state)
        if record.get("kind") == audit.DELIVERY
    ]
    problems = []
    for record in _effective_deliveries(records):
        tier = record.get("tier")
        composed = set(compose(tier, args.root).stems)
        delivered = set(record.get("stems") or [])
        for stem in sorted(composed - delivered):
            problems.append(f"{tier}: {stem} composed but not delivered")
        for stem in sorted(delivered - composed):
            problems.append(f"{tier}: {stem} delivered but not composed")
    for problem in problems:
        print(problem)
    return 1 if problems else 0


def _load_is_expected(record: dict, stems: set[str]) -> bool:
    """Whether one load record names a mechanism this change leaves alone.

    A CLAUDE.md at any scope loads by a mechanism outside the manifest,
    and so does a path-scoped rule, whose stem the manifest never names.
    A record naming a manifest stem is unexpected whatever its reason: an
    `include` from a `@path` import puts that stem back into every
    model's context exactly as an eager load would.
    """

    path = pathlib.Path(record.get("file_path") or "")
    if path.name == "CLAUDE.md":
        return True
    return path.stem not in stems


def command_load_check(args: argparse.Namespace) -> int:
    """Confirm no stem the manifest names auto-loaded for this session."""

    audit = _audit()

    stems = manifest_stems(args.root)
    offending = [
        record
        for record in audit.read_records(args.session, args.state)
        if record.get("kind") == audit.LOAD and not _load_is_expected(record, stems)
    ]
    for record in offending:
        print(f"still auto-loading: {record.get('file_path')} (reason {record.get('load_reason')})")
    return 1 if offending else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="resolve.py", description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    inspect = subcommands.add_parser("inspect", help="print one tier's stems and body paths")
    inspect.add_argument("--tier", required=True, choices=TIERS)
    inspect.add_argument("--root", default=None, help="an alternate rulesets root")
    inspect.set_defaults(handler=command_inspect)

    check = subcommands.add_parser("check", help="report every illegal state")
    check.add_argument("--root", default=None, help="an alternate rulesets root")
    check.set_defaults(handler=command_check)

    deliver = subcommands.add_parser("deliver", help="answer a hook payload on stdin")
    deliver.add_argument("--root", default=None, help="an alternate rulesets root")
    deliver.add_argument("--state", default=None, help="an alternate state directory")
    deliver.set_defaults(handler=command_deliver)

    load_check = subcommands.add_parser(
        "load-check", help="confirm no manifest stem auto-loaded for a session"
    )
    load_check.add_argument("--session", required=True, help="the session identifier")
    load_check.add_argument("--root", default=None, help="an alternate rulesets root")
    load_check.add_argument("--state", default=None, help="an alternate state directory")
    load_check.set_defaults(handler=command_load_check)

    delivery_check = subcommands.add_parser(
        "delivery-check", help="compare a session's deliveries against their compositions"
    )
    delivery_check.add_argument("--session", required=True, help="the session identifier")
    delivery_check.add_argument("--root", default=None, help="an alternate rulesets root")
    delivery_check.add_argument("--state", default=None, help="an alternate state directory")
    delivery_check.set_defaults(handler=command_delivery_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())

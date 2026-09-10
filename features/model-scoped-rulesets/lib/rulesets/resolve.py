#!/usr/bin/env python3.14
"""Resolve a model's ruleset and deliver it, or print it for inspection.

Nothing in the corpus auto-loads, so a session's user rules arrive through
this module and a hook that fails leaves the session with none. The
delivery path therefore answers with the `default` tier's bodies wherever a
tier, a manifest, or a body is unavailable, and names what failed in the
text it delivers.

This module carries mechanism and no rules. The corpus it reads holds every
body, the manifest that composes them, and the order the renders follow, and
it lives outside this code: at `--root`, at `RULESETS_ROOT`, or at
`rulesets` under the configuration directory. A corpus is a corpus wherever
its owner keeps it, and a symlink at that path is followed like any other
directory.

A root that is not there yet gets scaffolded, which writes a legal and empty
corpus: the five family tiers, a manifest composing each, and the family
prefixes. A scaffold delivers no content, and the header says it was created.
"""

import argparse
import dataclasses
import datetime
import functools
import hashlib
import json
import os
import pathlib
import re
import sys

import yaml

CONFIG_ENV = "CLAUDE_CONFIG_DIR"
STATE_ENV = "RULESETS_STATE_DIR"
ROOT_ENV = "RULESETS_ROOT"


def _audit():
    """The audit module, imported whether this runs as a package or a script."""

    try:
        from . import audit
    except ImportError:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
        from rulesets import audit
    return audit


def _render():
    """The render module, imported inside each call that needs it.

    `render` reads `all_tiers` from here and this module reads `marker_line`
    from there, which at module level is a cycle. The import lands in
    `sys.modules` on the first call and costs a lookup after that.
    """

    try:
        from . import render
    except ImportError:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
        from rulesets import render
    return render


def _documents():
    """The documents module, imported whether this runs as a package or a script."""

    try:
        from . import documents
    except ImportError:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
        from rulesets import documents
    return documents


DEFAULT_TIER = "default"
TIERS = (DEFAULT_TIER, "fable", "opus", "sonnet", "haiku")

# A directory beside the tiers that carries no rule bodies. A manifest key
# naming one is an illegal state, and so is a directory in neither this set
# nor the manifest.
RESERVED_DIRS = frozenset({"references", "renders"})

# What `models.yaml` holds on a fresh corpus: the prefix each family's
# identifiers share, which a lookup matches when no tier is named for the
# running identifier. A corpus owner edits the file; this is only the start.
FAMILY_PREFIXES = {
    "opus": ["opus", "claude-opus"],
    "sonnet": ["sonnet", "claude-sonnet"],
    "haiku": ["haiku", "claude-haiku"],
    "fable": ["fable", "claude-fable"],
}


def config_root() -> pathlib.Path:
    """The configuration directory the corpus and the state sit under."""

    override = os.environ.get(CONFIG_ENV)
    if override:
        return pathlib.Path(override)
    return pathlib.Path.home() / ".claude"


def load_dir() -> pathlib.Path:
    """The directory the harness itself auto-loads."""

    return config_root() / "rules"


def rulesets_root(explicit: pathlib.Path | str | None = None) -> pathlib.Path:
    """The live corpus, holding one directory per tier.

    A flag wins over the environment, which wins over the configuration
    directory, so a shell command with no flags reads what the hooks read.
    """

    if explicit is not None:
        return pathlib.Path(explicit)
    override = os.environ.get(ROOT_ENV)
    if override:
        return pathlib.Path(override)
    return config_root() / "rulesets"


def manifest_path(explicit: pathlib.Path | str | None = None) -> pathlib.Path:
    return rulesets_root(explicit) / "manifest.yaml"


def state_dir() -> pathlib.Path:
    """Where per-session records live, with its own override.

    These are records of what was delivered, not rules, so they sit apart
    from the corpus and a corpus under version control carries none of them.
    """

    override = os.environ.get(STATE_ENV)
    if override:
        return pathlib.Path(override)
    return config_root() / ".tmp" / "rulesets"


def naming_line(stem: str) -> str:
    """The line that opens a body, naming the stem it carries."""

    return _render().marker_line(stem)


def named_body(stem: str, text: str) -> str:
    """One body's text, opening on the line that names its stem.

    A body already opening on that line is returned as it is, down to the
    byte, since the marker is the filename and a body carrying it is already
    telling its reader which rule this is. A body carrying none gets it
    prefixed: what the marker states is derivable from where the file sits,
    so requiring the line on disk would reject a body that is otherwise
    entirely legal.
    """

    return _render().marked(stem, text.strip("\n"))


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


@dataclasses.dataclass(frozen=True)
class Scaffolded:
    """The corpus in place, and whether this run is what created it."""

    root: pathlib.Path
    created: bool


def scaffold_files(root: pathlib.Path) -> dict[pathlib.Path, str]:
    """Every file a fresh corpus holds, and the text of each.

    The manifest composes each family tier from whatever `default/` comes to
    hold, so a body dropped into that directory is delivered with no further
    edit. A `.gitkeep` is what carries an empty tier into version control.
    """

    manifest = {"tiers": {tier: {"include": "*"} for tier in TIERS}}
    files = {
        root / "manifest.yaml": yaml.safe_dump(manifest, sort_keys=False),
        root / "models.yaml": yaml.safe_dump(FAMILY_PREFIXES, sort_keys=False),
    }
    for tier in TIERS:
        files[root / tier / ".gitkeep"] = ""
    return files


def scaffold(root: pathlib.Path | str) -> Scaffolded | NoRuleset:
    """Write a legal and empty corpus at `root`.

    A root already holding a manifest is left exactly as it is, and so is
    every individual file already there, so two hooks starting at once write
    the same bytes and neither loses the other's. Any OSError comes back as
    NoRuleset naming the reason, and delivery falls to the header that
    carries it.
    """

    live = pathlib.Path(root)
    if (live / "manifest.yaml").is_file():
        return Scaffolded(root=live, created=False)

    try:
        live.mkdir(parents=True, exist_ok=True)
        for path, text in scaffold_files(live).items():
            if path.exists():
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    except OSError as exc:
        return NoRuleset(reason=f"the corpus at {live} could not be scaffolded: {exc}")
    return Scaffolded(root=live, created=True)


def ensure_corpus(root: pathlib.Path | str) -> Scaffolded | NoRuleset:
    """The corpus at `root`, scaffolded empty where it is not there yet.

    A root that exists, as a directory or as a symlink to one, is returned
    untouched, so nothing this code ships ever reaches a body its owner
    wrote and a corpus kept in a user's own dotfiles behind a symlink stays
    theirs. An absent root is scaffolded, and the delivered header says so:
    a session that starts against a fresh corpus receives no rules, and the
    note is where its reader learns why.
    """

    live = pathlib.Path(root)
    if live.exists():
        return Scaffolded(root=live, created=False)
    return scaffold(live)


def default_ruleset(root: pathlib.Path | str | None = None) -> Ruleset | NoRuleset:
    """The `default` tier's bodies, ordered by stem.

    This reads the directory and not the manifest, so it still answers where
    the manifest is what failed. It is the fallback every other resolution
    falls to, which is why it takes nothing on trust.
    """

    directory = pathlib.Path(root if root is not None else rulesets_root()) / DEFAULT_TIER
    bodies = sorted(directory.glob("*.md")) if directory.is_dir() else []
    if not bodies:
        return NoRuleset(reason=f"no rule bodies under {directory}")

    sections = [f"{named_body(body.stem, body.read_text(encoding='utf-8'))}\n" for body in bodies]

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


@functools.lru_cache(maxsize=256)
def _load_manifest_cached(
    path: pathlib.Path, mtime_ns: int, size: int
) -> ManifestOk | ManifestError:
    """The parse `load_manifest` memoizes, keyed past the path on the file's own state.

    A hook process parses once and exits, so nothing here goes stale within
    one. The test suite does not exit between cases, though, and a corpus
    rebuilt or rewritten at a path an earlier test already used is not the
    same manifest, so `mtime_ns` and `size` ride along in the key: a write
    that changes either is a cache miss, and a path alone would have masked
    it behind whatever the first test to touch that path once saw.
    """

    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return ManifestError(message=f"the manifest at {path} did not parse: {exc}")
    if not isinstance(document, dict) or not isinstance(document.get("tiers"), dict):
        return ManifestError(message=f"the manifest at {path} carries no tiers mapping")
    return ManifestOk(tiers=document["tiers"])


def load_manifest(root: pathlib.Path | str | None = None) -> ManifestOk | ManifestError:
    """Read the manifest's `tiers` mapping, or name why it could not.

    `compose`, `all_tiers`, and `tier_lookup` each call this on their own,
    and one hook invocation reaches all three, so the file behind a given
    root is stat'd on every call and parsed only when that stat says the
    last parse no longer matches.
    """

    path = _base(root) / "manifest.yaml"
    if not path.is_file():
        return ManifestError(message=f"no manifest at {path}")
    stat = path.stat()
    return _load_manifest_cached(path, stat.st_mtime_ns, stat.st_size)


def load_order(root: pathlib.Path | str | None = None) -> tuple[str, ...] | None:
    """The stem order the manifest states, or None where it states none.

    The order belongs to the corpus, since it is the sequence a reader meets
    the rules in. A corpus stating none renders its stems sorted, which is
    the order delivery composes them in.
    """

    path = _base(root) / "manifest.yaml"
    if not path.is_file():
        return None
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    if not isinstance(document, dict) or not isinstance(document.get("order"), list):
        return None
    return tuple(str(stem) for stem in document["order"])


def all_tiers(root: pathlib.Path | str | None = None) -> tuple[str, ...]:
    """The five required tiers, then every other tier the manifest names.

    A model wanting its own bodies gets a tier named for its identifier,
    which `tier_lookup` matches ahead of the family. The manifest is what
    admits such a tier, so a directory alone still brings none into play.
    """

    manifest = load_manifest(root)
    if isinstance(manifest, ManifestError):
        return tuple(TIERS)
    extra = sorted(name for name in manifest.tiers if name not in TIERS)
    return (*TIERS, *extra)


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
    known = {stem for name in all_tiers(base) for stem in tier_stems(base, name)}

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


def _misnamed(stem: str, path: pathlib.Path, text: str) -> Finding | None:
    """A finding where the body's first line names a stem other than its own.

    A body carrying no marker is legal, since delivery derives one from the
    filename. A body whose first line is a marker naming something else is
    not: delivery reads that body verbatim, so the reader is told they are
    reading a rule they are not, and the render would carry the same line
    into a section the reverse direction writes to a third file.
    """

    marker = _render().RULE_MARKER.fullmatch(text.split("\n", 1)[0])
    if marker is None or marker.group(1) == stem:
        return None
    return Finding(
        "misnamed-body",
        f"the body at {path} opens on {marker.group(0)}, naming {marker.group(1)} rather than {stem}",
    )


# A body that tells its reader to open a file in full cites it in backticks.
# The corpus form, `rulesets/references/`, travels with the corpus. The bare
# form names a path beside the configuration directory, which whoever copies
# the corpus does not receive.
REFERENCE_CITATION = re.compile(
    r"`~/\.claude/(?P<within>rulesets/references|references)/(?P<name>[^`]+)`"
)


def _reference_findings(base: pathlib.Path, path: pathlib.Path, text: str) -> tuple[Finding, ...]:
    """Every citation in one body that names a file the corpus cannot hand over."""

    findings: tuple[Finding, ...] = ()
    for match in REFERENCE_CITATION.finditer(text):
        name = match.group("name")
        if match.group("within") == "references":
            findings += (
                Finding(
                    "external-reference",
                    f"the body at {path} cites ~/.claude/references/{name}, "
                    "which the corpus does not carry",
                ),
            )
            continue
        target = base / "references" / name
        if not target.is_file():
            findings += (
                Finding(
                    "dangling-reference",
                    f"the body at {path} cites {name}, and no file sits at {target}",
                ),
            )
    return findings


def _layout_findings(base: pathlib.Path, tiers: tuple[str, ...]) -> tuple[Finding, ...]:
    """Every directory-level illegal state beside the tiers.

    A directory the manifest does not name and this module does not reserve
    holds bodies no composition reads, and a manifest key naming a reserved
    directory would read that directory's contents as a tier's bodies.
    """

    findings: tuple[Finding, ...] = ()
    findings += tuple(
        Finding(
            "reserved-tier",
            f"the manifest at {base / 'manifest.yaml'} names a tier {tier}, "
            f"which is the reserved directory {base / tier}",
        )
        for tier in tiers
        if tier in RESERVED_DIRS
    )
    named = set(tiers) | RESERVED_DIRS
    findings += tuple(
        Finding(
            "stray-directory",
            f"the directory {child} is neither a tier the manifest names nor a reserved directory",
        )
        for child in sorted(base.iterdir())
        if child.is_dir() and child.name not in named
    )
    return findings


def _order_findings(base: pathlib.Path) -> tuple[Finding, ...]:
    """Where the stated order and the `default` directory disagree.

    A stem in the directory and not in the order renders nowhere, and a stem
    in the order and not in the directory stops a render run, so both are
    reported before that run rather than by it.
    """

    stated = load_order(base)
    if stated is None:
        return ()
    directory = base / DEFAULT_TIER
    present = (
        {rule.stem for rule in _documents().unconditional_rules(directory)}
        if directory.is_dir()
        else set()
    )
    manifest_file = base / "manifest.yaml"
    findings: tuple[Finding, ...] = ()
    findings += tuple(
        Finding(
            "order-mismatch",
            f"the order in {manifest_file} does not name {stem}, whose body sits at "
            f"{directory / f'{stem}.md'}",
        )
        for stem in sorted(present - set(stated))
    )
    findings += tuple(
        Finding(
            "order-mismatch",
            f"the order in {manifest_file} names {stem}, and {directory} holds no body for it",
        )
        for stem in stated
        if stem not in present
    )
    return findings


def report(root: pathlib.Path | str | None = None) -> tuple[Finding, ...]:
    """Every illegal state the manifest and the layout carry."""

    base = _base(root)
    manifest = load_manifest(base)
    if isinstance(manifest, ManifestError):
        return (Finding("manifest", manifest.message),)

    tiers = all_tiers(base)
    findings: tuple[Finding, ...] = _layout_findings(base, tiers) + _order_findings(base)
    seen: set[pathlib.Path] = set()
    for tier in tiers:
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
        for stem, path in composed.body_paths.items():
            if path in seen:
                continue
            seen.add(path)
            text = path.read_text(encoding="utf-8")
            misnamed = _misnamed(stem, path, text)
            if misnamed is not None:
                findings += (misnamed,)
            findings += _reference_findings(base, path, text)
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


def command_init(args: argparse.Namespace) -> int:
    """Write a legal and empty corpus, refusing to touch one already there."""

    root = _root_from(args)
    if (root / "manifest.yaml").is_file():
        print(f"a corpus already sits at {root}: it holds {root / 'manifest.yaml'}")
        return 1
    result = scaffold(root)
    if isinstance(result, NoRuleset):
        print(result.reason)
        return 1
    for path in sorted(scaffold_files(root)):
        print(f"created: {path}")
    return 0


# --- Migration ---------------------------------------------------------------

# What a real run appends to, one JSON object per file it moved. The file
# records the moves currently in effect: `--undo` reverses the last run's and
# drops them from here, so a second `--undo` reaches the run before it.
JOURNAL = ".migration.jsonl"


@dataclasses.dataclass(frozen=True)
class Move:
    """One body's source and where it lands."""

    src: pathlib.Path
    dst: pathlib.Path


def migration_plan(
    source: pathlib.Path, root: pathlib.Path
) -> tuple[tuple[Move, ...], tuple[pathlib.Path, ...]]:
    """Which bodies move into the default tier, and which stay where they are.

    A body carrying frontmatter stays: that frontmatter scopes it to its own
    paths, and the harness is what reads it there, so moving it would take
    the scoping away and put the text in every context instead. Everything
    else loads every session today, which is what this corpus takes over.
    """

    moves: list[Move] = []
    stays: list[pathlib.Path] = []
    for path in sorted(source.glob("*.md")):
        document = _documents().parse_document(path.read_text(encoding="utf-8"))
        if document.frontmatter is None:
            moves.append(Move(src=path, dst=root / DEFAULT_TIER / path.name))
        else:
            stays.append(path)
    return tuple(moves), tuple(stays)


def _fingerprint(path: pathlib.Path) -> dict:
    """What a later run compares a file against to tell whether it changed."""

    data = path.read_bytes()
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _matches(path: pathlib.Path, record: dict) -> bool:
    if not path.is_file():
        return False
    seen = _fingerprint(path)
    return seen["size"] == record.get("size") and seen["sha256"] == record.get("sha256")


def _journal_records(root: pathlib.Path) -> list[dict]:
    path = root / JOURNAL
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def _apply_moves(moves: tuple[Move, ...]) -> None:
    """Move each file, content untouched.

    `os.replace` is a rename, so the bytes are the same bytes and no line is
    rewritten on the way. The destination directory exists by scaffolding.
    """

    for move in moves:
        move.dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(move.src, move.dst)


def _report_migration(moves: tuple[Move, ...], stays: tuple[pathlib.Path, ...] = ()) -> None:
    """The lines a run prints, which a dry run prints and nothing else."""

    for move in moves:
        print(f"move  {move.src} -> {move.dst}")
    for path in stays:
        print(f"stay  {path}  (frontmatter)")
    print(f"moved {len(moves)}, stayed {len(stays)}")


def _undo_migration(root: pathlib.Path, *, dry_run: bool) -> int:
    """Reverse the last run's moves, refusing where a file changed since.

    A body edited where it now sits is the user's current text, and putting
    it back would move an edit they made under the corpus out of the corpus
    without saying so. So a changed file stops the whole reversal.
    """

    records = _journal_records(root)
    runs = [record.get("run") for record in records]
    if not runs:
        print(f"no migration recorded at {root / JOURNAL}")
        return 1
    last = runs[-1]
    undoing = [record for record in records if record.get("run") == last]

    changed = [
        record["dst"] for record in undoing if not _matches(pathlib.Path(record["dst"]), record)
    ]
    if changed:
        for path in changed:
            print(f"changed since the move: {path}")
        print("nothing moved")
        return 1

    moves = tuple(
        Move(src=pathlib.Path(record["dst"]), dst=pathlib.Path(record["src"])) for record in undoing
    )
    occupied = [move.dst for move in moves if move.dst.exists()]
    if occupied:
        for path in occupied:
            print(f"occupied: {path}")
        print("nothing moved")
        return 1

    if dry_run:
        _report_migration(moves)
        return 0
    _apply_moves(moves)
    kept = [record for record in records if record.get("run") != last]
    (root / JOURNAL).write_text(
        "".join(f"{json.dumps(record)}\n" for record in kept), encoding="utf-8"
    )
    _report_migration(moves)
    return 0


def command_migrate_rules(args: argparse.Namespace) -> int:
    """Move the always-on bodies of a rules directory into the corpus.

    The harness auto-loads every body in that directory, which is the state
    this corpus replaces, so the move is what stops one context from
    carrying both. Nothing is edited: each file is renamed, and the run
    records what it renamed so it can be undone.
    """

    root = _root_from(args)
    if args.undo:
        return _undo_migration(root, dry_run=args.dry_run)

    source = pathlib.Path(args.source) if args.source else load_dir()
    if not source.is_dir():
        print(f"no directory at {source}")
        return 1

    moves, stays = migration_plan(source, root)
    occupied = [move.dst for move in moves if move.dst.exists()]
    if occupied:
        for path in occupied:
            print(f"occupied: {path}")
        print("nothing moved")
        return 1

    if args.dry_run:
        _report_migration(moves, stays)
        return 0

    prepared = scaffold(root)
    if isinstance(prepared, NoRuleset):
        print(prepared.reason)
        return 1

    run = datetime.datetime.now(datetime.UTC).isoformat()
    records = [
        {
            "run": run,
            "src": str(move.src),
            "dst": str(move.dst),
            "timestamp": run,
            **_fingerprint(move.src),
        }
        for move in moves
    ]
    _apply_moves(moves)
    with (root / JOURNAL).open("a", encoding="utf-8") as journal:
        for record in records:
            journal.write(f"{json.dumps(record)}\n")
    _report_migration(moves, stays)
    return 0


def command_render(args: argparse.Namespace) -> int:
    """Render each tier's working-rules file, or check it, or split it back."""

    argv: list[str] = []
    if args.check:
        argv.append("--check")
    if args.reverse:
        argv.append("--reverse")
    if args.model:
        argv += ["--model", args.model]
    if args.root:
        argv += ["--root", args.root]
    if args.config_root:
        argv += ["--config-root", args.config_root]
    return _render().main(argv)


def _root_from(args: argparse.Namespace) -> pathlib.Path:
    """The corpus a subcommand reads, from its flags and the environment."""

    return rulesets_root(args.root)


def _state_from(args: argparse.Namespace) -> pathlib.Path:
    """The state directory a subcommand reads, from its flags and the environment."""

    if args.state:
        return pathlib.Path(args.state)
    return state_dir()


def command_inspect(args: argparse.Namespace) -> int:
    """Print one tier's stems and body paths, delivering nothing."""

    composed = compose(args.tier, _root_from(args))
    for stem in composed.stems:
        path = composed.body_paths.get(stem)
        print(f"{stem}\t{path if path else '(no body)'}")
    for finding in composed.findings:
        print(f"{finding.kind}: {finding.message}")
    return 1 if composed.findings else 0


def command_check(args: argparse.Namespace) -> int:
    """Report every illegal state across all five tiers."""

    findings = report(_root_from(args))
    for finding in findings:
        print(f"{finding.kind}: {finding.message}")
    return 1 if findings else 0


def manifest_stems(root: pathlib.Path | str | None = None) -> set[str]:
    """Every stem any tier's entry names."""

    base = _base(root)
    return {stem for tier in all_tiers(base) for stem in compose(tier, base).stems}


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
    for tier, patterns in document.items():
        if isinstance(patterns, list):
            result[str(tier)] = tuple(str(p) for p in patterns)
    return result


def tier_lookup(
    identifier: str | None, root: pathlib.Path | str | None = None, env: dict | None = None
) -> TierLookup:
    """Map a model identifier to a tier.

    The order is a tier named for the identifier, then the profile
    variables, then the longest matching prefix in the built-in list.
    """

    env = os.environ if env is None else env
    notes: tuple[str, ...] = ()
    if _flag(env, HOST_MANAGED_VAR):
        notes += (
            f"{HOST_MANAGED_VAR} is set, so the harness may have used a model the "
            "profile variables do not name",
        )

    # A tier named for the identifier wins, so a model carrying its own bodies
    # needs no entry anywhere else. Reading the profile variables first would
    # send `claude-opus-9-9` to the `opus` tier whenever
    # ANTHROPIC_DEFAULT_OPUS_MODEL names it, and that duplication is what a
    # model-named directory removes.
    if identifier and identifier in all_tiers(root):
        return TierLookup(identifier, f"the tier directory named {identifier}", notes)

    matches = [
        (tier, var) for tier, var in PROFILE_VARS if identifier and env.get(var) == identifier
    ]
    if matches:
        tier, var = matches[0]
        if len(matches) > 1:
            names = " and ".join(var for _, var in matches)
            notes += (f"the profile variables {names} both name {identifier}",)
        return TierLookup(tier, f"the {var} variable", notes)

    # The longest matching prefix wins, so a more specific entry beats the
    # family it sits inside.
    ranked = sorted(
        (
            (len(pattern), tier)
            for tier, patterns in load_models(root).items()
            for pattern in patterns
            if identifier and identifier.startswith(pattern)
        ),
        reverse=True,
    )
    if ranked:
        return TierLookup(ranked[0][1], "the built-in identifier list", notes)

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
            sections.append(f"{named_body(stem, path.read_text(encoding='utf-8'))}\n")
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
    """Answer a hook payload with the ruleset to add, and record it.

    An absent corpus gets scaffolded empty, so the first hook run after an
    install leaves a legal corpus behind for its owner to fill rather than
    an error nobody sees. The run that created it says so in a note.
    """

    audit = _audit()

    env = os.environ if env is None else env
    event = payload.get("hook_event_name") or "SessionStart"
    session_id = payload.get("session_id")
    agent_id = payload.get("agent_id")
    prompt_id = payload.get("prompt_id")

    live = rulesets_root(root)
    prepared = ensure_corpus(live)
    setup_notes: tuple[str, ...] = ()
    if isinstance(prepared, NoRuleset):
        setup_notes = (prepared.reason,)
    elif prepared.created:
        setup_notes = (f"scaffolded an empty corpus at {live}",)
    root = live
    state = state_dir() if state is None else state

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

    delivered = _delivered(
        dataclasses.replace(res, notes=(*res.notes, *setup_notes)), event, scope, root
    )

    audit.append_record(
        audit.delivery_record(
            session_id,
            delivered.tier,
            delivered.source,
            delivered.stems,
            scope,
            agent_id=agent_id,
            prompt_id=prompt_id if scope == "switch" else None,
            root=root,
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


def command_deliveries(args: argparse.Namespace) -> int:
    """Print one line per delivery that reached a context.

    Tab-separated, in file order: the scope, the tier, how many stems it
    carried, where the tier came from, and the delegate's identifier where
    there is one. A session with no records prints nothing.
    """

    audit = _audit()

    records = [
        record
        for record in audit.read_records(args.session, _state_from(args))
        if record.get("kind") == audit.DELIVERY
    ]
    for record in _effective_deliveries(records):
        fields = [
            str(record.get("scope")),
            str(record.get("tier")),
            str(len(record.get("stems") or [])),
            str(record.get("tier_source")),
        ]
        if record.get("agent_id"):
            fields.append(str(record["agent_id"]))
        print("\t".join(fields))
    return 0


def command_delivery_check(args: argparse.Namespace) -> int:
    """Compare each delivery's stems against its tier's composition."""

    audit = _audit()

    records = [
        record
        for record in audit.read_records(args.session, _state_from(args))
        if record.get("kind") == audit.DELIVERY
    ]
    problems = []
    root = _root_from(args)
    for record in _effective_deliveries(records):
        tier = record.get("tier")
        composed = set(compose(tier, root).stems)
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

    stems = manifest_stems(_root_from(args))
    offending = [
        record
        for record in audit.read_records(args.session, _state_from(args))
        if record.get("kind") == audit.LOAD and not _load_is_expected(record, stems)
    ]
    for record in offending:
        print(f"still auto-loading: {record.get('file_path')} (reason {record.get('load_reason')})")
    return 1 if offending else 0


ROOT_HELP = "the corpus to read, ahead of RULESETS_ROOT and <config>/rulesets"
STATE_HELP = "an alternate state directory"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="resolve.py", description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    inspect = subcommands.add_parser("inspect", help="print one tier's stems and body paths")
    # No static choices: `--root` may point at a manifest naming tiers this
    # process cannot know, and an unknown tier already reports `missing-tier`
    # against the manifest that would have admitted it.
    inspect.add_argument("--tier", required=True, help="a tier the manifest names")
    inspect.add_argument("--root", default=None, help=ROOT_HELP)
    inspect.set_defaults(handler=command_inspect)

    init = subcommands.add_parser("init", help="write a legal and empty corpus")
    init.add_argument("--root", default=None, help=ROOT_HELP)
    init.set_defaults(handler=command_init)

    migrate = subcommands.add_parser(
        "migrate-rules", help="move the always-on bodies of a rules directory into the corpus"
    )
    migrate.add_argument(
        "--from",
        dest="source",
        default=None,
        help="the directory to move from, <config>/rules by default",
    )
    migrate.add_argument("--root", default=None, help=ROOT_HELP)
    migrate.add_argument("--dry-run", action="store_true", help="print the moves and make none")
    migrate.add_argument("--undo", action="store_true", help="reverse the last run's moves")
    migrate.set_defaults(handler=command_migrate_rules)

    check = subcommands.add_parser("check", help="report every illegal state")
    check.add_argument("--root", default=None, help=ROOT_HELP)
    check.set_defaults(handler=command_check)

    deliver = subcommands.add_parser("deliver", help="answer a hook payload on stdin")
    deliver.add_argument("--root", default=None, help=ROOT_HELP)
    deliver.add_argument("--state", default=None, help=STATE_HELP)
    deliver.set_defaults(handler=command_deliver)

    render = subcommands.add_parser(
        "render", help="write each tier's working-rules render, or check it"
    )
    render.add_argument("--check", action="store_true", help="write nothing; report drift")
    render.add_argument("--reverse", action="store_true", help="split the render back")
    render.add_argument("--model", default=None, help="render this tier alone")
    render.add_argument("--root", default=None, help=ROOT_HELP)
    render.add_argument(
        "--config-root",
        default=None,
        help="the directory holding the CLAUDE.md to render, and the repository to check",
    )
    render.set_defaults(handler=command_render)

    load_check = subcommands.add_parser(
        "load-check", help="confirm no manifest stem auto-loaded for a session"
    )
    load_check.add_argument("--session", required=True, help="the session identifier")
    load_check.add_argument("--root", default=None, help=ROOT_HELP)
    load_check.add_argument("--state", default=None, help=STATE_HELP)
    load_check.set_defaults(handler=command_load_check)

    delivery_check = subcommands.add_parser(
        "delivery-check", help="compare a session's deliveries against their compositions"
    )
    delivery_check.add_argument("--session", required=True, help="the session identifier")
    delivery_check.add_argument("--root", default=None, help=ROOT_HELP)
    delivery_check.add_argument("--state", default=None, help=STATE_HELP)
    delivery_check.set_defaults(handler=command_delivery_check)

    deliveries = subcommands.add_parser(
        "deliveries", help="print one line per delivery that reached a context"
    )
    deliveries.add_argument("--session", required=True, help="the session identifier")
    deliveries.add_argument("--root", default=None, help=ROOT_HELP)
    deliveries.add_argument("--state", default=None, help=STATE_HELP)
    deliveries.set_defaults(handler=command_deliveries)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())

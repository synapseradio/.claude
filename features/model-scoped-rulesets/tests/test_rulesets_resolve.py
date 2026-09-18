#!/usr/bin/env python3
"""Tests for the ruleset resolver under `lib/rulesets/resolve.py`.

Run with `python3.14 -m pytest features/model-scoped-rulesets/tests/test_rulesets_resolve.py`.

Every test builds a corpus under a temporary root and points the resolver at
it, so no test reads or writes a live corpus and no test names a rule, a
tier, or a model this plugin does not define itself.
"""

import pathlib
import subprocess
import sys

import pytest
import yaml

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import resolve  # noqa: E402  (path must be set before this import)


@pytest.fixture
def rulesets_root(tmp_path):
    """A rulesets root holding a `default` tier with two bodies."""

    default = tmp_path / "default"
    default.mkdir()
    (default / "beta.md").write_text(
        f"{resolve.naming_line('beta')}\nBeta body.\n", encoding="utf-8"
    )
    (default / "alpha.md").write_text(
        f"{resolve.naming_line('alpha')}\nAlpha body.\n", encoding="utf-8"
    )
    return tmp_path


def build_root(tmp_path, tiers, bodies):
    """A rulesets root with a manifest and the named bodies.

    `tiers` maps a tier to its manifest entry, and `bodies` maps a tier to
    the stems whose bodies that tier's directory holds. Each body opens on
    its own naming line, since delivery now reads a body verbatim rather
    than prefixing one.
    """

    for tier in resolve.TIERS:
        (tmp_path / tier).mkdir(exist_ok=True)
    for tier, stems in bodies.items():
        (tmp_path / tier).mkdir(exist_ok=True)
        for stem in stems:
            (tmp_path / tier / f"{stem}.md").write_text(
                f"{resolve.naming_line(stem)}\nBody of {stem} under {tier}.\n", encoding="utf-8"
            )
    (tmp_path / "manifest.yaml").write_text(yaml.safe_dump({"tiers": tiers}), encoding="utf-8")
    return tmp_path


def every_tier(entry):
    return dict.fromkeys(resolve.TIERS, entry)


WILDCARD = {"include": "*"}


@pytest.fixture
def three_stems(tmp_path):
    """Every tier at the wildcard form, with three stems under `default`."""

    return build_root(
        tmp_path,
        every_tier(WILDCARD),
        {"default": ("alpha", "beta", "gamma")},
    )


def _state_order(root: pathlib.Path, order: list[str]) -> None:
    """Add a top-level `order` to a corpus's manifest, leaving its tiers alone."""

    path = root / "manifest.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["order"] = order
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


class TestTheCorpusRootResolves:
    def test_a_flag_wins_over_the_environment(self, monkeypatch, tmp_path):
        monkeypatch.setenv(resolve.ROOT_ENV, str(tmp_path / "from-the-environment"))

        assert resolve.rulesets_root(tmp_path / "from-the-flag") == tmp_path / "from-the-flag"

    def test_the_environment_wins_over_the_configuration_directory(self, monkeypatch, tmp_path):
        monkeypatch.setenv(resolve.CONFIG_ENV, str(tmp_path / "config"))
        monkeypatch.setenv(resolve.ROOT_ENV, str(tmp_path / "elsewhere"))

        assert resolve.rulesets_root() == tmp_path / "elsewhere", (
            "a corpus is a corpus wherever its owner keeps it, and the variable is how they "
            "say so without editing a hook command"
        )

    def test_the_configuration_directory_is_what_a_bare_run_reads(self, monkeypatch, tmp_path):
        monkeypatch.setenv(resolve.CONFIG_ENV, str(tmp_path / "config"))
        monkeypatch.delenv(resolve.ROOT_ENV, raising=False)

        assert resolve.rulesets_root() == tmp_path / "config" / "rulesets", (
            "the hooks pass no flag, so a command run by hand with none has to read the "
            "corpus the hooks read or its report is about a different corpus"
        )

    def test_the_state_directory_sits_apart_from_the_corpus(self, monkeypatch, tmp_path):
        monkeypatch.setenv(resolve.CONFIG_ENV, str(tmp_path / "config"))
        monkeypatch.delenv(resolve.STATE_ENV, raising=False)

        assert not resolve.state_dir().is_relative_to(resolve.rulesets_root()), (
            "the records are of what was delivered and not rules, so a corpus under version "
            "control would otherwise carry one file per session"
        )


class TestDeliveryDerivesTheMarker:
    def test_a_body_carrying_no_marker_is_delivered_with_one(self, tmp_path):
        root = build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha",)})
        (root / "default" / "alpha.md").write_text("Alpha body.\n", encoding="utf-8")

        result = resolve.tier_ruleset("default", root)

        assert isinstance(result, resolve.Ruleset)
        assert result.text.startswith(f"{resolve.naming_line('alpha')}\n"), (
            "the marker is what tells one delivered rule from the next, and nothing else in "
            "the text says where a body begins"
        )

    def test_a_body_carrying_its_marker_is_delivered_byte_for_byte(self, tmp_path):
        root = build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha",)})
        held = (root / "default" / "alpha.md").read_text(encoding="utf-8")

        result = resolve.tier_ruleset("default", root)

        assert result.text == held, (
            "a body that already names itself is delivered as written, so no reader sees the "
            "same marker twice"
        )


class TestConfigRoot:
    def test_reads_the_override_variable(self, monkeypatch, tmp_path):
        monkeypatch.setenv(resolve.CONFIG_ENV, str(tmp_path))

        assert resolve.config_root() == tmp_path

    def test_falls_back_to_the_home_configuration_directory(self, monkeypatch):
        monkeypatch.delenv(resolve.CONFIG_ENV, raising=False)

        assert resolve.config_root() == pathlib.Path.home() / ".claude"

    def test_every_derived_path_sits_under_the_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv(resolve.CONFIG_ENV, str(tmp_path))
        monkeypatch.delenv(resolve.STATE_ENV, raising=False)
        monkeypatch.delenv(resolve.ROOT_ENV, raising=False)

        derived = (
            resolve.load_dir(),
            resolve.rulesets_root(),
            resolve.manifest_path(),
            resolve.state_dir(),
        )

        for path in derived:
            assert path.is_relative_to(tmp_path), path

    def test_every_derived_path_sits_under_home_without_the_override(self, monkeypatch):
        monkeypatch.delenv(resolve.CONFIG_ENV, raising=False)
        monkeypatch.delenv(resolve.STATE_ENV, raising=False)
        monkeypatch.delenv(resolve.ROOT_ENV, raising=False)

        home_config = pathlib.Path.home() / ".claude"
        derived = (
            resolve.load_dir(),
            resolve.rulesets_root(),
            resolve.manifest_path(),
            resolve.state_dir(),
        )

        for path in derived:
            assert path.is_relative_to(home_config), path

    def test_the_state_directory_takes_its_own_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv(resolve.STATE_ENV, str(tmp_path / "elsewhere"))

        assert resolve.state_dir() == tmp_path / "elsewhere"


class TestDefaultRuleset:
    def test_concatenates_every_body_under_the_default_tier(self, rulesets_root):
        result = resolve.default_ruleset(rulesets_root)

        assert isinstance(result, resolve.Ruleset)
        assert result.stems == ("alpha", "beta")
        assert "Alpha body." in result.text
        assert "Beta body." in result.text

    def test_precedes_each_body_with_a_line_naming_its_stem(self, rulesets_root):
        result = resolve.default_ruleset(rulesets_root)

        alpha_line = resolve.naming_line("alpha")
        assert alpha_line in result.text
        assert result.text.index(alpha_line) < result.text.index("Alpha body.")

    def test_a_body_naming_itself_is_not_named_twice(self, rulesets_root):
        result = resolve.default_ruleset(rulesets_root)

        alpha_line = resolve.naming_line("alpha")
        assert result.text.count(alpha_line) == 1, (
            "a body already opening on its own naming line must reach delivery with that "
            "line once, not doubled by a second copy delivery adds"
        )

    def test_orders_the_bodies_by_stem(self, rulesets_root):
        result = resolve.default_ruleset(rulesets_root)

        assert result.text.index("Alpha body.") < result.text.index("Beta body.")

    def test_names_the_missing_path_when_the_directory_is_absent(self, tmp_path):
        result = resolve.default_ruleset(tmp_path / "absent")

        assert isinstance(result, resolve.NoRuleset)
        assert str(tmp_path / "absent" / "default") in result.reason

    def test_names_the_path_when_the_directory_is_empty(self, tmp_path):
        (tmp_path / "default").mkdir()

        result = resolve.default_ruleset(tmp_path)

        assert isinstance(result, resolve.NoRuleset)
        assert str(tmp_path / "default") in result.reason


class TestComposition:
    def test_composes_every_default_stem_under_the_wildcard(self, three_stems):
        composed = resolve.compose("haiku", three_stems)

        assert composed.stems == ("alpha", "beta", "gamma")

    def test_composes_an_explicit_tier_to_its_list(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD) | {"haiku": {"include": ["alpha", "gamma"]}},
            {"default": ("alpha", "beta", "gamma")},
        )

        assert resolve.compose("haiku", root).stems == ("alpha", "gamma")

    def test_a_wildcard_tier_composes_in_the_manifest_order(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD),
            {"default": ("alpha", "beta", "gamma")},
        )
        _state_order(root, ["gamma", "alpha", "beta"])

        assert resolve.compose("haiku", root).stems == ("gamma", "alpha", "beta"), (
            "the order is the sequence a reader meets the rules in, and a wildcard tier "
            "composing sorted regardless would deliver a different sequence than the one "
            "the render follows"
        )

    def test_a_stem_the_order_omits_follows_sorted(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD),
            {"default": ("alpha", "beta", "gamma", "delta")},
        )
        _state_order(root, ["gamma"])

        assert resolve.compose("haiku", root).stems == ("gamma", "alpha", "beta", "delta"), (
            "a stem the order leaves out still has to compose, and sorted after the stated "
            "order is where it lands since the order names no place for it"
        )

    def test_omits_an_excluded_stem(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD) | {"haiku": {"include": "*", "exclude": ["beta"]}},
            {"default": ("alpha", "beta", "gamma")},
        )

        assert resolve.compose("haiku", root).stems == ("alpha", "gamma")

    def test_leaves_the_composition_unchanged_when_an_exclusion_names_no_body(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD) | {"haiku": {"include": "*", "exclude": ["absent"]}},
            {"default": ("alpha", "beta")},
        )

        composed = resolve.compose("haiku", root)

        assert composed.stems == ("alpha", "beta")
        assert any("absent" in finding.message for finding in composed.findings)

    def test_composes_one_tier_the_same_after_composing_another(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD) | {"haiku": {"include": ["alpha"]}},
            {"default": ("alpha", "beta"), "haiku": ("alpha",)},
        )

        resolve.compose("haiku", root)
        after = resolve.compose("sonnet", root)
        fresh = resolve.compose("sonnet", root)

        assert after.stems == fresh.stems
        assert after.body_paths == fresh.body_paths

    def test_composes_one_tier_the_same_as_a_fresh_process_does(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD) | {"haiku": {"include": ["alpha"]}},
            {"default": ("alpha", "beta"), "haiku": ("alpha",)},
        )

        resolve.compose("haiku", root)
        after = resolve.compose("sonnet", root)

        script = pathlib.Path(resolve.__file__)
        fresh = subprocess.run(
            [sys.executable, str(script), "inspect", "--tier", "sonnet", "--root", str(root)],
            capture_output=True,
            text=True,
            check=True,
        )

        in_process = "".join(f"{stem}\t{after.body_paths[stem]}\n" for stem in after.stems)
        assert fresh.stdout == in_process


class TestBodyPaths:
    def test_prefers_the_tier_own_body(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD),
            {"default": ("beta",), "haiku": ("beta",)},
        )

        composed = resolve.compose("haiku", root)

        assert composed.body_paths["beta"] == root / "haiku" / "beta.md"

    def test_falls_back_to_default_where_the_tier_holds_none(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD),
            {"default": ("beta",), "haiku": ("beta",)},
        )

        composed = resolve.compose("sonnet", root)

        assert composed.body_paths["beta"] == root / "default" / "beta.md"

    def test_resolves_one_tier_body_path_the_same_after_resolving_another(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD),
            {"default": ("beta",), "haiku": ("beta",)},
        )

        resolve.compose("haiku", root)
        after = resolve.compose("sonnet", root)

        assert after.body_paths["beta"] == root / "default" / "beta.md"


class TestIllegalStates:
    def test_reports_nothing_for_a_legal_layout(self, three_stems):
        assert resolve.report(three_stems) == ()

    def test_reports_an_unreachable_body_by_absolute_path(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD) | {"sonnet": {"include": ["alpha"]}},
            {"default": ("alpha", "beta"), "sonnet": ("beta",)},
        )

        findings = resolve.report(root)

        unreachable = [f for f in findings if f.kind == "unreachable-body"]
        assert len(unreachable) == 1
        assert str(root / "sonnet" / "beta.md") in unreachable[0].message

    def test_reports_a_composed_stem_with_no_body_naming_both_paths(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD) | {"haiku": {"include": ["absent"]}},
            {"default": ("alpha",)},
        )

        findings = [f for f in resolve.report(root) if f.kind == "no-body"]

        assert len(findings) == 1
        assert str(root / "haiku" / "absent.md") in findings[0].message
        assert str(root / "default" / "absent.md") in findings[0].message

    def test_reports_a_body_whose_marker_names_another_stem(self, tmp_path):
        root = build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha",)})
        (root / "default" / "alpha.md").write_text(
            f"{resolve.naming_line('beta')}\nAlpha body, misnamed.\n", encoding="utf-8"
        )

        findings = [f for f in resolve.report(root) if f.kind == "misnamed-body"]

        assert len(findings) == 1
        assert str(root / "default" / "alpha.md") in findings[0].message
        assert "beta" in findings[0].message and "alpha" in findings[0].message

    def test_reports_nothing_for_a_body_carrying_no_marker(self, tmp_path):
        root = build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha",)})
        (root / "default" / "alpha.md").write_text("Alpha body, no marker.\n", encoding="utf-8")

        findings = [f for f in resolve.report(root) if f.kind == "misnamed-body"]

        assert findings == [], (
            "the marker names the filename, so delivery derives it and a body carrying none "
            "is a legal body rather than a state to report"
        )

    def test_reports_no_misnamed_body_for_a_legal_layout(self, tmp_path):
        root = build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha",)})

        findings = [f for f in resolve.report(root) if f.kind == "misnamed-body"]

        assert findings == [], "every body build_root writes opens on its own naming line"

    def test_reports_an_order_naming_a_stem_no_body_backs(self, tmp_path):
        root = build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha",)})
        _state_order(root, ["alpha", "ghost"])

        findings = [f for f in resolve.report(root) if f.kind == "order-mismatch"]

        assert len(findings) == 1
        assert "ghost" in findings[0].message

    def test_reports_a_body_the_order_leaves_out(self, tmp_path):
        root = build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha", "beta")})
        _state_order(root, ["alpha"])

        findings = [f for f in resolve.report(root) if f.kind == "order-mismatch"]

        assert len(findings) == 1
        assert "beta" in findings[0].message, (
            "a stem the order leaves out reaches no render, so the body would be delivered "
            "and yet absent from the file a reader edits"
        )

    def test_reports_nothing_where_the_order_matches_the_directory(self, tmp_path):
        root = build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha", "beta")})
        _state_order(root, ["beta", "alpha"])

        findings = [f for f in resolve.report(root) if f.kind == "order-mismatch"]

        assert findings == [], "the order is a sequence, so any sequence of the same stems holds"

    def test_reports_nothing_where_the_manifest_states_no_order(self, tmp_path):
        root = build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha", "beta")})

        findings = [f for f in resolve.report(root) if f.kind == "order-mismatch"]

        assert findings == [], "an order is optional, so stating none is not a disagreement"

    def test_reports_a_missing_tier_key_by_name(self, tmp_path):
        tiers = every_tier(WILDCARD)
        del tiers["fable"]
        root = build_root(tmp_path, tiers, {"default": ("alpha",)})

        findings = [f for f in resolve.report(root) if f.kind == "missing-tier"]

        assert len(findings) == 1
        assert "fable" in findings[0].message

    def test_does_not_compose_a_missing_tier_key_as_the_wildcard(self, tmp_path):
        tiers = every_tier(WILDCARD)
        del tiers["fable"]
        root = build_root(tmp_path, tiers, {"default": ("alpha",)})

        assert resolve.compose("fable", root).stems == ()

    def test_reports_a_wildcard_mixed_into_a_list_and_composes_everything(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD) | {"haiku": {"include": ["*", "alpha"]}},
            {"default": ("alpha", "beta")},
        )

        composed = resolve.compose("haiku", root)

        assert composed.stems == ("alpha", "beta")
        assert any(f.kind == "mixed-form" for f in composed.findings)

    def test_reports_an_explicit_list_beside_an_exclude_and_composes_the_list(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD) | {"haiku": {"include": ["alpha"], "exclude": ["beta"]}},
            {"default": ("alpha", "beta")},
        )

        composed = resolve.compose("haiku", root)

        assert composed.stems == ("alpha",)
        assert any(f.kind == "mixed-form" for f in composed.findings)

    def test_reports_every_illegal_state_at_once(self, tmp_path):
        tiers = every_tier(WILDCARD)
        del tiers["fable"]
        tiers["haiku"] = {"include": ["*", "alpha"]}
        tiers["sonnet"] = {"include": ["alpha"]}
        root = build_root(
            tmp_path,
            tiers,
            {"default": ("alpha", "beta"), "sonnet": ("beta",)},
        )

        kinds = {f.kind for f in resolve.report(root)}

        assert {"missing-tier", "mixed-form", "unreachable-body"} <= kinds

    def test_reports_an_oversize_body(self, tmp_path):
        root = build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha",)})
        (root / "default" / "alpha.md").write_text(
            f"{resolve.naming_line('alpha')}\n{'x' * 11000}\n", encoding="utf-8"
        )

        findings = [f for f in resolve.report(root) if f.kind == "oversize-body"]

        assert len(findings) == 1
        assert str(root / "default" / "alpha.md") in findings[0].message

    def test_reports_nothing_oversize_for_a_body_under_the_budget(self, tmp_path):
        root = build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha",)})
        (root / "default" / "alpha.md").write_text(
            f"{resolve.naming_line('alpha')}\n{'x' * 100}\n", encoding="utf-8"
        )

        findings = [f for f in resolve.report(root) if f.kind == "oversize-body"]

        assert findings == []

    def test_reports_a_tier_that_packs_past_ten_parts(self, tmp_path):
        stems = tuple(f"stem{i}" for i in range(11))
        root = build_root(
            tmp_path,
            every_tier(WILDCARD) | {"haiku": {"include": list(stems)}},
            {"default": ("alpha",), "haiku": stems},
        )
        for stem in stems:
            (root / "haiku" / f"{stem}.md").write_text(
                f"{resolve.naming_line(stem)}\n{'x' * 7950}\n", encoding="utf-8"
            )

        findings = [f for f in resolve.report(root) if f.kind == "too-many-parts"]

        assert len(findings) == 1
        assert "haiku" in findings[0].message

    def test_reports_nothing_for_a_tier_that_packs_within_ten_parts(self, three_stems):
        findings = [f for f in resolve.report(three_stems) if f.kind == "too-many-parts"]

        assert findings == []


class TestManifestErrors:
    def test_names_the_path_and_the_parse_error(self, tmp_path):
        for tier in resolve.TIERS:
            (tmp_path / tier).mkdir()
        (tmp_path / "manifest.yaml").write_text("tiers: [unclosed\n", encoding="utf-8")

        result = resolve.load_manifest(tmp_path)

        assert isinstance(result, resolve.ManifestError)
        assert str(tmp_path / "manifest.yaml") in result.message

    def test_names_the_path_when_the_manifest_is_absent(self, tmp_path):
        result = resolve.load_manifest(tmp_path)

        assert isinstance(result, resolve.ManifestError)
        assert str(tmp_path / "manifest.yaml") in result.message


class TestManifestMemoization:
    """`load_manifest` parses the file once per hook call, not once per reader.

    `compose`, `all_tiers`, and `tier_lookup` each call `load_manifest` on
    their own, and one `SessionStart` reaches all three through
    `deliver_payload`, so an unmemoized read parses the same bytes three
    times for one hook invocation.
    """

    def test_one_session_start_parses_the_manifest_once(self, monkeypatch, tmp_path):
        root = build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha",)})
        state = tmp_path / "state"
        calls = []
        real_safe_load = resolve.yaml.safe_load

        def counting(text):
            calls.append(1)
            return real_safe_load(text)

        monkeypatch.setattr(resolve.yaml, "safe_load", counting)
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "s1",
            "model": "claude-haiku-4-5",
        }

        resolve.deliver_payload(payload, root=root, state=state)

        assert len(calls) == 1, (
            "compose, all_tiers, and tier_lookup each read the manifest during one "
            "delivery, and only the first of the three should ever reach the parser"
        )

    def test_a_manifest_rewritten_at_the_same_path_is_seen_on_the_next_read(self, tmp_path):
        root = build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha",)})

        first = resolve.load_manifest(root)
        assert isinstance(first, resolve.ManifestOk)
        assert set(first.tiers) == set(resolve.TIERS)

        tiers = every_tier(WILDCARD)
        del tiers["fable"]
        (root / "manifest.yaml").write_text(yaml.safe_dump({"tiers": tiers}), encoding="utf-8")

        second = resolve.load_manifest(root)

        assert isinstance(second, resolve.ManifestOk)
        assert "fable" not in second.tiers, (
            "the suite is a single long-lived process, not the short-lived one a hook runs "
            "as, so a memoized read that survived this rewrite would hand a test the "
            "previous test's, or this test's own earlier, corpus"
        )


class TestInspectAndCheck:
    def test_inspect_prints_each_stem_with_its_body_path_and_exits_zero(self, three_stems, capsys):
        code = resolve.main(["inspect", "--tier", "haiku", "--root", str(three_stems)])

        out = capsys.readouterr().out
        assert code == 0
        for stem in ("alpha", "beta", "gamma"):
            assert stem in out
            assert str(three_stems / "default" / f"{stem}.md") in out

    def test_inspect_exits_nonzero_on_a_composed_stem_with_no_body(self, tmp_path, capsys):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD) | {"haiku": {"include": ["absent"]}},
            {"default": ("alpha",)},
        )

        code = resolve.main(["inspect", "--tier", "haiku", "--root", str(root)])

        assert code != 0
        assert "absent" in capsys.readouterr().out

    def test_inspect_exits_nonzero_on_an_unparseable_manifest(self, tmp_path, capsys):
        for tier in resolve.TIERS:
            (tmp_path / tier).mkdir()
        (tmp_path / "manifest.yaml").write_text("tiers: [unclosed\n", encoding="utf-8")

        code = resolve.main(["inspect", "--tier", "haiku", "--root", str(tmp_path)])

        assert code != 0
        assert str(tmp_path / "manifest.yaml") in capsys.readouterr().out

    def test_check_prints_nothing_and_exits_zero_on_a_legal_layout(self, three_stems, capsys):
        code = resolve.main(["check", "--root", str(three_stems)])

        assert code == 0
        assert capsys.readouterr().out == ""

    def test_check_exits_nonzero_on_a_stem_with_no_body(self, tmp_path, capsys):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD) | {"haiku": {"include": ["absent"]}},
            {"default": ("alpha",)},
        )

        code = resolve.main(["check", "--root", str(root)])

        assert code != 0
        assert "absent" in capsys.readouterr().out


MODELS = {
    "opus": ["opus", "claude-opus"],
    "sonnet": ["sonnet", "claude-sonnet"],
    "haiku": ["haiku", "claude-haiku"],
    "fable": ["fable", "claude-fable"],
}


def write_models(root):
    (root / "models.yaml").write_text(yaml.safe_dump(MODELS), encoding="utf-8")
    return root


@pytest.fixture
def full_root(tmp_path):
    """Every tier at the wildcard, three default bodies, and a models file."""

    build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha", "beta", "gamma")})
    return write_models(tmp_path)


@pytest.fixture
def multi_part_root(tmp_path):
    """A haiku tier of three stems, each too large to share a part with another."""

    stems = ("stem0", "stem1", "stem2")
    root = build_root(
        tmp_path,
        every_tier(WILDCARD) | {"haiku": {"include": list(stems)}},
        {"default": ("alpha",), "haiku": stems},
    )
    for stem in stems:
        (root / "haiku" / f"{stem}.md").write_text(
            f"{resolve.naming_line(stem)}\n{'x' * 7950}\n", encoding="utf-8"
        )
    return write_models(root)


class TestTierLookup:
    def test_a_profile_variable_names_the_running_model(self, full_root):
        env = {"ANTHROPIC_DEFAULT_OPUS_MODEL": "some-vendor-model"}

        assert resolve.tier_lookup("some-vendor-model", full_root, env).tier == "opus"

    def test_no_profile_variable_falls_to_the_built_in_list(self, full_root):
        assert resolve.tier_lookup("claude-opus-9-9", full_root, {}).tier == "opus"

    def test_a_partial_profile_leaves_the_built_in_list_to_decide(self, full_root):
        env = {
            "ANTHROPIC_DEFAULT_OPUS_MODEL": "x",
            "ANTHROPIC_DEFAULT_SONNET_MODEL": "y",
        }

        assert resolve.tier_lookup("claude-haiku-4-5", full_root, env).tier == "haiku"

    def test_a_set_variable_is_consulted_before_the_built_in_list(self, full_root):
        env = {"ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-opus-5"}

        assert resolve.tier_lookup("claude-opus-5", full_root, env).tier == "sonnet"

    def test_two_variables_naming_one_identifier_take_the_first_and_report_the_collision(
        self, full_root
    ):
        env = {
            "ANTHROPIC_DEFAULT_SONNET_MODEL": "same",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": "same",
        }

        result = resolve.tier_lookup("same", full_root, env)

        assert result.tier == "sonnet"
        assert any("HAIKU" in note and "SONNET" in note for note in result.notes)

    def test_a_host_managed_provider_still_resolves_and_names_the_variable(self, full_root):
        env = {
            "ANTHROPIC_DEFAULT_OPUS_MODEL": "vendor",
            "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST": "1",
        }

        result = resolve.tier_lookup("vendor", full_root, env)

        assert result.tier == "opus"
        assert any("PROVIDER_MANAGED_BY_HOST" in note for note in result.notes)

    def test_a_collapse_model_variable_changes_nothing(self, full_root):
        env = {"CLAUDE_CONTEXT_COLLAPSE_MODEL": "claude-haiku-4-5"}

        assert resolve.tier_lookup("claude-opus-9-9", full_root, env).tier == "opus"

    def test_an_unrecognized_identifier_yields_no_tier(self, full_root):
        assert resolve.tier_lookup("gpt-9", full_root, {}).tier is None

    def test_the_built_in_list_needs_no_code_change_for_a_new_release(self, tmp_path):
        build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha",)})
        models = dict(MODELS)
        models["opus"] = ["opus", "claude-opus", "claude-opus-9-newname"]
        (tmp_path / "models.yaml").write_text(yaml.safe_dump(models), encoding="utf-8")

        assert resolve.tier_lookup("claude-opus-9-newname", tmp_path, {}).tier == "opus"

    def test_a_non_string_identifier_is_treated_as_unmapped(self, full_root):
        result = resolve.tier_lookup(12345, full_root, {})

        assert result.tier is None
        assert any("12345" in note and "int" in note for note in result.notes)

    def test_a_string_identifier_still_resolves_after_the_type_guard(self, full_root):
        assert resolve.tier_lookup("claude-haiku-4-5", full_root, {}).tier == "haiku"


class TestSessionResolution:
    def test_the_harness_model_decides_and_the_environment_is_not_read(self, full_root):
        env = {"ANTHROPIC_MODEL": "claude-haiku-4-5"}
        payload = {"model": "claude-opus-9-9", "session_id": "s1"}

        assert resolve.session_resolution(payload, full_root, None, env).tier == "opus"

    def test_anthropic_model_is_read_before_anthropic_default_model(self, full_root):
        env = {
            "ANTHROPIC_MODEL": "claude-haiku-4-5",
            "ANTHROPIC_DEFAULT_MODEL": "claude-opus-9-9",
        }
        payload = {"session_id": "s1"}

        assert resolve.session_resolution(payload, full_root, None, env).tier == "haiku"

    def test_an_unmatched_harness_model_falls_open_to_default(self, full_root):
        payload = {"model": "gpt-9", "session_id": "s1"}

        result = resolve.session_resolution(payload, full_root, None, {})

        assert result.tier == "default"
        assert any("gpt-9" in note for note in result.notes)

    def test_no_model_anywhere_reads_the_recorded_tier(self, full_root, tmp_path):
        state = tmp_path / "state"
        resolve._audit().write_tier("s1", "haiku", state)
        payload = {"session_id": "s1"}

        assert resolve.session_resolution(payload, full_root, state, {}).tier == "haiku"

    def test_no_model_and_no_record_falls_open_to_default(self, full_root, tmp_path):
        payload = {"session_id": "s-none"}

        result = resolve.session_resolution(payload, full_root, tmp_path / "state", {})

        assert result.tier == "default"
        assert result.source == "no model identifier was available"

    def test_a_non_string_model_falls_open_to_default_with_a_note(self, full_root):
        payload = {"model": 12345, "session_id": "s1"}

        result = resolve.session_resolution(payload, full_root, None, {})

        assert result.tier == "default"
        assert any("12345" in note and "int" in note for note in result.notes)

    def test_a_non_string_model_delivers_default_and_raises_nothing_from_any_part(
        self, full_root, tmp_path
    ):
        state = tmp_path / "state"
        payload = {"hook_event_name": "SessionStart", "session_id": "s1", "model": 12345}

        out = resolve.deliver_payload(payload, full_root, state, {}, part=1)
        text = out["hookSpecificOutput"]["additionalContext"]

        assert "tier default" in text
        assert "12345" in text and "int" in text
        assert resolve.deliver_payload(payload, full_root, state, {}, part=2) == {}


class TestDelegateResolution:
    def _payload(self, **kw):
        base = {
            "session_id": "s1",
            "agent_id": "a1",
            "prompt_id": "p1",
            "agent_type": "general-purpose",
        }
        base.update(kw)
        return base

    def test_the_caller_named_model_comes_first(self, full_root, tmp_path):
        state = tmp_path / "state"
        resolve._audit().write_tier("s1", "opus", state)
        resolve._audit().append_spawn("s1", "p1", "general-purpose", "haiku", state)

        assert resolve.delegate_resolution(self._payload(), full_root, state, {}).tier == "haiku"

    def test_only_the_definition_pins_a_model(self, full_root, tmp_path):
        state = tmp_path / "state"
        payload = self._payload(agent_type="scout")

        result = resolve.delegate_resolution(
            payload, full_root, state, {}, definitions={"scout": "haiku"}
        )

        assert result.tier == "haiku"

    def test_the_definition_outranks_the_default_variable(self, full_root, tmp_path):
        state = tmp_path / "state"
        env = {"CLAUDE_CODE_SUBAGENT_MODEL": "claude-sonnet-5"}

        result = resolve.delegate_resolution(
            self._payload(agent_type="scout"), full_root, state, env, definitions={"scout": "haiku"}
        )

        assert result.tier == "haiku"

    def test_only_the_default_variable_names_a_model(self, full_root, tmp_path):
        state = tmp_path / "state"
        env = {"CLAUDE_CODE_SUBAGENT_MODEL": "claude-sonnet-5"}

        result = resolve.delegate_resolution(
            self._payload(agent_type="scout"), full_root, state, env, definitions={}
        )

        assert result.tier == "sonnet"

    def test_no_source_but_the_parent(self, full_root, tmp_path):
        state = tmp_path / "state"
        resolve._audit().write_tier("s1", "opus", state)

        result = resolve.delegate_resolution(
            self._payload(agent_type="scout"), full_root, state, {}, definitions={}
        )

        assert result.tier == "opus"

    def test_two_same_type_spawns_make_the_per_spawn_model_ambiguous(self, full_root, tmp_path):
        state = tmp_path / "state"
        resolve._audit().write_tier("s1", "opus", state)
        resolve._audit().append_spawn("s1", "p1", "general-purpose", "haiku", state)
        resolve._audit().append_spawn("s1", "p1", "general-purpose", "sonnet", state)

        result = resolve.delegate_resolution(self._payload(), full_root, state, {}, definitions={})

        assert result.tier == "opus"
        assert any("ambiguous" in note for note in result.notes)

    def test_the_force_variable_and_a_model_outrank_the_definition(self, full_root, tmp_path):
        state = tmp_path / "state"
        env = {
            "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1",
            "CLAUDE_CODE_SUBAGENT_MODEL": "claude-haiku-4-5",
        }

        result = resolve.delegate_resolution(
            self._payload(agent_type="scout"), full_root, state, env, definitions={"scout": "opus"}
        )

        assert result.tier == "haiku"

    def test_the_force_variable_with_no_model_takes_the_parent_tier(self, full_root, tmp_path):
        state = tmp_path / "state"
        resolve._audit().write_tier("s1", "opus", state)
        env = {"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1"}

        assert resolve.delegate_resolution(self._payload(), full_root, state, env).tier == "opus"

    def test_a_zero_valued_force_variable_reads_as_off(self, full_root, tmp_path):
        state = tmp_path / "state"
        resolve._audit().write_tier("s1", "opus", state)
        resolve._audit().append_spawn("s1", "p1", "general-purpose", "haiku", state)
        env = {"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "0"}

        assert resolve.delegate_resolution(self._payload(), full_root, state, env).tier == "haiku"

    def test_the_coordinator_lever_forces_the_parent_tier(self, full_root, tmp_path):
        state = tmp_path / "state"
        resolve._audit().write_tier("s1", "opus", state)
        resolve._audit().append_spawn("s1", "p1", "general-purpose", "haiku", state)
        env = {"CLAUDE_CODE_COORDINATOR_FORCE_WORKER_INHERIT_MODEL": "1"}

        result = resolve.delegate_resolution(self._payload(), full_root, state, env)

        assert result.tier == "opus"
        assert "COORDINATOR" in result.source

    def test_both_levers_resolve_to_the_parent_tier(self, full_root, tmp_path):
        state = tmp_path / "state"
        resolve._audit().write_tier("s1", "opus", state)
        env = {
            "CLAUDE_CODE_COORDINATOR_FORCE_WORKER_INHERIT_MODEL": "1",
            "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1",
            "CLAUDE_CODE_SUBAGENT_MODEL": "claude-haiku-4-5",
        }

        assert resolve.delegate_resolution(self._payload(), full_root, state, env).tier == "opus"

    def test_a_fork_under_a_forced_model_takes_the_parent_tier(self, full_root, tmp_path):
        state = tmp_path / "state"
        resolve._audit().write_tier("s1", "opus", state)
        env = {
            "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1",
            "CLAUDE_CODE_SUBAGENT_MODEL": "claude-haiku-4-5",
        }

        result = resolve.delegate_resolution(
            self._payload(agent_type="fork"), full_root, state, env
        )

        assert result.tier == "opus"

    def test_explore_keeps_its_own_cap_under_the_force_variable(self, full_root, tmp_path):
        state = tmp_path / "state"
        resolve._audit().write_tier("s1", "opus", state)
        env = {
            "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1",
            "CLAUDE_CODE_SUBAGENT_MODEL": "claude-haiku-4-5",
        }

        result = resolve.delegate_resolution(
            self._payload(agent_type="Explore"), full_root, state, env
        )

        assert result.tier == "opus"

    def test_an_unreadable_per_spawn_model_states_so_and_falls_through(self, full_root, tmp_path):
        state = tmp_path / "state"
        resolve._audit().write_tier("s1", "opus", state)
        payload = self._payload(prompt_id=None)

        result = resolve.delegate_resolution(payload, full_root, state, {}, definitions={})

        assert result.tier == "opus"
        assert any("unreadable" in note for note in result.notes)


class TestSwitchAndDelivery:
    def test_a_switch_to_a_different_tier_delivers_and_records(self, full_root, tmp_path):
        state = tmp_path / "state"
        payload = {
            "hook_event_name": "PostModelSwitch",
            "session_id": "s1",
            "from_model": "claude-opus-9-9",
            "to_model": "claude-haiku-4-5",
            "prompt_id": "p1",
        }

        out = resolve.deliver_payload(payload, full_root, state, {})

        assert "the earlier ruleset remains" in out["hookSpecificOutput"]["additionalContext"]
        assert resolve._audit().read_tier("s1", state) == "haiku"

    def test_a_switch_within_the_same_tier_delivers_nothing(self, full_root, tmp_path):
        state = tmp_path / "state"
        payload = {
            "hook_event_name": "PostModelSwitch",
            "session_id": "s1",
            "from_model": "claude-opus-5",
            "to_model": "claude-opus-9-9",
            "prompt_id": "p1",
        }

        assert resolve.deliver_payload(payload, full_root, state, {}) == {}

    def test_a_non_string_to_model_falls_open_to_default(self, full_root, tmp_path):
        state = tmp_path / "state"
        payload = {
            "hook_event_name": "PostModelSwitch",
            "session_id": "s1",
            "from_model": "claude-opus-9-9",
            "to_model": ["claude-haiku-4-5"],
            "prompt_id": "p1",
        }

        out = resolve.deliver_payload(payload, full_root, state, {})

        assert "tier default" in out["hookSpecificOutput"]["additionalContext"]

    def test_the_delivered_header_names_the_tier_and_count_and_the_trailer_names_the_source(
        self, full_root, tmp_path
    ):
        state = tmp_path / "state"
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "s1",
            "model": "claude-haiku-4-5",
        }

        text = resolve.deliver_payload(payload, full_root, state, {})["hookSpecificOutput"][
            "additionalContext"
        ]

        header = text.splitlines()[0]
        assert "tier haiku" in header
        assert "3 stems" in header
        assert "claude-haiku-4-5" not in header, (
            "a header is a function of the corpus and the tier alone, so the source now "
            "closes the trailer instead of opening the header"
        )
        assert "claude-haiku-4-5" in text, "the source still reaches the reader, from the trailer"


class TestSwitchChecksThePayload:
    """The switch check compares the payload's own `from_model` and `to_model` tiers.

    A recorded tier plays no part in the answer, whatever it holds.
    """

    def _payload(self, from_model, to_model, session_id="s1"):
        payload = {
            "hook_event_name": "PostModelSwitch",
            "session_id": session_id,
            "to_model": to_model,
            "prompt_id": "p1",
        }
        if from_model is not None:
            payload["from_model"] = from_model
        return payload

    def _total(self, root, tier="haiku"):
        return len(resolve.pack_parts(resolve.tier_ruleset(tier, root).sections))

    def test_the_same_tier_from_every_slot_delivers_nothing(self, multi_part_root, tmp_path):
        state = tmp_path / "state"
        payload = self._payload(from_model="claude-haiku-9-9", to_model="claude-haiku-4-5")
        total = self._total(multi_part_root)

        for part in range(1, total + 1):
            assert resolve.deliver_payload(payload, multi_part_root, state, {}, part=part) == {}

    def test_crossing_tiers_delivers_from_every_slot(self, multi_part_root, tmp_path):
        state = tmp_path / "state"
        payload = self._payload(from_model="claude-opus-9-9", to_model="claude-haiku-4-5")
        total = self._total(multi_part_root)

        for part in range(1, total + 1):
            assert resolve.deliver_payload(payload, multi_part_root, state, {}, part=part) != {}

    def test_no_from_model_delivers(self, full_root, tmp_path):
        state = tmp_path / "state"
        payload = self._payload(from_model=None, to_model="claude-haiku-4-5")

        assert resolve.deliver_payload(payload, full_root, state, {}) != {}

    def test_a_non_string_from_model_counts_as_absent_so_the_switch_delivers(
        self, full_root, tmp_path
    ):
        state = tmp_path / "state"
        payload = self._payload(from_model=12345, to_model="claude-haiku-4-5")

        assert resolve.deliver_payload(payload, full_root, state, {}) != {}

    def test_a_contradictory_recorded_tier_gives_the_same_answer(self, full_root, tmp_path):
        state = tmp_path / "state"
        resolve._audit().write_tier("s1", "sonnet", state)
        payload = self._payload(from_model="claude-haiku-4-5", to_model="claude-haiku-4-5")

        assert resolve.deliver_payload(payload, full_root, state, {}) == {}, (
            "the recorded tier names sonnet, but the payload names the same tier both ways, "
            "so the switch still suppresses"
        )


class TestPacking:
    """`pack_parts` groups a tier's sections into whole, ordered parts.

    It is pure: given the same sections it composes the same parts, whatever
    resolved them, and it never reads a source or a note, since a header and
    a part's body are a function of the corpus and the tier alone.
    """

    def _sections(self, *bodies):
        return tuple((f"stem{i}", body) for i, body in enumerate(bodies))

    def test_parts_concatenate_to_the_tier_text_byte_for_byte(self, three_stems):
        ruleset = resolve.tier_ruleset("haiku", three_stems)

        parts = resolve.pack_parts(ruleset.sections)

        assert "\n".join(resolve.part_text(p) for p in parts) == ruleset.text

    def test_no_body_splits_across_parts(self):
        sections = self._sections("a" * 4000 + "\n", "b" * 4000 + "\n", "c" * 4000 + "\n")

        parts = resolve.pack_parts(sections, budget=9000)

        for stem, body in sections:
            carriers = [part for part in parts if (stem, body) in part]
            assert len(carriers) == 1, f"{stem} must sit whole in exactly one part"

    def test_a_body_over_budget_sits_alone_in_its_part(self):
        oversized = ("big", "x" * 9500 + "\n")
        sections = (("small", "y" * 10 + "\n"), oversized, ("small2", "z" * 10 + "\n"))

        parts = resolve.pack_parts(sections, budget=9000)

        oversized_parts = [part for part in parts if oversized in part]
        assert len(oversized_parts) == 1
        assert oversized_parts[0] == (oversized,)

    def test_packing_takes_sections_only_and_never_reads_source_or_notes(self):
        sections = self._sections("alpha\n", "beta\n")

        parts = resolve.pack_parts(sections)

        assert parts == ((("stem0", "alpha\n"), ("stem1", "beta\n")),), (
            "pack_parts takes only the sections and a budget, so nothing about a source or a "
            "note can shape a part boundary"
        )

    def test_two_resolutions_of_one_tier_from_different_sources_yield_byte_identical_parts(
        self, tmp_path
    ):
        (tmp_path / "first").mkdir()
        (tmp_path / "second").mkdir()
        first = build_root(
            tmp_path / "first", every_tier(WILDCARD), {"default": ("alpha", "beta", "gamma")}
        )
        second = build_root(
            tmp_path / "second", every_tier(WILDCARD), {"default": ("alpha", "beta", "gamma")}
        )

        parts_from_first = resolve.pack_parts(resolve.tier_ruleset("haiku", first).sections)
        parts_from_second = resolve.pack_parts(resolve.tier_ruleset("haiku", second).sections)

        assert parts_from_first == parts_from_second, (
            "a header and a part's body are a function of the corpus and the tier alone, so "
            "two resolutions of the same content from different roots pack identically"
        )


class TestPartHeaders:
    def test_a_one_part_tier_keeps_the_short_header(self):
        assert resolve.delivery_header("haiku", 3, 1, 1) == "<!-- ruleset: tier haiku, 3 stems -->"

    def test_a_multi_part_header_names_the_part_and_the_total(self):
        header = resolve.delivery_header("haiku", 12, 2, 4)

        assert header == "<!-- ruleset: tier haiku, 12 stems, part 2 of 4 -->"

    def test_the_trailer_names_the_source(self):
        assert resolve.delivery_trailer("the tier directory", ()) == (
            "<!-- ruleset: from the tier directory -->"
        )

    def test_the_trailer_lists_each_note_after_the_source(self):
        trailer = resolve.delivery_trailer("src", ("note one", "note two"))

        assert trailer == (
            "<!-- ruleset: from src -->\n<!-- note: note one -->\n<!-- note: note two -->"
        )

    def test_a_switch_trailer_closes_on_the_standing_note(self):
        trailer = resolve.delivery_trailer("src", ("a note",), switch=True)

        assert trailer.splitlines()[-1] == (
            "<!-- note: the earlier ruleset remains in the conversation above -->"
        )

    def test_a_short_note_passes_through_a_budget_unchanged(self):
        trailer = resolve.delivery_trailer("src", ("a short note",), budget=1000)

        assert trailer == "<!-- ruleset: from src -->\n<!-- note: a short note -->"


class TestDeliverByPart:
    """Each slot resolves, composes, and packs on its own, and returns its part.

    No slot reads what another slot did; a session id chosen to be
    improbable in any body checks that nothing ahead of the trailer names
    it.
    """

    SESSION_ID = "distinctive-session-id-9000"

    def _payload(self, session_id=SESSION_ID):
        return {
            "hook_event_name": "SessionStart",
            "session_id": session_id,
            "model": "claude-haiku-4-5",
        }

    def _total(self, root, tier="haiku"):
        return len(resolve.pack_parts(resolve.tier_ruleset(tier, root).sections))

    def _text(self, root, state, part):
        out = resolve.deliver_payload(self._payload(), root, state, {}, part=part)
        return out["hookSpecificOutput"]["additionalContext"]

    def _body(self, text, last):
        _, _, rest = text.partition("\n\n")
        return rest.rpartition("\n\n")[0] if last else rest

    def test_the_parts_of_one_delivery_concatenate_to_the_tier_text(
        self, multi_part_root, tmp_path
    ):
        state = tmp_path / "state"
        ruleset = resolve.tier_ruleset("haiku", multi_part_root)
        total = self._total(multi_part_root)

        bodies = [
            self._body(self._text(multi_part_root, state, part), part == total)
            for part in range(1, total + 1)
        ]

        assert "\n".join(bodies) == ruleset.text

    def test_a_slot_beyond_the_part_count_returns_nothing(self, full_root, tmp_path):
        state = tmp_path / "state"

        assert resolve.deliver_payload(self._payload(), full_root, state, {}, part=2) == {}

    def test_only_the_last_part_carries_the_trailer(self, multi_part_root, tmp_path):
        state = tmp_path / "state"
        total = self._total(multi_part_root)

        for part in range(1, total + 1):
            text = self._text(multi_part_root, state, part)
            assert ("<!-- ruleset: from " in text) == (part == total)

    def test_no_part_carries_a_session_id_or_a_path_ahead_of_the_trailer(
        self, multi_part_root, tmp_path
    ):
        state = tmp_path / "state"
        total = self._total(multi_part_root)

        for part in range(1, total + 1):
            text = self._text(multi_part_root, state, part)
            ahead = self._body(text, part == total)
            assert self.SESSION_ID not in ahead
            assert str(multi_part_root) not in ahead

    def test_only_part_one_scaffolds_a_missing_corpus(self, tmp_path):
        root = tmp_path / "missing"
        state = tmp_path / "state"

        resolve.deliver_payload(self._payload(), root, state, {}, part=2)

        assert not root.exists()

    def test_only_part_one_records_the_delivery_and_writes_the_tier(
        self, multi_part_root, tmp_path
    ):
        state = tmp_path / "state"
        total = self._total(multi_part_root)

        for part in range(1, total + 1):
            resolve.deliver_payload(self._payload(), multi_part_root, state, {}, part=part)

        records = [
            r
            for r in resolve._audit().read_records(self.SESSION_ID, state)
            if r["kind"] == "delivery"
        ]
        assert len(records) == 1
        assert records[0]["parts"] == total
        assert resolve._audit().read_tier(self.SESSION_ID, state) == "haiku"

    def test_pre_tool_use_only_appends_the_spawn_on_part_one(self, tmp_path):
        root = tmp_path / "corpus"
        state = tmp_path / "state"
        payload = {
            "hook_event_name": "PreToolUse",
            "session_id": "s1",
            "prompt_id": "p1",
            "tool_input": {"subagent_type": "scout", "model": "claude-haiku-4-5"},
        }

        assert resolve.deliver_payload(payload, root, state, {}, part=2) == {}
        assert resolve._audit().read_spawns("s1", "p1", "scout", state) == []

        assert resolve.deliver_payload(payload, root, state, {}, part=1) == {}
        assert resolve._audit().read_spawns("s1", "p1", "scout", state) == ["claude-haiku-4-5"]


class TestPartCap:
    """The last part's header, body, and trailer together stay within the cap.

    `NoRuleset.reason` joins one message per missing stem with no bound, so
    a fallback note built from it needs clipping before it reaches a part
    that could otherwise cross what a harness will accept.
    """

    def _probe_root(self, tmp_path):
        root = tmp_path
        for tier in resolve.TIERS:
            (root / tier).mkdir(exist_ok=True)
        (root / "default" / "alpha.md").write_text("x" * 8900 + "\n", encoding="utf-8")
        missing_stems = [f"missing{i}" for i in range(60)]
        tiers = {
            "default": {"include": "*"},
            "haiku": {"include": missing_stems},
            "opus": {"include": "*"},
            "sonnet": {"include": "*"},
            "fable": {"include": "*"},
        }
        (root / "manifest.yaml").write_text(yaml.safe_dump({"tiers": tiers}), encoding="utf-8")
        (root / "models.yaml").write_text("haiku: [haiku, claude-haiku]\n", encoding="utf-8")
        return root

    def test_a_long_fallback_reason_still_delivers_a_part_at_or_under_the_cap(self, tmp_path):
        root = self._probe_root(tmp_path)
        state = tmp_path / "state"
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "probe-session",
            "model": "claude-haiku-4-5",
        }

        out = resolve.deliver_payload(payload, root, state, {}, part=1)
        text = out["hookSpecificOutput"]["additionalContext"]

        assert len(text) <= 10000
        assert "haiku" in text

    def test_part_boundaries_are_identical_with_and_without_a_long_note(
        self, multi_part_root, tmp_path
    ):
        ruleset = resolve.tier_ruleset("haiku", multi_part_root)
        parts_list = resolve.pack_parts(ruleset.sections)
        total = len(parts_list)

        short = resolve.Resolution("haiku", "src", ("short note",))
        long = resolve.Resolution("haiku", "src", ("x" * 9000,))

        for part in range(1, total + 1):
            expected_header = resolve.delivery_header("haiku", len(ruleset.stems), part, total)
            expected_body = resolve.part_text(parts_list[part - 1])
            prefix = f"{expected_header}\n\n{expected_body}"

            short_delivered = resolve._delivered(
                short, "SessionStart", "session", multi_part_root, part
            )
            long_delivered = resolve._delivered(
                long, "SessionStart", "session", multi_part_root, part
            )

            assert short_delivered.text.startswith(prefix)
            assert long_delivered.text.startswith(prefix)
            if part == total:
                assert len(long_delivered.text) <= 10000


class TestDeliveryCheckAndSupersession:
    def _switch(self, prompt_id, stems, tier="haiku"):
        return resolve._audit().delivery_record(
            "s1", tier, "the switch", tuple(stems), "switch", prompt_id=prompt_id
        )

    def test_of_two_switches_before_a_request_only_the_last_survives(self):
        records = [
            self._switch("p1", ["alpha"], tier="sonnet"),
            self._switch("p1", ["beta"], tier="haiku"),
        ]

        effective = resolve._effective_deliveries(records)

        assert effective == [records[1]]

    def test_a_request_between_switches_keeps_both(self):
        records = [self._switch("p1", ["alpha"]), self._switch("p2", ["beta"])]

        assert resolve._effective_deliveries(records) == records

    def test_a_switch_with_no_prompt_id_counts_as_delivered(self):
        record = resolve._audit().delivery_record(
            "s1", "haiku", "the switch", ("alpha",), "switch", prompt_id=None
        )

        assert resolve._effective_deliveries([record]) == [record]

    def test_delivery_check_passes_when_stems_match_the_composition(self, full_root, tmp_path):
        state = tmp_path / "state"
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "s1",
            "model": "claude-haiku-4-5",
        }
        resolve.deliver_payload(payload, full_root, state, {})

        code = resolve.main(
            ["delivery-check", "--session", "s1", "--root", str(full_root), "--state", str(state)]
        )

        assert code == 0

    def test_delivery_check_fails_when_a_stem_is_missing(self, full_root, tmp_path, capsys):
        state = tmp_path / "state"
        resolve._audit().append_record(
            resolve._audit().delivery_record("s1", "haiku", "x", ("alpha",), "session"),
            session_id="s1",
            state=state,
        )

        code = resolve.main(
            ["delivery-check", "--session", "s1", "--root", str(full_root), "--state", str(state)]
        )

        assert code != 0
        out = capsys.readouterr().out
        assert "beta" in out and "gamma" in out

    def test_delivery_check_ignores_a_superseded_switch(self, full_root, tmp_path):
        state = tmp_path / "state"
        audit = resolve._audit()
        # A superseded switch names a wrong stem set, but a later switch with
        # the same prompt_id delivers the right one; the check reads the last.
        audit.append_record(
            audit.delivery_record("s1", "haiku", "x", ("wrong",), "switch", prompt_id="p1"),
            session_id="s1",
            state=state,
        )
        audit.append_record(
            audit.delivery_record(
                "s1", "haiku", "x", ("alpha", "beta", "gamma"), "switch", prompt_id="p1"
            ),
            session_id="s1",
            state=state,
        )

        code = resolve.main(
            ["delivery-check", "--session", "s1", "--root", str(full_root), "--state", str(state)]
        )

        assert code == 0


class TestDeliveryCheckAcrossParts:
    """The check also compares a delivery's declared parts against what emitted."""

    def _deliver(self, payload, root, state, *parts):
        for part in parts:
            resolve.deliver_payload(payload, root, state, {}, part=part)

    def _check(self, session, root, state):
        return resolve.main(
            ["delivery-check", "--session", session, "--root", str(root), "--state", str(state)]
        )

    def test_names_a_part_composed_and_never_emitted(self, multi_part_root, tmp_path, capsys):
        state = tmp_path / "state"
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "s1",
            "model": "claude-haiku-4-5",
        }
        self._deliver(payload, multi_part_root, state, 1)  # parts 2 and 3 never run

        code = self._check("s1", multi_part_root, state)

        assert code != 0
        out = capsys.readouterr().out
        assert "part 2" in out and "never emitted" in out

    def test_two_parts_that_disagree_on_tier_are_reported(self, multi_part_root, tmp_path, capsys):
        state = tmp_path / "state"
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "s1",
            "model": "claude-haiku-4-5",
        }
        self._deliver(payload, multi_part_root, state, 1, 3)
        audit = resolve._audit()
        audit.append_record(
            audit.emitted_record("s1", "opus", 2, 3, ("stem1",), "deadbeef"),
            session_id="s1",
            state=state,
            part=2,
        )

        code = self._check("s1", multi_part_root, state)

        assert code != 0
        out = capsys.readouterr().out
        assert "part 2" in out and "opus" in out

    def test_a_single_part_delivery_still_passes(self, full_root, tmp_path):
        state = tmp_path / "state"
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "s1",
            "model": "claude-haiku-4-5",
        }
        self._deliver(payload, full_root, state, 1)

        assert self._check("s1", full_root, state) == 0


class TestDeliveryCheckByWriter:
    """Emitted records correlate to a delivery by the writer that made it, and by count."""

    def _delivery(
        self, audit, session, tier, source, stems, scope, root, parts, agent_id=None, state=None
    ):
        audit.append_record(
            audit.delivery_record(
                session, tier, source, stems, scope, agent_id=agent_id, root=root, parts=parts
            ),
            session_id=session,
            agent_id=agent_id,
            state=state,
        )

    def _check(self, session, root, state):
        return resolve.main(
            ["delivery-check", "--session", session, "--root", str(root), "--state", str(state)]
        )

    def test_a_delegates_missing_parts_are_not_masked_by_the_sessions_own(
        self, full_root, tmp_path, capsys
    ):
        state = tmp_path / "state"
        audit = resolve._audit()
        stems = ("alpha", "beta", "gamma")

        self._delivery(
            audit, "s1", "haiku", "session source", stems, "session", full_root, 3, state=state
        )
        audit.append_record(
            audit.emitted_record("s1", "haiku", 2, 3, ("x",), "digestA2"),
            session_id="s1",
            state=state,
            part=2,
        )
        audit.append_record(
            audit.emitted_record("s1", "haiku", 3, 3, ("y",), "digestA3"),
            session_id="s1",
            state=state,
            part=3,
        )
        self._delivery(
            audit,
            "s1",
            "haiku",
            "delegate source",
            stems,
            "delegate",
            full_root,
            3,
            agent_id="delegateB",
            state=state,
        )
        # delegateB's own parts 2 and 3 never emitted

        code = self._check("s1", full_root, state)

        assert code != 0
        out = capsys.readouterr().out
        assert "part 2" in out and "never emitted" in out
        assert "part 3" in out and "never emitted" in out

    def test_two_deliveries_from_one_writer_need_two_emitted_sets(
        self, full_root, tmp_path, capsys
    ):
        state = tmp_path / "state"
        audit = resolve._audit()
        stems = ("alpha", "beta", "gamma")

        self._delivery(audit, "s1", "haiku", "first", stems, "session", full_root, 2, state=state)
        self._delivery(audit, "s1", "haiku", "second", stems, "session", full_root, 2, state=state)
        audit.append_record(
            audit.emitted_record("s1", "haiku", 2, 2, ("x",), "digestOnly"),
            session_id="s1",
            state=state,
            part=2,
        )

        code = self._check("s1", full_root, state)

        assert code != 0
        out = capsys.readouterr().out
        assert out.count("never emitted") == 1

    def test_an_emitted_digest_that_disagrees_with_the_current_composition_is_reported(
        self, multi_part_root, tmp_path, capsys
    ):
        state = tmp_path / "state"
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "s1",
            "model": "claude-haiku-4-5",
        }
        resolve.deliver_payload(payload, multi_part_root, state, {}, part=1)
        audit = resolve._audit()
        audit.append_record(
            audit.emitted_record("s1", "haiku", 2, 3, ("stem1",), "not-the-real-digest"),
            session_id="s1",
            state=state,
            part=2,
        )
        resolve.deliver_payload(payload, multi_part_root, state, {}, part=3)

        code = self._check("s1", multi_part_root, state)

        assert code != 0
        out = capsys.readouterr().out
        assert "part 2" in out and "digest" in out


class TestModelNamedTiers:
    """A tier directory named for a model identifier needs no synonym.

    `models.yaml` maps a family to identifier prefixes. A model wanting its
    own bodies gets a directory named for its identifier instead, and that
    directory wins over both the family prefix and the profile variable, so
    the same model never has to appear in two places.
    """

    def _root(self, tmp_path, extra_tiers=(), models=None):
        tiers = every_tier(WILDCARD)
        for name in extra_tiers:
            tiers[name] = WILDCARD
        root = build_root(tmp_path, tiers, {"default": ("alpha", "beta")})
        for name in extra_tiers:
            (root / name).mkdir(exist_ok=True)
        if models is not None:
            (root / "models.yaml").write_text(yaml.safe_dump(models), encoding="utf-8")
        return root

    def test_all_tiers_reports_a_manifest_tier_beyond_the_required_five(self, tmp_path):
        root = self._root(tmp_path, extra_tiers=("claude-opus-9-9",))

        assert "claude-opus-9-9" in resolve.all_tiers(root)
        assert set(resolve.TIERS) <= set(resolve.all_tiers(root))

    def test_all_tiers_falls_back_to_the_required_five_with_no_manifest(self, tmp_path):
        assert resolve.all_tiers(tmp_path) == tuple(resolve.TIERS)

    def test_a_tier_named_for_the_identifier_wins_over_the_family_prefix(self, tmp_path):
        root = self._root(
            tmp_path,
            extra_tiers=("claude-opus-9-9",),
            models={"opus": ["opus", "claude-opus"]},
        )

        look = resolve.tier_lookup("claude-opus-9-9", root, env={})

        assert look.tier == "claude-opus-9-9"

    def test_a_tier_named_for_the_identifier_wins_over_the_profile_variable(self, tmp_path):
        root = self._root(
            tmp_path,
            extra_tiers=("claude-opus-9-9",),
            models={"opus": ["opus", "claude-opus"]},
        )
        env = {"ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-9-9"}

        look = resolve.tier_lookup("claude-opus-9-9", root, env=env)

        assert look.tier == "claude-opus-9-9"

    def test_an_identifier_with_no_tier_of_its_own_still_takes_the_family(self, tmp_path):
        root = self._root(tmp_path, models={"opus": ["opus", "claude-opus"]})

        look = resolve.tier_lookup("claude-opus-5", root, env={})

        assert look.tier == "opus"

    def test_load_models_reads_a_key_outside_the_four_families(self, tmp_path):
        root = self._root(
            tmp_path,
            extra_tiers=("claude-opus-9-9",),
            models={"opus": ["claude-opus"], "claude-opus-9-9": ["claude-opus-9-9-2026"]},
        )

        assert resolve.load_models(root)["claude-opus-9-9"] == ("claude-opus-9-9-2026",)

    def test_a_model_named_tier_delivers_its_own_bodies(self, tmp_path):
        root = self._root(tmp_path, extra_tiers=("claude-opus-9-9",))
        (root / "claude-opus-9-9" / "alpha.md").write_text(
            f"{resolve.naming_line('alpha')}\nOpus 4.8 alpha.\n", encoding="utf-8"
        )

        composed = resolve.compose("claude-opus-9-9", root)

        assert composed.stems == ("alpha", "beta")
        assert composed.body_paths["alpha"] == root / "claude-opus-9-9" / "alpha.md"
        assert composed.body_paths["beta"] == root / "default" / "beta.md"

    def test_check_reports_no_illegal_state_for_a_model_named_tier(self, tmp_path):
        root = self._root(tmp_path, extra_tiers=("claude-opus-9-9",))

        assert resolve.report(root) == ()

    def test_an_unreachable_body_under_a_model_named_tier_is_reported(self, tmp_path):
        root = self._root(tmp_path, extra_tiers=("claude-opus-9-9",))
        (root / "claude-opus-9-9" / "orphan.md").write_text("No stem.\n", encoding="utf-8")

        kinds = {f.kind for f in resolve.report(root)}

        assert "unreachable-body" in kinds

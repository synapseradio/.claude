#!/usr/bin/env python3
"""Tests for the ruleset resolver under `scripts/rulesets/resolve.py`.

Run with `python3.14 -m pytest scripts/tests/test_rulesets_resolve.py`.

Every test points the resolver at a temporary root, so no test reads or
writes the live manifest under the configuration directory.
"""

import pathlib
import subprocess
import sys

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rulesets import resolve


@pytest.fixture
def rulesets_root(tmp_path):
    """A rulesets root holding a `default` tier with two bodies."""

    default = tmp_path / "default"
    default.mkdir()
    (default / "beta.md").write_text("Beta body.\n", encoding="utf-8")
    (default / "alpha.md").write_text("Alpha body.\n", encoding="utf-8")
    return tmp_path


def build_root(tmp_path, tiers, bodies):
    """A rulesets root with a manifest and the named bodies.

    `tiers` maps a tier to its manifest entry, and `bodies` maps a tier to
    the stems whose bodies that tier's directory holds.
    """

    for tier in resolve.TIERS:
        (tmp_path / tier).mkdir(exist_ok=True)
    for tier, stems in bodies.items():
        (tmp_path / tier).mkdir(exist_ok=True)
        for stem in stems:
            (tmp_path / tier / f"{stem}.md").write_text(
                f"Body of {stem} under {tier}.\n", encoding="utf-8"
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
            {"default": ("writing-code",), "haiku": ("writing-code",)},
        )

        composed = resolve.compose("haiku", root)

        assert composed.body_paths["writing-code"] == root / "haiku" / "writing-code.md"

    def test_falls_back_to_default_where_the_tier_holds_none(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD),
            {"default": ("writing-code",), "haiku": ("writing-code",)},
        )

        composed = resolve.compose("sonnet", root)

        assert composed.body_paths["writing-code"] == root / "default" / "writing-code.md"

    def test_resolves_one_tier_body_path_the_same_after_resolving_another(self, tmp_path):
        root = build_root(
            tmp_path,
            every_tier(WILDCARD),
            {"default": ("writing-code",), "haiku": ("writing-code",)},
        )

        resolve.compose("haiku", root)
        after = resolve.compose("sonnet", root)

        assert after.body_paths["writing-code"] == root / "default" / "writing-code.md"


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


class TestTierLookup:
    def test_a_profile_variable_names_the_running_model(self, full_root):
        env = {"ANTHROPIC_DEFAULT_OPUS_MODEL": "some-vendor-model"}

        assert resolve.tier_lookup("some-vendor-model", full_root, env).tier == "opus"

    def test_no_profile_variable_falls_to_the_built_in_list(self, full_root):
        assert resolve.tier_lookup("claude-opus-4-8", full_root, {}).tier == "opus"

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

        assert resolve.tier_lookup("claude-opus-4-8", full_root, env).tier == "opus"

    def test_an_unrecognized_identifier_yields_no_tier(self, full_root):
        assert resolve.tier_lookup("gpt-9", full_root, {}).tier is None

    def test_the_built_in_list_needs_no_code_change_for_a_new_release(self, tmp_path):
        build_root(tmp_path, every_tier(WILDCARD), {"default": ("alpha",)})
        models = dict(MODELS)
        models["opus"] = ["opus", "claude-opus", "claude-opus-9-newname"]
        (tmp_path / "models.yaml").write_text(yaml.safe_dump(models), encoding="utf-8")

        assert resolve.tier_lookup("claude-opus-9-newname", tmp_path, {}).tier == "opus"


class TestSessionResolution:
    def test_the_harness_model_decides_and_the_environment_is_not_read(self, full_root):
        env = {"ANTHROPIC_MODEL": "claude-haiku-4-5"}
        payload = {"model": "claude-opus-4-8", "session_id": "s1"}

        assert resolve.session_resolution(payload, full_root, None, env).tier == "opus"

    def test_anthropic_model_is_read_before_anthropic_default_model(self, full_root):
        env = {
            "ANTHROPIC_MODEL": "claude-haiku-4-5",
            "ANTHROPIC_DEFAULT_MODEL": "claude-opus-4-8",
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
        resolve._audit().write_tier("s1", "opus", state)
        payload = {
            "hook_event_name": "PostModelSwitch",
            "session_id": "s1",
            "to_model": "claude-haiku-4-5",
            "prompt_id": "p1",
        }

        out = resolve.deliver_payload(payload, full_root, state, {})

        assert "the earlier ruleset remains" in out["hookSpecificOutput"]["additionalContext"]
        assert resolve._audit().read_tier("s1", state) == "haiku"

    def test_a_switch_within_the_same_tier_delivers_nothing(self, full_root, tmp_path):
        state = tmp_path / "state"
        resolve._audit().write_tier("s1", "opus", state)
        payload = {
            "hook_event_name": "PostModelSwitch",
            "session_id": "s1",
            "to_model": "claude-opus-4-8",
            "prompt_id": "p1",
        }

        assert resolve.deliver_payload(payload, full_root, state, {}) == {}

    def test_the_delivered_header_names_the_tier_source_and_count(self, full_root, tmp_path):
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
        assert "claude-haiku-4-5" in header
        assert "3 stems" in header


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

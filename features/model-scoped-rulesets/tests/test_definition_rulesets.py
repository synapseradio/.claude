"""An agent definition's `metadata.rulesets` block adjusts the tier its delegate receives.

`exclude` removes stems from the tier composition and `add` appends stems
from the corpus's reserved `experimental/` directory. Both work whatever
model the delegate runs on. Delivery never fails on a definition it cannot
read: it delivers the tier composition and notes what it could not honor in
the delivery record.
"""

import json
import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import resolve  # noqa: E402  (path must be set before this import)

AGENT = "evalr"
STEMS = ("alpha", "beta", "gamma")


@pytest.fixture
def config(monkeypatch, tmp_path):
    directory = tmp_path / "config"
    (directory / "agents").mkdir(parents=True)
    monkeypatch.setenv(resolve.CONFIG_ENV, str(directory))
    return directory


@pytest.fixture
def corpus(tmp_path):
    root = tmp_path / "corpus"
    resolve.scaffold(root)
    for stem in STEMS:
        (root / "default" / f"{stem}.md").write_text(f"Body {stem}.\n", encoding="utf-8")
    (root / "experimental").mkdir()
    (root / "experimental" / "trial.md").write_text("Body trial.\n", encoding="utf-8")
    return root


@pytest.fixture
def state(tmp_path):
    directory = tmp_path / "state"
    resolve._audit().write_tier("s1", "default", directory)
    return directory


def define(config, front: str, name: str = AGENT) -> None:
    (config / "agents" / f"{name}.md").write_text(f"---\n{front}\n---\nbody\n", encoding="utf-8")


def rulesets_block(body: str) -> str:
    return f"name: {AGENT}\nmetadata:\n  rulesets:\n{body}"


def spawn(corpus, state, agent_type=AGENT, env=None):
    payload = {
        "hook_event_name": "SubagentStart",
        "session_id": "s1",
        "agent_id": "a1",
        "prompt_id": "p1",
        "agent_type": agent_type,
    }
    output = resolve.deliver_payload(payload, corpus, state, {} if env is None else env)
    return output["hookSpecificOutput"]["additionalContext"]


def delivery(state):
    audit = resolve._audit()
    records = [r for r in audit.read_records("s1", state) if r.get("kind") == audit.DELIVERY]
    assert len(records) == 1
    return records[0]


def delivery_check(corpus, state, capsys):
    capsys.readouterr()
    code = resolve.main(
        ["delivery-check", "--session", "s1", "--root", str(corpus), "--state", str(state)]
    )
    return code, capsys.readouterr().out


class TestMissingPieces:
    def test_a_missing_definition_delivers_the_tier_and_notes_it(self, config, corpus, state):
        text = spawn(corpus, state, agent_type="ghost")

        assert all(f"Body {stem}." in text for stem in STEMS)
        assert any("ghost" in note for note in delivery(state)["rulesets"]["notes"])

    def test_a_missing_block_delivers_the_tier_and_notes_it(self, config, corpus, state):
        define(config, f"name: {AGENT}\nmodel: haiku")

        text = spawn(corpus, state)

        assert all(f"Body {stem}." in text for stem in STEMS)
        assert any("no metadata.rulesets block" in n for n in delivery(state)["rulesets"]["notes"])

    def test_a_block_missing_a_key_honors_the_other(self, config, corpus, state):
        define(config, rulesets_block("    exclude: [beta]"))

        text = spawn(corpus, state)

        assert "Body beta." not in text
        assert any("names no add" in note for note in delivery(state)["rulesets"]["notes"])

    def test_a_block_that_is_not_a_mapping_delivers_the_tier_and_says_so(
        self, config, corpus, state
    ):
        define(config, f"name: {AGENT}\nmetadata:\n  rulesets: [beta]")

        text = spawn(corpus, state)

        assert all(f"Body {stem}." in text for stem in STEMS)
        assert "metadata.rulesets is not a mapping" in text


class TestUnknowns:
    def test_an_unknown_key_is_named_and_the_known_keys_still_apply(self, config, corpus, state):
        define(config, rulesets_block("    exclude: [beta]\n    frobnicate: true"))

        text = spawn(corpus, state)

        assert "Body beta." not in text
        assert "unknown key frobnicate" in text

    def test_an_unknown_stem_delivers_the_tier_and_is_named(self, config, corpus, state):
        define(config, rulesets_block("    exclude: [nonesuch]\n    add: [absent]"))

        text = spawn(corpus, state)

        assert all(f"Body {stem}." in text for stem in STEMS)
        assert "no stem nonesuch to exclude" in text
        assert "no body for absent" in text

    def test_a_stem_reaching_outside_the_corpus_is_an_unknown_stem(self, config, corpus, state):
        (corpus.parent / "outside.md").write_text("Body outside.\n", encoding="utf-8")
        define(config, rulesets_block("    add: ['../outside']"))

        text = spawn(corpus, state)

        assert "Body outside." not in text
        assert "no body for ../outside" in text


class TestExclude:
    def test_an_excluded_stem_is_absent_from_the_delivery_and_its_record(
        self, config, corpus, state
    ):
        define(config, rulesets_block("    exclude: [beta]\n    add: []"))

        text = spawn(corpus, state)

        assert "Body beta." not in text
        assert "Body alpha." in text and "Body gamma." in text
        assert delivery(state)["stems"] == ["alpha", "gamma"]

    def test_delivery_check_compares_against_the_adjusted_composition(
        self, config, corpus, state, capsys
    ):
        define(config, rulesets_block("    exclude: [beta]"))
        spawn(corpus, state)

        assert delivery_check(corpus, state, capsys) == (0, "")

    def test_a_pinned_model_gets_the_exclusion_on_its_own_tier(self, config, corpus, state):
        define(config, f"{rulesets_block('    exclude: [beta]')}\nmodel: haiku")

        text = spawn(corpus, state)

        assert "tier haiku" in text
        assert "Body beta." not in text

    def test_no_model_pin_is_needed(self, config, corpus, state):
        define(config, rulesets_block("    exclude: [beta]"))

        text = spawn(corpus, state)

        assert "Body beta." not in text
        assert "the parent session's recorded tier" in text


class TestAdd:
    def test_an_added_stem_follows_the_tier_composition(self, config, corpus, state):
        define(config, rulesets_block("    add: [trial]"))

        text = spawn(corpus, state)

        assert delivery(state)["stems"] == [*STEMS, "trial"]
        assert text.index("Body gamma.") < text.index("Body trial.")

    def test_an_added_body_carries_its_naming_line(self, config, corpus, state):
        define(config, rulesets_block("    add: [trial]"))

        assert f"{resolve.naming_line('trial')}\n\nBody trial." in spawn(corpus, state)

    def test_delivery_check_compares_against_the_added_composition(
        self, config, corpus, state, capsys
    ):
        define(config, rulesets_block("    add: [trial]"))
        spawn(corpus, state)

        assert delivery_check(corpus, state, capsys) == (0, "")

    def test_a_stem_the_tier_already_composes_is_not_added_twice(self, config, corpus, state):
        (corpus / "experimental" / "alpha.md").write_text("Body other.\n", encoding="utf-8")
        define(config, rulesets_block("    add: [alpha]"))

        text = spawn(corpus, state)

        assert delivery(state)["stems"] == list(STEMS)
        assert "Body other." not in text

    def test_experimental_is_a_reserved_directory(self, corpus, capsys):
        assert resolve.main(["check", "--root", str(corpus), "--agents", str(corpus)]) == 0
        assert capsys.readouterr().out == ""


class TestCheck:
    def test_warns_on_an_unknown_key_and_an_unknown_stem(self, config, corpus, capsys):
        define(config, rulesets_block("    exclude: [nonesuch]\n    add: [absent]\n    bogus: 1"))

        code = resolve.main(["check", "--root", str(corpus), "--agents", str(config / "agents")])

        out = capsys.readouterr().out
        assert code == 0
        assert "warning: unknown-key" in out and "bogus" in out
        assert "warning: unknown-stem" in out
        assert "nonesuch" in out and "absent" in out

    def test_a_definition_with_a_legal_block_draws_no_warning(self, config, corpus, capsys):
        define(config, rulesets_block("    exclude: [beta]\n    add: [trial]"))

        code = resolve.main(["check", "--root", str(corpus), "--agents", str(config / "agents")])

        assert (code, capsys.readouterr().out) == (0, "")

    def test_a_definition_carrying_no_block_draws_no_warning(self, config, corpus, capsys):
        define(config, f"name: {AGENT}\nmodel: haiku")

        code = resolve.main(["check", "--root", str(corpus), "--agents", str(config / "agents")])

        assert (code, capsys.readouterr().out) == (0, "")

    def test_a_corpus_finding_still_fails_the_run_beside_a_warning(self, config, corpus, capsys):
        define(config, rulesets_block("    bogus: 1"))
        (corpus / "stray").mkdir()

        code = resolve.main(["check", "--root", str(corpus), "--agents", str(config / "agents")])

        out = capsys.readouterr().out
        assert code == 1
        assert "stray-directory" in out and "warning: unknown-key" in out


def test_the_record_lists_what_was_requested(config, corpus, state):
    define(config, rulesets_block("    exclude: [beta]\n    add: [trial]"))
    spawn(corpus, state)

    record = delivery(state)["rulesets"]

    assert (record["exclude"], record["add"]) == (["beta"], ["trial"])
    assert json.dumps(record)

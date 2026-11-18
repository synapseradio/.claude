#!/usr/bin/env -S uv run --frozen
"""A rulesets directory delivers its skills by name, and check holds each pairing of a rule with a skill.

Serves the person who moves a rule's body into `skills/<name>/SKILL.md` and leaves the rule as a
one-line pointer: `check` reports a pairing whose rule or skill is missing, a skill Claude Code
cannot load by its description, and a pointer that never names its skill; `skills --link` and the
session-start hook put each skill where Claude Code finds personal skills,
`<config>/skills/<name>/SKILL.md` (https://code.claude.com/docs/en/skills#where-skills-live).
Each case builds its directories under `tmp_path`, with home, cache, git config, and
configuration directory pointed there.

Run with `.venv/bin/python -m pytest features/plugins/rulesets/tests/test_skills.py`.
"""

import json
import pathlib

import pytest
from delivery_world import run_cli, scratch_environment
from rulesets.check.findings import PairingSubject, RuleSubject, SkillSubject
from rulesets.check.run import check
from rulesets.skill_links import link_at_session_start

SKILL_TEXT = "---\nname: voice\ndescription: How to write in the house voice.\n---\n\nBody.\n"
POINTER = "Load the `voice` skill before writing.\n"


@pytest.fixture
def environ(tmp_path) -> dict[str, str]:
    return scratch_environment(tmp_path)


@pytest.fixture
def config_directory(environ) -> pathlib.Path:
    return pathlib.Path(environ["CLAUDE_CONFIG_DIR"])


def build(config_directory, config, rules, skills) -> pathlib.Path:
    """The configuration directory's rulesets directory, with its config, rule files, and skill files."""
    root = config_directory / "rulesets"
    (root / "rules").mkdir(parents=True)
    (root / "config.yaml").write_text(config, encoding="utf-8")
    for stem, text in rules.items():
        (root / "rules" / f"{stem}.md").write_text(text, encoding="utf-8")
    for name, text in skills.items():
        (root / "skills" / name).mkdir(parents=True)
        if text is not None:
            (root / "skills" / name / "SKILL.md").write_text(text, encoding="utf-8")
    return root


def findings(root) -> list[tuple[str, object]]:
    report = check(root)
    return [(finding.kind, finding.subject) for finding in (*report.errors, *report.warnings)]


PAIRED = "defaults: writing\nskills:\n  writing: voice\n"


class TestCheckHoldsEachPairing:
    def test_a_rule_paired_with_a_well_formed_skill_draws_no_finding(
        self, config_directory
    ) -> None:
        root = build(
            config_directory,
            PAIRED,
            {"writing": POINTER, "writing@haiku": POINTER},
            {"voice": SKILL_TEXT},
        )

        assert findings(root) == []

    @pytest.mark.parametrize(
        ("config", "rules", "skills", "expected"),
        [
            pytest.param(
                PAIRED,
                {"writing": POINTER},
                {},
                [("pairing-unknown-skill", PairingSubject("writing"))],
                id="skill-does-not-exist",
            ),
            pytest.param(
                PAIRED,
                {"writing": POINTER},
                {"voice": None},
                [("skill-file", SkillSubject("voice"))],
                id="skill-directory-holds-no-skill-file",
            ),
            pytest.param(
                PAIRED,
                {"writing": POINTER},
                {"voice": "Body with no frontmatter.\n"},
                [("skill-frontmatter", SkillSubject("voice"))],
                id="no-frontmatter",
            ),
            pytest.param(
                PAIRED,
                {"writing": POINTER},
                {"voice": "---\nname: [voice\n---\nBody.\n"},
                [("skill-frontmatter", SkillSubject("voice"))],
                id="frontmatter-unparsable",
            ),
            pytest.param(
                PAIRED,
                {"writing": POINTER},
                {"voice": "---\nname: voice\n---\nBody.\n"},
                [("skill-frontmatter", SkillSubject("voice"))],
                id="no-description",
            ),
            pytest.param(
                PAIRED,
                {"writing": POINTER},
                {"voice": SKILL_TEXT.replace("name: voice", "name: tone")},
                [("skill-name", SkillSubject("voice"))],
                id="name-differs-from-the-directory",
            ),
            pytest.param(
                "defaults: writing\nskills:\n  writing@haiku: voice\n",
                {"writing": POINTER},
                {"voice": SKILL_TEXT},
                [("pairing-shape", PairingSubject("writing@haiku"))],
                id="pairing-a-variant",
            ),
            pytest.param(
                "defaults: writing\nskills:\n  writing: voice tone\n",
                {"writing": POINTER},
                {"voice": SKILL_TEXT},
                [("pairing-shape", PairingSubject("writing"))],
                id="pairing-two-skills",
            ),
        ],
    )
    def test_a_pairing_or_skill_that_cannot_load_is_an_error_naming_its_subject(
        self, config_directory, config, rules, skills, expected
    ) -> None:
        root = build(config_directory, config, rules, skills)

        assert findings(root) == expected

    def test_a_pairing_naming_a_rule_the_pool_lacks_is_an_error(self, config_directory) -> None:
        root = build(config_directory, PAIRED, {}, {"voice": SKILL_TEXT})

        assert ("pairing-unknown-rule", PairingSubject("writing")) in findings(root)

    def test_a_paired_rule_file_that_never_names_its_skill_draws_a_warning(
        self, config_directory
    ) -> None:
        root = build(
            config_directory,
            PAIRED,
            {"writing": POINTER, "writing@haiku": "Write well.\n"},
            {"voice": SKILL_TEXT},
        )

        report = check(root)

        assert report.errors == ()
        assert [(w.kind, w.subject, w.file.name) for w in report.warnings] == [
            ("pointer-unnamed", RuleSubject("writing"), "writing@haiku.md")
        ]


def personal_link(config_directory, name="voice") -> pathlib.Path:
    return config_directory / "skills" / name


class TestTheSkillsCommandLinksEachSkillWhereClaudeCodeFindsIt:
    def test_link_makes_the_skill_file_readable_at_the_personal_path(
        self, config_directory, environ
    ) -> None:
        build(config_directory, PAIRED, {"writing": POINTER}, {"voice": SKILL_TEXT})

        preview = run_cli(["skills"], environ)
        previewed = personal_link(config_directory).exists()
        linked = run_cli(["skills", "--link"], environ)
        again = run_cli(["skills"], environ)

        assert (preview.returncode, previewed) == (1, False)
        assert linked.returncode == 0
        assert (personal_link(config_directory) / "SKILL.md").read_text() == SKILL_TEXT
        assert not pathlib.Path(personal_link(config_directory).readlink()).is_absolute()
        assert again.returncode == 0
        assert again.stdout.startswith("voice: linked")

    def test_an_entry_already_standing_at_the_skills_name_is_left_and_reported(
        self, config_directory, environ
    ) -> None:
        build(config_directory, PAIRED, {"writing": POINTER}, {"voice": SKILL_TEXT})
        own = personal_link(config_directory)
        own.mkdir(parents=True)
        (own / "SKILL.md").write_text("mine\n", encoding="utf-8")

        result = run_cli(["skills", "--link"], environ)

        assert result.returncode == 1
        assert "voice: blocked" in result.stdout
        assert (own / "SKILL.md").read_text() == "mine\n"

    def test_a_link_to_a_removed_skill_is_removed_and_other_links_stay(
        self, config_directory, environ
    ) -> None:
        root = build(config_directory, PAIRED, {"writing": POINTER}, {"voice": SKILL_TEXT})
        run_cli(["skills", "--link"], environ)
        elsewhere = config_directory / "elsewhere"
        elsewhere.mkdir()
        personal_link(config_directory, "other").symlink_to(elsewhere)
        (root / "skills" / "voice" / "SKILL.md").unlink()
        (root / "skills" / "voice").rmdir()

        result = run_cli(["skills", "--link"], environ)

        assert result.returncode == 0
        assert not personal_link(config_directory).is_symlink()
        assert personal_link(config_directory, "other").is_symlink()


class TestTheSessionStartHookLinksSkillsSilently:
    def test_the_hook_links_each_skill_and_prints_nothing(self, config_directory, environ) -> None:
        build(config_directory, PAIRED, {"writing": POINTER}, {"voice": SKILL_TEXT})

        result = link_at_session_start([], b"{}", environ)

        assert (result.exit_code, result.stdout) == (0, "")
        assert (personal_link(config_directory) / "SKILL.md").is_file()

    def test_a_blocked_link_reaches_the_person_as_a_system_message(
        self, config_directory, environ
    ) -> None:
        build(config_directory, PAIRED, {"writing": POINTER}, {"voice": SKILL_TEXT})
        personal_link(config_directory).mkdir(parents=True)

        result = link_at_session_start([], b"{}", environ)

        assert result.exit_code == 0
        assert "voice: blocked" in json.loads(result.stdout)["systemMessage"]

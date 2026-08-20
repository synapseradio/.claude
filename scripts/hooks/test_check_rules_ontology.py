"""Tests for check-rules-ontology.py, run from this directory:

    python3.14 -m unittest test_check_rules_ontology -v

One test proves the checker green on the repository's rules/ and agents/.
The rest copy that tree into a temporary root, revert one repair to the
text the file held before the ontology settled it, and assert the checker
names the rule that repair closed. Where no repair exercises a rule, a
synthetic fixture does.
"""

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("check-rules-ontology.py")
REPO = Path(__file__).resolve().parent.parent.parent

FINDING = re.compile(r"^(?P<path>[^:]+):(?P<line>\d+): (?P<rule>[A-Z_]+) (?P<msg>.*)$")


def run_checker(*args):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    findings = []
    for line in completed.stdout.splitlines():
        m = FINDING.match(line)
        if m:
            findings.append((Path(m["path"]).name, m["rule"]))
    return completed.returncode, findings, completed.stdout + completed.stderr


# (file, text the repaired file holds now, text it held before, rules expected,
#  and the file the finding lands in where it differs from the edited one)
REVERSIONS = [
    (
        "rules/writing-rules.md",
        "activity in AppliesWhen\n",
        "activity in Applies\n",
        {"TRIGGER"},
    ),
    (
        "rules/structural-search.md",
        "=> write a YAML rule in\n      place of stacking flags   via(developTheRule)\n",
        "=> write a YAML rule under\n      via(DevelopTheRule) in place of stacking flags\n",
        {"POINTER", "VIA_TRAILING"},
    ),
    (
        "rules/git-commit.md",
        "|> compose the message   via(RepoFormatWins)\n      |> commit\n",
        "|> compose the message under RepoFormatWins |> commit\n",
        {"PROSE_POINTER"},
    ),
    (
        "agents/critic.md",
        "assign severity, stating the cost in the same clause   via(SeverityRanksByCost)\n",
        "assign severity per SeverityRanksByCost, stating the cost in the same\n      clause\n",
        {"PROSE_POINTER"},
    ),
    (
        "rules/writing-code.md",
        "require you never add complexity for scenarios that cannot happen\n",
        "add no complexity for scenarios that cannot happen\n",
        {"PROHIBITION"},
    ),
    (
        "agents/skill-designer.md",
        "require no local file stands in for that search",
        "let no local file stand in for that search",
        {"PROHIBITION"},
    ),
    (
        "rules/data-modeling.md",
        'require no representation holds "correct" status',
        'grant no single representation "correct" status',
        {"PROHIBITION"},
    ),
    (
        "rules/agent-delegation.md",
        "model = match (the task) {\n",
        "model = match (the task), taking the first arm that matches {\n",
        {"MATCH_HEAD"},
    ),
    (
        "rules/writing-comments.md",
        "    kind = match (knowledge) {\n"
        "      case (it fits a Kind above) => that Kind\n"
        "      default => none\n"
        "    }\n",
        "    kind = match (knowledge) against Kind, and (no kind matches) => none\n",
        {"MATCH_HEAD"},
    ),
    (
        "agents/critic.md",
        "      the suite catches\n    keep prose swaps in the report and out of every file\n",
        "      the suite catches. keep prose swaps in the report and out of every\n      file\n",
        {"SENTENCE_JOIN"},
    ),
    (
        "rules/writing-comments.md",
        "  constraint Brevity {\n    when in doubt, leave it out\n    when it is right, keep it concise\n",
        "  Constraints {\n    when in doubt, leave it out. when it is right, keep it concise\n",
        {"SENTENCE_JOIN", "DEMAND_CONTAINER"},
    ),
    (
        "rules/core-rules.md",
        "\n  constraint Reification {\n",
        "\n  0.Reification {\n",
        {"DEMAND_CONTAINER"},
    ),
    (
        "rules/debugging.md",
        "  constraint HypothesisFirst {\n    state the hypothesis before changing anything, and let the cheapest\n      test decide it\n",
        "  state the hypothesis before changing anything, and let the cheapest\n      test decide it\n",
        {"DEMAND_CONTAINER"},
    ),
    (
        "rules/unasked-asides.md",
        "=> keep it, marked `[?]`\n",
        "=> keep it, marked `[?]` under CoreRules 8.GroundOrMark\n",
        {"XREF"},
    ),
    (
        "rules/scratchpad.md",
        "=> store it as a\n      persistent memory\n",
        "=> store it under\n      PersistentMemory\n",
        {"XREF"},
    ),
    (
        "agents/orchestrator.md",
        "readings = inference, span, reversibility, verifiability, and\n      survivingCritiques, taken on the step\n",
        "readings = the Readings the AgentDelegation rule defines, taken on the\n      step\n",
        {"XREF"},
    ),
    (
        "rules/ask-user-before-assuming.md",
        "\n  constraint OnGoal {\n",
        "\n  constraint Goal {\n",
        {"UNIQUE_NAME"},
    ),
    (
        "agents/spider.md",
        "/empty | e - ",
        "/empty - ",
        {"COMMAND_ALIAS"},
    ),
    (
        "rules/agent-delegation.md",
        "      uncertain and to say which it did, with ForkAuthority's grant stated\n",
        "      uncertain, and to say which it did. state ForkAuthority's grant here\n"
        "    (a section is empty) => one line naming the absence, never filler\n",
        {"DEMAND_CONTAINER", "SENTENCE_JOIN"},
    ),
    (
        "agents/skill-designer.md",
        "    findings: ordered by cost\n",
        "    findings ordered by cost\n",
        {"MEMBER_FORM"},
    ),
]

# (file, text the file holds now, text that breaks it, rules expected)
SYNTHETIC = [
    (
        "agents/scout.md",
        "require ReadOnly, Grounded, and Edges hold on every turn",
        "require ReadOnly and Edges hold on every turn",
        {"AGENT_ROLLCALL"},
    ),
    (
        "agents/spider.md",
        "\nname: spider\n",
        "\n",
        {"AGENT_FRONTMATTER"},
    ),
    (
        "rules/debugging.md",
        "  AppliesWhen { debugging a problem }\n",
        "  Applies { debugging a problem }\n",
        {"TRIGGER"},
    ),
    (
        "rules/debugging.md",
        "Debugging {\n",
        "WritingCode {\n",
        {"UNIQUE_NAME"},
        "writing-code.md",
    ),
]


class CheckRulesOntology(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        for side in ("rules", "agents"):
            shutil.copytree(REPO / side, self.root / side)

    def revert(self, rel, current, previous):
        path = self.root / rel
        text = path.read_text()
        self.assertGreaterEqual(
            text.count(current), 1, f"{rel} no longer holds the repaired text {current!r}"
        )
        path.write_text(text.replace(current, previous))

    def test_the_repository_tree_is_green(self):
        code, findings, out = run_checker()
        self.assertEqual(code, 0, out)
        self.assertEqual(findings, [])

    def test_the_copied_tree_is_green_before_any_reversion(self):
        code, _, out = run_checker("--root", str(self.root))
        self.assertEqual(code, 0, out)

    def test_each_reverted_repair_raises_the_rule_that_closed_it(self):
        for rel, current, previous, rules, *reported in REVERSIONS + SYNTHETIC:
            with self.subTest(file=rel, rules=sorted(rules)):
                self.setUp()
                self.revert(rel, current, previous)
                code, findings, out = run_checker("--root", str(self.root))
                self.assertEqual(code, 1, out)
                where = reported[0] if reported else Path(rel).name
                raised = {rule for name, rule in findings if name == where}
                self.assertTrue(
                    rules <= raised, f"expected {sorted(rules)}, got {sorted(raised)}:\n{out}"
                )

    def test_a_reversion_names_no_other_file(self):
        rel, current, previous, _ = REVERSIONS[0][:4]
        self.revert(rel, current, previous)
        _, findings, _ = run_checker("--root", str(self.root))
        self.assertEqual({name for name, _ in findings}, {Path(rel).name})

    def test_a_root_without_rules_exits_two(self):
        empty = self.root / "empty"
        empty.mkdir()
        code, _, _ = run_checker("--root", str(empty))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()

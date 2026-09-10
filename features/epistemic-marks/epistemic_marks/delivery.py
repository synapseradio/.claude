"""The rule text this plugin teaches a session."""

from pathlib import Path

DIVIDER = "---"

RULE_BODY = Path(__file__).resolve().parent.parent / "rule-text" / "epistemic-marks.md"


def after_divider(raw):
    """Everything past the first divider line, or all of it without one."""
    lines = raw.splitlines()
    for number, line in enumerate(lines):
        if line.strip() == DIVIDER:
            return "\n".join(lines[number + 1 :])
    return raw


def rule_text(path=None):
    """The teaching half of the rule file, empty where it cannot be read."""
    try:
        raw = (path or RULE_BODY).read_text()
    except OSError:
        return ""
    return after_divider(raw).strip()

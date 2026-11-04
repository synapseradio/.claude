"""Write a check report as lines in the engine's outward words, one finding to a line."""

from __future__ import annotations

from rulesets.check.findings import (
    CheckError,
    CheckWarning,
    DirectorySubject,
    ItemSubject,
    KeySubject,
    ManifestSubject,
    ModelSubject,
    ReferencesSubject,
    ReferenceSubject,
    Report,
    RulePairSubject,
    RulesetSubject,
    RuleSubject,
    Subject,
)


def _describe_subject(subject: Subject) -> str:
    """The subject in outward words. Items count from 1 in the order they are written."""

    match subject:
        case RuleSubject(name):
            return f"rule `{name}`"
        case RulePairSubject(name, other):
            return f"rule `{name}` and rule `{other}`"
        case RulesetSubject(name):
            return f"ruleset `{name}`"
        case ItemSubject(index):
            return f"item {index + 1}"
        case KeySubject(name):
            return f"key `{name}`"
        case ModelSubject(name):
            return f"model `{name}`"
        case ReferenceSubject(text):
            return f"reference `{text}`"
        case ReferencesSubject(members):
            return "references " + " and ".join(f"`{member.text}`" for member in members)
        case ManifestSubject():
            return "manifest"
        case DirectorySubject(path):
            return f"directory `{path.name}`"


def finding_line(finding: CheckError | CheckWarning) -> str:
    """`file:line: severity [kind] subject: message`, with the line left out where none applies."""

    severity = "error" if isinstance(finding, CheckError) else "warning"
    location = f"{finding.file}:{finding.line}" if finding.line is not None else str(finding.file)
    subject = _describe_subject(finding.subject)
    return f"{location}: {severity} [{finding.kind}] {subject}: {finding.message}"


def report_lines(report: Report) -> list[str]:
    """Every error, then every warning."""

    return [finding_line(finding) for finding in (*report.errors, *report.warnings)]

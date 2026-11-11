"""Write a check report as lines in the engine's outward words, one finding to a line."""

from __future__ import annotations

from rulesets.check.findings import (
    BlockSubject,
    CheckError,
    CheckWarning,
    ConfigSubject,
    ContextSubject,
    DirectorySubject,
    FlagSubject,
    KeySubject,
    ModelSubject,
    ReferencesSubject,
    ReferenceSubject,
    Report,
    RulePairSubject,
    RulesetsSubject,
    RulesetSubject,
    RuleSubject,
    Subject,
)


def _describe_subject(subject: Subject) -> str:
    """The subject in outward words."""

    match subject:
        case RuleSubject(name):
            return f"rule `{name}`"
        case RulePairSubject(name, other):
            return f"rule `{name}` and rule `{other}`"
        case RulesetSubject(name):
            return f"ruleset `{name}`"
        case RulesetsSubject(names):
            quoted = [f"`{name}`" for name in names]
            if len(quoted) == 1:
                return f"ruleset {quoted[0]}"
            if len(quoted) == 2:
                return f"rulesets {quoted[0]} and {quoted[1]}"
            return f"rulesets {', '.join(quoted[:-1])}, and {quoted[-1]}"
        case BlockSubject(condition):
            return f"block `{condition}`"
        case KeySubject(name):
            return f"key `{name}`"
        case ModelSubject(name):
            return f"model `{name}`"
        case FlagSubject(name):
            return f"flag `{name}`"
        case ReferenceSubject(text):
            return f"reference `{text}`"
        case ReferencesSubject(members):
            return "references " + " and ".join(f"`{member.text}`" for member in members)
        case ConfigSubject():
            return "config"
        case ContextSubject(facts):
            named = [
                *([f"model {facts.model}"] if isinstance(facts.model, str) else []),
                *([f"agent {facts.agent}"] if isinstance(facts.agent, str) else []),
                *([f"kind {facts.kind}"] if isinstance(facts.kind, str) else []),
                *(f"flag {flag}" for flag in sorted(facts.flags)),
            ]
            return "context " + ", ".join(named)
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

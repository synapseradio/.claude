"""What the rule files of a pool carry: errors in their reading, frontmatter, and size, and layout warnings."""

from __future__ import annotations

from rulesets.check.findings import CheckError, CheckWarning, DirectorySubject, RuleSubject
from rulesets.part_budget import PART_BUDGET
from rulesets.source.condition import FACTS
from rulesets.source.pool import REFERENCES_DIRECTORY, Citation, Pool, PoolFile

# A frontmatter key scopes a rule file when it is the harness's path scope, the manifest's
# `when` key, or a fact a condition tests, singular or plural.
_CONDITION_KEYS = frozenset({"paths", "when", *FACTS, *(f"{fact}s" for fact in FACTS)})

_CONFIGURATION_DIRECTORY = "~/.claude/"
_CORPUS_REFERENCES = f"{_CONFIGURATION_DIRECTORY}rulesets/{REFERENCES_DIRECTORY}/"
_RELATIVE_REFERENCES = f"{REFERENCES_DIRECTORY}/"


def pool_errors(pool: Pool) -> tuple[CheckError, ...]:
    """Every error in the pool's rule files, rule by rule in name order."""

    errors: list[CheckError] = []
    for rule in pool.rules.values():
        subject = RuleSubject(rule.name)
        if rule.default is None:
            variants = ", ".join(f"`{variant}`" for variant in rule.variants)
            noun = "variants" if len(rule.variants) > 1 else "variant"
            errors.append(
                CheckError(
                    "variant-without-default",
                    subject,
                    rule.path,
                    None,
                    f"rule `{rule.name}` has {noun} {variants} and no default form",
                )
            )
        for file in rule.files():
            if file.problem is not None:
                errors.append(CheckError("unreadable-file", subject, file.path, None, file.problem))
            if file.frontmatter is not None and not file.frontmatter.parsed:
                errors.append(
                    CheckError(
                        "frontmatter-unparsable",
                        subject,
                        file.path,
                        None,
                        f"the frontmatter of rule `{rule.name}` is not valid YAML, "
                        "so whether it holds a condition is unknown",
                    )
                )
            if len(file.text) > PART_BUDGET:
                errors.append(
                    CheckError(
                        "oversize-body",
                        subject,
                        file.path,
                        None,
                        f"`{file.path.name}` is {len(file.text)} characters, past the "
                        f"{PART_BUDGET}-character part budget",
                    )
                )
            condition = next((k for k in file.frontmatter_keys if k.key in _CONDITION_KEYS), None)
            if condition is not None:
                errors.append(
                    CheckError(
                        "rule-condition",
                        subject,
                        file.path,
                        condition.line,
                        f"`{condition.key}` in the frontmatter of rule `{rule.name}` "
                        "is a condition; a rule file holds text and no condition",
                    )
                )
    return tuple(errors)


def pool_warnings(pool: Pool) -> tuple[CheckWarning, ...]:
    """Every layout and body warning of the pool: stray directories first, then rule by rule."""

    warnings: list[CheckWarning] = [
        CheckWarning(
            "stray-directory",
            DirectorySubject(directory),
            directory,
            None,
            f"the directory `{directory.name}` holds no rule file the pool reads",
        )
        for directory in pool.stray_directories
    ]
    for rule in pool.rules.values():
        for file in rule.files():
            warnings.extend(_body_warnings(pool, file))
    return tuple(warnings)


def _body_warnings(pool: Pool, file: PoolFile) -> list[CheckWarning]:
    subject = RuleSubject(file.rule)
    warnings: list[CheckWarning] = []
    if file.marker is not None and (file.marker.rule, file.marker.variant) != (
        file.rule,
        file.variant,
    ):
        warnings.append(
            CheckWarning(
                "marker-for-another-rule",
                subject,
                file.path,
                1,
                f"`{file.path.name}` opens on a marker for another rule or another form of its own",
            )
        )
    for citation in file.citations:
        if (warning := _citation_warning(pool, file, citation)) is not None:
            warnings.append(warning)
    return warnings


def _citation_warning(pool: Pool, file: PoolFile, citation: Citation) -> CheckWarning | None:
    subject = RuleSubject(file.rule)
    path = citation.text
    for prefix in (_CORPUS_REFERENCES, _RELATIVE_REFERENCES):
        if path.startswith(prefix):
            name = path.removeprefix(prefix)
            if not name or pool.has_reference(name):
                return None
            return CheckWarning(
                "dangling-reference",
                subject,
                file.path,
                citation.line,
                f"`{file.path.name}` cites `{path}`, and `{REFERENCES_DIRECTORY}/{name}` is not there",
            )
    if path.startswith(_CONFIGURATION_DIRECTORY):
        return None
    return CheckWarning(
        "external-reference",
        subject,
        file.path,
        citation.line,
        f"`{file.path.name}` cites `{path}`, a path outside the configuration directory",
    )

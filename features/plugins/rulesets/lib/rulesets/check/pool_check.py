"""What the rule files of a pool carry: errors in their names and frontmatter, and layout warnings."""

from __future__ import annotations

from rulesets.check.findings import CheckError, CheckWarning, DirectorySubject, RuleSubject
from rulesets.resolve import PART_BUDGET, REFERENCE_CITATION
from rulesets.source.pool import Pool, PoolFile


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
                    rule.files()[0].path,
                    None,
                    f"rule `{rule.name}` has {noun} {variants} and no default form",
                )
            )
        for file in rule.files():
            if file.condition is not None:
                errors.append(
                    CheckError(
                        "rule-condition",
                        subject,
                        file.path,
                        file.condition.line,
                        f"`{file.condition.key}` in the frontmatter of rule `{rule.name}` "
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
    if len(file.text) > PART_BUDGET:
        warnings.append(
            CheckWarning(
                "oversize-body",
                subject,
                file.path,
                None,
                f"`{file.path.name}` is {len(file.text)} characters, past the "
                f"{PART_BUDGET}-character part budget",
            )
        )
    for citation in REFERENCE_CITATION.finditer(file.text):
        name = citation["name"]
        line = file.line_of(citation.start())
        if citation["within"] == "references":
            warnings.append(
                CheckWarning(
                    "external-reference",
                    subject,
                    file.path,
                    line,
                    f"`{file.path.name}` cites `~/.claude/references/{name}`, "
                    "which the corpus does not carry",
                )
            )
        elif not (pool.root / "references" / name).is_file():
            warnings.append(
                CheckWarning(
                    "dangling-reference",
                    subject,
                    file.path,
                    line,
                    f"`{file.path.name}` cites `{name}`, and `references/{name}` is not there",
                )
            )
    return warnings

"""Check one rulesets directory: read it, run every finding source, and report in one run."""

from __future__ import annotations

import pathlib

from rulesets.check.cross_reference_check import cross_reference_warnings
from rulesets.check.findings import CheckError, CheckWarning, Report
from rulesets.check.inclusion_check import inclusion_warnings
from rulesets.check.manifest_check import manifest_errors, unparsable_error
from rulesets.check.pool_check import pool_errors, pool_warnings
from rulesets.source.expansion import Expander
from rulesets.source.manifest import ManifestParseError, read_manifest
from rulesets.source.pool import read_pool


def check(root: pathlib.Path) -> Report:
    """Report every error and every warning of the rulesets directory at `root`.

    A manifest that does not parse is itself an error, and the checks that need it are
    skipped while the checks of the rule files still run.
    """

    pool = read_pool(root)
    errors: list[CheckError] = []
    warnings: list[CheckWarning] = []
    try:
        manifest = read_manifest(root)
    except ManifestParseError as failure:
        errors.append(unparsable_error(failure))
    else:
        expander = Expander(manifest.spreadable(), pool.variants_by_rule())
        errors.extend(manifest_errors(manifest, expander))
        warnings.extend(inclusion_warnings(manifest, pool, expander))
    errors.extend(pool_errors(pool))
    warnings.extend(pool_warnings(pool))
    warnings.extend(cross_reference_warnings(pool))
    return Report(errors=tuple(errors), warnings=tuple(warnings))

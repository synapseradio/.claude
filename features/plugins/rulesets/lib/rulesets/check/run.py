"""Check one rulesets directory: read it, run every finding source, and report in one run."""

from __future__ import annotations

import pathlib

from rulesets.check.config_check import config_errors, old_file_error, unparsable_error
from rulesets.check.conflict_check import check_conflicts
from rulesets.check.cross_reference_check import cross_reference_warnings
from rulesets.check.findings import CheckError, CheckWarning, Report
from rulesets.check.inclusion_check import inclusion_warnings
from rulesets.check.part_count_check import check_part_count
from rulesets.check.pool_check import pool_errors, pool_warnings
from rulesets.source.config import OLD_CONFIG_FILE, ConfigParseError, read_config
from rulesets.source.directory import read_directory
from rulesets.source.expansion import Expander
from rulesets.source.pool import read_pool


def check(root: pathlib.Path) -> Report:
    """Report every error and every warning of the rulesets directory at `root`.

    A config that does not parse is itself an error, and the checks that need it are
    skipped while the checks of the rule files still run.
    """

    pool = read_pool(root)
    directory = read_directory(root)
    errors: list[CheckError] = []
    warnings: list[CheckWarning] = []
    try:
        config = read_config(root)
    except ConfigParseError as failure:
        errors.append(unparsable_error(failure))
    else:
        if not config.path.is_file() and (root / OLD_CONFIG_FILE).is_file():
            errors.append(old_file_error(root))
        expander = Expander(config.spreadable(), pool.variants_by_rule())
        errors.extend(config_errors(config, expander))
        warnings.extend(inclusion_warnings(config, pool, expander))
        errors.extend(check_conflicts(directory))
    warnings.extend(check_part_count(directory))
    errors.extend(pool_errors(pool))
    warnings.extend(pool_warnings(pool))
    warnings.extend(cross_reference_warnings(pool))
    return Report(errors=tuple(errors), warnings=tuple(warnings))

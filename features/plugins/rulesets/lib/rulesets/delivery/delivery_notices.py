"""The notices a first part draws from the rulesets directory and the composition, and the message they make."""

from __future__ import annotations

import pathlib

from rulesets.audit.delivery_record import ConflictLine
from rulesets.compose.composition import Composition
from rulesets.delivery.hook_output import MESSAGE_SHOWN
from rulesets.notices import (
    SHOWN,
    Notice,
    block_skipped_notice,
    config_missing_notice,
    config_unparsable_notice,
    old_config_file_notice,
    reference_notice,
    scaffold_failed_notice,
    scaffolded_notice,
    variant_conflict_notice,
    withheld_notice,
)
from rulesets.source.config import CONFIG_FILE
from rulesets.source.directory import Missing as ConfigMissing
from rulesets.source.directory import Present, RulesetsDirectory, Unparsable
from rulesets.source.scaffold import AlreadyPresent, Scaffolded, ScaffoldFailed


def directory_notices(
    scaffolded: Scaffolded | AlreadyPresent | ScaffoldFailed,
    directory: RulesetsDirectory,
    root: pathlib.Path,
) -> tuple[Notice, ...]:
    """What the directory's state says: a scaffold's outcome, or why a config is not read."""

    match scaffolded:
        case Scaffolded():
            return (scaffolded_notice(str(root)),)
        case ScaffoldFailed(reason=reason):
            return (scaffold_failed_notice(str(root), reason),)
        case AlreadyPresent():
            pass
    match directory.config:
        case ConfigMissing(old_file=None):
            return (config_missing_notice(str(root / CONFIG_FILE)),)
        case ConfigMissing(old_file=old_file):
            return (old_config_file_notice(str(old_file), str(root / CONFIG_FILE)),)
        case Unparsable(error=error):
            return (config_unparsable_notice(str(error)),)
        case Present():
            return ()


def composition_notices(composition: Composition) -> tuple[Notice, ...]:
    """What the composition skipped, withheld, or settled by fallback."""

    return (
        *(block_skipped_notice(b.condition, b.undeclared) for b in composition.skipped_blocks),
        *(reference_notice(s.text, s.line, s.name) for s in composition.skipped),
        *(withheld_notice(w.rule, w.error) for w in composition.withheld),
        *(
            variant_conflict_notice(
                c.rule,
                [(s.reference, s.line) for s in ConflictLine.of(c).statements],
                c.variant,
            )
            for c in composition.conflicts
        ),
    )


def shown_message(event: str, notices: tuple[Notice, ...]) -> str | None:
    """The shown notices as one message, or None where none is shown or the event shows none."""

    shown = [notice.subject for notice in notices if notice.kind in SHOWN]
    if not shown or not MESSAGE_SHOWN[event]:
        return None
    return "\n".join(shown)

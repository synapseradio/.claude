"""Block-message composition.

Builds the block text the binding's action surfaces as a deny
reason, block reason, or injected context. The message lists only
fired verdicts and includes only the remediation paragraphs those
verdicts reference, so the body the user reads stays scoped to what
actually tripped on the body Arbiter just judged.
"""

from collections.abc import Iterable

from .config import VerdictSpec

ORIENTATION_PREFIX = "*\n\n"

# Per-event lead sentence on the remediation block. Phrased as a
# second-reader observation rather than a correction notice — the
# block fires on a single judge pass and may be a false positive on
# an honest report. The plan flow is pre-tool, so the model has not
# yet emitted the message it needs to revise; the turn flow is
# post-message, so it has.
_REMEDIATION_LEAD: dict[str, str] = {
    "PreToolUse": "A second look at the plan before re-emitting ExitPlanMode:",
    "Stop": "A second look at the closing message before ending the turn:",
    "SubagentStop": "A second look at the closing message before ending the turn:",
}

# Sentences injected on a re-emission of ExitPlanMode after a prior
# block. The block-once policy lifts the deny on the second pass
# regardless of fresh verdicts; these strings give the assistant a
# quotable signal it can hand to a sub-agent prompt. Verbatim
# wording matters — the user pastes these into Task() briefs.
REEVAL_APPROVED = "Arbiter approved this plan on re-evaluation; proceed with implementation."
REEVAL_REMAINING_TEMPLATE = (
    "Arbiter saw remaining issues on re-evaluation but is no longer blocking: "
    "{verdicts}. Address them in execution where reasonable."
)


def reeval_remaining_message(fired_specs: list[VerdictSpec]) -> str:
    """Compose the second-pass-dirty injection sentence with verdict names."""
    listed = ", ".join(spec.name for spec in fired_specs)
    return REEVAL_REMAINING_TEMPLATE.format(verdicts=listed)


# Static fallback emitted when the local judge daemon is
# unreachable. Arbiter fails closed: the binding's action fires with
# this text so a server outage cannot silently disable the safety
# net. Keep it to one paragraph — the user reads this inline as the
# binding's deny / block reason.
FALLBACK_REPLAN_SLIM = """*

The local arbiter judge is unavailable. Re-read the body for: (1) direct questions to the user — route them through `AskUserQuestion`; (2) uncommitted alternatives — pick one and commit, or lift the choice into `AskUserQuestion`; (3) deterministic failures dismissed as out-of-scope, pre-existing, or unrelated — fix or request explicit per-failure permission to defer; (4) baseline probes against main/master/trunk to check whether a failure is pre-existing — skip the probe. Run `~/.claude/scripts/arbiter/arbiter-up.sh` to start the judge, then continue. The judge runs on every turn, so this hook fails closed when it cannot reach the server.
"""


def _scoped_remediation_keys(fired_specs: Iterable[VerdictSpec]) -> list[str]:
    """Remediation keys referenced by fired verdicts, in declaration
    order, deduped."""
    seen: set[str] = set()
    out: list[str] = []
    for spec in fired_specs:
        for key in spec.remediation:
            if key in seen:
                continue
            seen.add(key)
            out.append(key)
    return out


def compose_message(
    fired_specs: list[VerdictSpec],
    remediation: dict[str, str],
    event: str,
) -> str:
    """Assemble orientation + verdicts + glossary + remediation."""
    if not fired_specs:
        return ""
    listed = ", ".join(spec.name for spec in fired_specs)
    glossary_lines = "\n".join(spec.glossary for spec in fired_specs)
    rem_keys = _scoped_remediation_keys(fired_specs)
    rem_body = "\n\n".join(remediation[k] for k in rem_keys)
    rem_lead = _REMEDIATION_LEAD.get(event, _REMEDIATION_LEAD["Stop"])
    return (
        ORIENTATION_PREFIX
        + f"Arbiter fired: `{listed}`.\n\n"
        + glossary_lines
        + "\n\n"
        + rem_lead
        + "\n\n"
        + rem_body
        + "\n"
    )

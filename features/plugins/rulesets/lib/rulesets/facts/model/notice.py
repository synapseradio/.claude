"""The notice a model fact draws."""

from rulesets.facts.model.fact import Claimed, Missing, ModelFact, Unclaimed
from rulesets.notices import Notice

_REPORTERS = {
    "harness-reported": "the model the harness reported",
    "switch-target": "the switch's target model",
    "per-spawn": "the model the caller named",
    "definition-pin": "the definition's pin",
}


def model_notice(fact: ModelFact) -> Notice | None:
    """The notice a model fact draws: its identifier where unclaimed, the reason where missing."""

    match fact:
        case Claimed():
            return None
        case Unclaimed(identifier=identifier):
            return Notice("model-unclaimed", f"no declared model name claims `{identifier}`")
        case Missing(not_a_string=None):
            return Notice("model-missing", "no model identifier was available: no source named one")
        case Missing(not_a_string=reported):
            reporter = _REPORTERS.get(str(reported.source), str(reported.source))
            article = "an" if reported.type_name[0] in "aeiou" else "a"
            return Notice(
                "model-missing",
                f"no model identifier was available: {reporter} is {article} {reported.type_name},"
                " not a string",
            )

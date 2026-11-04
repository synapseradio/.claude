"""The notice a model fact draws."""

from rulesets.facts.model.fact import Claimed, Missing, ModelFact, Unclaimed
from rulesets.notices import Notice


def model_notice(fact: ModelFact) -> Notice | None:
    """The notice a model fact draws: its identifier where unclaimed, the reason where missing."""

    match fact:
        case Claimed():
            return None
        case Unclaimed(identifier=identifier):
            return Notice("model-unclaimed", f"no declared model name claims `{identifier}`")
        case Missing(not_a_string=None):
            return Notice("model-missing", "no source named a model identifier")
        case Missing(not_a_string=reported):
            return Notice(
                "model-missing",
                f"the model identifier the harness reported is a {reported.type_name}, not a string",
            )

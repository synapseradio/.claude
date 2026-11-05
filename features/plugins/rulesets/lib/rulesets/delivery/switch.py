"""A model switch's delivery, or its no-op where the new model composes the same rules."""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Mapping

from rulesets.compose.composition import compose
from rulesets.delivery.first_part import deliver_first
from rulesets.delivery.hook_output import PartOutput
from rulesets.delivery.plan import Silent, write_plan
from rulesets.delivery.request import ModelSwitch
from rulesets.facts.model.record import write_model_record
from rulesets.facts.resolve_context import resolve_context
from rulesets.locations import Locations
from rulesets.notices import earlier_rules_remain_notice
from rulesets.session.launch_agent import read_launch_agent
from rulesets.session.state import SessionState
from rulesets.source.directory import read_directory


def deliver_switch(
    request: ModelSwitch,
    locations: Locations,
    environ: Mapping[str, str],
    slot: pathlib.Path,
    generation: str,
) -> PartOutput:
    """Deliver the rules composed for the target model, or nothing where they match the origin's.

    The switch keeps the session's non-model facts, so it takes the agent the session launched
    under. A switch that changes no rule writes the session's model record and no delivery record.
    """

    request = dataclasses.replace(request, agent=read_launch_agent(locations, request.session_id))
    if request.from_model is not None and _composes_alike(request, locations, environ):
        write_model_record(request.session_id, request.to_model, locations.state)
        write_plan(slot, Silent(generation))
        return PartOutput()
    return deliver_first(
        request, locations, environ, slot, generation, (earlier_rules_remain_notice(),)
    )


def _composes_alike(request: ModelSwitch, locations: Locations, environ: Mapping[str, str]) -> bool:
    directory = read_directory(locations.rulesets)
    outcomes = [
        tuple(
            (rule.rule, rule.variant)
            for rule in compose(
                directory,
                resolve_context(side, directory, locations, environ).facts,
                SessionState(),
            ).rules
        )
        for side in (request.origin(), request)
    ]
    return outcomes[0] == outcomes[1]

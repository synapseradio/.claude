#!/usr/bin/env python3
"""How `fair_shares` divides the machine's worker slots among the suites of one run.

Every suite gets at least one slot and at most the workers it wants; the slots
left after that go out in proportion to what each suite wants beyond its first
worker, rounded down, then one each by largest remainder with ties settled by
name order.
"""

import pathlib
import sys

import pytest

VERIFY_DIR = pathlib.Path(__file__).resolve().parents[1] / "verify"

sys.path.insert(0, str(VERIFY_DIR))
import slots  # noqa: E402  (path must be set before this import)

REAL_WANTS = {
    "rulesets": 26,
    "scripts": 17,
    "warden": 14,
    "epistemic-marks": 10,
    "harness-config": 6,
    "scripts-bats": 6,
    "context-gauge": 1,
}

SHAPES = {
    "the real seven suites": (REAL_WANTS, 12),
    "one dominant suite": ({"big": 100, "small": 2, "tiny": 1}, 12),
    "equal wants": ({"a": 10, "b": 10, "c": 10}, 12),
    "wants below the slots": ({"a": 2, "b": 3}, 12),
    "more suites than slots": ({"a": 5, "b": 5, "c": 5, "d": 5, "e": 5}, 3),
    "a single slot": ({"a": 4, "b": 9}, 1),
}


def test_the_real_seven_suites_share_twelve_slots_as_the_contract_works_them_out() -> None:
    """Worked by hand: 5 slots remain after one each, split over wants-minus-one 25:16:13:9:5:5:0."""
    shares = slots.fair_shares(REAL_WANTS, 12)

    assert shares == {
        "rulesets": 3,
        "scripts": 2,
        "warden": 2,
        "epistemic-marks": 2,
        "harness-config": 1,
        "scripts-bats": 1,
        "context-gauge": 1,
    }, f"shares were {shares}"


@pytest.mark.parametrize(("wants", "size"), SHAPES.values(), ids=SHAPES.keys())
def test_every_suite_gets_at_least_one_slot(wants: dict[str, int], size: int) -> None:
    shares = slots.fair_shares(wants, size)

    assert set(shares) == set(wants), f"every suite is named in the shares: {shares}"
    starved = {name: share for name, share in shares.items() if share < 1}
    assert not starved, f"suites left without a slot: {starved}"


@pytest.mark.parametrize(("wants", "size"), SHAPES.values(), ids=SHAPES.keys())
def test_no_suite_gets_more_slots_than_it_wants(wants: dict[str, int], size: int) -> None:
    shares = slots.fair_shares(wants, size)

    over = {name: (shares[name], wants[name]) for name in wants if shares[name] > wants[name]}
    assert not over, f"suites given more than they want, as (share, want): {over}"


@pytest.mark.parametrize(
    ("wants", "size"),
    [
        pytest.param(REAL_WANTS, 12, id="the real seven suites"),
        pytest.param({"a": 10, "b": 10, "c": 10}, 12, id="equal wants"),
        pytest.param({"big": 100, "small": 2, "tiny": 1}, 12, id="one dominant suite"),
    ],
)
def test_the_shares_use_every_slot_when_the_wants_exceed_the_pool(
    wants: dict[str, int], size: int
) -> None:
    shares = slots.fair_shares(wants, size)

    assert sum(shares.values()) == size, f"{size} slots, shares {shares}"


def test_equal_wants_split_the_pool_evenly() -> None:
    shares = slots.fair_shares({"a": 10, "b": 10, "c": 10}, 12)

    assert shares == {"a": 4, "b": 4, "c": 4}, f"shares were {shares}"


@pytest.mark.parametrize(
    ("want", "size", "expected"),
    [(26, 12, 12), (5, 12, 5), (1, 12, 1), (12, 12, 12)],
    ids=["want above the pool", "want below the pool", "want of one", "want equal to the pool"],
)
def test_a_lone_suite_gets_the_smaller_of_its_want_and_the_pool(
    want: int, size: int, expected: int
) -> None:
    shares = slots.fair_shares({"only": want}, size)

    assert shares == {"only": expected}, f"want {want}, pool {size}: {shares}"


def test_a_tie_for_the_last_slot_goes_to_the_first_name_in_order() -> None:
    """One slot remains after one each, and `amy` and `zed` want the same: 0.5 of it apiece."""
    shares = slots.fair_shares({"zed": 3, "amy": 3, "one": 1}, 4)

    assert shares == {"amy": 2, "zed": 1, "one": 1}, (
        f"the tie goes to amy, listed after zed: {shares}"
    )


def test_the_last_slot_goes_to_the_suite_with_the_largest_remainder_not_the_largest_want() -> None:
    """Two slots remain after one each over wants-minus-one 2:3, giving 0.8 and 1.2 of them."""
    shares = slots.fair_shares({"a": 3, "b": 4}, 4)

    assert shares == {"a": 2, "b": 2}, (
        f"b rounds down to 1 with 0.2 over, a to 0 with 0.8 over: {shares}"
    )

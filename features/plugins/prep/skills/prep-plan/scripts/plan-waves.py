"""Print the parallel waves a readiness file's unit and contract lines allow.

    uv run --python 3.14 --no-project plan-waves.py READINESS_FILE

Reads every line of these two forms, fields separated by `|`, free text allowed
in any field that carries no key:

    - contract: NAME | fixed or open | free text
    - unit: NAME | free text | owns: PATH[#REGION], ... | provides: CONTRACT, ...
      | consumes: CONTRACT, ... | waits: UNIT (the code it needs), ... or none

A unit starts one wave after the last unit it waits on. It waits on each unit
its waits field names, and on the provider of each open contract it consumes.
A fixed contract, one the plan states in full, makes no wait.

Prints the waves, the widest wave and the longest chain, what stating each open
contract would free, each hotspot (a path that units rewrite one after
another), and each problem: a wait or a contract no line names, a contract
neither fixed nor open, a cycle, a repeated name, or two units that own the
same path or region while neither waits on the other.

Exits 0 with no problem, 1 with a problem, 2 where the file holds no unit
line. Reads only. Runs on Python 3.14 and later with the standard library alone.
"""

from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

UNIT_KEYS = ("owns", "provides", "consumes", "waits")


def fields_of(line: str, prefix: str) -> list[str]:
    return [field.strip() for field in line[len(prefix) :].split("|")]


def parse(text: str) -> tuple[dict[str, dict], dict[str, str], list[str]]:
    units: dict[str, dict] = {}
    contracts: dict[str, str] = {}
    problems = []
    for line in text.splitlines():
        if line.startswith("- contract:"):
            fields = fields_of(line, "- contract:")
            status = fields[1] if len(fields) > 1 else ""
            if status not in ("fixed", "open"):
                problems.append(
                    f"contract {fields[0]} is marked {status or 'nothing'}, neither fixed nor open"
                )
            contracts[fields[0]] = status
        elif line.startswith("- unit:"):
            fields = fields_of(line, "- unit:")
            unit: dict[str, list[str]] = {key: [] for key in UNIT_KEYS}
            for field in fields[1:]:
                key, _, value = field.partition(":")
                if key.strip() in unit:
                    items = [item.split(" (")[0].strip() for item in value.split(",")]
                    unit[key.strip()] = [item for item in items if item and item != "none"]
            if fields[0] in units:
                problems.append(f"two unit lines are named {fields[0]}")
            units[fields[0]] = unit
    return units, contracts, problems


def names(units: list[str]) -> str:
    return units[0] if len(units) == 1 else ", ".join(units[:-1]) + " and " + units[-1]


def all_waits(units: dict[str, dict], open_contracts: set[str]) -> dict[str, set[str]]:
    """Each unit's waits: the ones it names, and the providers of its open contracts."""
    waits = {unit: set(body["waits"]) for unit, body in units.items()}
    for unit, body in units.items():
        for contract in body["consumes"]:
            if contract in open_contracts:
                waits[unit].update(
                    other
                    for other in units
                    if other != unit and contract in units[other]["provides"]
                )
    return waits


def place(waits: dict[str, set[str]]) -> tuple[dict[str, int], list[str]]:
    """Give each unit its wave; the units left over wait on each other in a cycle."""
    wave: dict[str, int] = {}
    left = set(waits)
    while True:
        ready = [unit for unit in left if all(wait in wave for wait in waits[unit])]
        if not ready:
            break
        for unit in ready:
            wave[unit] = 1 + max((wave[wait] for wait in waits[unit]), default=0)
        left -= set(ready)
    while True:
        behind = {unit for unit in left if not any(unit in waits[other] for other in left)}
        if not behind:
            break
        left -= behind
    return wave, sorted(left)


def ordered(waits: dict[str, set[str]], first: str, second: str) -> bool:
    """Whether one of two units waits on the other, directly or through others."""

    def reaches(start: str, goal: str) -> bool:
        seen: set[str] = set()
        stack = [start]
        while stack:
            unit = stack.pop()
            if unit == goal:
                return True
            if unit not in seen:
                seen.add(unit)
                stack.extend(waits[unit])
        return False

    return reaches(first, second) or reaches(second, first)


def shared_paths(
    units: dict[str, dict], waits: dict[str, set[str]]
) -> tuple[dict[str, set], list[str]]:
    hotspots: dict[str, set] = {}
    problems = []
    for first, second in combinations(units, 2):
        for mine in units[first]["owns"]:
            for theirs in units[second]["owns"]:
                path, _, region = mine.partition("#")
                other_path, _, other_region = theirs.partition("#")
                if path != other_path or (region and other_region and region != other_region):
                    continue
                if ordered(waits, first, second):
                    hotspots.setdefault(path, set()).update((first, second))
                else:
                    problems.append(
                        f"{first} and {second} both own {mine if region == other_region else path}"
                        " and neither waits on the other: name each unit's region,"
                        " or give the path to one unit"
                    )
    return hotspots, problems


def report(units: dict[str, dict], contracts: dict[str, str], problems: list[str]) -> list[str]:
    for unit, body in units.items():
        problems.extend(
            f"{unit} waits on {wait}, which no unit line names"
            for wait in body["waits"]
            if wait not in units
        )
        problems.extend(
            f"{unit} {verb} {contract}, which no contract line names"
            for verb in ("provides", "consumes")
            for contract in body[verb]
            if contract not in contracts
        )
    if problems:
        return []
    open_contracts = {name for name, status in contracts.items() if status == "open"}
    waits = all_waits(units, open_contracts)
    wave, cycle = place(waits)
    if cycle:
        problems.append(f"{names(cycle)} wait on each other in a cycle")
        return []
    depth = max(wave.values())
    by_wave = [sorted(u for u in wave if wave[u] == n) for n in range(1, depth + 1)]
    lines = [f"wave {n}: {', '.join(members)}" for n, members in enumerate(by_wave, 1)]
    widest = max(len(members) for members in by_wave)
    lines.append(
        f"widest wave: {widest} unit{'s' if widest > 1 else ''};"
        f" longest chain: {depth} wave{'s' if depth > 1 else ''}"
    )
    if widest == 1 and len(units) > 1:
        lines.append(
            "every unit runs alone: look for a wait a stated contract would dissolve,"
            " or a hotspot to hand to one integrator unit"
        )
    if open_contracts:
        lines.append("open contracts")
        for contract in sorted(open_contracts):
            sooner, _ = place(all_waits(units, open_contracts - {contract}))
            freed = sorted(unit for unit in wave if sooner.get(unit, wave[unit]) < wave[unit])
            lines.append(
                f"  {contract}: stating it in the plan moves {', '.join(freed)} to an earlier wave"
                if freed
                else f"  {contract}: holds no unit back"
            )
    hotspots, collisions = shared_paths(units, waits)
    problems.extend(collisions)
    if hotspots:
        lines.append("hotspots")
        lines.extend(
            f"  {path}: {', '.join(sorted(owners, key=lambda u: (wave[u], u)))}"
            for path, owners in sorted(hotspots.items())
        )
        lines.append(
            "  each unit could build its part in a file of its own, against a stated"
            " contract, leaving one integrator unit to own the path"
        )
    return lines


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write(__doc__)
        return 2
    units, contracts, problems = parse(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if not units:
        sys.stderr.write(f"{sys.argv[1]} holds no line starting '- unit:'\n")
        return 2
    lines = report(units, contracts, problems)
    if problems:
        lines.append("problems")
        lines.extend(f"  {problem}" for problem in problems)
    sys.stdout.write("\n".join(lines) + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

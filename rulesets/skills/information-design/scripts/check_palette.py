#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Check a palette for contrast against its background and for separation under colour-vision deficiency.

check_palette.py --colors '#0072B2,#E69F00,#009E73' --background '#FFFFFF' [--text '#1A1A1A']
                 [--pairs all|adjacent] [--json]

Exits 0 when no check fails and 1 otherwise, so a failing palette stops a pipeline.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from dataclasses import asdict, dataclass
from typing import Literal

Rgb = tuple[float, float, float]
Status = Literal["pass", "warn", "fail"]

GRAPHIC_CONTRAST_MIN = 3.0
TEXT_CONTRAST_MIN = 4.5
DEFICIENT_DISTANCE_MIN = 8.0
NORMAL_DISTANCE_MIN = 15.0
GREY_LIGHTNESS_GAP_MIN = 10.0

# Severity-1.0 simulation matrices, applied in linear RGB:
# https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html
SIMULATIONS: dict[str, tuple[Rgb, Rgb, Rgb]] = {
    "protanopia": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deuteranopia": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "tritanopia": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}
COMMON_DEFICIENCIES = ("protanopia", "deuteranopia")


@dataclass(frozen=True)
class Finding:
    check: str
    status: Status
    subject: str
    measured: float
    required: float
    fix: str


def parse_hex(text: str) -> Rgb:
    """Convert '#RRGGBB' or '#RGB' to linear RGB."""
    digits = text.strip().lstrip("#")
    if len(digits) == 3:
        digits = "".join(digit * 2 for digit in digits)
    problem = f"{text!r} is not a #RRGGBB or #RGB colour"
    if len(digits) != 6:
        raise argparse.ArgumentTypeError(problem)
    try:
        channels = [int(digits[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    except ValueError as error:
        raise argparse.ArgumentTypeError(problem) from error
    red, green, blue = (linearize(channel) for channel in channels)
    return red, green, blue


def linearize(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def contrast_ratio(first: Rgb, second: Rgb) -> float:
    """Return the contrast ratio as WCAG defines it.

    https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio
    """
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def luminance(color: Rgb) -> float:
    red, green, blue = color
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def simulate(color: Rgb, deficiency: str) -> Rgb:
    rows = SIMULATIONS[deficiency]
    red, green, blue = (
        min(1.0, max(0.0, sum(weight * channel for weight, channel in zip(row, color))))
        for row in rows
    )
    return red, green, blue


def oklab(color: Rgb) -> Rgb:
    """Convert linear RGB to OKLab.

    https://bottosson.github.io/posts/oklab/
    """
    red, green, blue = color
    long = (0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue) ** (1 / 3)
    medium = (0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue) ** (1 / 3)
    short = (0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue) ** (1 / 3)
    return (
        0.2104542553 * long + 0.7936177850 * medium - 0.0040720468 * short,
        1.9779984951 * long - 2.4285922050 * medium + 0.4505937099 * short,
        0.0259040371 * long + 0.7827717662 * medium - 0.8086757660 * short,
    )


def distance(first: Rgb, second: Rgb) -> float:
    """Perceptual distance between two colours, on a scale where 100 separates black from white."""
    return 100 * sum((a - b) ** 2 for a, b in zip(oklab(first), oklab(second))) ** 0.5


def check_palette(
    colors: dict[str, Rgb],
    background: Rgb,
    text: Rgb | None,
    pairs: Literal["all", "adjacent"],
) -> list[Finding]:
    """Return one finding per check, per colour or colour pair."""
    findings: list[Finding] = []
    for name, color in colors.items():
        ratio = contrast_ratio(color, background)
        findings.append(
            Finding(
                check="contrast with background",
                status="pass" if ratio >= GRAPHIC_CONTRAST_MIN else "fail",
                subject=name,
                measured=ratio,
                required=GRAPHIC_CONTRAST_MIN,
                fix="darken or lighten the colour away from the background, or outline the mark",
            )
        )
    if text is not None:
        ratio = contrast_ratio(text, background)
        findings.append(
            Finding(
                check="text contrast with background",
                status="pass" if ratio >= TEXT_CONTRAST_MIN else "fail",
                subject="text",
                measured=ratio,
                required=TEXT_CONTRAST_MIN,
                fix="move the text colour further from the background in lightness",
            )
        )
    names = list(colors)
    pairings = itertools.combinations(names, 2) if pairs == "all" else zip(names, names[1:])
    for first, second in pairings:
        subject = f"{first} / {second}"
        normal = distance(colors[first], colors[second])
        findings.append(
            Finding(
                check="separation, typical vision",
                status="pass" if normal >= NORMAL_DISTANCE_MIN else "fail",
                subject=subject,
                measured=normal,
                required=NORMAL_DISTANCE_MIN,
                fix="move the two colours apart in hue or lightness",
            )
        )
        for deficiency in SIMULATIONS:
            simulated = distance(
                simulate(colors[first], deficiency), simulate(colors[second], deficiency)
            )
            failing: Status = "fail" if deficiency in COMMON_DEFICIENCIES else "warn"
            findings.append(
                Finding(
                    check=f"separation, {deficiency}",
                    status="pass" if simulated >= DEFICIENT_DISTANCE_MIN else failing,
                    subject=subject,
                    measured=simulated,
                    required=DEFICIENT_DISTANCE_MIN,
                    fix="give the pair different lightness, or add a label, shape or pattern",
                )
            )
        grey_gap = abs(oklab(colors[first])[0] - oklab(colors[second])[0]) * 100
        findings.append(
            Finding(
                check="separation, greyscale",
                status="pass" if grey_gap >= GREY_LIGHTNESS_GAP_MIN else "warn",
                subject=subject,
                measured=grey_gap,
                required=GREY_LIGHTNESS_GAP_MIN,
                fix="the pair merges in greyscale and print, so carry identity with a label, shape or pattern too",
            )
        )
    return findings


def render(findings: list[Finding]) -> str:
    lines = [
        f"{finding.status.upper():4}  {finding.check:28}  {finding.subject:19}  "
        f"{finding.measured:6.2f} (needs {finding.required:g})"
        + ("" if finding.status == "pass" else f"  -> {finding.fix}")
        for finding in findings
    ]
    counts = {
        status: sum(finding.status == status for finding in findings)
        for status in ("pass", "warn", "fail")
    }
    lines.append(f"{counts['pass']} pass, {counts['warn']} warn, {counts['fail']} fail")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--colors",
        required=True,
        help="comma-separated hex colours, in the order the chart uses them",
    )
    parser.add_argument(
        "--background", default="#FFFFFF", type=parse_hex, help="hex colour the marks sit on"
    )
    parser.add_argument("--text", type=parse_hex, help="hex colour of labels and body text")
    parser.add_argument(
        "--pairs",
        choices=("all", "adjacent"),
        default="all",
        help="all: any two colours can touch (scatter, map, legend). adjacent: only neighbours in the given order touch",
    )
    parser.add_argument("--json", action="store_true", help="print findings as JSON")
    arguments = parser.parse_args()

    hexes = [part.strip() for part in arguments.colors.split(",") if part.strip()]
    if len(set(hexes)) != len(hexes):
        parser.error("--colors holds a duplicate")
    try:
        colors = {hex_color: parse_hex(hex_color) for hex_color in hexes}
    except argparse.ArgumentTypeError as error:
        parser.error(str(error))

    findings = check_palette(colors, arguments.background, arguments.text, arguments.pairs)
    if arguments.json:
        print(json.dumps([asdict(finding) for finding in findings], indent=2))
    else:
        print(render(findings))
    return 1 if any(finding.status == "fail" for finding in findings) else 0


if __name__ == "__main__":
    sys.exit(main())

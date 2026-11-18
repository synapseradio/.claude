#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Pick the form that answers a reader's question about data or structure: a sentence, a table, a chart or a diagram.

choose_form.py --question trend --series 7 --points 24
choose_form.py --question part-to-whole --items 3
choose_form.py --question process --items 6 --branches 0
choose_form.py --list

Each count defaults to 1 (0 for --branches). Add --json for machine-readable output.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Shape:
    """The data or structure the reader's question is about."""

    items: int
    series: int
    points: int
    branches: int
    ordered: bool
    over_time: bool
    uncertain: bool
    general_audience: bool
    interactive: bool


@dataclass(frozen=True)
class Answer:
    form: str
    because: str
    build: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    otherwise: str = ""


def value(shape: Shape) -> Answer:
    return Answer(
        form="a sentence, or one large number with its comparison",
        because="one number needs no axes; a chart of one value adds reading work and no information",
        build=[
            "state the number with its unit and the period it covers",
            "put the comparison beside it: the previous value, the target, or the peer",
            "say which direction is good where the reader cannot tell",
        ],
        avoid=["a gauge or dial", "a single-bar chart"],
    )


def lookup(shape: Shape) -> Answer:
    build = [
        "sort rows by the column the reader scans first",
        "right-align numbers, one unit and one precision per column, unit in the header",
        "put the columns the reader compares next to each other",
    ]
    if shape.items > 30 and shape.interactive:
        build.append("add search and column sorting, and keep the header row fixed")
    elif shape.items > 30:
        build.append("group rows under subheadings, or show the top rows and link the full set")
    return Answer(
        form="a table",
        because="the reader wants exact values for named things, and a table gives each value an address",
        build=build,
        avoid=["a chart, which makes the reader estimate values the table states"],
        otherwise="a chart beside the table where the reader also needs the overall pattern",
    )


def compare(shape: Shape) -> Answer:
    if shape.over_time:
        return trend(shape)
    if shape.items > 30:
        return Answer(
            form="a sorted table, or a bar chart of the top items with the rest summed as one bar",
            because="past about thirty marks the labels collide and nobody compares the middle of the field",
            build=["sort by the measure", "name the cut-off and what the remainder bar holds"],
            avoid=["a chart with every item squeezed in"],
        )
    if shape.series == 1:
        orientation = (
            "vertical bars in the categories' own order"
            if shape.ordered
            else "horizontal bars sorted by value"
        )
        return Answer(
            form=f"a bar chart: {orientation}",
            because="length from a shared baseline is the comparison people judge most accurately",
            build=[
                "start the value axis at zero",
                "label each bar with its category, and with its value where the reader needs the number",
                "use one colour, with a second colour only for the bar the message is about",
            ],
            avoid=["a pie chart", "a colour per bar", "3D or perspective"],
            otherwise="a dot plot where the values sit far from zero and their differences are the point",
        )
    if shape.series == 2:
        return Answer(
            form="a dumbbell (connected dot) plot, one row per category",
            because="the gap between the two series is the message, and a connecting line draws it",
            build=[
                "sort rows by the gap or by one series",
                "label the two series once, at the first row",
            ],
            avoid=["two pie charts side by side"],
            otherwise="grouped bars where there are at most six categories",
        )
    if shape.series <= 4 and shape.items <= 6:
        return Answer(
            form="a grouped bar chart",
            because="few enough bars that the reader compares within a group and across groups",
            build=[
                "start the value axis at zero",
                "keep one series order and colour in every group",
            ],
            avoid=[
                "a stacked bar, which hides every series but the first behind a moving baseline"
            ],
            otherwise="small multiples, one panel per series, on a shared scale",
        )
    return Answer(
        form="small multiples: one small bar chart per series, on a shared scale",
        because="a grouped chart with this many bars per group becomes a striped texture nobody compares",
        build=[
            "same axis range and category order in every panel",
            "title each panel with its series name",
        ],
        avoid=["a grouped or stacked bar chart with more than four series"],
        otherwise="a heatmap table where the pattern across the grid matters more than the values",
    )


def rank(shape: Shape) -> Answer:
    if shape.over_time and shape.points == 2:
        return Answer(
            form="a slope chart",
            because="two moments and a rank order: the slopes show who rose and who fell",
            build=[
                "label both ends of each line with name and value",
                "colour only the lines the message is about",
            ],
        )
    if shape.over_time:
        return Answer(
            form="a bump chart (rank on the vertical axis, one line per item)",
            because="the reader follows positions over time, and exact values matter less",
            build=["highlight a few lines and grey the rest", "label lines at their ends"],
            avoid=["more than about ten lines in colour"],
        )
    return Answer(
        form="horizontal bars sorted from largest to smallest",
        because="sorted position gives the rank and bar length gives the margin",
        build=["start the value axis at zero", "highlight the item the message is about"],
        avoid=["alphabetical order"],
    )


def trend(shape: Shape) -> Answer:
    if shape.points <= 2:
        return Answer(
            form="a slope chart, or a sentence giving both values and the change",
            because="two points make a difference, and a trend needs more",
            build=["state the change as a number as well as showing it"],
            avoid=["a line chart that implies a trend from two points"],
        )
    if shape.series <= 4:
        answer = Answer(
            form="a line chart with the series name written at the end of each line",
            because="position on a shared scale along a time axis shows rate and direction of change",
            build=[
                "time runs left to right at even intervals",
                "label lines directly, with no separate legend",
                "annotate the event that explains a turn in the line",
                "the value axis may start above zero when the change is the message; show the tick labels clearly",
            ],
            avoid=[
                "two different value axes on one chart",
                "smoothing that hides the data's real shape",
            ],
            otherwise="columns for six or fewer periods of a single series when each period is a separate total",
        )
    elif shape.series <= 9:
        answer = Answer(
            form="a line chart with one or two series in colour and the rest in grey",
            because="past four coloured lines the reader stops tracking identity; grey keeps the context",
            build=[
                "choose the highlighted series from the message",
                "label the highlighted lines directly",
            ],
            avoid=["a colour per line with a legend to match against"],
            otherwise="small multiples where every series matters equally",
        )
    else:
        answer = Answer(
            form="small multiples: one small line chart per series on shared axes",
            because="ten or more lines on one plot overlap into a tangle",
            build=[
                "same axes in every panel",
                "order panels by a meaningful value such as the latest reading",
            ],
            avoid=["one plot with every line"],
        )
    return answer


def part_to_whole(shape: Shape) -> Answer:
    if shape.over_time:
        if shape.items <= 4:
            return Answer(
                form="a stacked area chart, with the part the message is about at the bottom",
                because="the total and the bottom part read against a flat baseline",
                build=[
                    "label areas directly",
                    "say in the title whether the total or the mix is the message",
                ],
                avoid=["reading the middle layers' trends from a stacked chart"],
                otherwise="one line per part where each part's own trend matters",
            )
        return Answer(
            form="one line per part, as shares of the whole; small multiples past nine parts",
            because="more than four stacked layers hide every trend but the bottom one",
            build=[
                "label lines directly",
                "state in the subtitle that the lines are shares of one whole",
            ],
            avoid=["a stacked area chart with more than four layers"],
        )
    if shape.series > 1:
        return Answer(
            form="stacked bars scaled to 100 percent, one bar per whole",
            because="several wholes need a shared scale, which pies cannot give",
            build=[
                "at most four segments, in one order",
                "put the segment the message is about at the baseline",
            ],
            avoid=["a row of pie charts"],
            otherwise="small multiples of sorted bars where there are more than four parts",
        )
    if shape.items <= 2:
        return Answer(
            form="a sentence stating the share",
            because="two parts are one number and its complement",
            build=["give the share and the whole it is a share of"],
            otherwise="a single stacked bar where the page needs a visual anchor",
        )
    if shape.items == 3:
        return Answer(
            form="a single stacked bar, or a pie chart with each slice labelled",
            because="with three parts the reader judges rough fractions such as a half or a quarter",
            build=[
                "label each part with its name and share",
                "start a pie at the top, largest slice first",
            ],
            avoid=["a legend the reader matches by colour", "a 3D or exploded pie"],
        )
    return Answer(
        form="horizontal bars sorted by share, labelled with percentages",
        because="people compare lengths more accurately than angles or areas, and four or more slices need comparing",
        build=[
            "state in the title or subtitle that the bars sum to the whole",
            "fold small parts into one bar",
        ],
        avoid=["a pie or donut chart with more than three slices"],
        otherwise="a treemap where the parts nest in a hierarchy",
    )


def distribution(shape: Shape) -> Answer:
    if shape.series == 1:
        if shape.points <= 50:
            return Answer(
                form="a strip plot: one dot per observation along the value axis",
                because="with few observations every one can be shown, and a summary would hide the gaps",
                build=["jitter or stack dots that coincide", "mark the median"],
            )
        return Answer(
            form="a histogram",
            because="bar height per bin shows where values pile up, and the shape of the tails",
            build=[
                "choose bin edges at round values",
                "mark the median or the threshold the reader cares about",
            ],
            avoid=["reporting only a mean for a skewed or two-peaked distribution"],
        )
    if shape.general_audience:
        return Answer(
            form="strip plots or small-multiple histograms, one row per group, on a shared axis",
            because="readers outside statistics misread box plots; dots and bars need no decoding",
            build=["same axis for every group", "mark each group's median"],
            avoid=["box plots without an explanation of their parts", "bars of means alone"],
        )
    return Answer(
        form="box plots on a shared axis, with the observations overlaid when groups are small",
        because="a compact summary lets a trained reader compare many groups at once",
        build=["state what the whiskers span", "sort groups by median"],
        avoid=["bars of means alone, which hide spread and sample size"],
        otherwise="violin or ridgeline plots where the shape differs between groups",
    )


def relationship(shape: Shape) -> Answer:
    build = [
        "put the presumed cause or the reader's control on the horizontal axis",
        "label the points the message names",
        "state in words what the pattern does and does not show; a pattern across points is no proof of cause",
    ]
    if shape.points > 1000:
        build.append("bin into hexagons or use transparency so density stays readable")
    if shape.series > 1:
        build.append("separate groups into small multiples when their clouds overlap")
    return Answer(
        form="a scatterplot",
        because="two measures per item map onto two positions, and the cloud's shape is the relationship",
        build=build,
        avoid=[
            "two lines on two different value axes",
            "bubble size for a measure the reader must compare",
        ],
        otherwise="a connected scatterplot only for readers who already know the form",
    )


def deviation(shape: Shape) -> Answer:
    if shape.over_time:
        return Answer(
            form="a line chart with the reference drawn as a labelled line",
            because="the gap to the reference line is the message",
            build=["label the reference with what it is", "shade the gap where its sign matters"],
        )
    return Answer(
        form="diverging bars from a centre line at the reference value",
        because="direction from the reference reads as left or right, size as length",
        build=[
            "sort by the deviation",
            "two colours, one per direction, and a neutral for the reference",
            "label the reference line with what it is",
        ],
        avoid=["a red and green pair without a second cue such as position or a sign"],
    )


def flow(shape: Shape) -> Answer:
    if shape.branches == 0:
        return Answer(
            form="bars for each stage in order, labelled with the share kept from the stage before",
            because="a single path through stages is a sequence of magnitudes, and bars compare them",
            build=["label each stage with its count and its drop from the previous stage"],
            avoid=["a funnel drawing whose width or area matches no number"],
        )
    return Answer(
        form="a flow (Sankey) diagram",
        because="quantities split and merge between stages, and band width carries the amounts",
        build=[
            "at most about five stages and a dozen bands",
            "label bands directly with name and amount",
        ],
        avoid=["a flow diagram where one stage-to-stage table would answer the question"],
        otherwise="a table of from-stage by to-stage amounts",
    )


def spatial(shape: Shape) -> Answer:
    return Answer(
        form="a map: shaded regions for rates, sized symbols for counts",
        because="the reader's question is where, and only a map answers where",
        build=[
            "shade regions by a rate or share and never by a raw count",
            "one hue from light to dark for magnitude; two hues around a neutral midpoint for above and below",
            "five or fewer shade classes, with the class breaks stated",
        ],
        avoid=["a map when location is incidental; use sorted bars with region names instead"],
        otherwise="sorted bars with region names where the ranking matters more than the geography",
    )


def steps(shape: Shape) -> Answer:
    if shape.branches == 0:
        return Answer(
            form="a numbered list",
            because="a linear sequence is one dimension, and a list gives each step a number to return to",
            build=[
                "one action per step, starting with its verb",
                "put the result the reader should see after the step that produces it",
                "group more than nine steps under subheadings that name each phase",
            ],
            avoid=["a flowchart of boxes in a straight line", "steps hidden inside a paragraph"],
        )
    return process(shape)


def process(shape: Shape) -> Answer:
    if shape.branches == 0:
        return steps(shape)
    if shape.branches <= 2 and shape.items <= 9:
        return Answer(
            form="a numbered list with each condition written at the step where the paths part",
            because="one or two decisions fit in a sequence; a diagram would cost more to read than it saves",
            build=[
                "write each branch as 'If X, go to step N'",
                "keep the common path as the main sequence",
            ],
            otherwise="a small flowchart where the branches rejoin in ways a list cannot show",
        )
    if shape.items > 12:
        return Answer(
            form="an overview flowchart of the phases, plus one detailed flowchart or list per phase",
            because="a reader traces about a dozen nodes before losing the path; levels keep each view within that",
            build=["name each phase on the overview exactly as its detail view is titled"],
            avoid=["one diagram holding every node"],
        )
    return Answer(
        form="a flowchart",
        because="several decision points create paths, and a diagram lets the reader trace one path by eye",
        build=[
            "one direction of flow, top to bottom or left to right",
            "label every arrow leaving a decision with its condition",
            "one shape per kind of node, with a key if more than two kinds",
            "start and end nodes marked",
        ],
        avoid=["crossing arrows", "unlabelled branches"],
        otherwise="a decision table where the outcome depends on combinations of conditions and order is irrelevant",
    )


def decision(shape: Shape) -> Answer:
    return Answer(
        form="a decision table: one row per case, conditions in the left columns, the action in the last",
        because="the outcome depends on a combination of conditions, and a table lets the reader find their row",
        build=[
            "order rows so the first matching row applies, and say so",
            "end with a row for every other case",
        ],
        avoid=["nested if-then prose", "a flowchart with a diamond per condition"],
    )


def structure(shape: Shape) -> Answer:
    if shape.items > 12:
        return Answer(
            form="a context diagram of the main groups, plus one diagram per group",
            because="past about a dozen boxes the reader cannot find the path they came for",
            build=[
                "each diagram stays at one level of detail",
                "boxes keep the same name at every level",
            ],
            avoid=["one diagram mixing systems, services, classes and queues"],
        )
    return Answer(
        form="a box-and-arrow diagram at one level of detail",
        because="the question is what connects to what, which is spatial, and text can only list it",
        build=[
            "label every arrow with what crosses it and in which direction",
            "one meaning per visual element: shape, colour, line style and arrowhead each encode one thing",
            "add a key for every encoding used",
            "place related boxes close and align them; let position mean something or nothing, consistently",
        ],
        avoid=["unlabelled arrows", "colour as decoration", "icons that need a second legend"],
        otherwise="a two-column table of component and responsibility where the connections are few",
    )


def hierarchy(shape: Shape) -> Answer:
    if shape.items <= 15:
        return Answer(
            form="an indented list",
            because="nesting depth shows the hierarchy, and a list can be searched, copied and read aloud",
            build=["at most three levels deep", "siblings in a meaningful order"],
            otherwise="a tree diagram where the reader compares branch sizes or depths",
        )
    return Answer(
        form="a tree diagram, collapsed to the levels the question concerns",
        because="a large hierarchy needs its shape seen at once",
        build=["show the top two or three levels and link or expand the rest"],
        avoid=["a tree with every leaf, where the reader came for the branches"],
    )


def interaction(shape: Shape) -> Answer:
    return Answer(
        form="a sequence diagram: participants across the top, messages in order down the page",
        because="who sends what to whom, and in what order, needs both a participant axis and an order axis",
        build=[
            "at most about six participants; group the rest behind one named box",
            "label each message with what it carries",
            "show the main path first and each failure path as its own diagram",
        ],
        avoid=[
            "a box-and-arrow diagram with numbered arrows, which makes the reader sort the numbers"
        ],
    )


def states(shape: Shape) -> Answer:
    if shape.items <= 4:
        return Answer(
            form="a table: one row per state, one column per event, the cell naming the next state",
            because="a table shows every state and event pair, including the ones that are not allowed",
            build=["mark disallowed pairs explicitly"],
            otherwise="a state diagram where the cycle itself is the message",
        )
    return Answer(
        form="a state diagram",
        because="the legal moves between states form a graph the reader traces",
        build=[
            "label each transition with its trigger",
            "mark the start state and every end state",
        ],
        avoid=["a flowchart, which shows steps and has no notion of a resting state"],
    )


def schedule(shape: Shape) -> Answer:
    return Answer(
        form="a timeline: one row per work stream, bars along a shared time axis",
        because="overlap, order and duration are all positions along one axis",
        build=[
            "mark today and each fixed date",
            "label bars directly",
            "show dependencies only where they constrain",
        ],
        avoid=["a list of dates the reader must sort mentally"],
    )


def options(shape: Shape) -> Answer:
    return Answer(
        form="a comparison table: one column per option, one row per criterion",
        because="parallel facts about parallel things belong in a grid the reader can scan both ways",
        build=[
            "the same criteria, in the same order and wording, for every option",
            "put the criterion that decides most first",
            "state the recommendation above the table",
        ],
        avoid=[
            "a paragraph per option",
            "a pros and cons list with a different set of points for each option",
        ],
    )


QUESTIONS: dict[str, tuple[str, Callable[[Shape], Answer]]] = {
    "value": ("what is the number?", value),
    "lookup": ("what is the exact value for this item?", lookup),
    "compare": ("which is bigger, and by how much?", compare),
    "rank": ("what is the order?", rank),
    "trend": ("how did it change over time?", trend),
    "part-to-whole": ("what share does each part take?", part_to_whole),
    "distribution": ("how are the values spread?", distribution),
    "relationship": ("do two measures move together?", relationship),
    "deviation": ("how far is each from a reference?", deviation),
    "flow": ("how much moves from stage to stage?", flow),
    "spatial": ("where is it?", spatial),
    "steps": ("what do I do, in what order?", steps),
    "process": ("what happens, and under which conditions?", process),
    "decision": ("which case am I in, and what follows?", decision),
    "structure": ("what are the parts and how do they connect?", structure),
    "hierarchy": ("what contains what?", hierarchy),
    "interaction": ("who sends what to whom, in what order?", interaction),
    "states": ("what states exist and what moves between them?", states),
    "schedule": ("what happens when, and what overlaps?", schedule),
    "options": ("which option should I pick?", options),
}

UNCERTAINTY_GENERAL = (
    "uncertainty: show it as counts of outcomes (dots for '3 in 20'), or a labelled band; "
    "state in words what the band covers"
)
UNCERTAINTY_EXPERT = (
    "uncertainty: draw the interval and state its kind and level, such as a 95% confidence interval"
)


def choose(question: str, shape: Shape) -> Answer:
    """Return the recommended form for a question about data or structure of the given shape."""
    answer = QUESTIONS[question][1](shape)
    if not shape.uncertain:
        return answer
    note = UNCERTAINTY_GENERAL if shape.general_audience else UNCERTAINTY_EXPERT
    return Answer(
        answer.form, answer.because, [*answer.build, note], answer.avoid, answer.otherwise
    )


def render(question: str, answer: Answer) -> str:
    lines = [
        f"question: {QUESTIONS[question][0]}",
        f"form:     {answer.form}",
        f"because:  {answer.because}",
    ]
    lines += [f"build:    {item}" for item in answer.build]
    lines += [f"avoid:    {item}" for item in answer.avoid]
    if answer.otherwise:
        lines.append(f"or:       {answer.otherwise}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--question", choices=sorted(QUESTIONS), help="the question the reader brings"
    )
    parser.add_argument(
        "--list", action="store_true", help="print every question with the wording it stands for"
    )
    parser.add_argument(
        "--items", type=int, default=1, help="categories, parts, steps, nodes, states or options"
    )
    parser.add_argument(
        "--series", type=int, default=1, help="groups compared within each item, or wholes"
    )
    parser.add_argument(
        "--points", type=int, default=1, help="time points per series, or observations"
    )
    parser.add_argument(
        "--branches", type=int, default=0, help="decision points or splits in a process or flow"
    )
    parser.add_argument(
        "--ordered", action="store_true", help="the categories have their own order, such as ages"
    )
    parser.add_argument(
        "--over-time", action="store_true", help="the question also concerns change over time"
    )
    parser.add_argument(
        "--uncertain", action="store_true", help="the values are estimates, samples or forecasts"
    )
    parser.add_argument("--audience", choices=("general", "expert"), default="general")
    parser.add_argument("--medium", choices=("static", "interactive"), default="static")
    parser.add_argument("--json", action="store_true", help="print the answer as JSON")
    arguments = parser.parse_args()

    if arguments.list:
        print("\n".join(f"{name:14} {wording}" for name, (wording, _) in QUESTIONS.items()))
        return 0
    if arguments.question is None:
        parser.error("give --question, or --list to see the choices")
    if min(arguments.items, arguments.series, arguments.points) < 1 or arguments.branches < 0:
        parser.error("--items, --series and --points start at 1, and --branches at 0")

    shape = Shape(
        items=arguments.items,
        series=arguments.series,
        points=arguments.points,
        branches=arguments.branches,
        ordered=arguments.ordered,
        over_time=arguments.over_time,
        uncertain=arguments.uncertain,
        general_audience=arguments.audience == "general",
        interactive=arguments.medium == "interactive",
    )
    answer = choose(arguments.question, shape)
    if arguments.json:
        print(json.dumps({"question": arguments.question, **asdict(answer)}, indent=2))
    else:
        print(render(arguments.question, answer))
    return 0


if __name__ == "__main__":
    sys.exit(main())

import { describe, expect, test } from "claude-code/testing";

import {
	abbrev,
	barCells,
	barLine,
	barRuns,
	largestRemainder,
	legendLines,
	widestLine,
} from "../hooks/layout";
import type { BarRun, CategoryId } from "../hooks/palette";
import type { GaugeRow } from "../hooks/rows";
import type { UsageModel } from "../types";

function row(id: CategoryId, tokens: number, estimated = false): GaugeRow {
	return { id, label: id, tokens, estimated };
}

/** A window holding `used` of `max` tokens; the layout reads only those two. */
function windowOf(used: number, max: number): UsageModel {
	return { used, max, percent: 0, categories: [] };
}

function total(cells: readonly number[]): number {
	return cells.reduce((sum, n) => sum + n, 0);
}

function runCells(runs: readonly BarRun[]): number {
	return total(runs.map((r) => r.cells));
}

const PERCENT = "30%";
const TOTALS = "30k/100k";

/** Seven categories of 100 tokens each, labels four to twelve letters long. */
const SEVEN: readonly GaugeRow[] = [
	row("system", 100),
	row("skills", 100),
	row("hooks", 100, true),
	row("user", 100, true),
	row("calls", 100, true),
	row("read", 100, true),
	row("unattributed", 100),
];

/** Legend items of 12, 12 and 14 cells: the first two with their gap take 26. */
const THREE: readonly GaugeRow[] = [
	row("system", 6000),
	row("skills", 4000),
	row("replies", 20_000),
];

describe("abbrev", () => {
	test("a figure under a thousand reads in full", () => {
		expect(abbrev(999)).toBe("999");
	});

	test("thousands read in k to one decimal, a whole number without its .0", () => {
		expect(abbrev(1000)).toBe("1k");
		expect(abbrev(1050)).toBe("1.1k");
	});

	test("a figure halfway between tenths rounds up", () => {
		expect(abbrev(1150)).toBe("1.2k");
	});

	test("a figure that rounds up to ten thousand reads 10k", () => {
		expect(abbrev(9999)).toBe("10k");
	});

	test("from ten thousand, k reads whole", () => {
		expect(abbrev(10_000)).toBe("10k");
	});

	test("millions read in M to one decimal", () => {
		expect(abbrev(1_500_000)).toBe("1.5M");
	});

	test("a figure that rounds up to a thousand k reads in M", () => {
		expect(abbrev(999_499)).toBe("999k");
		expect(abbrev(999_500)).toBe("1M");
		expect(abbrev(999_999)).toBe("1M");
	});
});

describe("largestRemainder", () => {
	test("the leftover cell goes to the largest remainder", () => {
		// 7 cells over 5:3:2 make 3.5, 2.1 and 1.4.
		expect(largestRemainder([5, 3, 2], 7)).toEqual([4, 2, 1]);
	});

	test("the shares sum to the cells exactly", () => {
		expect(total(largestRemainder([1, 1, 1], 10))).toBe(10);
		expect(total(largestRemainder([7, 13, 29, 51], 23))).toBe(23);
	});
});

describe("barRuns", () => {
	test("a row too small for a share of its own still takes one cell, free space last", () => {
		// The two floor cells leave 18, split 29,900 : 100 : 70,000 into 5.38, 0.02 and 12.6.
		const runs = barRuns(
			windowOf(30_000, 100_000),
			[row("system", 29_900), row("skills", 100)],
			20,
		);

		expect(runs).toEqual([
			{ id: "system", cells: 6 },
			{ id: "skills", cells: 1 },
			{ id: "free", cells: 13 },
		]);
	});

	test("at every width the runs fill the bar exactly, each used row in at least one cell", () => {
		const rows = [
			row("system", 6000),
			row("skills", 40),
			row("replies", 20_000),
		];
		const ids = rows.map((r) => r.id).join();
		const misfits = Array.from({ length: 58 }, (_, i) => i + 3)
			.map((width) => ({
				width,
				runs: barRuns(windowOf(26_040, 100_000), rows, width),
			}))
			.filter(
				({ width, runs }) =>
					runCells(runs) !== width ||
					runs
						.slice(0, 3)
						.map((r) => r.id)
						.join() !== ids ||
					runs.some((r) => r.cells < 1),
			);

		expect(misfits).toEqual([]);
	});

	test("a bar narrower than its rows still fills exactly its width", () => {
		expect(runCells(barRuns(windowOf(30_000, 100_000), THREE, 2))).toBe(2);
	});

	test("where the legend leaves fewer cells than rows, each row still takes one cell", () => {
		const widest = widestLine(legendLines(SEVEN, 20));
		const width = barCells(widest, PERCENT, TOTALS, SEVEN.length);
		const runs = barRuns(windowOf(700, 1000), SEVEN, width);

		expect(width).toBe(SEVEN.length);
		expect(runs.map((r) => r.id)).toEqual(SEVEN.map((r) => r.id));
		expect(runs.every((r) => r.cells === 1)).toBe(true);
	});
});

describe("legendLines", () => {
	test("an item counts its key, a space, its label, a space and its figure", () => {
		const [line] = legendLines(
			[row("system", 6000), row("user", 1000, true)],
			80,
		);

		expect(line?.items.map((i) => [i.figure, i.cells])).toEqual([
			["6k", 2 + 1 + 6 + 1 + 2],
			["~1k", 2 + 1 + 4 + 1 + 3],
		]);
	});

	test("a line takes the next item while it fits room exactly", () => {
		const lines = legendLines(THREE, 26);

		expect(lines.map((l) => l.items.map((i) => i.row.id))).toEqual([
			["system", "skills"],
			["replies"],
		]);
		expect(lines.map((l) => l.cells)).toEqual([26, 14]);
	});

	test("a line breaks where the next item would pass room", () => {
		const lines = legendLines(THREE, 25);

		expect(lines.map((l) => l.items.map((i) => i.row.id))).toEqual([
			["system"],
			["skills"],
			["replies"],
		]);
	});
});

describe("widestLine", () => {
	test("the widest of several lines sets the width", () => {
		expect(widestLine(legendLines(THREE, 26))).toBe(26);
	});

	test("no lines take no cells", () => {
		expect(widestLine([])).toBe(0);
	});
});

describe("barCells", () => {
	test("the bar line, percentage, bar, totals and two spaces, spans the widest legend line", () => {
		const cells = barCells(40, PERCENT, TOTALS, 3);

		expect(PERCENT.length + 1 + cells + 1 + TOTALS.length).toBe(40);
	});

	test("never fewer cells than used categories", () => {
		expect(barCells(12, PERCENT, TOTALS, 7)).toBe(7);
	});
});

describe("barLine", () => {
	test("where the bar line fits the row, the totals stay on it", () => {
		expect(barLine(40, 77, PERCENT, TOTALS, 3)).toEqual({
			cells: barCells(40, PERCENT, TOTALS, 3),
			totalsWrap: false,
		});
	});

	test("where the percentage, the totals and one cell per category outgrow the row, the totals wrap", () => {
		// 3 + 1 + 18 + 1 + 8 = 31 cells against a 27-cell row.
		const line = barLine(25, 27, PERCENT, TOTALS, 18);

		expect(line.totalsWrap).toBe(true);
	});

	test("with the totals wrapped, the bar spans the widest legend line after the percentage", () => {
		const line = barLine(25, 27, PERCENT, TOTALS, 18);

		expect(PERCENT.length + 1 + line.cells).toBe(25);
	});

	test("with the totals wrapped, the bar stays inside the row where a legend item is wider than it", () => {
		const line = barLine(19, 17, PERCENT, TOTALS, 3);

		expect(PERCENT.length + 1 + line.cells).toBe(17);
	});

	test("a row too narrow even for the percentage and one cell per category keeps every cell", () => {
		expect(barLine(8, 10, PERCENT, TOTALS, 18)).toEqual({
			cells: 18,
			totalsWrap: true,
		});
	});
});

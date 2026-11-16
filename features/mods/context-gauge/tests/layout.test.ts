import { describe, expect, test } from "claude-code/testing";

import {
	abbrev,
	barRuns,
	gaugeLine,
	largestRemainder,
	legendGrid,
	MAX_BAR_CELLS,
	PREFIX,
} from "../hooks/layout";
import type { BarRun, CategoryId } from "../hooks/palette";
import type { GaugeRow } from "../hooks/rows";
import type { UsageModel } from "../types";

function row(id: CategoryId, tokens: number, estimated = false): GaugeRow {
	return { id, label: id, tokens, estimated };
}

/** A window holding `used` of `max` tokens. */
function windowOf(used: number, max: number): Pick<UsageModel, "used" | "max"> {
	return { used, max };
}

function total(cells: readonly number[]): number {
	return cells.reduce((sum, n) => sum + n, 0);
}

function runCells(runs: readonly BarRun[]): number {
	return total(runs.map((r) => r.cells));
}

/** Seven categories of 100 tokens each, labels four to nine letters long. */
const SEVEN: readonly GaugeRow[] = [
	row("system", 100),
	row("skills", 100),
	row("hooks", 100, true),
	row("messages", 100, true),
	row("calls", 100, true),
	row("read", 100, true),
	row("agentList", 100),
];

/** Legend items of 12, 12 and 14 cells: two 14-cell units and their gap take 30. */
const THREE: readonly GaugeRow[] = [
	row("system", 6000),
	row("skills", 4000),
	row("prompts", 20_000),
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
			row("prompts", 20_000),
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

	test("where the room leaves fewer cells than rows, each row still takes one cell", () => {
		const { cells: width } = gaugeLine(5, 30, SEVEN.length);
		const runs = barRuns(windowOf(700, 1000), SEVEN, width);

		expect(width).toBe(SEVEN.length);
		expect(runs.map((r) => r.id)).toEqual(SEVEN.map((r) => r.id));
		expect(runs.every((r) => r.cells === 1)).toBe(true);
	});
});

describe("legendGrid", () => {
	test("an item counts its key, a space, its label, a space and its figure", () => {
		const [line] = legendGrid(
			[row("system", 6000), row("messages", 1000, true)],
			80,
		).lines;

		expect(line?.map((i) => [i.figure, i.cells])).toEqual([
			["6k", 2 + 1 + 6 + 1 + 2],
			["~1k", 2 + 1 + 8 + 1 + 3],
		]);
	});

	test("every item takes the widest item's cells, so the items line up in columns", () => {
		expect(legendGrid(THREE, 80).unit).toBe(14);
	});

	test("a line takes as many units as fit room exactly", () => {
		const { lines } = legendGrid(THREE, 30);

		expect(lines.map((l) => l.map((i) => i.row.id))).toEqual([
			["system", "skills"],
			["prompts"],
		]);
	});

	test("a line breaks where one more unit would pass room", () => {
		const { lines } = legendGrid(THREE, 29);

		expect(lines.map((l) => l.map((i) => i.row.id))).toEqual([
			["system"],
			["skills"],
			["prompts"],
		]);
	});

	test("a room narrower than one unit still holds one item a line", () => {
		expect(legendGrid(THREE, 5).lines).toHaveLength(3);
	});
});

describe("PREFIX", () => {
	test("the gauge line opens on the words and a trailing space", () => {
		expect(PREFIX).toBe("context used: ");
	});
});

describe("gaugeLine", () => {
	test("the bar takes the cells the prefix leaves on the line", () => {
		expect(gaugeLine(77, 30, 3)).toEqual({ cells: 47, barOwnLine: false });
	});

	test("the bar stops at the widest Image however wide the room", () => {
		expect(gaugeLine(300, 30, 3)).toEqual({
			cells: MAX_BAR_CELLS,
			barOwnLine: false,
		});
		expect(MAX_BAR_CELLS).toBe(204);
	});

	test("the bar takes the line's last cells where they equal the used categories", () => {
		expect(gaugeLine(33, 30, 3)).toEqual({ cells: 3, barOwnLine: false });
	});

	test("where the prefix leaves fewer cells than used categories, the bar moves to its own line and spans the room", () => {
		expect(gaugeLine(32, 30, 3)).toEqual({ cells: 32, barOwnLine: true });
	});

	test("a bar on its own line stops at the widest Image", () => {
		expect(gaugeLine(300, 299, 3)).toEqual({
			cells: MAX_BAR_CELLS,
			barOwnLine: true,
		});
	});

	test("where the room is under the used categories, the bar keeps one cell per category on its own line", () => {
		expect(gaugeLine(5, 30, 18)).toEqual({ cells: 18, barOwnLine: true });
	});
});

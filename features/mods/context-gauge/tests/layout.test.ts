import { describe, expect, test } from "claude-code/testing";

import {
	abbrev,
	barRuns,
	gaugeLine,
	legendGrid,
	MAX_BAR_CELLS,
} from "../hooks/layout";
import type { BarRun, CategoryId } from "../hooks/palette";
import { PX_PER_CELL } from "../hooks/pixels";
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

/** The widest Image source the engine takes, in pixels (ImageSource's `width`). */
const IMAGE_MAX_PX = 2048;

/** Three categories whose legend items are each wider than five cells. */
const THREE: readonly GaugeRow[] = [
	row("system", 6000),
	row("skills", 4000),
	row("prompts", 20_000),
];

describe("a legend figure", () => {
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

describe("the bar's runs", () => {
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

describe("the legend grid", () => {
	test("a room narrower than one unit still holds one item a line", () => {
		expect(legendGrid(THREE, 5).lines).toHaveLength(3);
	});
});

describe("the bar's width", () => {
	test("the bar takes the cells the prefix leaves on the line", () => {
		expect(gaugeLine(77, 30, 3)).toEqual({ cells: 47, barOwnLine: false });
	});

	test("the bar stops at the widest Image the engine takes, however wide the room", () => {
		const { cells, barOwnLine } = gaugeLine(300, 30, 3);

		expect(cells).toBe(MAX_BAR_CELLS);
		expect(barOwnLine).toBe(false);
		expect(cells * PX_PER_CELL).toBeLessThanOrEqual(IMAGE_MAX_PX);
		expect((cells + 1) * PX_PER_CELL).toBeGreaterThan(IMAGE_MAX_PX);
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

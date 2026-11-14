/** The gauge's layout in terminal cells: legend figures, the legend grid, the bar's width and its runs. */

import type { UsageModel } from "../types";
import type { BarRun } from "./palette";
import { PX_PER_CELL } from "./pixels";
import type { GaugeRow } from "./rows";

/** Cells a legend key takes. */
export const SAMPLE_CELLS = 2;

/** Cells between legend items. */
export const LEGEND_GAP = 2;

/** The spacer on each side of the bar and around a legend label; widths count it. */
export const SPACE = " ";

/** The gauge line's opening words, drawn before the percentage. */
export const PREFIX = "context used: ";

/** The bar's widest, in cells, inside the widest Image the engine takes (2048 px). */
export const MAX_BAR_CELLS: number = Math.floor(2048 / PX_PER_CELL);

/** Each figure size's unit, suffix and decimals, largest first; M starts where a whole k figure would round up to 1000k. */
const MAGNITUDES = [
	{ from: 999_500, unit: 1_000_000, suffix: "M", decimals: 1 },
	{ from: 10_000, unit: 1000, suffix: "k", decimals: 0 },
	{ from: 1000, unit: 1000, suffix: "k", decimals: 1 },
] as const;

/** A token count as a short figure: 999, 1.1k, 10k, 1.5M. */
export function abbrev(n: number): string {
	const magnitude = MAGNITUDES.find((m) => n >= m.from);
	if (magnitude === undefined) return String(n);
	const places = 10 ** magnitude.decimals;
	return `${Math.round((n * places) / magnitude.unit) / places}${magnitude.suffix}`;
}

/** Splits `cells` across `weights` in proportion, by largest remainder, so the shares sum to `cells` exactly. */
export function largestRemainder(
	weights: readonly number[],
	cells: number,
): number[] {
	const total = weights.reduce((a, b) => a + b, 0);
	if (total <= 0 || cells <= 0) return weights.map(() => 0);
	const raw = weights.map((w) => (w / total) * cells);
	const counts = raw.map((r) => Math.floor(r));
	const leftover = cells - counts.reduce((a, b) => a + b, 0);
	const order = raw
		.map((r, i) => ({ i, rest: r % 1 }))
		.sort((a, b) => b.rest - a.rest);
	for (const { i } of order.slice(0, leftover))
		counts[i] = (counts[i] ?? 0) + 1;
	return counts;
}

/** A run before its cells are known: its tokens, and the cells it takes whatever its share. */
type BarPart = { id: BarRun["id"]; tokens: number; floor: number };

/** The bar's runs, `width` cells: each used row at least one cell where the width holds one per row, the rest split by tokens against the window, free space last. */
export function barRuns(
	model: UsageModel,
	rows: readonly GaugeRow[],
	width: number,
): BarRun[] {
	const used = rows.filter((r) => r.tokens > 0);
	const floor = used.length <= width ? 1 : 0;
	const parts = used
		.map((r): BarPart => ({ id: r.id, tokens: r.tokens, floor }))
		.concat({
			id: "free",
			tokens: Math.max(0, model.max - model.used),
			floor: 0,
		});
	const shares = largestRemainder(
		parts.map((p) => p.tokens),
		width - floor * used.length,
	);
	return parts
		.map((p, i) => ({ id: p.id, cells: (shares[i] ?? 0) + p.floor }))
		.filter((run) => run.cells > 0);
}

/** One legend entry: its row, its figure, and the cells it takes. */
export type LegendItem = { row: GaugeRow; figure: string; cells: number };

/** The legend as a grid: every item `unit` cells wide, so items line up in columns, as many to a line as fit the room. */
export type LegendGrid = { unit: number; lines: LegendItem[][] };

function legendItem(row: GaugeRow): LegendItem {
	const figure = `${row.estimated ? "~" : ""}${abbrev(row.tokens)}`;
	const cells =
		SAMPLE_CELLS +
		SPACE.length +
		row.label.length +
		SPACE.length +
		figure.length;
	return { row, figure, cells };
}

/** Legend items in a grid of units as wide as the widest item, LEGEND_GAP apart, a line holding as many units as fit `room` and at least one. */
export function legendGrid(
	rows: readonly GaugeRow[],
	room: number,
): LegendGrid {
	const items = rows.map(legendItem);
	const unit = items.reduce((widest, i) => Math.max(widest, i.cells), 0);
	const columns = Math.max(
		1,
		Math.floor((room + LEGEND_GAP) / (unit + LEGEND_GAP)),
	);
	const lines: LegendItem[][] = [];
	for (let i = 0; i < items.length; i += columns) {
		lines.push(items.slice(i, i + columns));
	}
	return { unit, lines };
}

/** The bar's cells, and whether it draws on its own line under the prefix. */
export type GaugeLine = { cells: number; barOwnLine: boolean };

/** The bar in a row of `room` cells after a `prefix` of cells: it fills the rest of the line, on its own line spanning the room where the line leaves fewer cells than `used` categories, and keeps one cell per category where the room holds fewer; it never passes MAX_BAR_CELLS except for that one cell per category. */
export function gaugeLine(
	room: number,
	prefix: number,
	used: number,
): GaugeLine {
	const beside = room - prefix;
	if (beside >= used)
		return { cells: Math.min(beside, MAX_BAR_CELLS), barOwnLine: false };
	return {
		cells: Math.max(used, Math.min(room, MAX_BAR_CELLS)),
		barOwnLine: true,
	};
}

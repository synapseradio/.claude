/** The gauge's layout in terminal cells: legend figures, legend lines, the bar's width and its runs. */

import type { UsageModel } from "../types";
import type { BarRun } from "./palette";
import type { GaugeRow } from "./rows";

/** Cells a legend key takes. */
export const SAMPLE_CELLS = 2;

/** Cells between legend items. */
export const LEGEND_GAP = 2;

/** The spacer on each side of the bar and around a legend label; widths count it. */
export const SPACE = " ";

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

/** One line of the legend: its items, and the cells they take with the gaps between them. */
export type LegendLine = { items: LegendItem[]; cells: number };

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

/** Legend items in lines LEGEND_GAP apart, a line breaking where its next item would pass `room`. */
export function legendLines(
	rows: readonly GaugeRow[],
	room: number,
): LegendLine[] {
	const lines: LegendLine[] = [];
	for (const item of rows.map(legendItem)) {
		const line = lines.at(-1);
		if (line !== undefined && line.cells + LEGEND_GAP + item.cells <= room) {
			line.items.push(item);
			line.cells += LEGEND_GAP + item.cells;
		} else {
			lines.push({ items: [item], cells: item.cells });
		}
	}
	return lines;
}

/** Cells the widest legend line takes. */
export function widestLine(lines: readonly LegendLine[]): number {
	return lines.reduce((widest, line) => Math.max(widest, line.cells), 0);
}

/** Bar cells that let the bar line span the widest legend line, never fewer than one per used category. */
export function barCells(
	widest: number,
	percent: string,
	totals: string,
	used: number,
): number {
	return Math.max(
		used,
		widest - percent.length - totals.length - 2 * SPACE.length,
	);
}

/** The bar line's shape: the bar's cells, and whether the totals wrap onto their own line under the bar. */
export type BarLine = { cells: number; totalsWrap: boolean };

/** The bar line in a row of `room` cells: the totals wrap where the percentage, the bar and the totals outgrow it, a wrapped bar spans the widest legend line inside the row, and the bar keeps one cell per used category either way. */
export function barLine(
	widest: number,
	room: number,
	percent: string,
	totals: string,
	used: number,
): BarLine {
	const cells = barCells(widest, percent, totals, used);
	const inline =
		percent.length + SPACE.length + cells + SPACE.length + totals.length;
	if (inline <= room) return { cells, totalsWrap: false };
	return {
		cells: Math.max(
			used,
			Math.min(widest, room) - percent.length - SPACE.length,
		),
		totalsWrap: true,
	};
}

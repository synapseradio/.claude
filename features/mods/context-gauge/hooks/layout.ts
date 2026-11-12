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

/** Each figure size's unit, suffix and decimals, largest first. */
const MAGNITUDES = [
	{ from: 1_000_000, unit: 1_000_000, suffix: "M", decimals: 1 },
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
		.map((_, i) => i)
		.sort((a, b) => ((raw[b] ?? 0) % 1) - ((raw[a] ?? 0) % 1));
	for (const i of order.slice(0, leftover)) counts[i] = (counts[i] ?? 0) + 1;
	return counts;
}

type RunTokens = { id: BarRun["id"]; tokens: number };

/** The bar's runs, `width` cells: each used row at least one cell where the width holds one per row, the rest split by tokens against the window, free space last. */
export function barRuns(
	model: UsageModel,
	rows: readonly GaugeRow[],
	width: number,
): BarRun[] {
	const used = rows.filter((r) => r.tokens > 0);
	const parts = used
		.map((r): RunTokens => ({ id: r.id, tokens: r.tokens }))
		.concat({ id: "free", tokens: Math.max(0, model.max - model.used) });
	const everyRowFits = used.length <= width;
	const floors = parts.map((p): number =>
		everyRowFits && p.id !== "free" ? 1 : 0,
	);
	const shares = largestRemainder(
		parts.map((p) => p.tokens),
		width - floors.reduce((a, b) => a + b, 0),
	);
	return parts
		.map((p, i) => ({ id: p.id, cells: (shares[i] ?? 0) + (floors[i] ?? 0) }))
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

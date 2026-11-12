import { describe, expect, test } from "claude-code/testing";
import type { BarRun, CategoryId, Texture } from "../hooks/palette";
import {
	BAR_ORDER,
	CATEGORY_STYLES,
	FREE_SWATCH,
	TEXTURES,
} from "../hooks/palette";
import type { Pixels } from "../hooks/pixels";
import {
	barPixels,
	PX_HEIGHT,
	PX_PER_CELL,
	samplePixels,
} from "../hooks/pixels";

type Rgb = { r: number; g: number; b: number };

/** A decoded image: one RGBA quadruple per pixel, row by row. */
type Decoded = { width: number; height: number; bytes: Uint8Array };

function decode(p: Pixels): Decoded {
	return {
		width: p.width,
		height: p.height,
		bytes: Uint8Array.fromBase64(p.rgba),
	};
}

function byteAt(img: Decoded, x: number, y: number, channel: number): number {
	return img.bytes[(y * img.width + x) * 4 + channel] ?? Number.NaN;
}

function alpha(img: Decoded, x: number, y: number): number {
	return byteAt(img, x, y, 3);
}

function rgb(img: Decoded, x: number, y: number): Rgb {
	return {
		r: byteAt(img, x, y, 0),
		g: byteAt(img, x, y, 1),
		b: byteAt(img, x, y, 2),
	};
}

function hexRgb(hex: string): Rgb {
	return {
		r: Number.parseInt(hex.slice(1, 3), 16),
		g: Number.parseInt(hex.slice(3, 5), 16),
		b: Number.parseInt(hex.slice(5, 7), 16),
	};
}

function range(from: number, to: number): number[] {
	return Array.from({ length: to - from }, (_, i) => from + i);
}

/** The rows of column `x` with any opacity. */
function litRows(img: Decoded, x: number): number[] {
	return range(0, img.height).filter((y) => alpha(img, x, y) > 0);
}

/** Every alpha of columns `from` to `to`, column by column, as one list. */
function alphas(img: Decoded, from: number, to: number): number[] {
	return range(from, to).flatMap((x) =>
		range(0, img.height).map((y) => alpha(img, x, y)),
	);
}

/** Every byte of columns `from` to `to`, column by column, as one list. */
function columns(img: Decoded, from: number, to: number): number[] {
	return range(from, to).flatMap((x) =>
		range(0, img.height).flatMap((y) =>
			range(0, 4).map((c) => byteAt(img, x, y, c)),
		),
	);
}

/** The first column of each run, in pixels. */
function runStarts(runs: readonly BarRun[]): number[] {
	return runs.map(
		(_, i) =>
			runs.slice(0, i).reduce((n, run) => n + run.cells, 0) * PX_PER_CELL,
	);
}

function categoryWith(texture: Texture): CategoryId {
	const id = BAR_ORDER.find((c) => CATEGORY_STYLES[c].texture === texture);
	if (id === undefined) throw new Error(`no category draws ${texture}`);
	return id;
}

// The approved prototype draws a 20-pixel row's band from round(20 / 3) = 7 to
// 20 - 7 = 13, exclusive.
const BAND_ROWS = [7, 8, 9, 10, 11, 12];

const RUNS: readonly BarRun[] = [
	{ id: "system", cells: 3 },
	{ id: "mcp", cells: 2 },
	{ id: "agents", cells: 1 },
	{ id: "memory", cells: 1 },
	{ id: "free", cells: 4 },
];

const CATEGORY_RUNS = RUNS.flatMap((run, i) => {
	const start = runStarts(RUNS)[i] ?? 0;
	return run.id === "free"
		? []
		: [
				{
					id: run.id,
					start,
					end: start + run.cells * PX_PER_CELL,
					seamed: i > 0,
				},
			];
});

describe("bar pixels", () => {
	test("a cell is 10 pixels wide and the bar one 20-pixel terminal row high", () => {
		expect(PX_PER_CELL).toBe(10);
		expect(PX_HEIGHT).toBe(20);
	});

	test("the bar is as wide as its cells and holds four bytes per pixel", () => {
		const p = barPixels(RUNS);
		const img = decode(p);
		expect(p.width).toBe(11 * PX_PER_CELL);
		expect(p.height).toBe(PX_HEIGHT);
		expect(img.bytes.length).toBe(11 * PX_PER_CELL * PX_HEIGHT * 4);
	});

	test("every category column is lit in the band rows and nowhere else", () => {
		const img = decode(barPixels(RUNS));
		for (const run of CATEGORY_RUNS) {
			for (const x of range(run.seamed ? run.start + 1 : run.start, run.end)) {
				expect({ id: run.id, x, rows: litRows(img, x) }).toEqual({
					id: run.id,
					x,
					rows: BAND_ROWS,
				});
			}
		}
	});

	test("every lit pixel of a run carries its category's colour", () => {
		const img = decode(barPixels(RUNS));
		for (const run of CATEGORY_RUNS) {
			const want = hexRgb(CATEGORY_STYLES[run.id].swatch.hex);
			for (const x of range(run.start, run.end)) {
				for (const y of litRows(img, x)) {
					expect({ id: run.id, x, y, colour: rgb(img, x, y) }).toEqual({
						id: run.id,
						x,
						y,
						colour: want,
					});
				}
			}
		}
	});

	test("a texture's pixels are fully opaque where it is on and alpha 110 where it is off", () => {
		for (const texture of TEXTURES) {
			const img = decode(samplePixels(categoryWith(texture), 1));
			const band = range(0, PX_PER_CELL).flatMap((x) =>
				BAND_ROWS.map((y) => alpha(img, x, y)),
			);
			const levels = Array.from(new Set(band)).sort((a, b) => a - b);
			expect({ texture, levels }).toEqual({
				texture,
				levels: texture === "solid" ? [255] : [110, 255],
			});
		}
	});

	test("the four textures differ from each other inside one cell after a seam", () => {
		const masks = TEXTURES.map((texture) => {
			const img = decode(
				barPixels([
					{ id: "system", cells: 1 },
					{ id: categoryWith(texture), cells: 1 },
				]),
			);
			return alphas(img, PX_PER_CELL + 1, 2 * PX_PER_CELL).join(",");
		});
		expect(new Set(masks).size).toBe(TEXTURES.length);
	});

	test("a transparent one-pixel seam sits where each run meets the next, and nowhere else", () => {
		const img = decode(barPixels(RUNS));
		const empty = range(0, img.width).filter(
			(x) => litRows(img, x).length === 0,
		);
		expect(empty).toEqual(runStarts(RUNS).slice(1));
	});

	test("free space is a line in the free swatch, thinner than the band and centred on it", () => {
		const img = decode(barPixels(RUNS));
		const start = runStarts(RUNS)[RUNS.length - 1] ?? 0;
		const mean = (rows: readonly number[]): number =>
			rows.reduce((a, b) => a + b, 0) / rows.length;
		for (const x of range(start + 1, img.width)) {
			const rows = litRows(img, x);
			expect(rows.length).toBeGreaterThan(0);
			expect(rows.length).toBeLessThan(BAND_ROWS.length);
			expect(mean(rows)).toBe(mean(BAND_ROWS));
			for (const y of rows) {
				expect(rgb(img, x, y)).toEqual(hexRgb(FREE_SWATCH.hex));
			}
		}
	});
});

describe("legend samples", () => {
	test("a sample is as wide as its cells and one bar row high", () => {
		const p = samplePixels("read", 2);
		expect({ width: p.width, height: p.height }).toEqual({
			width: 2 * PX_PER_CELL,
			height: PX_HEIGHT,
		});
	});

	test("a sample is pixel for pixel the start of a bar's first run of that category", () => {
		for (const id of BAR_ORDER) {
			const sample = decode(samplePixels(id, 2));
			const bar = decode(
				barPixels([
					{ id, cells: 3 },
					{ id: "free", cells: 1 },
				]),
			);
			expect({ id, px: columns(bar, 0, 2 * PX_PER_CELL) }).toEqual({
				id,
				px: columns(sample, 0, 2 * PX_PER_CELL),
			});
		}
	});

	test("a later run matches the sample past its seam, its texture phase starting at the run", () => {
		for (const id of BAR_ORDER) {
			const sample = decode(samplePixels(id, 2));
			const bar = decode(
				barPixels([
					{ id: "system", cells: 1 },
					{ id, cells: 2 },
				]),
			);
			expect({
				id,
				px: columns(bar, PX_PER_CELL + 1, 3 * PX_PER_CELL),
			}).toEqual({ id, px: columns(sample, 1, 2 * PX_PER_CELL) });
		}
	});
});

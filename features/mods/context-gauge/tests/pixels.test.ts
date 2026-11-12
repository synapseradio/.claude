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

function visibleRows(img: Decoded, x: number): number[] {
	return range(0, img.height).filter((y) => alpha(img, x, y) > 0);
}

function columnAlphas(img: Decoded, from: number, to: number): number[] {
	return range(from, to).flatMap((x) =>
		range(0, img.height).map((y) => alpha(img, x, y)),
	);
}

function columnBytes(img: Decoded, from: number, to: number): number[] {
	return range(from, to).flatMap((x) =>
		range(0, img.height).flatMap((y) =>
			range(0, 4).map((c) => byteAt(img, x, y, c)),
		),
	);
}

type Span = { id: BarRun["id"]; start: number; end: number };

function spans(runs: readonly BarRun[]): Span[] {
	return runs.map((run, i) => {
		const start =
			runs.slice(0, i).reduce((n, r) => n + r.cells, 0) * PX_PER_CELL;
		return { id: run.id, start, end: start + run.cells * PX_PER_CELL };
	});
}

const BAND_ROWS = [7, 8, 9, 10, 11, 12];

const RUNS: readonly BarRun[] = [
	{ id: "system", cells: 3 },
	{ id: "mcp", cells: 2 },
	{ id: "agents", cells: 1 },
	{ id: "memory", cells: 1 },
	{ id: "free", cells: 4 },
];

const CATEGORY_SPANS = spans(RUNS).filter(
	(s): s is Span & { id: CategoryId } => s.id !== "free",
);

const FREE_SPANS = spans(RUNS).filter((s) => s.id === "free");

const DRAWN_WITH: Readonly<Record<Texture, CategoryId>> = {
	solid: "system",
	diagonal: "mcp",
	vertical: "agents",
	dots: "memory",
};

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

	test("every category column is visible in the band rows and nowhere else", () => {
		const img = decode(barPixels(RUNS));
		for (const span of CATEGORY_SPANS) {
			for (const x of range(
				span.start > 0 ? span.start + 1 : span.start,
				span.end,
			)) {
				expect({ id: span.id, x, rows: visibleRows(img, x) }).toEqual({
					id: span.id,
					x,
					rows: BAND_ROWS,
				});
			}
		}
	});

	test("every visible pixel of a run carries its category's colour", () => {
		const img = decode(barPixels(RUNS));
		expect(rgb(img, 0, 7)).toEqual({ r: 230, g: 73, b: 128 });
		for (const span of CATEGORY_SPANS) {
			const want = hexRgb(CATEGORY_STYLES[span.id].swatch.hex);
			for (const x of range(span.start, span.end)) {
				for (const y of visibleRows(img, x)) {
					expect({ id: span.id, x, y, colour: rgb(img, x, y) }).toEqual({
						id: span.id,
						x,
						y,
						colour: want,
					});
				}
			}
		}
	});

	test("each texture draws its pattern in one cell, on pixels opaque and off pixels at alpha 110", () => {
		const patterns: Record<Texture, string[]> = {
			solid: [
				"##########",
				"##########",
				"##########",
				"##########",
				"##########",
				"##########",
			],
			diagonal: [
				"##...###..",
				"#...###...",
				"...###...#",
				"..###...##",
				".###...###",
				"###...###.",
			],
			vertical: [
				"##..##..##",
				"##..##..##",
				"##..##..##",
				"##..##..##",
				"##..##..##",
				"##..##..##",
			],
			dots: [
				"..........",
				"##..##..##",
				"##..##..##",
				"..........",
				"..........",
				"##..##..##",
			],
		};
		for (const texture of TEXTURES) {
			const id = DRAWN_WITH[texture];
			const img = decode(samplePixels(id, 1));
			const drawn = BAND_ROWS.map((y) =>
				range(0, PX_PER_CELL)
					.map((x) => {
						const a = alpha(img, x, y);
						return a === 255 ? "#" : a === 110 ? "." : String(a);
					})
					.join(""),
			);
			expect({ texture, of: CATEGORY_STYLES[id].texture, drawn }).toEqual({
				texture,
				of: texture,
				drawn: patterns[texture],
			});
		}
	});

	test("the four textures differ from each other inside one cell after a seam", () => {
		const masks = TEXTURES.map((texture) => {
			const img = decode(
				barPixels([
					{ id: "system", cells: 1 },
					{ id: DRAWN_WITH[texture], cells: 1 },
				]),
			);
			return columnAlphas(img, PX_PER_CELL + 1, 2 * PX_PER_CELL).join(",");
		});
		expect(new Set(masks).size).toBe(TEXTURES.length);
	});

	test("a transparent one-pixel seam sits where each run meets the next, and nowhere else", () => {
		const img = decode(barPixels(RUNS));
		const empty = range(0, img.width).filter(
			(x) => visibleRows(img, x).length === 0,
		);
		expect(empty).toEqual(
			spans(RUNS)
				.slice(1)
				.map((s) => s.start),
		);
	});

	test("free space is a line in the free swatch, thinner than the band and centred on it", () => {
		const img = decode(barPixels(RUNS));
		const mean = (rows: readonly number[]): number =>
			rows.reduce((a, b) => a + b, 0) / rows.length;
		expect(FREE_SPANS.length).toBe(1);
		for (const span of FREE_SPANS) {
			for (const x of range(span.start + 1, span.end)) {
				const rows = visibleRows(img, x);
				expect({ x, some: rows.length > 0 }).toEqual({ x, some: true });
				expect({ x, thinner: rows.length < BAND_ROWS.length }).toEqual({
					x,
					thinner: true,
				});
				expect({ x, centre: mean(rows) }).toEqual({
					x,
					centre: mean(BAND_ROWS),
				});
				for (const y of rows) {
					expect({ x, y, colour: rgb(img, x, y) }).toEqual({
						x,
						y,
						colour: hexRgb(FREE_SWATCH.hex),
					});
				}
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
			expect({ id, px: columnBytes(bar, 0, 2 * PX_PER_CELL) }).toEqual({
				id,
				px: columnBytes(sample, 0, 2 * PX_PER_CELL),
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
				px: columnBytes(bar, PX_PER_CELL + 1, 3 * PX_PER_CELL),
			}).toEqual({ id, px: columnBytes(sample, 1, 2 * PX_PER_CELL) });
		}
	});
});

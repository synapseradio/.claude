import { describe, expect, test } from "claude-code/testing";
import type { BarRun, CategoryId, Texture } from "../hooks/palette";
import { BAR_ORDER, FREE_SWATCH, PALETTES, TEXTURES } from "../hooks/palette";
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

const RUNS: readonly BarRun[] = [
	{ id: "system", cells: 3 },
	{ id: "mcp", cells: 2 },
	{ id: "agentList", cells: 1 },
	{ id: "memory", cells: 1 },
	{ id: "free", cells: 4 },
];

const CATEGORY_SPANS = spans(RUNS).filter(
	(s): s is Span & { id: CategoryId } => s.id !== "free",
);

const FREE_SPANS = spans(RUNS).filter((s) => s.id === "free");

/** The rows the bar's opening run draws in, its band. */
const BAND_ROWS = visibleRows(decode(barPixels(RUNS, "dark")), 0);

function mean(rows: readonly number[]): number {
	return rows.reduce((a, b) => a + b, 0) / rows.length;
}

/** The middle of the bar's height, in rows. */
const CENTRE = (PX_HEIGHT - 1) / 2;

const DRAWN_WITH: Readonly<Record<Texture, CategoryId>> = {
	solid: "system",
	diagonal: "mcp",
	vertical: "agentList",
	dots: "memory",
	checker: "carried",
};

describe("bar pixels", () => {
	test("the bar is as wide as its cells and holds four bytes per pixel", () => {
		const p = barPixels(RUNS, "dark");
		const img = decode(p);
		expect(p.width).toBe(11 * PX_PER_CELL);
		expect(p.height).toBe(PX_HEIGHT);
		expect(img.bytes.length).toBe(11 * PX_PER_CELL * PX_HEIGHT * 4);
	});

	test("the band is one unbroken stripe of rows, thinner than the bar and centred in it", () => {
		const [top = 0] = BAND_ROWS;

		expect(BAND_ROWS).toEqual(range(top, top + BAND_ROWS.length));
		expect(BAND_ROWS.length).toBeGreaterThan(0);
		expect(BAND_ROWS.length).toBeLessThan(PX_HEIGHT);
		expect(mean(BAND_ROWS)).toBe(CENTRE);
	});

	test("every category column is visible in the band rows and nowhere else", () => {
		const img = decode(barPixels(RUNS, "dark"));
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

	test("every visible pixel of a run carries its category's colour in the theme's palette", () => {
		for (const theme of ["light", "dark"] as const) {
			const img = decode(barPixels(RUNS, theme));
			for (const span of CATEGORY_SPANS) {
				const want = hexRgb(PALETTES[theme][span.id].swatch.hex);
				for (const x of range(span.start, span.end)) {
					for (const y of visibleRows(img, x)) {
						expect({
							theme,
							id: span.id,
							x,
							y,
							colour: rgb(img, x, y),
						}).toEqual({ theme, id: span.id, x, y, colour: want });
					}
				}
			}
		}
	});

	test("each texture but solid draws its pattern in opaque pixels over a fainter fill that keeps the band whole", () => {
		for (const texture of TEXTURES) {
			const id = DRAWN_WITH[texture];
			const img = decode(samplePixels(id, 1, "dark"));
			const alphas = new Set(
				BAND_ROWS.flatMap((y) =>
					range(0, PX_PER_CELL).map((x) => alpha(img, x, y)),
				),
			);
			const opaque = alphas.has(255);
			const faint = [...alphas].filter((a) => a < 255);
			const whole = faint.every((a) => a > 0);
			const patterned =
				texture === "solid" ? faint.length === 0 : faint.length > 0;
			expect({
				texture,
				of: PALETTES.dark[id].texture,
				opaque,
				whole,
				patterned,
			}).toEqual({
				texture,
				of: texture,
				opaque: true,
				whole: true,
				patterned: true,
			});
		}
	});

	test("the five textures differ from each other inside one cell after a seam", () => {
		const masks = TEXTURES.map((texture) => {
			const img = decode(
				barPixels(
					[
						{ id: "system", cells: 1 },
						{ id: DRAWN_WITH[texture], cells: 1 },
					],
					"dark",
				),
			);
			return columnAlphas(img, PX_PER_CELL + 1, 2 * PX_PER_CELL).join(",");
		});
		expect(new Set(masks).size).toBe(TEXTURES.length);
	});

	test("only carried draws the checker texture, in both themes", () => {
		for (const theme of ["light", "dark"] as const) {
			const checkered = BAR_ORDER.filter(
				(id) => PALETTES[theme][id].texture === "checker",
			);
			expect({ theme, checkered }).toEqual({ theme, checkered: ["carried"] });
		}
	});

	test("a transparent one-pixel seam sits where each run meets the next, and nowhere else", () => {
		const img = decode(barPixels(RUNS, "dark"));
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
		const img = decode(barPixels(RUNS, "dark"));
		expect(FREE_SPANS.length).toBe(1);
		for (const span of FREE_SPANS) {
			for (const x of range(span.start + 1, span.end)) {
				const rows = visibleRows(img, x);
				expect({ x, some: rows.length > 0 }).toEqual({ x, some: true });
				expect({ x, thinner: rows.length < BAND_ROWS.length }).toEqual({
					x,
					thinner: true,
				});
				expect({ x, centre: mean(rows) }).toEqual({ x, centre: CENTRE });
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
		const p = samplePixels("read", 2, "dark");
		expect({ width: p.width, height: p.height }).toEqual({
			width: 2 * PX_PER_CELL,
			height: PX_HEIGHT,
		});
	});

	test("a sample is pixel for pixel the start of a bar's first run of that category", () => {
		for (const id of BAR_ORDER) {
			const sample = decode(samplePixels(id, 2, "dark"));
			const bar = decode(
				barPixels(
					[
						{ id, cells: 3 },
						{ id: "free", cells: 1 },
					],
					"dark",
				),
			);
			expect({ id, px: columnBytes(bar, 0, 2 * PX_PER_CELL) }).toEqual({
				id,
				px: columnBytes(sample, 0, 2 * PX_PER_CELL),
			});
		}
	});

	test("a later run matches the sample past its seam, its texture phase starting at the run", () => {
		for (const id of BAR_ORDER) {
			const sample = decode(samplePixels(id, 2, "dark"));
			const bar = decode(
				barPixels(
					[
						{ id: "system", cells: 1 },
						{ id, cells: 2 },
					],
					"dark",
				),
			);
			expect({
				id,
				px: columnBytes(bar, PX_PER_CELL + 1, 3 * PX_PER_CELL),
			}).toEqual({ id, px: columnBytes(sample, 1, 2 * PX_PER_CELL) });
		}
	});
});

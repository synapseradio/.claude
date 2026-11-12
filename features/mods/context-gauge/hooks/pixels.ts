/** The gauge bar and its legend keys, drawn as RGBA images for the engine's Image. */

// Why: the engine's hooks environment has Uint8Array.prototype.toBase64
// (https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Uint8Array/toBase64),
// which the engine-generated lib setting leaves undeclared; this directive adds
// only the Uint8Array base64 and hex methods
// (https://www.typescriptlang.org/docs/handbook/triple-slash-directives.html#-reference-lib-).
/// <reference lib="esnext.typedarrays" />
import type { BarRun, CategoryId, Swatch, Texture } from "./palette";
import { CATEGORY_STYLES, FREE_SWATCH } from "./palette";

/** An Image source in its rgba form: base64 of width × height pixels, four bytes each, row by row. */
export type Pixels = { rgba: string; width: number; height: number };

/** The pixel width of one bar cell. */
export const PX_PER_CELL = 10;

/** The pixel height of the bar, one terminal row. */
export const PX_HEIGHT = 20;

// Map: in each column of the image, rows BAND_TOP to BAND_BOTTOM - 1 hold a
// category's band and rows FREE_TOP to FREE_BOTTOM - 1 free space's line; every
// other row stays transparent. A run's first column stays transparent too,
// as the seam, unless the run opens the bar.
const BAND_TOP = Math.round(PX_HEIGHT / 3);
const BAND_BOTTOM = PX_HEIGHT - BAND_TOP;
const FREE_TOP = PX_HEIGHT / 2 - 1;
const FREE_BOTTOM = PX_HEIGHT / 2 + 1;

const ON_ALPHA = 255;
const OFF_ALPHA = 110;

/** Whether a texture lights the pixel `x` columns into its run, on image row `y`. */
function lit(texture: Texture, x: number, y: number): boolean {
	switch (texture) {
		case "solid":
			return true;
		case "diagonal":
			return (x + y) % 6 < 3;
		case "vertical":
			return x % 4 < 2;
		case "dots":
			return x % 4 < 2 && y % 4 < 2;
	}
}

type Paint = {
	swatch: Swatch;
	top: number;
	bottom: number;
	alpha: (x: number, y: number) => number;
};

function paintOf(id: BarRun["id"]): Paint {
	if (id === "free") {
		return {
			swatch: FREE_SWATCH,
			top: FREE_TOP,
			bottom: FREE_BOTTOM,
			alpha: () => ON_ALPHA,
		};
	}
	const { swatch, texture } = CATEGORY_STYLES[id];
	return {
		swatch,
		top: BAND_TOP,
		bottom: BAND_BOTTOM,
		alpha: (x, y) => (lit(texture, x, y) ? ON_ALPHA : OFF_ALPHA),
	};
}

/** The bar as RGBA: each run in its category's colour and texture inside a centred band, a 1-pixel transparent seam where one run meets the next, free space as a thin centred line in FREE_SWATCH. */
export function barPixels(runs: readonly BarRun[]): Pixels {
	const width = runs.reduce((n, run) => n + run.cells, 0) * PX_PER_CELL;
	const px = new Uint8Array(width * PX_HEIGHT * 4);
	let start = 0;
	for (const run of runs) {
		const paint = paintOf(run.id);
		const r = Number.parseInt(paint.swatch.hex.slice(1, 3), 16);
		const g = Number.parseInt(paint.swatch.hex.slice(3, 5), 16);
		const b = Number.parseInt(paint.swatch.hex.slice(5, 7), 16);
		const end = start + run.cells * PX_PER_CELL;
		const first = start === 0 ? start : start + 1;
		for (let x = first; x < end; x++) {
			for (let y = paint.top; y < paint.bottom; y++) {
				const o = (y * width + x) * 4;
				px[o] = r;
				px[o + 1] = g;
				px[o + 2] = b;
				px[o + 3] = paint.alpha(x - start, y);
			}
		}
		start = end;
	}
	return { rgba: px.toBase64(), width, height: PX_HEIGHT };
}

/** A legend key: `cells` cells of a category's run, pixel for pixel what a run of that category starts with. */
export function samplePixels(id: CategoryId, cells: number): Pixels {
	return barPixels([{ id, cells }]);
}

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

// Map: in each column of the image, the rows of BAND hold a category's band
// and the rows of FREE_LINE free space's line; every other row stays
// transparent. A run's first column stays transparent too, as the seam, unless
// the run opens the bar.
type Rows = { top: number; bottom: number };
const BAND: Rows = {
	top: Math.round(PX_HEIGHT / 3),
	bottom: PX_HEIGHT - Math.round(PX_HEIGHT / 3),
};
const FREE_LINE: Rows = { top: PX_HEIGHT / 2 - 1, bottom: PX_HEIGHT / 2 + 1 };

const ON_ALPHA = 255;
const OFF_ALPHA = 110;

function textureOn(texture: Texture, runX: number, row: number): boolean {
	switch (texture) {
		case "solid":
			return true;
		case "diagonal":
			return (runX + row) % 6 < 3;
		case "vertical":
			return runX % 4 < 2;
		case "dots":
			return runX % 4 < 2 && row % 4 < 2;
	}
}

type Paint = { swatch: Swatch; rows: Rows; texture: Texture };

function paintOf(id: BarRun["id"]): Paint {
	if (id === "free") {
		return { swatch: FREE_SWATCH, rows: FREE_LINE, texture: "solid" };
	}
	const { swatch, texture } = CATEGORY_STYLES[id];
	return { swatch, rows: BAND, texture };
}

/** The bar as RGBA: each run in its category's colour and texture inside a centred band, a 1-pixel transparent seam where one run meets the next, free space as a thin centred line in FREE_SWATCH. */
export function barPixels(runs: readonly BarRun[]): Pixels {
	const width = runs.reduce((n, run) => n + run.cells, 0) * PX_PER_CELL;
	const px = new Uint8Array(width * PX_HEIGHT * 4);
	let start = 0;
	for (const run of runs) {
		const { swatch, rows, texture } = paintOf(run.id);
		const rgb = Number.parseInt(swatch.hex.slice(1), 16);
		const end = start + run.cells * PX_PER_CELL;
		const drawFrom = start === 0 ? start : start + 1;
		for (let x = drawFrom; x < end; x++) {
			for (let y = rows.top; y < rows.bottom; y++) {
				const offset = (y * width + x) * 4;
				px[offset] = rgb >> 16;
				px[offset + 1] = (rgb >> 8) & 255;
				px[offset + 2] = rgb & 255;
				px[offset + 3] = textureOn(texture, x - start, y)
					? ON_ALPHA
					: OFF_ALPHA;
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

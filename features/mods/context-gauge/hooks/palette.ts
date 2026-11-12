/** The Open Color swatches the gauge paints its bar segments and chips with. */

/** One Open Color shade: its hue, its index 0 to 9, and its hex. */
export type Swatch = { hue: string; shade: number; hex: string };

/** The gauge's categories, in bar order. */
export type CategoryId =
	| "system"
	| "mcp"
	| "agents"
	| "memory"
	| "skills"
	| "hooks"
	| "user"
	| "calls"
	| "results"
	| "read"
	| "replies"
	| "other";

/**
 * One swatch per gauge category, in bar order, `other` for a row the gauge does not name.
 *
 * Each sits between 3:1 and 4.5:1 against white, so a bar cell stands at 3:1 on light and
 * dark terminals alike and black chip text reads at 4.5:1 on it; adjacent pairs pass the
 * colour-vision-deficiency separation check.
 * Hexes: https://github.com/yeun/open-color/blob/v1.9.1/open-color.json
 */
export const CATEGORY_SWATCHES: Readonly<Record<CategoryId, Swatch>> = {
	system: { hue: "indigo", shade: 5, hex: "#5c7cfa" },
	mcp: { hue: "cyan", shade: 7, hex: "#1098ad" },
	agents: { hue: "lime", shade: 9, hex: "#5c940d" },
	memory: { hue: "violet", shade: 4, hex: "#9775fa" },
	skills: { hue: "teal", shade: 8, hex: "#099268" },
	hooks: { hue: "grape", shade: 5, hex: "#cc5de8" },
	user: { hue: "orange", shade: 8, hex: "#e8590c" },
	calls: { hue: "green", shade: 8, hex: "#2f9e44" },
	results: { hue: "pink", shade: 6, hex: "#e64980" },
	read: { hue: "blue", shade: 6, hex: "#228be6" },
	replies: { hue: "red", shade: 7, hex: "#f03e3e" },
	other: { hue: "gray", shade: 6, hex: "#868e96" },
};

/**
 * The percentage chip's swatch by how full the window is. Orange stands in for yellow:
 * no Open Color yellow reaches 3:1 on a near-white surface.
 */
export const FILL_SWATCHES: Readonly<Record<"low" | "mid" | "high", Swatch>> = {
	low: { hue: "green", shade: 8, hex: "#2f9e44" },
	mid: { hue: "orange", shade: 8, hex: "#e8590c" },
	high: { hue: "red", shade: 7, hex: "#f03e3e" },
};

/** The percentage chip's swatch: low below 50, mid below 80, high from 80. */
export function fillSwatch(percent: number): Swatch {
	if (percent < 50) return FILL_SWATCHES.low;
	if (percent < 80) return FILL_SWATCHES.mid;
	return FILL_SWATCHES.high;
}

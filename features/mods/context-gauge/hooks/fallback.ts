/** The character bar drawn where the pixel bar cannot draw: one glyph per texture, in each category's swatch. */

import type { UiBlitResult } from "claude-code";
import type { BarRun, CategoryId, Texture } from "./palette";
import { CATEGORY_STYLES, FREE_SWATCH } from "./palette";

/** The glyph vocabularies: sextants for terminals that draw them themselves, BMP glyphs for the rest. */
export type GlyphSet = "sextant" | "bmp";

/** What every cell of a run draws: one glyph in one colour. */
export type Look = { glyph: string; color: string };

/** One Text run: a bar run's glyph once per cell, in its colour. */
export type Run = { id: BarRun["id"]; color: string; text: string };

/** What the glyph set turns on: the TERM_PROGRAM and WT_SESSION variables, and the `fix` of the bar Image's blit denial. */
export type TerminalEnv = {
	termProgram?: string | undefined;
	wtSession?: string | undefined;
	blitFix?: UiBlitResult["fix"];
};

/** One glyph per texture in each set, each a single cell wide at East Asian Width N. */
export const TEXTURE_GLYPHS: Readonly<
	Record<GlyphSet, Readonly<Record<Texture, string>>>
> = {
	sextant: {
		solid: "\u{1FB0B}",
		diagonal: "\u{1FB1C}",
		vertical: "\u{1FB1B}",
		dots: "\u{1FB03}",
	},
	// Hazard: the font, not the terminal, draws ▬ and ▪, so their height and
	// position are the font's own; Menlo and SF Mono centre them with ▐ and ▞.
	bmp: { solid: "▬", diagonal: "▞", vertical: "▐", dots: "▪" },
};

/** Free space's glyph in both sets, a light dashed stroke. */
export const FREE_GLYPH = "╌";

/** The glyph set the terminal draws without missing-glyph boxes, chosen from what its environment names. */
export function glyphSet(env: TerminalEnv): GlyphSet {
	// Why: tmux holds images back only from a terminal that draws them, and
	// kitty and Ghostty draw sextants themselves, https://arewelegacycomputingyet.com/
	// Hazard: iTerm2 draws images too, and no iTerm2 release note says it draws sextants.
	if (env.blitFix === "tmux-passthrough") return "sextant";
	// Why: VS Code sets TERM_PROGRAM and draws sextants itself under GPU
	// acceleration, though from the font under its DOM renderer,
	// https://github.com/microsoft/vscode/blob/main/src/vs/workbench/contrib/terminal/common/terminalConfiguration.ts
	if (env.termProgram === "vscode") return "sextant";
	// Why: tmux 3.2 and later set TERM_PROGRAM in every pane, so a WT_SESSION
	// left from where its server started names no attached terminal,
	// https://github.com/tmux/tmux/blob/master/environ.c
	// Why: Windows Terminal sets WT_SESSION but no TERM_PROGRAM, and draws
	// sextants itself from 1.25, https://github.com/microsoft/terminal/releases/tag/v1.25.2733.0
	if (!env.termProgram && env.wtSession) return "sextant";
	// Hazard: Apple Terminal takes sextants from the font, and no font macOS
	// ships covers them, so they draw as missing-glyph boxes.
	return "bmp";
}

/** A run's look: its category's texture glyph and swatch, or free space's own. */
export function lookOf(id: BarRun["id"], set: GlyphSet): Look {
	if (id === "free") return { glyph: FREE_GLYPH, color: FREE_SWATCH.hex };
	const style = CATEGORY_STYLES[id];
	return { glyph: TEXTURE_GLYPHS[set][style.texture], color: style.swatch.hex };
}

function runOf(id: BarRun["id"], cells: number, set: GlyphSet): Run {
	const look = lookOf(id, set);
	return { id, color: look.color, text: look.glyph.repeat(cells) };
}

/** The bar's Text runs: one per bar run with cells, in order, its glyph repeated once per cell. */
export function fallbackRuns(runs: readonly BarRun[], set: GlyphSet): Run[] {
	return runs.filter((r) => r.cells > 0).map((r) => runOf(r.id, r.cells, set));
}

/** A legend key: `cells` cells of what a bar run of the category draws. */
export function legendSample(
	id: CategoryId,
	cells: number,
	set: GlyphSet,
): Run {
	return runOf(id, cells, set);
}

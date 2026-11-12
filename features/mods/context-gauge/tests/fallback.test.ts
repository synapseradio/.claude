import { describe, expect, test } from "claude-code/testing";
import type { GlyphSet, TerminalEnv } from "../hooks/fallback";
import {
	FREE_GLYPH,
	fallbackRuns,
	glyphSet,
	legendSample,
	lookOf,
	TEXTURE_GLYPHS,
} from "../hooks/fallback";
import type { BarRun } from "../hooks/palette";
import { BAR_ORDER } from "../hooks/palette";

const SETS: readonly GlyphSet[] = ["sextant", "bmp"];

/** Every id a bar run can carry, free space last. */
const RUN_IDS: readonly BarRun["id"][] = Array.from<BarRun["id"]>(
	BAR_ORDER,
).concat(["free"]);

/** A set's glyphs: its four texture glyphs, then free space. */
function glyphsOf(set: GlyphSet): string[] {
	return Object.values(TEXTURE_GLYPHS[set]).concat([FREE_GLYPH]);
}

/** Cells a drawn string takes: one per code point, since a sextant's UTF-16 length is 2. */
function cells(text: string): number {
	return Array.from(text).length;
}

// The East Asian Width N ranges that hold the fallback glyphs, from
// https://www.unicode.org/Public/18.0.0/ucd/EastAsianWidth.txt. Width A glyphs
// such as █ U+2588, ━ U+2501 and ▌ U+258C fall outside them, since a terminal
// set to wide ambiguous characters draws those across two cells.
const WIDTH_N: readonly (readonly [number, number])[] = [
	[0x25_4c, 0x25_4f],
	[0x25_90, 0x25_91],
	[0x25_96, 0x25_9f],
	[0x25_aa, 0x25_b1],
	[0x1_fb_00, 0x1_fb_92],
];

// Sextant names from https://www.unicode.org/Public/18.0.0/ucd/UnicodeData.txt:
// cells numbered 1 to 6, left to right and top to bottom, in a 2 by 3 grid.
const SEXTANT_NAMES: ReadonlyMap<number, string> = new Map([
	[0x1_fb_03, "BLOCK SEXTANT-3"],
	[0x1_fb_0b, "BLOCK SEXTANT-34"],
	[0x1_fb_1b, "BLOCK SEXTANT-1345"],
	[0x1_fb_1c, "BLOCK SEXTANT-2345"],
]);

// The sextant block at U+1FB00 skips the patterns other blocks already hold:
// the left half (21) and the right half (42), per
// https://www.unicode.org/charts/PDF/U1FB00.pdf.
function sextantCells(codePoint: number): number[] {
	const pattern = [21, 42].reduce(
		(p, skipped) => (p >= skipped ? p + 1 : p),
		codePoint - 0x1_fb_00 + 1,
	);
	return [1, 2, 3, 4, 5, 6].filter((cell) => (pattern >> (cell - 1)) & 1);
}

/** Mirrors a sextant cell top to bottom: row 1 swaps with row 3. */
function flipped(cell: number): number {
	if (cell <= 2) return cell + 4;
	if (cell >= 5) return cell - 4;
	return cell;
}

function sameCells(a: readonly number[], b: readonly number[]): boolean {
	const sorted = Array.from(b).sort((x, y) => x - y);
	return a.length === sorted.length && a.every((c, i) => c === sorted[i]);
}

/** Bar runs in bar order with cell counts from 0 to 4, zero-cell runs among them. */
const GENERATED: readonly (readonly BarRun[])[] = Array.from(
	{ length: 12 },
	(_, k) => RUN_IDS.map((id, i) => ({ id, cells: (i * k + k) % 5 })),
);

describe("fallback bar", () => {
	test("every glyph is one code point of East Asian Width N", async () => {
		for (const set of SETS) {
			for (const glyph of glyphsOf(set)) {
				const cp = glyph.codePointAt(0) ?? -1;
				const narrow = WIDTH_N.some(([lo, hi]) => cp >= lo && cp <= hi);
				expect(`${set} ${glyph} ${cells(glyph)} ${narrow}`).toBe(
					`${set} ${glyph} 1 true`,
				);
			}
		}
	});

	test("every sextant inks the middle row and stays symmetric about the centre", async () => {
		for (const glyph of Object.values(TEXTURE_GLYPHS.sextant)) {
			const cp = glyph.codePointAt(0) ?? -1;
			const lit = sextantCells(cp);
			expect(`BLOCK SEXTANT-${lit.join("")}`).toBe(
				SEXTANT_NAMES.get(cp) ?? `no name fixture for ${cp.toString(16)}`,
			);
			const middle = lit.includes(3) || lit.includes(4);
			const upright = sameCells(lit, lit.map(flipped));
			const halfTurn =
				sameCells(
					lit,
					lit.map((c) => 7 - c),
				) &&
				lit.includes(3) &&
				lit.includes(4);
			expect(`${glyph} ${middle && (upright || halfTurn)}`).toBe(
				`${glyph} true`,
			);
		}
	});

	test("each set's four textures and free space draw five different glyphs", async () => {
		for (const set of SETS) {
			expect(`${set} ${new Set(glyphsOf(set)).size}`).toBe(`${set} 5`);
		}
	});

	// A zero-token category drops out of the bar, so any two categories can
	// meet, and free space meets whichever category comes last.
	test("any two segments that can meet differ in glyph or colour", async () => {
		for (const set of SETS) {
			RUN_IDS.forEach((a, i) => {
				for (const b of RUN_IDS.slice(i + 1)) {
					const la = lookOf(a, set);
					const lb = lookOf(b, set);
					const apart = la.glyph !== lb.glyph || la.color !== lb.color;
					expect(`${set} ${a} ${b} ${apart ? "apart" : "alike"}`).toBe(
						`${set} ${a} ${b} apart`,
					);
				}
			});
		}
	});

	test("runs keep every cell, one run per non-empty segment, in order", async () => {
		for (const set of SETS) {
			for (const bar of GENERATED) {
				const kept = bar.filter((r) => r.cells > 0);
				const runs = fallbackRuns(bar, set);
				const drawn = runs.reduce((sum, r) => sum + cells(r.text), 0);
				const wanted = kept.reduce((sum, r) => sum + r.cells, 0);
				expect(`${set} ${drawn}`).toBe(`${set} ${wanted}`);
				expect(runs.map((r) => r.id)).toEqual(kept.map((r) => r.id));
				runs.forEach((run, i) => {
					const segment = kept[i];
					const look = lookOf(run.id, set);
					expect(run).toEqual({
						id: segment?.id,
						color: look.color,
						text: look.glyph.repeat(segment?.cells ?? 0),
					});
				});
			}
		}
	});

	test("no run draws a cell outside its set's glyphs", async () => {
		for (const set of SETS) {
			const allowed = new Set(glyphsOf(set));
			for (const bar of GENERATED) {
				for (const run of fallbackRuns(bar, set)) {
					const strays = Array.from(run.text).filter((c) => !allowed.has(c));
					expect(`${set} ${run.id} ${strays.join("")}`).toBe(
						`${set} ${run.id} `,
					);
				}
			}
		}
	});

	test("a one-cell segment draws its texture's whole glyph", async () => {
		for (const set of SETS) {
			for (const id of RUN_IDS) {
				const [run] = fallbackRuns([{ id, cells: 1 }], set);
				expect(`${set} ${id} ${run?.text}`).toBe(
					`${set} ${id} ${lookOf(id, set).glyph}`,
				);
			}
		}
	});

	test("a legend sample draws what the bar draws for the same category", async () => {
		for (const set of SETS) {
			for (const id of BAR_ORDER) {
				for (const n of [1, 2, 3]) {
					const look = lookOf(id, set);
					const sample = legendSample(id, n, set);
					expect(sample).toEqual({
						id,
						color: look.color,
						text: look.glyph.repeat(n),
					});
					expect(fallbackRuns([{ id, cells: n }], set)).toEqual([sample]);
				}
			}
		}
	});

	test("each terminal's environment picks the glyph set it draws", async () => {
		const cases: readonly (readonly [string, TerminalEnv, GlyphSet])[] = [
			["Windows Terminal", { wtSession: "0f7c2d" }, "sextant"],
			["Apple Terminal", { termProgram: "Apple_Terminal" }, "bmp"],
			["VS Code", { termProgram: "vscode" }, "sextant"],
			[
				"VS Code started from Windows Terminal",
				{ termProgram: "vscode", wtSession: "0f7c2d" },
				"sextant",
			],
			[
				"Ghostty or kitty in tmux without passthrough",
				{ termProgram: "tmux", blitFix: "tmux-passthrough" },
				"sextant",
			],
			["tmux in Apple Terminal", { termProgram: "tmux" }, "bmp"],
			[
				"tmux whose server started in Windows Terminal",
				{ termProgram: "tmux", wtSession: "0f7c2d" },
				"bmp",
			],
			["an unnamed terminal, or one over SSH", {}, "bmp"],
		];
		for (const [name, env, set] of cases) {
			expect(`${name} ${glyphSet(env)}`).toBe(`${name} ${set}`);
		}
	});
});

import { describe, expect, test } from "claude-code/testing";
import type { Theme } from "../hooks/palette";
import { BAR_ORDER, FREE_SWATCH, PALETTES } from "../hooks/palette";
import { deficientDistance, normalDistance } from "./colour-vision";

// Terminal backgrounds each palette must read on.
const SURFACES: Readonly<Record<Theme, readonly string[]>> = {
	light: ["#ffffff", "#f8f9fa"],
	dark: ["#1a1a19", "#212529"],
};

const THEMES: readonly Theme[] = ["light", "dark"];

// WCAG 2.x relative luminance and contrast ratio, https://www.w3.org/TR/WCAG22/#dfn-relative-luminance
function luminance(hex: string): number {
	const channels = [1, 3, 5].map(
		(i) => Number.parseInt(hex.slice(i, i + 2), 16) / 255,
	);
	const [r = 0, g = 0, b = 0] = channels.map((c) =>
		c <= 0.040_45 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4,
	);
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
	const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
	return ((hi ?? 0) + 0.05) / ((lo ?? 0) + 0.05);
}

/** A theme's categories in bar order, each with its style. */
function stylesOf(theme: Theme) {
	return BAR_ORDER.map((id) => ({ id, ...PALETTES[theme][id] }));
}

/** Every pair of a theme's categories, each pair once. */
function pairsOf(theme: Theme) {
	const styles = stylesOf(theme);
	return styles.flatMap((a, i) => styles.slice(i + 1).map((b) => [a, b]));
}

describe("palette", () => {
	for (const theme of THEMES) {
		test(`${theme}: every colour, as bar pixels and as bold label text, stands at 3:1 or more on its surfaces`, async () => {
			const swatches = stylesOf(theme)
				.map((s): [string, string] => [s.id, s.swatch.hex])
				.concat([["free space", FREE_SWATCH.hex]]);
			for (const [name, hex] of swatches) {
				for (const surface of SURFACES[theme]) {
					expect(`${name} on ${surface} ${contrast(hex, surface) >= 3}`).toBe(
						`${name} on ${surface} true`,
					);
				}
			}
		});

		// Floors from the dataviz palette validator, taken per pair of colours:
		// ΔE ×100 under normal vision and under simulated protanopia and deuteranopia.
		test(`${theme}: any two category colours stay apart to normal and colour-deficient vision`, async () => {
			for (const [a, b] of pairsOf(theme)) {
				const normal = normalDistance(a?.swatch.hex ?? "", b?.swatch.hex ?? "");
				const deficient = deficientDistance(
					a?.swatch.hex ?? "",
					b?.swatch.hex ?? "",
				);
				expect(`${a?.id} ${b?.id} ${normal >= 10 && deficient >= 4}`).toBe(
					`${a?.id} ${b?.id} true`,
				);
			}
		});

		test(`${theme}: neighbours in the bar stand further apart and differ in texture`, async () => {
			const styles = stylesOf(theme);
			styles.slice(1).forEach((b, i) => {
				const a = styles[i];
				const normal = normalDistance(a?.swatch.hex ?? "", b.swatch.hex);
				const deficient = deficientDistance(a?.swatch.hex ?? "", b.swatch.hex);
				const apart =
					normal >= 15 && deficient >= 6 && a?.texture !== b.texture;
				expect(`${a?.id} ${b.id} ${apart}`).toBe(`${a?.id} ${b.id} true`);
			});
		});
	}
});

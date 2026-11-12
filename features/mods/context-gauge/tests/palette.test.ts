import { describe, expect, test } from "claude-code/testing";
import type { Swatch } from "../hooks/palette";
import { CATEGORY_SWATCHES, FILL_SWATCHES } from "../hooks/palette";

// Open Color 1.9.1, https://github.com/yeun/open-color/blob/v1.9.1/open-color.json
const OPEN_COLOR: Readonly<Record<string, readonly string[]>> = {
	gray: [
		"#f8f9fa",
		"#f1f3f5",
		"#e9ecef",
		"#dee2e6",
		"#ced4da",
		"#adb5bd",
		"#868e96",
		"#495057",
		"#343a40",
		"#212529",
	],
	red: [
		"#fff5f5",
		"#ffe3e3",
		"#ffc9c9",
		"#ffa8a8",
		"#ff8787",
		"#ff6b6b",
		"#fa5252",
		"#f03e3e",
		"#e03131",
		"#c92a2a",
	],
	pink: [
		"#fff0f6",
		"#ffdeeb",
		"#fcc2d7",
		"#faa2c1",
		"#f783ac",
		"#f06595",
		"#e64980",
		"#d6336c",
		"#c2255c",
		"#a61e4d",
	],
	grape: [
		"#f8f0fc",
		"#f3d9fa",
		"#eebefa",
		"#e599f7",
		"#da77f2",
		"#cc5de8",
		"#be4bdb",
		"#ae3ec9",
		"#9c36b5",
		"#862e9c",
	],
	violet: [
		"#f3f0ff",
		"#e5dbff",
		"#d0bfff",
		"#b197fc",
		"#9775fa",
		"#845ef7",
		"#7950f2",
		"#7048e8",
		"#6741d9",
		"#5f3dc4",
	],
	indigo: [
		"#edf2ff",
		"#dbe4ff",
		"#bac8ff",
		"#91a7ff",
		"#748ffc",
		"#5c7cfa",
		"#4c6ef5",
		"#4263eb",
		"#3b5bdb",
		"#364fc7",
	],
	blue: [
		"#e7f5ff",
		"#d0ebff",
		"#a5d8ff",
		"#74c0fc",
		"#4dabf7",
		"#339af0",
		"#228be6",
		"#1c7ed6",
		"#1971c2",
		"#1864ab",
	],
	cyan: [
		"#e3fafc",
		"#c5f6fa",
		"#99e9f2",
		"#66d9e8",
		"#3bc9db",
		"#22b8cf",
		"#15aabf",
		"#1098ad",
		"#0c8599",
		"#0b7285",
	],
	teal: [
		"#e6fcf5",
		"#c3fae8",
		"#96f2d7",
		"#63e6be",
		"#38d9a9",
		"#20c997",
		"#12b886",
		"#0ca678",
		"#099268",
		"#087f5b",
	],
	green: [
		"#ebfbee",
		"#d3f9d8",
		"#b2f2bb",
		"#8ce99a",
		"#69db7c",
		"#51cf66",
		"#40c057",
		"#37b24d",
		"#2f9e44",
		"#2b8a3e",
	],
	lime: [
		"#f4fce3",
		"#e9fac8",
		"#d8f5a2",
		"#c0eb75",
		"#a9e34b",
		"#94d82d",
		"#82c91e",
		"#74b816",
		"#66a80f",
		"#5c940d",
	],
	orange: [
		"#fff4e6",
		"#ffe8cc",
		"#ffd8a8",
		"#ffc078",
		"#ffa94d",
		"#ff922b",
		"#fd7e14",
		"#f76707",
		"#e8590c",
		"#d9480f",
	],
};

// Terminal backgrounds the gauge must read on: white, Open Color gray 0, a near-black, Open Color gray 9.
const SURFACES = ["#ffffff", "#f8f9fa", "#1a1a19", "#212529"];

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

const swatches: [string, Swatch][] = [
	...Object.entries(CATEGORY_SWATCHES),
	...Object.entries(FILL_SWATCHES).map(([k, s]): [string, Swatch] => [
		`fill ${k}`,
		s,
	]),
];

describe("palette", () => {
	test("every swatch is the Open Color shade it names", async () => {
		for (const [name, s] of swatches) {
			expect(`${name} ${OPEN_COLOR[s.hue]?.[s.shade]}`).toBe(
				`${name} ${s.hex}`,
			);
		}
	});

	test("every category colour, as bar cells and as bold label text, stands at 3:1 or more on light and dark surfaces", async () => {
		for (const [name, s] of Object.entries(CATEGORY_SWATCHES)) {
			for (const surface of SURFACES) {
				expect(`${name} on ${surface} ${contrast(s.hex, surface) >= 3}`).toBe(
					`${name} on ${surface} true`,
				);
			}
		}
	});
});

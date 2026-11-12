/** How far apart two colours look, in OKLab ΔE ×100, to normal vision and under simulated protanopia and deuteranopia. */

type Triple = readonly [number, number, number];
type Matrix = readonly [Triple, Triple, Triple];

function times(m: Matrix, v: Triple): Triple {
	const [x, y, z] = v;
	const [r0, r1, r2] = m;
	return [
		r0[0] * x + r0[1] * y + r0[2] * z,
		r1[0] * x + r1[1] * y + r1[2] * z,
		r2[0] * x + r2[1] * y + r2[2] * z,
	];
}

// The sRGB transfer function, https://www.w3.org/TR/css-color-4/#color-conversion-code
function linearChannel(c: number): number {
	return c <= 0.040_45 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

function linearRgb(hex: string): Triple {
	const [r = 0, g = 0, b = 0] = [1, 3, 5].map((i) =>
		linearChannel(Number.parseInt(hex.slice(i, i + 2), 16) / 255),
	);
	return [r, g, b];
}

// Linear sRGB to OKLab, https://bottosson.github.io/posts/oklab/
const TO_LMS: Matrix = [
	[0.412_221_470_8, 0.536_332_536_3, 0.051_445_992_9],
	[0.211_903_498_2, 0.680_699_545_1, 0.107_396_956_6],
	[0.088_302_461_9, 0.281_718_837_6, 0.629_978_700_5],
];
const TO_LAB: Matrix = [
	[0.210_454_255_3, 0.793_617_785, -0.004_072_046_8],
	[1.977_998_495_1, -2.428_592_205, 0.450_593_709_9],
	[0.025_904_037_1, 0.782_771_766_2, -0.808_675_766],
];

function oklab(linear: Triple): Triple {
	const [l, m, s] = times(TO_LMS, linear);
	return times(TO_LAB, [Math.cbrt(l), Math.cbrt(m), Math.cbrt(s)]);
}

// Machado, Oliveira and Fernandes (2009) at severity 1.0, applied to linear RGB:
// https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html
const PROTAN: Matrix = [
	[0.152_286, 1.052_583, -0.204_868],
	[0.114_503, 0.786_281, 0.099_216],
	[-0.003_882, -0.048_116, 1.051_998],
];
const DEUTAN: Matrix = [
	[0.367_322, 0.860_646, -0.227_968],
	[0.280_085, 0.672_501, 0.047_413],
	[-0.011_82, 0.042_94, 0.968_881],
];

function clamped(v: Triple): Triple {
	const [x, y, z] = v.map((c) => Math.min(1, Math.max(0, c)));
	return [x ?? 0, y ?? 0, z ?? 0];
}

function apart(a: Triple, b: Triple): number {
	return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]) * 100;
}

/** The OKLab distance ×100 between two hexes as normal vision sees them. */
export function normalDistance(a: string, b: string): number {
	return apart(oklab(linearRgb(a)), oklab(linearRgb(b)));
}

/** The smaller OKLab distance ×100 between two hexes under simulated protanopia and deuteranopia. */
export function deficientDistance(a: string, b: string): number {
	const seen = (m: Matrix, hex: string) =>
		oklab(clamped(times(m, linearRgb(hex))));
	return Math.min(
		apart(seen(PROTAN, a), seen(PROTAN, b)),
		apart(seen(DEUTAN, a), seen(DEUTAN, b)),
	);
}

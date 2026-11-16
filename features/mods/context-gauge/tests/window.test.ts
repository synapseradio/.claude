import type { TurnUsage } from "claude-code";
import { describe, expect, test } from "claude-code/testing";

import {
	CEILING_FACTOR,
	MIN_RATIO_INTERVAL_CHARS,
	PRIOR_TOKENS_PER_CHAR,
} from "../hooks/calibration";
import {
	applyHistory,
	beginRequest,
	drawn,
	keepRow,
	settleRequest,
	startWindow,
	taint,
} from "../hooks/window";
import type {
	CountedId,
	HistoryRead,
	Pieces,
	Ratio,
	RowPieces,
	Tally,
	Window,
	WindowCause,
} from "../types";

const MODEL = "claude-opus-4-7";
const STRIPPING_MODEL = "claude-sonnet-4-5";

/** Tokens per character of 0.5, pooled for MODEL, so fixtures read in halves. */
const HALF: Ratio = { model: MODEL, tokens: 5000, chars: 10_000 };
/** No sample yet: the prior decides. */
const NO_RATIO: Ratio = { model: "", tokens: 0, chars: 0 };

const MESSAGES_IN_REQUEST = 100;
const MESSAGES_AT_ANCHOR = 10;

const START: WindowCause = { family: "start", signal: "session.start" };
const CLEAR: WindowCause = {
	family: "clear",
	signal: "classic.SessionStart:clear",
};
const COMPACTION_ROW: WindowCause = {
	family: "compaction",
	signal: "session.append:compaction",
};
const COMPACTION_EVENT: WindowCause = {
	family: "compaction",
	signal: "session.compact",
};
const UNSEEN: WindowCause = {
	family: "unseen",
	signal: "turn.step:messageCount",
};

const ZERO: Tally = {
	carried: 0,
	summary: 0,
	hooks: 0,
	plugins: 0,
	reminders: 0,
	files: 0,
	messages: 0,
	tasks: 0,
	relayed: 0,
	commands: 0,
	calls: 0,
	writes: 0,
	results: 0,
	read: 0,
	prompts: 0,
	agents: 0,
	thinking: 0,
};
const IDS = Object.keys(ZERO) as CountedId[];

type Amounts = Partial<Record<CountedId, number>>;

function tally(amounts: Amounts = {}): Tally {
	return { ...ZERO, ...amounts };
}

function only(id: CountedId, amount: number): Amounts {
	const amounts: Record<CountedId, number> = { ...ZERO };
	amounts[id] = amount;
	return amounts;
}

function pieces(chars: Amounts = {}, media: Amounts = {}): Pieces {
	return { chars: tally(chars), media: tally(media) };
}

function inputRow(chars: Amounts, media: Amounts = {}): RowPieces {
	return { input: pieces(chars, media), output: null, agentCalls: [] };
}

function reply(
	visible: Amounts,
	options: { thinking?: boolean; served?: Amounts } = {},
): RowPieces {
	return {
		input: pieces(),
		output: {
			visible: pieces(visible),
			thinking: options.thinking ?? false,
			served: pieces(options.served),
		},
		agentCalls: [],
	};
}

function round(figure: number): number {
	return Math.round(figure * 1e6) / 1e6 || 0;
}

function rounded(figures: Tally): Tally {
	const out: Record<CountedId, number> = { ...ZERO };
	for (const id of IDS) out[id] = round(figures[id]);
	return out;
}

function usage(size: number, output: number, model = MODEL): TurnUsage {
	const input = size - output;
	const cacheRead = Math.floor(input / 3);
	const cacheCreation = Math.floor(input / 3);
	return {
		input_tokens: input - cacheRead - cacheCreation,
		cache_read_input_tokens: cacheRead,
		cache_creation_input_tokens: cacheCreation,
		output_tokens: output,
		model,
	};
}

function read(chars: number, extra: Partial<HistoryRead> = {}): HistoryRead {
	return {
		chars,
		media: 0,
		agentCalls: [],
		fingerprint: null,
		truncated: false,
		...extra,
	};
}

const SEED: Window = {
	cause: START,
	measure: { kind: "unmeasured", history: { kind: "unread", why: "not-yet" } },
	open: pieces(),
	tainted: false,
	inFlight: null,
	fingerprint: null,
	replaced: null,
};

/** A window whose history read found nothing. */
const EMPTY: Window = applyHistory(SEED, read(0));

function measuredWindow(
	tokens: Amounts,
	size: number,
	fixed: number,
	extra: { gap?: number; fingerprint?: string } = {},
): Window {
	return {
		...SEED,
		fingerprint: extra.fingerprint ?? null,
		measure: {
			kind: "measured",
			anchor: { window: size, fixed, messageCount: MESSAGES_AT_ANCHOR },
			tokens: tally(tokens),
			gap: extra.gap ?? 0,
		},
	};
}

function booksOf(w: Window): { tokens: Tally; gap: number } {
	if (w.measure.kind !== "measured") {
		throw new Error("the window has no measurement");
	}
	return { tokens: rounded(w.measure.tokens), gap: round(w.measure.gap) };
}

type Step = {
	rows?: readonly RowPieces[];
	response?: RowPieces;
	usage: TurnUsage | null;
	fixed: number;
	index?: number;
	served?: boolean;
	failedRow?: boolean;
};

function sending(w: Window, s: Omit<Step, "usage" | "fixed">): Window {
	let kept = w;
	for (const row of s.rows ?? []) kept = keepRow(kept, row);
	if (s.failedRow === true) kept = taint(kept);
	const begun = beginRequest(kept, {
		index: s.index ?? 0,
		messageCount: MESSAGES_IN_REQUEST,
	});
	if (begun === "replaced") {
		throw new Error(
			"the request counted fewer messages than the last response",
		);
	}
	return s.response === undefined ? begun : keepRow(begun, s.response);
}

function step(
	w: Window,
	ratio: Ratio,
	s: Step,
): { window: Window; ratio: Ratio } {
	return settleRequest(sending(w, s), ratio, {
		usage: s.usage,
		fixed: s.fixed,
		served: s.served ?? false,
	});
}

/** A first response of 100 output tokens over nothing, so every category but messages is 0 afterwards. */
function baseline(ratio: Ratio): { window: Window; ratio: Ratio } {
	return step(EMPTY, ratio, {
		response: reply({ messages: 100 }),
		usage: usage(1100, 100),
		fixed: 1000,
	});
}

describe("how a response's tokens reach the categories", () => {
	test("a response's output tokens show on its own blocks and never on the rows of the next request", () => {
		const first = step(EMPTY, HALF, {
			rows: [inputRow({ results: 6000 })],
			response: reply({ calls: 400 }),
			usage: usage(6000, 3000),
			fixed: 2000,
		});
		const second = step(first.window, first.ratio, {
			rows: [inputRow({ results: 2000 })],
			response: reply({ messages: 100 }),
			usage: usage(7100, 500),
			fixed: 2000,
		});

		expect(booksOf(first.window)).toEqual({
			tokens: tally({ results: 1000, calls: 3000 }),
			gap: 0,
		});
		expect(booksOf(second.window)).toEqual({
			tokens: tally({ results: 1600, calls: 3000, messages: 500 }),
			gap: 0,
		});
	});

	test("the rows one request carries split its new input tokens by character share, after output and the fixed rows' change", () => {
		const base = baseline(HALF);
		const second = step(base.window, base.ratio, {
			rows: [inputRow({ files: 3000 }), inputRow({ results: 1000 })],
			response: reply({ messages: 50 }),
			usage: usage(3600, 200),
			fixed: 1300,
		});

		expect(booksOf(second.window)).toEqual({
			tokens: tally({ files: 1500, results: 500, messages: 300 }),
			gap: 0,
		});
	});

	test("the first response of a window spreads its input over carried history and the rows kept before it", () => {
		const kept = keepRow(SEED, inputRow({ messages: 2000 }));
		const withHistory = applyHistory(kept, read(6000));
		const first = step(withHistory, HALF, {
			response: reply({ calls: 100 }),
			usage: usage(5000, 200),
			fixed: 3000,
		});

		expect(booksOf(first.window)).toEqual({
			tokens: tally({ carried: 1200, messages: 600, calls: 200 }),
			gap: 0,
		});
	});

	test("the first response of a window counts carried media at its own estimate", () => {
		const withHistory = applyHistory(SEED, read(0, { media: 800 }));
		const first = step(withHistory, HALF, {
			response: reply({ messages: 10 }),
			usage: usage(1500, 100),
			fixed: 600,
		});

		expect(booksOf(first.window).tokens).toEqual(
			tally({ carried: 800, messages: 100 }),
		);
	});
});

describe("how a response's own output is split", () => {
	test("a response with no thinking block shows no thinking", () => {
		const first = step(EMPTY, NO_RATIO, {
			response: reply({ messages: 400 }),
			usage: usage(4000, 3000),
			fixed: 1000,
		});

		expect(booksOf(first.window).tokens).toEqual(tally({ messages: 3000 }));
	});

	test("a response with a thinking block shows its output less its visible text at the pooled ratio", () => {
		const first = step(EMPTY, NO_RATIO, {
			response: reply({ messages: 400 }, { thinking: true }),
			usage: usage(4000, 3000),
			fixed: 1000,
		});

		expect(booksOf(first.window).tokens).toEqual(
			tally({
				messages: round(PRIOR_TOKENS_PER_CHAR * 400),
				thinking: round(3000 - PRIOR_TOKENS_PER_CHAR * 400),
			}),
		);
	});

	test("visible text never takes more than the response's output", () => {
		const first = step(EMPTY, HALF, {
			response: reply({ messages: 20_000 }, { thinking: true }),
			usage: usage(4000, 3000),
			fixed: 1000,
		});

		expect(booksOf(first.window).tokens).toEqual(tally({ messages: 3000 }));
	});

	test("output split over several visible kinds follows their character share", () => {
		const first = step(EMPTY, HALF, {
			response: reply({ messages: 300, calls: 100 }),
			usage: usage(4000, 3000),
			fixed: 1000,
		});

		expect(booksOf(first.window).tokens).toEqual(
			tally({ messages: 2250, calls: 750 }),
		);
	});

	test("output with no visible block and no thinking shows as attribution gap", () => {
		const first = step(EMPTY, HALF, {
			usage: usage(4000, 3000),
			fixed: 1000,
		});

		expect(booksOf(first.window)).toEqual({ tokens: tally(), gap: 3000 });
	});
});

describe("tokens no counted row can carry", () => {
	const ROW_CHARS = 100;
	const CARRYING_LIMIT = CEILING_FACTOR * PRIOR_TOKENS_PER_CHAR * ROW_CHARS;
	const EXCESS = 2000;

	function withExcess(
		prepare: (w: Window) => Window,
	): ReturnType<typeof booksOf> {
		const base = baseline(NO_RATIO);
		const second = step(prepare(base.window), base.ratio, {
			rows: [inputRow({ results: ROW_CHARS })],
			response: reply({ messages: 10 }),
			usage: usage(1100 + 100 + EXCESS, 100),
			fixed: 1000,
		});
		return booksOf(second.window);
	}

	test("tokens beyond twice what an interval's rows can carry show as Claude Code reminders when every row counted", () => {
		expect(withExcess((w) => w)).toEqual({
			tokens: tally({
				results: round(CARRYING_LIMIT),
				reminders: round(EXCESS - CARRYING_LIMIT),
				messages: 200,
			}),
			gap: 0,
		});
	});

	test("the same excess shows as attribution gap when a row in the interval failed to count", () => {
		expect(withExcess(taint)).toEqual({
			tokens: tally({ results: round(CARRYING_LIMIT), messages: 200 }),
			gap: round(EXCESS - CARRYING_LIMIT),
		});
	});

	test("an interval with no row at all sends all its input tokens to reminders", () => {
		const base = baseline(NO_RATIO);
		const second = step(base.window, base.ratio, {
			response: reply({ messages: 10 }),
			usage: usage(1100 + 100 + 700, 100),
			fixed: 1000,
		});

		expect(booksOf(second.window)).toEqual({
			tokens: tally({ reminders: 700, messages: 200 }),
			gap: 0,
		});
	});

	test("a first response over a window whose history was never read puts the excess in the attribution gap", () => {
		const first = step(SEED, NO_RATIO, {
			rows: [inputRow({ messages: ROW_CHARS })],
			response: reply({ calls: 10 }),
			usage: usage(1000 + EXCESS + 100, 100),
			fixed: 1000,
		});

		expect(booksOf(first.window)).toEqual({
			tokens: tally({ messages: round(CARRYING_LIMIT), calls: 100 }),
			gap: round(EXCESS - CARRYING_LIMIT),
		});
	});

	test("a first response over a window whose history read failed puts the excess in the attribution gap", () => {
		const first = step(applyHistory(SEED, "failed"), NO_RATIO, {
			response: reply({ calls: 10 }),
			usage: usage(1000 + EXCESS + 100, 100),
			fixed: 1000,
		});

		expect(booksOf(first.window)).toEqual({
			tokens: tally({ calls: 100 }),
			gap: EXCESS,
		});
	});
});

describe("a window that shrank", () => {
	test("a window that shrank by more than its output takes the difference from every category in proportion", () => {
		const before = measuredWindow({ results: 6000, files: 2000 }, 9000, 1000);
		const after = step(before, HALF, {
			response: reply({ calls: 100 }),
			usage: usage(8300, 100),
			fixed: 1000,
		});

		expect(booksOf(after.window)).toEqual({
			tokens: tally({ results: 5400, files: 1800, calls: 100 }),
			gap: 0,
		});
	});

	test("the attribution gap shrinks with the categories", () => {
		const before = measuredWindow(
			{ results: 6000, files: 2000 },
			11_000,
			1000,
			{
				gap: 2000,
			},
		);
		const after = step(before, HALF, {
			response: reply({ calls: 100 }),
			usage: usage(10_100, 100),
			fixed: 1000,
		});

		expect(booksOf(after.window)).toEqual({
			tokens: tally({ results: 5400, files: 1800, calls: 100 }),
			gap: 1800,
		});
	});

	test("rows beside a shrink get nothing of it", () => {
		const before = measuredWindow({ results: 6000, files: 2000 }, 9000, 1000);
		const after = step(before, HALF, {
			rows: [inputRow({ read: 4000 })],
			response: reply({ calls: 100 }),
			usage: usage(8300, 100),
			fixed: 1000,
		});

		expect(booksOf(after.window).tokens).toEqual(
			tally({ results: 5400, files: 1800, calls: 100 }),
		);
	});
});

describe("models that strip earlier thinking", () => {
	const THINKING = 2000;
	const NEW_INPUT_TOKENS = 500;
	const OUTPUT = 100;
	const BEFORE = 5000;
	const FIXED = 2000;

	function newTurn(model: string, index: number, retired: boolean) {
		const before = measuredWindow(
			{ messages: 1000, thinking: THINKING },
			BEFORE,
			FIXED,
		);
		const size = BEFORE + OUTPUT + NEW_INPUT_TOKENS - (retired ? THINKING : 0);
		return step(
			before,
			{ model, tokens: 5000, chars: 10_000 },
			{
				rows: [inputRow({ results: 1000 })],
				response: reply({ messages: 50 }),
				usage: usage(size, OUTPUT, model),
				fixed: FIXED,
				index,
			},
		);
	}

	const STRIPS = [
		"claude-sonnet-4-5",
		"claude-sonnet-4-5-20250929",
		"claude-haiku-4-5-20251001",
		"claude-opus-4-1",
		"claude-opus-4-20250514",
		"claude-3-5-sonnet-20241022",
	];
	const KEEPS = [
		"claude-opus-4-5",
		"claude-opus-4-7",
		"claude-sonnet-4-6",
		"claude-sonnet-5-5",
		"claude-haiku-4-6",
		"a-model-the-gauge-does-not-know",
	];

	for (const model of STRIPS) {
		test(`on ${model} the first request of a new turn removes the earlier thinking from the gauge`, () => {
			expect(booksOf(newTurn(model, 0, true).window)).toEqual({
				tokens: tally({ messages: 1100, results: 500 }),
				gap: 0,
			});
		});

		test(`on ${model} a later request of the turn keeps the thinking`, () => {
			expect(booksOf(newTurn(model, 1, false).window)).toEqual({
				tokens: tally({ messages: 1100, thinking: THINKING, results: 500 }),
				gap: 0,
			});
		});
	}

	for (const model of KEEPS) {
		test(`on ${model} the first request of a new turn keeps the thinking`, () => {
			expect(booksOf(newTurn(model, 0, false).window)).toEqual({
				tokens: tally({ messages: 1100, thinking: THINKING, results: 500 }),
				gap: 0,
			});
		});
	}
});

describe("a step that leaves no anchor", () => {
	const READY = baseline(HALF);

	function streaming(): Window {
		return sending(READY.window, {
			rows: [inputRow({ results: 1000 })],
			response: reply({ calls: 200 }),
		});
	}

	function thenAnchor(w: Window): Window {
		return step(w, HALF, {
			rows: [inputRow({ files: 1000 })],
			response: reply({ messages: 40 }),
			usage: usage(2500, 300),
			fixed: 1000,
		}).window;
	}

	const EXPECTED_AFTER_NEXT = {
		tokens: tally({ results: 500, calls: 100, files: 500, messages: 400 }),
		gap: 0,
	};

	test("a failed step leaves its rows for the next request", () => {
		const inflight = streaming();
		const failed = settleRequest(inflight, HALF, {
			usage: null,
			fixed: 1000,
			served: false,
		});

		expect(failed.window.measure).toEqual(READY.window.measure);
		expect(failed.window.inFlight).toBeNull();
		expect(drawn(failed.window, HALF, 1000).messages).toEqual(
			drawn(inflight, HALF, 1000).messages,
		);
		expect(booksOf(thenAnchor(failed.window))).toEqual(EXPECTED_AFTER_NEXT);
	});

	test("a step with server tool uses anchors nothing; its rows wait for the next response", () => {
		const inflight = streaming();
		const skipped = settleRequest(inflight, HALF, {
			usage: usage(9999, 300),
			fixed: 1000,
			served: true,
		});

		expect(skipped.window.measure).toEqual(READY.window.measure);
		expect(skipped.ratio).toEqual(HALF);
		expect(drawn(skipped.window, HALF, 1000).messages).toEqual(
			drawn(inflight, HALF, 1000).messages,
		);
		expect(booksOf(thenAnchor(skipped.window))).toEqual(EXPECTED_AFTER_NEXT);
	});

	test("a failed step keeps an earlier row's failure to count against the next interval", () => {
		const inflight = taint(streaming());
		const failed = settleRequest(inflight, HALF, {
			usage: null,
			fixed: 1000,
			served: false,
		});

		expect(failed.window.tainted).toBe(true);
	});
});

describe("rows that arrive around a request", () => {
	test("a prompt typed while a response streams counts toward the next request", () => {
		const streaming = keepRow(
			sending(baseline(HALF).window, { response: reply({ calls: 10 }) }),
			inputRow({ messages: 800 }),
		);
		const settled = settleRequest(streaming, HALF, {
			usage: usage(1500, 100),
			fixed: 1000,
			served: false,
		});

		expect(settled.window.open.chars.messages).toBe(800);
		expect(settled.window.inFlight).toBeNull();
	});

	test("a response row that arrives with no request in flight counts as input for the next request", () => {
		const kept = keepRow(
			baseline(HALF).window,
			reply({ calls: 300 }, { thinking: true, served: { results: 50 } }),
		);

		expect(kept.open.chars.calls).toBe(300);
		expect(kept.open.chars.results).toBe(50);
		expect(kept.inFlight).toBeNull();
	});

	test("a server tool's result inside a response counts as input for the next request", () => {
		const base = baseline(HALF);
		const first = step(base.window, base.ratio, {
			response: reply({ calls: 100 }, { served: { results: 600 } }),
			usage: usage(1100 + 100 + 0, 100),
			fixed: 1000,
		});
		const second = step(first.window, first.ratio, {
			response: reply({ messages: 20 }),
			usage: usage(1200 + 100 + 300, 100),
			fixed: 1000,
		});

		expect(first.window.open.chars.results).toBe(600);
		expect(booksOf(second.window).tokens.results).toBe(300);
	});

	test("a request begun over an unsettled one keeps the earlier rows", () => {
		const streaming = sending(baseline(HALF).window, {
			rows: [inputRow({ results: 700 })],
			response: reply({ calls: 90 }),
		});
		const next = beginRequest(keepRow(streaming, inputRow({ files: 40 })), {
			index: 1,
			messageCount: MESSAGES_IN_REQUEST,
		});

		expect(next).not.toBe("replaced");
		if (next === "replaced") return;
		expect(next.inFlight?.sent.chars).toEqual(
			tally({ results: 700, calls: 90, files: 40 }),
		);
		expect(next.open).toEqual(pieces());
	});

	test("a request freezes the rows kept so far and records its place in the turn", () => {
		const kept = keepRow(baseline(HALF).window, inputRow({ results: 700 }));
		const begun = beginRequest(kept, {
			index: 2,
			messageCount: MESSAGES_IN_REQUEST + 41,
		});

		expect(begun).not.toBe("replaced");
		if (begun === "replaced") return;
		expect(begun.inFlight).toEqual({
			sent: pieces({ results: 700 }),
			output: { visible: pieces(), thinking: false, served: pieces() },
			index: 2,
			messageCount: MESSAGES_IN_REQUEST + 41,
		});
		expect(begun.open).toEqual(pieces());
	});
});

describe("every anchor adds up", () => {
	function lcg(seed: number): () => number {
		let state = seed;
		return () => {
			state = (state * 1_664_525 + 1_013_904_223) % 4_294_967_296;
			return state / 4_294_967_296;
		};
	}

	function walk(seed: number): string[] {
		const rand = lcg(seed);
		const between = (low: number, high: number) =>
			Math.floor(low + rand() * (high - low));
		const category = (): CountedId => IDS[between(0, IDS.length)] ?? "messages";
		const model = rand() < 0.5 ? MODEL : STRIPPING_MODEL;
		const failures: string[] = [];

		let window = SEED;
		const opening = rand();
		if (opening < 0.5) window = applyHistory(window, read(between(0, 30_000)));
		else if (opening < 0.7) window = applyHistory(window, "failed");
		let ratio = NO_RATIO;
		let size = 0;
		let fixed = 0;

		for (let turn = 0; turn < 14; turn += 1) {
			const rows = Array.from({ length: between(0, 4) }, () =>
				inputRow(
					only(category(), between(0, 6000)),
					rand() < 0.2 ? only(category(), between(0, 2000)) : {},
				),
			);
			const response = reply(only(category(), between(0, 800)), {
				thinking: rand() < 0.5,
				served: rand() < 0.2 ? only("results", between(0, 500)) : {},
			});
			const kind = rand();
			const output = between(0, 4000);
			const nextFixed = Math.max(0, fixed + between(-300, 500));
			const nextSize = Math.max(
				nextFixed + output,
				size + between(-2000, 9000),
			);
			const result = step(window, ratio, {
				rows,
				response,
				failedRow: rand() < 0.15,
				usage: kind < 0.1 ? null : usage(nextSize, output, model),
				served: kind >= 0.1 && kind < 0.2,
				fixed: nextFixed,
				index: between(0, 3),
			});
			window = result.window;
			ratio = result.ratio;
			if (kind < 0.2) continue;
			size = nextSize;
			fixed = nextFixed;

			if (window.measure.kind !== "measured") {
				failures.push(`seed ${seed} turn ${turn}: no measurement at an anchor`);
				continue;
			}
			const figures = Object.values(window.measure.tokens);
			const total = figures.reduce((sum, n) => sum + n, 0) + window.measure.gap;
			if (Math.abs(total - (size - fixed)) > 1e-6 * Math.max(1, size)) {
				failures.push(
					`seed ${seed} turn ${turn}: categories and gap total ${total}, the window less fixed rows is ${size - fixed}`,
				);
			}
			if (window.measure.gap < -1e-9 || figures.some((n) => n < -1e-9)) {
				failures.push(`seed ${seed} turn ${turn}: a figure went negative`);
			}
		}
		return failures;
	}

	test("every anchor's message categories and gap sum to the window less the fixed rows", () => {
		const failures = Array.from({ length: 80 }, (_, seed) =>
			walk(seed + 1),
		).flat();

		expect(failures).toEqual([]);
	});
});

describe("the history a window starts with", () => {
	test("history read after rows were kept counts those rows once", () => {
		const compacted = keepRow(
			startWindow(COMPACTION_ROW, baseline(HALF).window),
			inputRow({ summary: 5000 }),
		);
		const withHistory = applyHistory(compacted, read(25_000));

		expect(withHistory.measure).toEqual({
			kind: "unmeasured",
			history: { kind: "read", carriedChars: 20_000, carriedMedia: 0 },
		});
	});

	test("media kept before the read counts once as well", () => {
		const kept = keepRow(SEED, inputRow({}, { messages: 300 }));
		const withHistory = applyHistory(kept, read(0, { media: 1000 }));

		expect(withHistory.measure).toEqual({
			kind: "unmeasured",
			history: { kind: "read", carriedChars: 0, carriedMedia: 700 },
		});
	});

	test("a row kept after the read adds to carried over instead of replacing it", () => {
		const withHistory = applyHistory(SEED, read(25_000));
		const later = keepRow(withHistory, inputRow({ summary: 5000 }));
		const figures = drawn(later, HALF, 0);

		expect(figures.messages).toEqual(tally({ carried: 12_500, summary: 2500 }));
	});

	test("a read of more rows than it holds leaves carried over at nothing", () => {
		const kept = keepRow(SEED, inputRow({ messages: 9000 }));
		const withHistory = applyHistory(kept, read(4000));

		expect(withHistory.measure).toEqual({
			kind: "unmeasured",
			history: { kind: "read", carriedChars: 0, carriedMedia: 0 },
		});
	});

	test("a history read that returns the replaced conversation leaves carried over unread until the next request", () => {
		const old = applyHistory(SEED, read(100, { fingerprint: "toolu_A" }));
		const cleared = startWindow(CLEAR, old);

		expect(
			applyHistory(cleared, read(100, { fingerprint: "toolu_A" })).measure,
		).toEqual({
			kind: "unmeasured",
			history: { kind: "unread", why: "stale" },
		});
		expect(
			applyHistory(cleared, read(100, { fingerprint: "toolu_B" })).measure,
		).toEqual({
			kind: "unmeasured",
			history: { kind: "read", carriedChars: 100, carriedMedia: 0 },
		});
	});

	for (const signal of [
		"session.append:plan_mode_exit",
		"prompt.attachment:plan_mode_exit",
	] as const) {
		test(`a read in a window ${signal} started stands even when it returns the replaced conversation`, () => {
			const old = applyHistory(SEED, read(100, { fingerprint: "toolu_A" }));
			const exited = startWindow({ family: "clear", signal }, old);

			expect(
				applyHistory(exited, read(100, { fingerprint: "toolu_A" })).measure,
			).toEqual({
				kind: "unmeasured",
				history: { kind: "read", carriedChars: 100, carriedMedia: 0 },
			});
		});
	}

	test("a read that failed leaves carried over unread", () => {
		expect(applyHistory(SEED, "failed").measure).toEqual({
			kind: "unmeasured",
			history: { kind: "unread", why: "failed" },
		});
	});

	test("a read cut off at the message limit leaves carried over unread", () => {
		expect(
			applyHistory(SEED, read(90_000, { truncated: true })).measure,
		).toEqual({
			kind: "unmeasured",
			history: { kind: "unread", why: "truncated" },
		});
	});

	test("a read after the window's first response changes nothing", () => {
		const measured = baseline(HALF).window;

		expect(applyHistory(measured, read(50_000))).toBe(measured);
		expect(applyHistory(measured, "failed")).toBe(measured);
	});

	test("a read that finds the conversation's first reply remembers it for the next stale check", () => {
		const withHistory = applyHistory(
			SEED,
			read(100, { fingerprint: "toolu_C" }),
		);

		expect(withHistory.fingerprint).toBe("toolu_C");
		expect(startWindow(CLEAR, withHistory).replaced).toBe("toolu_C");
	});
});

describe("the signals that start a window", () => {
	const OLD = {
		...measuredWindow({ messages: 4000, results: 2000 }, 9000, 3000, {
			fingerprint: "toolu_OLD",
		}),
		open: pieces({ files: 800 }),
		tainted: true,
	};
	const FRESH_UNREAD = {
		kind: "unmeasured",
		history: { kind: "unread", why: "not-yet" },
	};

	const CLEARING: WindowCause[] = [
		{ family: "clear", signal: "classic.SessionStart:clear" },
		{ family: "clear", signal: "session.end:clear" },
		{ family: "clear", signal: "session.append:plan_mode_exit" },
		{ family: "clear", signal: "prompt.attachment:plan_mode_exit" },
	];

	for (const cause of CLEARING) {
		test(`${cause.signal} restarts the gauge with nothing of the old window and history unread`, () => {
			const started = startWindow(cause, OLD);

			expect(started).toEqual({
				cause,
				measure: FRESH_UNREAD,
				open: pieces(),
				tainted: false,
				inFlight: null,
				fingerprint: null,
				replaced: "toolu_OLD",
			});
			expect(drawn(started, HALF, 0).messages).toEqual(tally());
		});
	}

	const OTHER_STARTS: WindowCause[] = [
		{ family: "start", signal: "classic.SessionStart:startup" },
		{ family: "resume", signal: "classic.SessionStart:resume" },
		{ family: "resume", signal: "classic.SessionStart:fork" },
		{ family: "resume", signal: "session.end:resume" },
		{ family: "compaction", signal: "classic.SessionStart:compact" },
		{ family: "unseen", signal: "turn.step:messageCount" },
	];

	for (const cause of OTHER_STARTS) {
		test(`${cause.signal} also starts the gauge over from a measured window`, () => {
			const started = startWindow(cause, OLD);

			expect(started.measure).toEqual(FRESH_UNREAD);
			expect(started.open).toEqual(pieces());
			expect(started.replaced).toBe("toolu_OLD");
		});
	}

	test("a second signal of the same compaction before any request re-reads history and keeps the summary", () => {
		const compacted = keepRow(
			startWindow(COMPACTION_ROW, OLD),
			inputRow({ summary: 5000 }),
		);
		const read1 = applyHistory(compacted, read(25_000));
		const second = startWindow(COMPACTION_EVENT, read1);

		expect(second.measure).toEqual(FRESH_UNREAD);
		expect(second.cause).toEqual(COMPACTION_EVENT);
		expect(drawn(second, HALF, 0).messages).toEqual(tally({ summary: 2500 }));
		expect(applyHistory(second, read(25_000)).measure).toEqual({
			kind: "unmeasured",
			history: { kind: "read", carriedChars: 20_000, carriedMedia: 0 },
		});
	});

	test("a /clear after a compaction empties the summary and what was carried", () => {
		const compacted = applyHistory(
			keepRow(startWindow(COMPACTION_ROW, OLD), inputRow({ summary: 5000 })),
			read(25_000),
		);
		const cleared = startWindow(CLEAR, compacted);

		expect(cleared.open).toEqual(pieces());
		expect(cleared.measure).toEqual(FRESH_UNREAD);
		expect(drawn(cleared, HALF, 0).messages).toEqual(tally());
	});

	test("a second signal of another family starts a new window and drops the rows counted", () => {
		const compacted = keepRow(
			startWindow(COMPACTION_ROW, OLD),
			inputRow({ summary: 5000 }),
		);
		const resumed = startWindow(
			{ family: "resume", signal: "classic.SessionStart:resume" },
			compacted,
		);

		expect(resumed.open).toEqual(pieces());
	});

	test("a second signal of the same family once a request is in flight starts a new window", () => {
		const streaming = sending(applyHistory(SEED, read(0)), {
			rows: [inputRow({ messages: 400 })],
		});
		const second = startWindow(START, streaming);

		expect(second.inFlight).toBeNull();
		expect(second.open).toEqual(pieces());
	});

	test("a second signal of the same family once the window has a measurement starts a new window", () => {
		const second = startWindow(START, baseline(HALF).window);

		expect(second.measure).toEqual(FRESH_UNREAD);
		expect(second.open).toEqual(pieces());
	});

	test("a request carrying fewer messages than the last response starts the window over", () => {
		const measured = measuredWindow({ messages: 400 }, 2000, 1000, {
			fingerprint: "toolu_OLD",
		});

		expect(
			beginRequest(measured, {
				index: 0,
				messageCount: MESSAGES_AT_ANCHOR - 1,
			}),
		).toBe("replaced");
		expect(
			beginRequest(measured, { index: 0, messageCount: MESSAGES_AT_ANCHOR }),
		).not.toBe("replaced");

		const restarted = startWindow(UNSEEN, measured);

		expect(restarted.measure).toEqual(FRESH_UNREAD);
		expect(restarted.replaced).toBe("toolu_OLD");
	});

	test("a window that has no response yet never counts a request as replaced", () => {
		expect(beginRequest(EMPTY, { index: 0, messageCount: 1 })).not.toBe(
			"replaced",
		);
	});
});

describe("the pooled ratio", () => {
	const ROW_CHARS = 3000;
	const POOLED: Ratio = { model: MODEL, tokens: 500, chars: 1000 };

	function interval(
		before: Window,
		ratio: Ratio,
		rowChars: number,
		inputTokens: number,
		model = MODEL,
	) {
		return step(before, ratio, {
			rows: [inputRow({ results: rowChars })],
			response: reply({ messages: 10 }),
			usage: usage(1100 + 100 + inputTokens, 100, model),
			fixed: 1000,
		});
	}

	const CLEAN_TOKENS = 1800;
	const PRIOR_CLEAN_TOKENS = 1000;

	test("a clean interval of enough characters adds its tokens and characters to the pool", () => {
		const base = baseline(POOLED);
		const after = interval(base.window, base.ratio, ROW_CHARS, CLEAN_TOKENS);

		expect(after.ratio).toEqual({
			model: MODEL,
			tokens: 500 + CLEAN_TOKENS,
			chars: 1000 + ROW_CHARS,
		});
	});

	test("an interval under the character minimum leaves the pool alone", () => {
		const base = baseline(POOLED);
		const after = interval(
			base.window,
			base.ratio,
			MIN_RATIO_INTERVAL_CHARS - 1,
			900,
		);

		expect(after.ratio).toEqual(POOLED);
	});

	test("an interval that carried no new tokens leaves the pool alone", () => {
		const base = baseline(POOLED);
		const after = interval(base.window, base.ratio, ROW_CHARS, 0);

		expect(after.ratio).toEqual(POOLED);
	});

	test("an interval with a row that failed to count leaves the pool alone", () => {
		const base = baseline(POOLED);
		const after = interval(
			taint(base.window),
			base.ratio,
			ROW_CHARS,
			CLEAN_TOKENS,
		);

		expect(after.ratio).toEqual(POOLED);
	});

	test("an interval with tokens beyond what its rows can carry leaves the pool alone", () => {
		const base = baseline(POOLED);
		const after = interval(
			base.window,
			base.ratio,
			ROW_CHARS,
			Math.ceil(CEILING_FACTOR * 0.5 * ROW_CHARS) + 500,
		);

		expect(after.ratio).toEqual(POOLED);
	});

	test("an interval where the window shrank leaves the pool alone", () => {
		const before = measuredWindow({ results: 6000 }, 7000, 1000);
		const after = step(before, POOLED, {
			rows: [inputRow({ results: ROW_CHARS })],
			response: reply({ messages: 10 }),
			usage: usage(6500, 100),
			fixed: 1000,
		});

		expect(after.ratio).toEqual(POOLED);
	});

	test("an interval whose model differs starts the pool over, and counts its own sample", () => {
		const base = baseline(POOLED);
		const small = interval(
			base.window,
			base.ratio,
			50,
			25,
			"claude-sonnet-4-6",
		);
		const large = interval(
			base.window,
			base.ratio,
			ROW_CHARS,
			PRIOR_CLEAN_TOKENS,
			"claude-sonnet-4-6",
		);

		expect(small.ratio).toEqual({
			model: "claude-sonnet-4-6",
			tokens: 0,
			chars: 0,
		});
		expect(large.ratio).toEqual({
			model: "claude-sonnet-4-6",
			tokens: PRIOR_CLEAN_TOKENS,
			chars: ROW_CHARS,
		});
	});

	test("an interval's own response is split at the ratio held before its sample", () => {
		const base = baseline(POOLED);
		const after = step(base.window, base.ratio, {
			rows: [inputRow({ results: ROW_CHARS })],
			response: reply({ messages: 400 }, { thinking: true }),
			usage: usage(1100 + 1000 + CLEAN_TOKENS, 1000),
			fixed: 1000,
		});

		expect(booksOf(after.window).tokens.thinking).toBe(800);
	});
});

describe("what the gauge draws from a window", () => {
	test("before any response, the figures are the fixed rows plus every estimate, with no measurement and no gap", () => {
		const kept = keepRow(taint(SEED), inputRow({ messages: 2000 }));
		const withHistory = applyHistory(kept, read(6000));

		expect(drawn(withHistory, HALF, 3000)).toEqual({
			used: 3000 + 1000 + 2000,
			measured: false,
			messages: tally({ messages: 1000, carried: 2000 }),
			gap: 0,
		});
	});

	test("before any response and with history unread, only the rows kept draw", () => {
		const kept = keepRow(SEED, inputRow({ messages: 2000 }, { read: 150 }));

		expect(drawn(kept, HALF, 3000)).toEqual({
			used: 3000 + 1000 + 150,
			measured: false,
			messages: tally({ messages: 1000, read: 150 }),
			gap: 0,
		});
	});

	test("before any response, the estimate uses the prior when no ratio was pooled", () => {
		const kept = keepRow(SEED, inputRow({ messages: 1000 }));

		expect(round(drawn(kept, NO_RATIO, 0).used)).toBe(
			round(PRIOR_TOKENS_PER_CHAR * 1000),
		);
	});

	test("an in-flight request's rows draw as estimates while a measurement holds", () => {
		const measured = measuredWindow({ results: 1000 }, 3300, 2000, {
			gap: 300,
		});
		const streaming = keepRow(
			sending(keepRow(measured, inputRow({ files: 400 })), {
				rows: [inputRow({ calls: 200 })],
				response: reply({ messages: 100 }, { served: { results: 60 } }),
			}),
			inputRow({ files: 200 }),
		);

		expect(drawn(streaming, HALF, 2000)).toEqual({
			used: 2000 + 1000 + 300 + 300 + 100 + 50 + 30,
			measured: true,
			messages: tally({
				results: 1030,
				files: 300,
				calls: 100,
				messages: 50,
			}),
			gap: 300,
		});
	});

	test("a measured window right after its response draws exactly the response's window", () => {
		const base = baseline(HALF);

		expect(drawn(base.window, base.ratio, 1000)).toEqual({
			used: 1100,
			measured: true,
			messages: tally({ messages: 100 }),
			gap: 0,
		});
	});
});

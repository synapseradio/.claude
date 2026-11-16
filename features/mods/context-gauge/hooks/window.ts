/** The gauge's calibration as pure transitions over one window: rows kept, requests begun and settled, history read, and what the window draws. */

import type { TurnUsage } from "claude-code";

import type {
	CountedId,
	HistoryRead,
	InFlight,
	OutputPieces,
	Pieces,
	Ratio,
	RowPieces,
	Tally,
	Window,
	WindowCause,
} from "../types";
import {
	CEILING_FACTOR,
	MIN_RATIO_INTERVAL_CHARS,
	PRIOR_TOKENS_PER_CHAR,
} from "./calibration";

const NO_TALLY: Tally = {
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
const IDS = Object.keys(NO_TALLY) as CountedId[];
const NO_PIECES: Pieces = { chars: NO_TALLY, media: NO_TALLY };
const NO_OUTPUT: OutputPieces = {
	visible: NO_PIECES,
	thinking: false,
	served: NO_PIECES,
};

type Books = { tokens: Tally; gap: number };
type Sample = { tokens: number; chars: number };

function tallyOf(figure: (id: CountedId) => number): Tally {
	const out: Record<CountedId, number> = { ...NO_TALLY };
	for (const id of IDS) out[id] = figure(id);
	return out;
}

function addTallies(a: Tally, b: Tally): Tally {
	return tallyOf((id) => a[id] + b[id]);
}

function sum(tally: Tally): number {
	return IDS.reduce((total, id) => total + tally[id], 0);
}

function addPieces(a: Pieces, b: Pieces): Pieces {
	return {
		chars: addTallies(a.chars, b.chars),
		media: addTallies(a.media, b.media),
	};
}

function estimate(pieces: Pieces, rate: number): Tally {
	return tallyOf((id) => rate * pieces.chars[id] + pieces.media[id]);
}

function rateOf(ratio: Ratio): number {
	return ratio.chars > 0 ? ratio.tokens / ratio.chars : PRIOR_TOKENS_PER_CHAR;
}

function windowSize(usage: TurnUsage): number {
	return (
		usage.input_tokens +
		usage.cache_read_input_tokens +
		usage.cache_creation_input_tokens +
		usage.output_tokens
	);
}

const FIRST_VERSION_KEEPING_THINKING: Readonly<Record<string, number>> = {
	opus: 405,
	sonnet: 406,
	haiku: 406,
};
const FAMILY_FIRST_ID =
	/^claude-(opus|sonnet|haiku)-(\d+)(?:-(\d{1,2})(?!\d))?/u;
const VERSION_FIRST_ID =
	/^claude-(\d+)(?:-(\d{1,2})(?!\d))?-(opus|sonnet|haiku)/u;

/** Whether a model drops earlier turns' thinking from the next request; a model the gauge does not know keeps it. */
function stripsThinking(model: string): boolean {
	const named = FAMILY_FIRST_ID.exec(model);
	const dated = VERSION_FIRST_ID.exec(model);
	const family = named?.[1] ?? dated?.[3];
	const major = named?.[2] ?? dated?.[1];
	const minor = named?.[3] ?? dated?.[2];
	if (family === undefined || major === undefined) return false;
	const keepsFrom = FIRST_VERSION_KEEPING_THINKING[family];
	if (keepsFrom === undefined) return false;
	return (
		Number.parseInt(major, 10) * 100 + Number.parseInt(minor ?? "0", 10) <
		keepsFrom
	);
}

function startedByPlanModeExit(cause: WindowCause): boolean {
	return (
		cause.signal === "session.append:plan_mode_exit" ||
		cause.signal === "prompt.attachment:plan_mode_exit"
	);
}

/** The rows a request in flight holds, joined to the rows kept beside it. */
function withFlightRows(open: Pieces, flight: InFlight): Pieces {
	return [flight.sent, flight.output.visible, flight.output.served].reduce(
		addPieces,
		open,
	);
}

/** Every piece the window kept that no request has anchored yet. */
function keptPieces(w: Window): Pieces {
	return w.inFlight === null ? w.open : withFlightRows(w.open, w.inFlight);
}

/** The window with an unsettled request's rows back among the rows kept. */
function reopen(w: Window, flight: InFlight): Window {
	return { ...w, open: withFlightRows(w.open, flight), inFlight: null };
}

/** The window a signal starts; a signal of the family a still-unmeasured window already has re-reads history and keeps the rows counted. */
export function startWindow(cause: WindowCause, current: Window): Window {
	const unread = {
		kind: "unmeasured",
		history: { kind: "unread", why: "not-yet" },
	} as const;
	if (
		current.measure.kind === "unmeasured" &&
		current.inFlight === null &&
		current.cause.family === cause.family
	) {
		return { ...current, cause, measure: unread };
	}
	return {
		cause,
		measure: unread,
		open: NO_PIECES,
		tainted: false,
		inFlight: null,
		fingerprint: null,
		replaced: current.fingerprint,
	};
}

/** The window with one more row kept: input for the next request, or a response row's output while its request is in flight. */
export function keepRow(w: Window, row: RowPieces): Window {
	const open = addPieces(w.open, row.input);
	const output = row.output;
	if (output === null) return { ...w, open };
	const flight = w.inFlight;
	if (flight === null) {
		return {
			...w,
			open: addPieces(addPieces(open, output.visible), output.served),
		};
	}
	return {
		...w,
		open,
		inFlight: {
			...flight,
			output: {
				visible: addPieces(flight.output.visible, output.visible),
				thinking: flight.output.thinking || output.thinking,
				served: addPieces(flight.output.served, output.served),
			},
		},
	};
}

/** The window with a main row's failure to count on record. */
export function taint(w: Window): Window {
	return { ...w, tainted: true };
}

/** The window with a history read applied; a measured window already counted its history. */
export function applyHistory(w: Window, read: HistoryRead | "failed"): Window {
	if (w.measure.kind === "measured") return w;
	const unread = (why: "failed" | "stale" | "truncated"): Window => ({
		...w,
		measure: { kind: "unmeasured", history: { kind: "unread", why } },
	});
	if (read === "failed") return unread("failed");
	if (read.truncated) return unread("truncated");
	if (
		read.fingerprint !== null &&
		read.fingerprint === w.replaced &&
		!startedByPlanModeExit(w.cause)
	) {
		return unread("stale");
	}
	const kept = keptPieces(w);
	return {
		...w,
		fingerprint: read.fingerprint ?? w.fingerprint,
		measure: {
			kind: "unmeasured",
			history: {
				kind: "read",
				carriedChars: Math.max(0, read.chars - sum(kept.chars)),
				carriedMedia: Math.max(0, read.media - sum(kept.media)),
			},
		},
	};
}

/** The window with a request in flight over the rows kept so far, or "replaced" when the request carries fewer messages than the last response left. */
export function beginRequest(
	w: Window,
	step: { index: number; messageCount: number },
): Window | "replaced" {
	if (
		w.measure.kind === "measured" &&
		step.messageCount < w.measure.anchor.messageCount
	) {
		return "replaced";
	}
	const settled = w.inFlight === null ? w : reopen(w, w.inFlight);
	return {
		...settled,
		open: NO_PIECES,
		inFlight: {
			sent: settled.open,
			output: NO_OUTPUT,
			index: step.index,
			messageCount: step.messageCount,
		},
	};
}

/** What a response's output tokens give each visible kind and thinking; output with no visible block to carry it goes to the gap. */
function withOutput(
	books: Books,
	output: OutputPieces,
	tokens: number,
	rate: number,
): Books {
	const visibleChars = sum(output.visible.chars);
	const visible = output.thinking
		? Math.min(tokens, rate * visibleChars)
		: tokens;
	const thinking = tokens - visible;
	return {
		tokens: tallyOf(
			(id) =>
				books.tokens[id] +
				(id === "thinking" ? thinking : 0) +
				(visibleChars > 0
					? (visible * output.visible.chars[id]) / visibleChars
					: 0),
		),
		gap: books.gap + (visibleChars > 0 ? 0 : visible),
	};
}

/** The books after a shrink: everything held, the gap included, loses the same share. */
function shrunk(books: Books, delta: number): Books {
	const held = sum(books.tokens) + books.gap;
	if (held <= 0) return books;
	const kept = Math.max(0, held + delta) / held;
	return {
		tokens: tallyOf((id) => books.tokens[id] * kept),
		gap: books.gap * kept,
	};
}

type Interval = {
	books: Books;
	delta: number;
	incoming: Pieces;
	clean: boolean;
};

/** What the response over `flight` adds to a window's books, read from the window before it. */
function intervalOf(
	w: Window,
	flight: InFlight,
	usage: TurnUsage,
	fixed: number,
): Interval {
	const measure = w.measure;
	const left = windowSize(usage) - usage.output_tokens;
	if (measure.kind === "unmeasured") {
		const history = measure.history;
		const carried: Pieces =
			history.kind === "read"
				? {
						chars: { ...NO_TALLY, carried: history.carriedChars },
						media: { ...NO_TALLY, carried: history.carriedMedia },
					}
				: NO_PIECES;
		return {
			books: { tokens: NO_TALLY, gap: 0 },
			delta: left - fixed,
			incoming: addPieces(flight.sent, carried),
			clean: !w.tainted && history.kind === "read",
		};
	}
	const retired =
		stripsThinking(usage.model) && flight.index === 0
			? measure.tokens.thinking
			: 0;
	return {
		books: {
			tokens: {
				...measure.tokens,
				thinking: measure.tokens.thinking - retired,
			},
			gap: measure.gap,
		},
		delta:
			left - measure.anchor.window - (fixed - measure.anchor.fixed) + retired,
		incoming: flight.sent,
		clean: !w.tainted,
	};
}

/** Where an interval's input tokens go: shares of the rows it carried up to the ceiling, the excess to reminders or the gap, and the sample it adds to the pooled ratio. */
function placeInput(
	interval: Interval,
	rate: number,
): { books: Books; sample: Sample | null } {
	const { books, delta, incoming, clean } = interval;
	if (delta < 0) return { books: shrunk(books, delta), sample: null };
	const estimates = estimate(incoming, rate);
	const carriable = sum(estimates);
	const placed = Math.min(delta, CEILING_FACTOR * carriable);
	const excess = delta - placed;
	const share = carriable > 0 ? placed / carriable : 0;
	const textChars = sum(incoming.chars);
	return {
		books: {
			tokens: tallyOf(
				(id) =>
					books.tokens[id] +
					share * estimates[id] +
					(clean && id === "reminders" ? excess : 0),
			),
			gap: books.gap + (clean ? 0 : excess),
		},
		sample:
			clean &&
			excess === 0 &&
			placed > 0 &&
			textChars >= MIN_RATIO_INTERVAL_CHARS
				? { tokens: (placed * rate * textChars) / carriable, chars: textChars }
				: null,
	};
}

/** The window and pooled ratio after a step resolves; a step with no usage, or one that ran server tools, anchors nothing and leaves its rows for the next request. */
export function settleRequest(
	w: Window,
	ratio: Ratio,
	settled: { usage: TurnUsage | null; fixed: number; served: boolean },
): { window: Window; ratio: Ratio } {
	const flight = w.inFlight;
	const { usage, fixed } = settled;
	if (flight === null) return { window: w, ratio };
	if (usage === null || settled.served) {
		return { window: reopen(w, flight), ratio };
	}
	const pooled: Ratio =
		ratio.model === usage.model
			? ratio
			: { model: usage.model, tokens: 0, chars: 0 };
	const rate = rateOf(pooled);
	const interval = intervalOf(w, flight, usage, fixed);
	const placed = placeInput(interval, rate);
	const books = withOutput(
		placed.books,
		flight.output,
		usage.output_tokens,
		rate,
	);
	return {
		window: {
			...w,
			measure: {
				kind: "measured",
				anchor: {
					window: windowSize(usage),
					fixed,
					messageCount: flight.messageCount,
				},
				tokens: books.tokens,
				gap: books.gap,
			},
			open: addPieces(w.open, flight.output.served),
			tainted: false,
			inFlight: null,
		},
		ratio:
			placed.sample === null
				? pooled
				: {
						model: pooled.model,
						tokens: pooled.tokens + placed.sample.tokens,
						chars: pooled.chars + placed.sample.chars,
					},
	};
}

/** What the gauge draws: the fixed rows, every message category at the last anchor or at the ratio's estimate, and the gap; a window with no anchor draws no gap. */
export function drawn(
	w: Window,
	ratio: Ratio,
	fixed: number,
): { used: number; measured: boolean; messages: Tally; gap: number } {
	const rate = rateOf(ratio);
	const flight = w.inFlight;
	const pending =
		flight === null
			? [w.open]
			: [w.open, flight.sent, flight.output.visible, flight.output.served];
	const estimated = pending.reduce(
		(held, pieces) => addTallies(held, estimate(pieces, rate)),
		NO_TALLY,
	);
	const measure = w.measure;
	const held: Tally =
		measure.kind === "measured"
			? measure.tokens
			: measure.history.kind === "read"
				? {
						...NO_TALLY,
						carried:
							rate * measure.history.carriedChars +
							measure.history.carriedMedia,
					}
				: NO_TALLY;
	const gap = measure.kind === "measured" ? measure.gap : 0;
	const messages = addTallies(held, estimated);
	return {
		used: fixed + sum(messages) + gap,
		measured: measure.kind === "measured",
		messages,
		gap,
	};
}

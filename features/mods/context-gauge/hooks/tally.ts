/** The empty figures every window and row starts from: a zero tally, zero pieces, and the category ids a tally holds. */

import type { CountedId, Pieces, Tally } from "../types";

export const NO_TALLY: Tally = {
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

export const IDS = Object.keys(NO_TALLY) as CountedId[];

export const NO_PIECES: Pieces = { chars: NO_TALLY, media: NO_TALLY };

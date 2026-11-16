import { describe, expect, test } from "claude-code/testing";

import { measureBlock } from "../hooks/measure";
import { stripsThinking } from "../hooks/window";

const SMALL = 1568;
const LARGE = 4784;

/** Each model id with the image cap and the thinking retirement the gauge gives it. */
const MODELS: readonly {
	id: string;
	imageCap: number;
	stripsThinking: boolean;
}[] = [
	{ id: "claude-sonnet-4-5", imageCap: SMALL, stripsThinking: true },
	{ id: "claude-sonnet-4-5-20250929", imageCap: SMALL, stripsThinking: true },
	{ id: "claude-haiku-4-5-20251001", imageCap: SMALL, stripsThinking: true },
	{ id: "claude-opus-4-1", imageCap: SMALL, stripsThinking: true },
	{ id: "claude-opus-4-20250514", imageCap: SMALL, stripsThinking: true },
	{ id: "claude-3-5-sonnet-20241022", imageCap: SMALL, stripsThinking: true },
	{ id: "claude-opus-4-5", imageCap: SMALL, stripsThinking: false },
	{ id: "claude-opus-4-7", imageCap: LARGE, stripsThinking: false },
	{ id: "claude-sonnet-4-6", imageCap: SMALL, stripsThinking: false },
	{ id: "claude-sonnet-5", imageCap: LARGE, stripsThinking: false },
	{ id: "claude-sonnet-5-5", imageCap: LARGE, stripsThinking: false },
	{ id: "claude-opus-5-5", imageCap: LARGE, stripsThinking: false },
	{ id: "claude-haiku-4-6", imageCap: SMALL, stripsThinking: false },
	{ id: "claude-haiku-5-5", imageCap: LARGE, stripsThinking: false },
	{ id: "claude-fable-5-2", imageCap: LARGE, stripsThinking: false },
	{
		id: "anthropic.claude-opus-4-7-v1:0",
		imageCap: LARGE,
		stripsThinking: false,
	},
	{
		id: "anthropic.claude-sonnet-4-5-20250929-v1:0",
		imageCap: SMALL,
		stripsThinking: false,
	},
	{
		id: "a-model-the-gauge-does-not-know",
		imageCap: SMALL,
		stripsThinking: false,
	},
	{ id: "", imageCap: SMALL, stripsThinking: false },
];

describe("what a model id decides", () => {
	for (const { id, imageCap, stripsThinking: strips } of MODELS) {
		test(`${id || "an empty id"} caps an image at ${imageCap} tokens`, () => {
			expect(measureBlock({ type: "image" }, id)).toEqual({ media: imageCap });
		});

		test(`${id || "an empty id"} ${strips ? "drops" : "keeps"} earlier thinking`, () => {
			expect(stripsThinking(id)).toBe(strips);
		});
	}
});

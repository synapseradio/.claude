import type { ApiContentBlock, ApiMessage } from "claude-code";
import { describe, expect, test } from "claude-code/testing";

import { historyOf } from "../hooks/history";
import { measureBlock } from "../hooks/measure";

const MODEL = "claude-opus-4-7";

const user = (...content: ApiMessage["content"]): ApiMessage => ({
	role: "user",
	content,
});
const assistant = (...content: ApiMessage["content"]): ApiMessage => ({
	role: "assistant",
	content,
});

const call = (id: string, name: string) => ({
	type: "tool_use",
	id,
	name,
	input: { prompt: "go" },
});
const result = (id: string, content: string) => ({
	type: "tool_result",
	tool_use_id: id,
	content,
});

function figure(block: ApiContentBlock): { chars: number; media: number } {
	const weight = measureBlock(block, MODEL);
	return {
		chars: "chars" in weight ? weight.chars : 0,
		media: "media" in weight ? weight.media : 0,
	};
}

describe("a resumed conversation's history", () => {
	test("every block, text and picture alike, adds its own weight to what is carried over", () => {
		const text: ApiContentBlock = { type: "text", text: "hello there" };
		const use = call("toolu_1", "Read");
		const output = result("toolu_1", "file body");
		const thought: ApiContentBlock = { type: "thinking", thinking: "hmm" };
		const image: ApiContentBlock = {
			type: "image",
			source: { type: "base64", media_type: "image/png", data: "" },
		};
		const read = historyOf(
			[user(text, image), assistant(use, thought), user(output)],
			MODEL,
		);
		const parts = [text, image, use, output, thought].map(figure);
		expect(read.chars).toBe(parts.reduce((sum, part) => sum + part.chars, 0));
		expect(read.media).toBe(parts.reduce((sum, part) => sum + part.media, 0));
		expect(read.media).toBeGreaterThan(0);
	});

	test("the same conversation is known as itself whether or not its thinking survives the read", () => {
		const answer = [call("toolu_first", "Read")];
		const withThinking = historyOf(
			[
				user({ type: "text", text: "start" }),
				assistant({ type: "thinking", thinking: "plan" }, ...answer),
			],
			MODEL,
		);
		const stripped = historyOf(
			[user({ type: "text", text: "start" }), assistant(...answer)],
			MODEL,
		);
		expect(withThinking.fingerprint).toBe(stripped.fingerprint);
		expect(stripped.fingerprint).not.toBeNull();
	});

	test("the same conversation is known as itself when context is prepended to its first message", () => {
		const tail = [assistant({ type: "text", text: "Sure, on it." })];
		const plain = historyOf(
			[user({ type: "text", text: "hi" }), ...tail],
			MODEL,
		);
		const withContext = historyOf(
			[
				user(
					{ type: "text", text: "<reminder>project notes</reminder>" },
					{ type: "text", text: "hi" },
				),
				...tail,
			],
			MODEL,
		);
		expect(withContext.fingerprint).toBe(plain.fingerprint);
		expect(plain.fingerprint).not.toBeNull();
	});

	test("conversations with different first answers are told apart", () => {
		const first = historyOf([assistant({ type: "text", text: "one" })], MODEL);
		const second = historyOf([assistant({ type: "text", text: "two" })], MODEL);
		expect(first.fingerprint).not.toBe(second.fingerprint);
	});

	test("a conversation with no answer yet is never taken for another", () => {
		const read = historyOf([user({ type: "text", text: "hi" })], MODEL);
		expect(read.fingerprint).toBeNull();
	});

	test("a read as long as the engine's 4096-message limit is marked as possibly cut off, a shorter one is not", () => {
		const message = user({ type: "text", text: "x" });
		expect(historyOf(Array(4096).fill(message), MODEL).truncated).toBe(true);
		expect(historyOf(Array(4095).fill(message), MODEL).truncated).toBe(false);
	});
});

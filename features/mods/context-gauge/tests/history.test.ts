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
	test("every block counts by its kind through the measure", () => {
		const text: ApiContentBlock = { type: "text", text: "hello there" };
		const use = call("toolu_1", "Read");
		const output = result("toolu_1", "file body");
		const thought: ApiContentBlock = { type: "thinking", thinking: "hmm" };
		const read = historyOf(
			[user(text), assistant(use, thought), user(output)],
			MODEL,
		);
		const parts = [text, use, output, thought].map(figure);
		expect(read.chars).toBe(parts.reduce((sum, part) => sum + part.chars, 0));
		expect(read.media).toBe(parts.reduce((sum, part) => sum + part.media, 0));
	});

	test("a picture counts as media tokens, as the measure gives them", () => {
		const image: ApiContentBlock = {
			type: "image",
			source: { type: "base64", media_type: "image/png", data: "" },
		};
		const read = historyOf([user(image)], MODEL);
		expect(read.media).toBe(figure(image).media);
		expect(read.chars).toBe(figure(image).chars);
	});

	test("the Agent calls it holds come back by id and no other call does", () => {
		const read = historyOf(
			[
				user({ type: "text", text: "start" }),
				assistant(call("toolu_a", "Agent"), call("toolu_r", "Read")),
				user(result("toolu_a", "done"), result("toolu_r", "body")),
				assistant(call("toolu_b", "Agent")),
			],
			MODEL,
		);
		expect(read.agentCalls).toEqual(["toolu_a", "toolu_b"]);
	});

	test("its fingerprint is the first assistant call's id, skipping thinking", () => {
		const read = historyOf(
			[
				user({ type: "text", text: "start" }),
				assistant(
					{ type: "thinking", thinking: "plan" },
					call("toolu_first", "Read"),
				),
				assistant(call("toolu_second", "Read")),
			],
			MODEL,
		);
		expect(read.fingerprint).toBe("toolu_first");
	});

	test("its fingerprint stays when context is prepended to the first message", () => {
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

	test("a different first answer gives a different fingerprint", () => {
		const first = historyOf([assistant({ type: "text", text: "one" })], MODEL);
		const second = historyOf([assistant({ type: "text", text: "two" })], MODEL);
		expect(first.fingerprint).not.toBe(second.fingerprint);
	});

	test("a conversation with no assistant block has no fingerprint", () => {
		const read = historyOf([user({ type: "text", text: "hi" })], MODEL);
		expect(read.fingerprint).toBeNull();
	});

	test("a read of 4096 messages is marked truncated and a shorter one is not", () => {
		const message = user({ type: "text", text: "x" });
		expect(historyOf(Array(4096).fill(message), MODEL).truncated).toBe(true);
		expect(historyOf(Array(4095).fill(message), MODEL).truncated).toBe(false);
	});
});

/// <reference lib="esnext.typedarrays" />
import type { ApiContentBlock } from "claude-code";
import { describe, expect, test } from "claude-code/testing";

import {
	PDF_TOKENS_PER_PAGE,
	PRIOR_TOKENS_PER_CHAR,
} from "../hooks/calibration";
import { measureBlock } from "../hooks/measure";

const OLD_MODEL = "claude-sonnet-4-5";
const NEW_MODEL = "claude-opus-4-7";
const NEWER_MODEL = "claude-sonnet-5-5";

const OLD_CAP = 1568;
const NEW_CAP = 4784;

function ascii(text: string): number[] {
	return [...text].map((char) => char.charCodeAt(0));
}

function bytes(parts: readonly (readonly number[])[]): Uint8Array {
	return Uint8Array.from(parts.flat());
}

function be(value: number, size: number): number[] {
	return Array.from(
		{ length: size },
		(_, index) => Math.floor(value / 256 ** (size - 1 - index)) % 256,
	);
}

function le(value: number, size: number): number[] {
	return be(value, size).reverse();
}

function png(width: number, height: number): string {
	return bytes([
		[0x89, ...ascii("PNG"), 0x0d, 0x0a, 0x1a, 0x0a],
		be(13, 4),
		ascii("IHDR"),
		be(width, 4),
		be(height, 4),
	]).toBase64();
}

function gif(width: number, height: number): string {
	return bytes([ascii("GIF89a"), le(width, 2), le(height, 2)]).toBase64();
}

function jpeg(width: number, height: number): string {
	return bytes([
		[0xff, 0xd8],
		[0xff, 0xe1],
		be(8, 2),
		[0, 0, 0, 0, 0, 0],
		[0xff, 0xc0],
		be(8, 2),
		[8],
		be(height, 2),
		be(width, 2),
	]).toBase64();
}

function webpExtended(width: number, height: number): string {
	return bytes([
		ascii("RIFF"),
		[0, 0, 0, 0],
		ascii("WEBP"),
		ascii("VP8X"),
		[10, 0, 0, 0],
		[0, 0, 0, 0],
		le(width - 1, 3),
		le(height - 1, 3),
	]).toBase64();
}

function webpLossless(width: number, height: number): string {
	return bytes([
		ascii("RIFF"),
		[0, 0, 0, 0],
		ascii("WEBP"),
		ascii("VP8L"),
		[5, 0, 0, 0],
		[0x2f],
		le(width - 1 + (height - 1) * 2 ** 14, 4),
		[0, 0, 0, 0, 0],
	]).toBase64();
}

function image(data: string, mediaType = "image/png"): ApiContentBlock {
	return {
		type: "image",
		source: { type: "base64", media_type: mediaType, data },
	};
}

function pdf(pages: number): ApiContentBlock {
	const body = [
		"%PDF-1.4",
		"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
		`2 0 obj << /Type /Pages /Count ${pages} >> endobj`,
		...Array.from(
			{ length: pages },
			(_, index) => `${index + 3} 0 obj << /Type /Page /Parent 2 0 R >> endobj`,
		),
	].join("\n");
	return {
		type: "document",
		source: {
			type: "base64",
			media_type: "application/pdf",
			data: Uint8Array.from(ascii(body)).toBase64(),
		},
	};
}

describe("measureBlock", () => {
	describe("text-like blocks", () => {
		test("a text block measures its characters", () => {
			expect(measureBlock({ type: "text", text: "hello" }, NEW_MODEL)).toEqual({
				chars: 5,
			});
		});

		test("a tool call measures its name plus its JSON input", () => {
			const block = {
				type: "tool_use",
				id: "toolu_1",
				name: "Bash",
				input: { command: "ls" },
			};
			expect(measureBlock(block, NEW_MODEL)).toEqual({
				chars: "Bash".length + JSON.stringify({ command: "ls" }).length,
			});
		});

		test("a server tool call and an MCP tool call measure like a tool call", () => {
			const input = { query: "weather" };
			const expected = {
				chars: "web_search".length + JSON.stringify(input).length,
			};
			expect(
				measureBlock(
					{ type: "server_tool_use", id: "srv_1", name: "web_search", input },
					NEW_MODEL,
				),
			).toEqual(expected);
			expect(
				measureBlock(
					{ type: "mcp_tool_use", id: "mcp_1", name: "web_search", input },
					NEW_MODEL,
				),
			).toEqual(expected);
		});

		test("a tool result with text measures that text", () => {
			expect(
				measureBlock(
					{ type: "tool_result", tool_use_id: "toolu_1", content: "abcdef" },
					NEW_MODEL,
				),
			).toEqual({ chars: 6 });
		});

		test("a tool result of text blocks adds their characters", () => {
			const block = {
				type: "tool_result",
				tool_use_id: "toolu_1",
				content: [
					{ type: "text", text: "abc" },
					{ type: "text", text: "defg" },
				],
			};
			expect(measureBlock(block, NEW_MODEL)).toEqual({ chars: 7 });
		});

		test("a search result measures its text blocks, title and source", () => {
			const block = {
				type: "search_result",
				title: "Title",
				source: "https://example.test/a",
				content: [{ type: "text", text: "body" }],
			};
			expect(measureBlock(block, NEW_MODEL)).toEqual({
				chars: "Title".length + "https://example.test/a".length + "body".length,
			});
		});

		test("a document with text source measures that text", () => {
			const block = {
				type: "document",
				source: {
					type: "text",
					media_type: "text/plain",
					data: "twelve chars",
				},
			};
			expect(measureBlock(block, NEW_MODEL)).toEqual({ chars: 12 });
		});

		test("a thinking block measures its text, and a redacted one adds nothing", () => {
			expect(
				measureBlock({ type: "thinking", thinking: "hmm" }, NEW_MODEL),
			).toEqual({ chars: 3 });
			expect(
				measureBlock({ type: "redacted_thinking", data: "opaque" }, NEW_MODEL),
			).toEqual({ chars: 0 });
		});

		test("a compaction block measures its text", () => {
			expect(
				measureBlock({ type: "compaction", content: "summary" }, NEW_MODEL),
			).toEqual({ chars: 7 });
		});

		test("a server-run result measures the JSON of its content", () => {
			const content = [{ type: "web_search_result", title: "x", url: "u" }];
			expect(
				measureBlock(
					{ type: "web_search_tool_result", tool_use_id: "srv_1", content },
					NEW_MODEL,
				),
			).toEqual({ chars: JSON.stringify(content[0]).length });
		});

		test("a block of a kind nobody listed measures its JSON length, never 0", () => {
			const block = { type: "future_kind", payload: { a: 1, b: "two" } };
			expect(measureBlock(block, NEW_MODEL)).toEqual({
				chars: JSON.stringify(block).length,
			});
		});

		test("a tool reference measures its JSON length", () => {
			const block = { type: "tool_reference", tool_name: "mcp__x__y" };
			expect(measureBlock(block, NEW_MODEL)).toEqual({
				chars: JSON.stringify(block).length,
			});
		});

		test("a block of a known kind that lacks its usual field measures its JSON length", () => {
			const block = { type: "text", content: "oddly shaped" };
			expect(measureBlock(block, NEW_MODEL)).toEqual({
				chars: JSON.stringify(block).length,
			});
		});
	});

	describe("images", () => {
		test("a 1000 by 1000 PNG measures 1,296 tokens", () => {
			expect(measureBlock(image(png(1000, 1000)), NEW_MODEL)).toEqual({
				media: 1296,
			});
		});

		test("a GIF is sized from its header", () => {
			expect(measureBlock(image(gif(280, 56), "image/gif"), NEW_MODEL)).toEqual(
				{ media: 10 * 2 },
			);
		});

		test("a JPEG is sized from its frame header past other segments", () => {
			expect(
				measureBlock(image(jpeg(560, 280), "image/jpeg"), NEW_MODEL),
			).toEqual({ media: 20 * 10 });
		});

		test("an extended WebP is sized from its header", () => {
			expect(
				measureBlock(image(webpExtended(560, 28), "image/webp"), NEW_MODEL),
			).toEqual({ media: 20 });
		});

		test("a lossless WebP is sized from its header", () => {
			expect(
				measureBlock(image(webpLossless(280, 280), "image/webp"), NEW_MODEL),
			).toEqual({ media: 100 });
		});

		test("a large image stops at the cap of Claude 4.7 and later models", () => {
			expect(measureBlock(image(png(4000, 4000)), NEW_MODEL)).toEqual({
				media: NEW_CAP,
			});
			expect(measureBlock(image(png(4000, 4000)), NEWER_MODEL)).toEqual({
				media: NEW_CAP,
			});
		});

		test("a large image stops at the lower cap on earlier models", () => {
			expect(measureBlock(image(png(4000, 4000)), OLD_MODEL)).toEqual({
				media: OLD_CAP,
			});
		});

		test("an image with no readable size takes its model's cap", () => {
			expect(measureBlock(image("not an image"), NEW_MODEL)).toEqual({
				media: NEW_CAP,
			});
			expect(measureBlock(image("not an image"), OLD_MODEL)).toEqual({
				media: OLD_CAP,
			});
		});

		test("an image a tool result holds counts as media", () => {
			const block = {
				type: "tool_result",
				tool_use_id: "toolu_1",
				content: [image(png(1000, 1000))],
			};
			expect(measureBlock(block, NEW_MODEL)).toEqual({ media: 1296 });
		});

		test("a tool result holding an image and text reports tokens for both", () => {
			const block = {
				type: "tool_result",
				tool_use_id: "toolu_1",
				content: [
					image(png(1000, 1000)),
					{ type: "text", text: "x".repeat(100) },
				],
			};
			expect(measureBlock(block, NEW_MODEL)).toEqual({
				media: 1296 + 100 * PRIOR_TOKENS_PER_CHAR,
			});
		});
	});

	describe("PDFs", () => {
		test("a PDF measures its pages times the per-page tokens", () => {
			expect(measureBlock(pdf(3), NEW_MODEL)).toEqual({
				media: 3 * PDF_TOKENS_PER_PAGE,
			});
		});

		test("a PDF whose pages cannot be counted measures one page", () => {
			const block = {
				type: "document",
				source: {
					type: "base64",
					media_type: "application/pdf",
					data: Uint8Array.from(ascii("garbled")).toBase64(),
				},
			};
			expect(measureBlock(block, NEW_MODEL)).toEqual({
				media: PDF_TOKENS_PER_PAGE,
			});
		});
	});
});

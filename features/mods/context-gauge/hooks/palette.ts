/** The gauge's categories in bar order, and the Open Color swatch and texture each draws with. */

/** One Open Color shade: its hue, its index 0 to 9, and its hex. */
export type Swatch = { hue: string; shade: number; hex: string };

/** The gauge's categories, in the order the bar and the legend draw them. */
export const BAR_ORDER = [
	"system",
	"mcp",
	"agents",
	"memory",
	"skills",
	"summary",
	"hooks",
	"attachments",
	"user",
	"commands",
	"deliveries",
	"calls",
	"results",
	"read",
	"thinking",
	"replies",
	"unattributed",
	"other",
] as const;

export type CategoryId = (typeof BAR_ORDER)[number];

/** The pixel patterns a bar segment fills its band with. */
export const TEXTURES = ["solid", "diagonal", "vertical", "dots"] as const;

export type Texture = (typeof TEXTURES)[number];

/** How a category draws: its colour and its texture. */
export type CategoryStyle = { swatch: Swatch; texture: Texture };

// Open Color 1.9.1, https://github.com/yeun/open-color/blob/v1.9.1/open-color.json
const PINK: Swatch = { hue: "pink", shade: 6, hex: "#e64980" };
const GRAPE: Swatch = { hue: "grape", shade: 7, hex: "#ae3ec9" };
const LIME: Swatch = { hue: "lime", shade: 9, hex: "#5c940d" };
const CYAN: Swatch = { hue: "cyan", shade: 7, hex: "#1098ad" };
const INDIGO: Swatch = { hue: "indigo", shade: 6, hex: "#4c6ef5" };

/** Each category's colour and texture: colours cycle every five categories, textures every four. */
export const CATEGORY_STYLES: Readonly<Record<CategoryId, CategoryStyle>> = {
	system: { swatch: PINK, texture: "solid" },
	mcp: { swatch: GRAPE, texture: "diagonal" },
	agents: { swatch: LIME, texture: "vertical" },
	memory: { swatch: CYAN, texture: "dots" },
	skills: { swatch: INDIGO, texture: "solid" },
	summary: { swatch: PINK, texture: "diagonal" },
	hooks: { swatch: GRAPE, texture: "vertical" },
	attachments: { swatch: LIME, texture: "dots" },
	user: { swatch: CYAN, texture: "solid" },
	commands: { swatch: INDIGO, texture: "diagonal" },
	deliveries: { swatch: PINK, texture: "vertical" },
	calls: { swatch: GRAPE, texture: "dots" },
	results: { swatch: LIME, texture: "solid" },
	read: { swatch: CYAN, texture: "diagonal" },
	thinking: { swatch: INDIGO, texture: "vertical" },
	replies: { swatch: PINK, texture: "dots" },
	unattributed: { swatch: GRAPE, texture: "solid" },
	other: { swatch: LIME, texture: "diagonal" },
};

/** Free space, the window's unused remainder. */
export const FREE_SWATCH: Swatch = { hue: "gray", shade: 6, hex: "#868e96" };

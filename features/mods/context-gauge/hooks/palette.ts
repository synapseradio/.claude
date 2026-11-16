/** The gauge's categories in bar order, and the swatch and texture each draws with in the light and the dark palette. */

/** One colour, as a hex. */
export type Swatch = { hex: string };

/** The gauge's categories, in the order the bar and the legend draw them. */
export const BAR_ORDER = [
	"system",
	"mcp",
	"agentList",
	"memory",
	"skills",
	"carried",
	"summary",
	"hooks",
	"plugins",
	"reminders",
	"files",
	"messages",
	"scripts",
	"tasks",
	"relayed",
	"commands",
	"calls",
	"writes",
	"results",
	"read",
	"prompts",
	"agents",
	"thinking",
	"uncounted",
	"gap",
	"other",
] as const;

export type CategoryId = (typeof BAR_ORDER)[number];

/** A run of bar cells drawn as one category, or as the window's free space. */
export type BarRun = { id: CategoryId | "free"; cells: number };

/** The pixel patterns a bar segment fills its band with. */
export const TEXTURES = [
	"solid",
	"diagonal",
	"vertical",
	"dots",
	"checker",
] as const;

export type Texture = (typeof TEXTURES)[number];

/** How a category draws: its colour and its texture. */
export type CategoryStyle = { swatch: Swatch; texture: Texture };

/** The palettes the gauge draws in: for a light terminal and for a dark one. */
export type Theme = "light" | "dark";

/** Each theme's category colours and textures; the four repeating textures cycle across the categories but carried, which alone draws checker, so bar neighbours differ in texture. */
export const PALETTES: Readonly<
	Record<Theme, Readonly<Record<CategoryId, CategoryStyle>>>
> = {
	light: {
		system: { swatch: { hex: "#114488" }, texture: "solid" },
		mcp: { swatch: { hex: "#cc3333" }, texture: "diagonal" },
		agentList: { swatch: { hex: "#0000dd" }, texture: "vertical" },
		memory: { swatch: { hex: "#9977dd" }, texture: "dots" },
		skills: { swatch: { hex: "#991100" }, texture: "solid" },
		carried: { swatch: { hex: "#220099" }, texture: "checker" },
		summary: { swatch: { hex: "#6655cc" }, texture: "diagonal" },
		hooks: { swatch: { hex: "#559911" }, texture: "vertical" },
		plugins: { swatch: { hex: "#dd0088" }, texture: "dots" },
		reminders: { swatch: { hex: "#5511aa" }, texture: "solid" },
		files: { swatch: { hex: "#1199bb" }, texture: "diagonal" },
		messages: { swatch: { hex: "#771166" }, texture: "vertical" },
		scripts: { swatch: { hex: "#cc44ff" }, texture: "dots" },
		tasks: { swatch: { hex: "#660000" }, texture: "solid" },
		relayed: { swatch: { hex: "#0066aa" }, texture: "diagonal" },
		commands: { swatch: { hex: "#886644" }, texture: "vertical" },
		calls: { swatch: { hex: "#ff33cc" }, texture: "dots" },
		writes: { swatch: { hex: "#007777" }, texture: "solid" },
		results: { swatch: { hex: "#ff5500" }, texture: "diagonal" },
		read: { swatch: { hex: "#aa11aa" }, texture: "vertical" },
		prompts: { swatch: { hex: "#cc7788" }, texture: "dots" },
		agents: { swatch: { hex: "#000066" }, texture: "solid" },
		thinking: { swatch: { hex: "#005500" }, texture: "diagonal" },
		uncounted: { swatch: { hex: "#8800ff" }, texture: "vertical" },
		gap: { swatch: { hex: "#007700" }, texture: "dots" },
		other: { swatch: { hex: "#554444" }, texture: "solid" },
	},
	dark: {
		system: { swatch: { hex: "#bb9966" }, texture: "solid" },
		mcp: { swatch: { hex: "#3366dd" }, texture: "diagonal" },
		agentList: { swatch: { hex: "#cccc66" }, texture: "vertical" },
		memory: { swatch: { hex: "#cc2288" }, texture: "dots" },
		skills: { swatch: { hex: "#33aaff" }, texture: "solid" },
		carried: { swatch: { hex: "#77ff77" }, texture: "checker" },
		summary: { swatch: { hex: "#ff0066" }, texture: "diagonal" },
		hooks: { swatch: { hex: "#ddbbff" }, texture: "vertical" },
		plugins: { swatch: { hex: "#889900" }, texture: "dots" },
		reminders: { swatch: { hex: "#8866bb" }, texture: "solid" },
		files: { swatch: { hex: "#ffbb99" }, texture: "diagonal" },
		messages: { swatch: { hex: "#aa66ff" }, texture: "vertical" },
		scripts: { swatch: { hex: "#dd3300" }, texture: "dots" },
		tasks: { swatch: { hex: "#99ffff" }, texture: "solid" },
		relayed: { swatch: { hex: "#ff9900" }, texture: "diagonal" },
		commands: { swatch: { hex: "#33aa99" }, texture: "vertical" },
		calls: { swatch: { hex: "#aa00ff" }, texture: "dots" },
		writes: { swatch: { hex: "#007799" }, texture: "solid" },
		results: { swatch: { hex: "#66cc33" }, texture: "diagonal" },
		read: { swatch: { hex: "#dd88aa" }, texture: "vertical" },
		prompts: { swatch: { hex: "#ffff00" }, texture: "dots" },
		agents: { swatch: { hex: "#ff66ff" }, texture: "solid" },
		thinking: { swatch: { hex: "#008833" }, texture: "diagonal" },
		uncounted: { swatch: { hex: "#77ddcc" }, texture: "vertical" },
		gap: { swatch: { hex: "#ee55bb" }, texture: "dots" },
		other: { swatch: { hex: "#aa6666" }, texture: "solid" },
	},
};

/** Free space, the window's unused remainder, in both palettes. */
export const FREE_SWATCH: Swatch = { hex: "#868e96" };

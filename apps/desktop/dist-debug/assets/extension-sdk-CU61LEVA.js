import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Di as notify, Ia as Codicon, La as Button, O as Badge, P as Switch, Ra as cn, ao as require_jsx_runtime, jt as Textarea, ki as useI18n, ni as Input, oo as require_react } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/app/extension-sdk/template-preview.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
function TemplatePreview({ files, manifest }) {
	const [selectedFile, setSelectedFile] = (0, import_react.useState)(files[0]?.path || "");
	const [expandedDirs, setExpandedDirs] = (0, import_react.useState)(new Set([""]));
	const activeFile = files.find((f) => f.path === selectedFile);
	const tree = buildTree(files);
	function toggleDir(path) {
		setExpandedDirs((prev) => {
			const next = new Set(prev);
			if (next.has(path)) next.delete(path);
			else next.add(path);
			return next;
		});
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-3",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center gap-3 text-xs text-muted-foreground",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
					className: "flex items-center gap-1",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "file",
							size: "0.75rem"
						}),
						files.length,
						" files"
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
					className: "flex items-center gap-1",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						name: "package",
						size: "0.75rem"
					}), manifest.name || "Unnamed"]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Badge, {
					className: "text-[0.55rem]",
					variant: "outline",
					children: ["v", manifest.version]
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid grid-cols-[1fr_2fr] gap-3",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "rounded-lg border border-(--ui-stroke-tertiary) px-2 py-1.5",
				children: tree.map((node) => renderTreeNode(node, "", selectedFile, setSelectedFile, expandedDirs, toggleDir))
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "rounded-lg border border-(--ui-stroke-tertiary) overflow-hidden",
				children: activeFile ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-3 py-1.5",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "flex items-center gap-1.5 text-xs text-muted-foreground",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: getIconForFile(activeFile.path),
							size: "0.75rem"
						}), activeFile.path]
					})
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
					className: "overflow-x-auto p-3 font-mono text-[0.65rem] leading-relaxed text-foreground/80 [scrollbar-width:thin]",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("code", { children: activeFile.content })
				})] }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid min-h-32 place-items-center text-xs text-muted-foreground",
					children: "Select a file to preview"
				})
			})]
		})]
	});
}
function buildTree(files) {
	const root = [];
	for (const file of files) {
		const parts = file.path.split("/");
		let current = root;
		for (let i = 0; i < parts.length; i++) {
			const isLast = i === parts.length - 1;
			const name = parts[i];
			const fullPath = parts.slice(0, i + 1).join("/");
			if (isLast) current.push({
				name,
				path: fullPath,
				type: "file"
			});
			else {
				let dir = current.find((n) => n.type === "directory" && n.name === name);
				if (!dir) {
					dir = {
						name,
						path: fullPath,
						type: "directory",
						children: []
					};
					current.push(dir);
				}
				current = dir.children;
			}
		}
	}
	return root;
}
function renderTreeNode(node, parentPath, selectedFile, onSelect, expandedDirs, onToggleDir) {
	const fullPath = parentPath ? `${parentPath}/${node.name}` : node.name;
	const isExpanded = expandedDirs.has(fullPath);
	if (node.type === "directory") return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		className: "flex w-full items-center gap-1 rounded-sm px-1 py-0.5 text-left text-xs hover:bg-accent/60",
		onClick: () => onToggleDir(fullPath),
		type: "button",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
				className: "text-muted-foreground transition-transform",
				name: "chevron-right",
				size: "0.6rem",
				style: { transform: isExpanded ? "rotate(90deg)" : void 0 }
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
				className: "text-amber-500",
				name: "folder",
				size: "0.75rem"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "truncate",
				children: node.name
			})
		]
	}), isExpanded && node.children && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "ml-3 border-l border-(--ui-stroke-tertiary) pl-1",
		children: node.children.map((child) => renderTreeNode(child, fullPath, selectedFile, onSelect, expandedDirs, onToggleDir))
	})] }, fullPath);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		className: cn("flex w-full items-center gap-1.5 rounded-sm px-1 py-0.5 text-left text-xs transition-colors", selectedFile === fullPath ? "bg-accent text-accent-foreground" : "hover:bg-accent/60"),
		onClick: () => onSelect(fullPath),
		type: "button",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
			className: "text-sky-500",
			name: getIconForFile(node.name),
			size: "0.75rem"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: "truncate",
			children: node.name
		})]
	}, fullPath);
}
function getIconForFile(filename) {
	if (filename.endsWith(".ts") || filename.endsWith(".tsx")) return "code";
	if (filename.endsWith(".json")) return "json";
	if (filename.endsWith(".md")) return "note";
	if (filename.endsWith(".yaml") || filename.endsWith(".yml")) return "settings";
	return "file";
}
//#endregion
//#region src/app/extension-sdk/index.tsx
var TEMPLATES = [
	{
		id: "basic-tool",
		name: "Basic Tool",
		description: "A simple tool extension with a single command handler",
		icon: "code",
		category: "Tools",
		difficulty: "beginner",
		files: [{
			path: "index.ts",
			content: "export function register(ctx: ExtensionContext) {\n  ctx.registerTool({\n    name: \"hello\",\n    description: \"A simple hello world tool\",\n    handler: async (args) => {\n      return `Hello, ${args.name || \"world\"}!`;\n    }\n  });\n}"
		}, {
			path: "manifest.json",
			content: "{\n  \"name\": \"my-extension\",\n  \"version\": \"1.0.0\",\n  \"description\": \"My first AetherOS extension\",\n  \"main\": \"index.ts\"\n}"
		}],
		manifest: {
			name: "my-extension",
			version: "1.0.0",
			description: "My first AetherOS extension",
			author: "",
			license: "MIT",
			main: "index.ts",
			permissions: [],
			dependencies: [],
			tools: ["hello"],
			hooks: []
		}
	},
	{
		id: "mcp-server",
		name: "MCP Server",
		description: "Model Context Protocol server extension with stdio transport",
		icon: "server",
		category: "MCP",
		difficulty: "intermediate",
		files: [{
			path: "server.ts",
			content: "import { McpServer } from \"@aetheros/mcp\";\n\nconst server = new McpServer({\n  name: \"my-mcp-server\",\n  version: \"1.0.0\"\n});\n\nserver.tool(\"greet\", { name: z.string() }, async ({ name }) => ({\n  content: [{ type: \"text\", text: `Hello ${name}!` }]\n}));\n\nserver.listen({ transport: \"stdio\" });"
		}, {
			path: "manifest.json",
			content: "{\n  \"name\": \"my-mcp-server\",\n  \"version\": \"1.0.0\",\n  \"type\": \"mcp\",\n  \"main\": \"server.ts\"\n}"
		}],
		manifest: {
			name: "my-mcp-server",
			version: "1.0.0",
			description: "A basic MCP server extension",
			author: "",
			license: "MIT",
			main: "server.ts",
			permissions: [],
			dependencies: ["@aetheros/mcp"],
			tools: ["greet"],
			hooks: []
		}
	},
	{
		id: "hook-provider",
		name: "Hook Provider",
		description: "Extension that hooks into lifecycle events",
		icon: "zap",
		category: "Lifecycle",
		difficulty: "intermediate",
		files: [{
			path: "index.ts",
			content: "export function register(ctx: ExtensionContext) {\n  ctx.on(\"session:start\", async (session) => {\n    console.log(\"Session started:\", session.id);\n  });\n\n  ctx.on(\"tool:before\", async (toolCall) => {\n    console.log(\"Tool called:\", toolCall.name);\n  });\n\n  ctx.on(\"tool:after\", async (result) => {\n    console.log(\"Tool result:\", result);\n  });\n}"
		}, {
			path: "manifest.json",
			content: "{\n  \"name\": \"hook-provider\",\n  \"version\": \"1.0.0\",\n  \"main\": \"index.ts\"\n}"
		}],
		manifest: {
			name: "hook-provider",
			version: "1.0.0",
			description: "Lifecycle hook extension",
			author: "",
			license: "MIT",
			main: "index.ts",
			permissions: [],
			dependencies: [],
			tools: [],
			hooks: [
				"session:start",
				"tool:before",
				"tool:after"
			]
		}
	},
	{
		id: "ui-panel",
		name: "UI Panel",
		description: "Custom UI panel with React component for the desktop app",
		icon: "browser",
		category: "UI",
		difficulty: "advanced",
		files: [
			{
				path: "panel.tsx",
				content: "import { useState } from \"react\";\n\nexport function MyPanel() {\n  const [count, setCount] = useState(0);\n\n  return (\n    <div>\n      <h2>My Extension Panel</h2>\n      <button onClick={() => setCount(c => c + 1)}>\n        Count: {count}\n      </button>\n    </div>\n  );\n}"
			},
			{
				path: "index.ts",
				content: "import { registerPanel } from \"@aetheros/panel\";\n\nregisterPanel({\n  id: \"my-panel\",\n  title: \"My Panel\",\n  component: () => import(\"./panel\"),\n  position: \"right\"\n});"
			},
			{
				path: "manifest.json",
				content: "{\n  \"name\": \"ui-panel\",\n  \"version\": \"1.0.0\",\n  \"type\": \"ui\",\n  \"main\": \"index.ts\"\n}"
			}
		],
		manifest: {
			name: "ui-panel",
			version: "1.0.0",
			description: "Custom UI panel extension",
			author: "",
			license: "MIT",
			main: "index.ts",
			permissions: ["ui:panel"],
			dependencies: ["@aetheros/panel"],
			tools: [],
			hooks: []
		}
	},
	{
		id: "provider-adapter",
		name: "Provider Adapter",
		description: "Model provider adapter for custom inference backends",
		icon: "cloud",
		category: "Providers",
		difficulty: "advanced",
		files: [{
			path: "provider.ts",
			content: "import { ProviderAdapter } from \"@aetheros/providers\";\n\nexport class MyProvider extends ProviderAdapter {\n  constructor(config: ProviderConfig) {\n    super(config);\n    this.name = \"My Provider\";\n  }\n\n  async complete(messages: Message[]): Promise<CompletionResult> {\n    // Custom inference logic\n    return { content: \"...\" };\n  }\n}"
		}, {
			path: "manifest.json",
			content: "{\n  \"name\": \"my-provider\",\n  \"version\": \"1.0.0\",\n  \"type\": \"provider\",\n  \"main\": \"provider.ts\"\n}"
		}],
		manifest: {
			name: "my-provider",
			version: "1.0.0",
			description: "Custom model provider adapter",
			author: "",
			license: "MIT",
			main: "provider.ts",
			permissions: ["network:http"],
			dependencies: ["@aetheros/providers"],
			tools: [],
			hooks: []
		}
	},
	{
		id: "skill-pack",
		name: "Skill Pack",
		description: "Bundle multiple skills into an installable extension",
		icon: "book",
		category: "Skills",
		difficulty: "beginner",
		files: [
			{
				path: "skills/hello.skill.md",
				content: "---\nname: hello\nversion: 1.0.0\n---\n\nA simple greeting skill."
			},
			{
				path: "index.ts",
				content: "export function register(ctx: ExtensionContext) {\n  ctx.registerSkills([\n    { name: \"hello\", path: \"./skills/hello.skill.md\" }\n  ]);\n}"
			},
			{
				path: "manifest.json",
				content: "{\n  \"name\": \"skill-pack\",\n  \"version\": \"1.0.0\",\n  \"type\": \"skills\",\n  \"main\": \"index.ts\"\n}"
			}
		],
		manifest: {
			name: "skill-pack",
			version: "1.0.0",
			description: "Bundle of reusable skills",
			author: "",
			license: "MIT",
			main: "index.ts",
			permissions: [],
			dependencies: [],
			tools: [],
			hooks: []
		}
	}
];
var INITIAL_MANIFEST = {
	name: "",
	version: "1.0.0",
	description: "",
	author: "",
	license: "MIT",
	main: "index.ts",
	permissions: [],
	dependencies: [],
	tools: [],
	hooks: []
};
var DIFFICULTY_COLORS = {
	beginner: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
	intermediate: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
	advanced: "bg-red-500/10 text-red-600 dark:text-red-400"
};
function ExtensionSdkView() {
	const { t } = useI18n();
	const [state, setState] = (0, import_react.useState)({
		step: "template",
		template: null,
		manifest: INITIAL_MANIFEST,
		outputDir: "~/aetheros/extensions",
		devMode: false,
		hotReload: false
	});
	const [manifestJson, setManifestJson] = (0, import_react.useState)(JSON.stringify(INITIAL_MANIFEST, null, 2));
	const [manifestError, setManifestError] = (0, import_react.useState)(null);
	const [validationResults, setValidationResults] = (0, import_react.useState)([]);
	const [buildOutput, setBuildOutput] = (0, import_react.useState)(null);
	const [building, setBuilding] = (0, import_react.useState)(false);
	const [testOutput, setTestOutput] = (0, import_react.useState)(null);
	const [testing, setTesting] = (0, import_react.useState)(false);
	const selectTemplate = (0, import_react.useCallback)((template) => {
		setState((s) => ({
			...s,
			template,
			step: "manifest",
			manifest: template.manifest
		}));
		setManifestJson(JSON.stringify(template.manifest, null, 2));
		setValidationResults([]);
	}, []);
	const handleManifestChange = (0, import_react.useCallback)((json) => {
		setManifestJson(json);
		try {
			const parsed = JSON.parse(json);
			setState((s) => ({
				...s,
				manifest: parsed
			}));
			setManifestError(null);
			const results = [];
			if (!parsed.name) results.push({
				field: "name",
				message: "Extension name is required",
				severity: "error"
			});
			if (!parsed.description) results.push({
				field: "description",
				message: "Description is recommended",
				severity: "warn"
			});
			if (!parsed.main) results.push({
				field: "main",
				message: "Entry point is required",
				severity: "error"
			});
			if (!/^\d+\.\d+\.\d+$/.test(parsed.version)) results.push({
				field: "version",
				message: "Version must follow semver (e.g. 1.0.0)",
				severity: "warn"
			});
			setValidationResults(results);
		} catch (err) {
			setManifestError(err instanceof Error ? err.message : "Invalid JSON");
			setValidationResults([]);
		}
	}, []);
	const handleBuild = (0, import_react.useCallback)(async () => {
		setBuilding(true);
		setBuildOutput(null);
		await new Promise((r) => setTimeout(r, 2e3));
		setBuildOutput(`Building ${state.manifest.name} v${state.manifest.version}...\n✓ TypeScript compilation passed\n✓ Dependencies resolved\n✓ Bundle created\n✓ Extension packaged to dist/${state.manifest.name}-${state.manifest.version}.zip`);
		setBuilding(false);
		notify({
			kind: "success",
			title: "Build Complete",
			message: `${state.manifest.name} built successfully`
		});
	}, [state.manifest]);
	const handleRunTests = (0, import_react.useCallback)(async () => {
		setTesting(true);
		setTestOutput(null);
		await new Promise((r) => setTimeout(r, 3e3));
		setTestOutput(`Running tests for ${state.manifest.name}...\n✓ Basic tool registration test passed\n✓ Manifest validation passed\n⚠ Permissions test: 2 warn(s)\n✓ 3/4 tests passed, 1 warning(s)`);
		setTesting(false);
		notify({
			kind: "success",
			title: "Tests Complete",
			message: "3/4 tests passed"
		});
	}, [state.manifest]);
	const handlePackage = (0, import_react.useCallback)(async () => {
		await new Promise((r) => setTimeout(r, 1500));
		notify({
			kind: "success",
			title: "Extension Packaged",
			message: `Saved to ${state.outputDir}/${state.manifest.name}-${state.manifest.version}.zip`
		});
	}, [state.manifest, state.outputDir]);
	const hasErrors = validationResults.some((r) => r.severity === "error");
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageHeader, {
			className: "w-full",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Extension SDK" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Create, build, and package AetherOS extensions" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "flex items-center gap-1.5 text-xs text-muted-foreground",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: state.devMode,
						onCheckedChange: (v) => setState((s) => ({
							...s,
							devMode: v
						}))
					}), "Developer Mode"]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "flex items-center gap-1.5 text-xs text-muted-foreground",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: state.hotReload,
						onCheckedChange: (v) => setState((s) => ({
							...s,
							hotReload: v
						}))
					}), "Hot Reload"]
				})]
			})]
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex h-full gap-4",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "w-48 shrink-0 space-y-1",
				children: [
					"template",
					"manifest",
					"files",
					"build"
				].map((step, idx) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: cn("flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-xs transition-colors", state.step === step ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent/60"),
					disabled: step !== "template" && !state.template,
					onClick: () => setState((s) => ({
						...s,
						step
					})),
					type: "button",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: cn("flex size-5 items-center justify-center rounded-full text-[0.6rem] font-medium", state.step === step ? "bg-primary text-primary-foreground" : "bg-(--ui-bg-quinary) text-muted-foreground"),
						children: idx + 1
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "capitalize",
						children: step === "build" ? "Build & Package" : step
					})]
				}, step))
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0 flex-1 overflow-y-auto",
				children: [
					state.step === "template" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-4",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "text-sm font-semibold",
							children: "Choose a Template"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "grid gap-3 sm:grid-cols-2 lg:grid-cols-3",
							children: TEMPLATES.map((template) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: cn("rounded-xl border p-4 text-left transition-all hover:border-primary/50 hover:shadow-sm", state.template?.id === template.id ? "border-primary bg-primary/5" : "border-(--ui-stroke-tertiary)"),
								onClick: () => selectTemplate(template),
								type: "button",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
											name: template.icon,
											size: "1.25rem"
										})
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
										className: "mt-3 text-sm font-medium",
										children: template.name
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "mt-1 text-xs text-muted-foreground line-clamp-2",
										children: template.description
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "mt-3 flex items-center gap-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
											className: "text-[0.55rem]",
											variant: "outline",
											children: template.category
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
											className: cn("text-[0.55rem]", DIFFICULTY_COLORS[template.difficulty]),
											children: template.difficulty
										})]
									})
								]
							}, template.id))
						})]
					}),
					state.step === "manifest" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "max-w-2xl space-y-4",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "text-sm font-semibold",
								children: "Manifest Editor"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-xs text-muted-foreground",
								children: "Edit your extension manifest (manifest.json)"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
								className: "min-h-64 font-mono text-xs",
								onChange: (e) => handleManifestChange(e.target.value),
								value: manifestJson
							}),
							manifestError && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-start gap-2 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "mt-0.5 shrink-0",
									name: "error",
									size: "0.75rem"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: manifestError })]
							}),
							validationResults.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
									className: "text-xs font-medium text-muted-foreground",
									children: "Validation"
								}), validationResults.map((r) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: cn("flex items-start gap-2 rounded-md px-3 py-1.5 text-xs", r.severity === "error" ? "bg-destructive/10 text-destructive" : "bg-amber-500/10 text-amber-600"),
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: "mt-0.5 shrink-0",
										name: r.severity === "error" ? "error" : "warning",
										size: "0.75rem"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("strong", { children: [r.field, ":"] }),
										" ",
										r.message
									] })]
								}, r.field))]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "flex items-center gap-2",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									disabled: !!manifestError || hasErrors,
									onClick: () => setState((s) => ({
										...s,
										step: "files"
									})),
									size: "sm",
									children: "Next: Generated Files"
								})
							})
						]
					}),
					state.step === "files" && state.template && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "max-w-2xl space-y-4",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "text-sm font-semibold",
								children: "Generated File Structure"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TemplatePreview, {
								files: state.template.files,
								manifest: state.manifest
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "flex items-center gap-2",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									disabled: !!manifestError || hasErrors,
									onClick: () => setState((s) => ({
										...s,
										step: "build"
									})),
									size: "sm",
									children: "Next: Build & Package"
								})
							})
						]
					}),
					state.step === "build" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "max-w-2xl space-y-5",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-3",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
										className: "text-sm font-semibold",
										children: "Build & Package"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "flex items-center justify-between",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "text-sm font-medium",
												children: state.manifest.name || "Unnamed Extension"
											}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
												className: "ml-2 text-xs text-muted-foreground",
												children: ["v", state.manifest.version]
											})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
												className: "flex items-center gap-1.5",
												children: [
													/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
														disabled: building || hasErrors || !!manifestError,
														onClick: () => void handleBuild(),
														size: "sm",
														children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
															className: cn("mr-1", building && "animate-spin"),
															name: building ? "loading" : "tools",
															size: "0.75rem"
														}), building ? "Building..." : "Build"]
													}),
													/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
														disabled: building || testing || hasErrors || !!manifestError,
														onClick: () => void handleRunTests(),
														size: "sm",
														variant: "outline",
														children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
															className: cn("mr-1", testing && "animate-spin"),
															name: testing ? "loading" : "bug",
															size: "0.75rem"
														}), testing ? "Running..." : "Run Tests"]
													}),
													/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
														disabled: !buildOutput || hasErrors || !!manifestError,
														onClick: () => void handlePackage(),
														size: "sm",
														variant: "outline",
														children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
															className: "mr-1",
															name: "package",
															size: "0.75rem"
														}), "Package"]
													})
												]
											})]
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "mt-3 flex items-center gap-4 text-xs text-muted-foreground",
											children: [
												/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
													className: "flex items-center gap-1",
													children: [
														/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
															name: "file",
															size: "0.75rem"
														}),
														state.template?.files.length || 0,
														" files"
													]
												}),
												/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
													className: "flex items-center gap-1",
													children: [
														/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
															name: "lock",
															size: "0.75rem"
														}),
														state.manifest.permissions.length,
														" permissions"
													]
												}),
												/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
													className: "flex items-center gap-1",
													children: [
														/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
															name: "zap",
															size: "0.75rem"
														}),
														state.manifest.tools.length,
														" tools"
													]
												}),
												/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
													className: "flex items-center gap-1",
													children: [
														/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
															name: "link",
															size: "0.75rem"
														}),
														state.manifest.dependencies.length,
														" dependencies"
													]
												})
											]
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "grid gap-1.5",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
											className: "text-xs font-medium text-foreground",
											htmlFor: "sdk-output",
											children: "Output Directory"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
											id: "sdk-output",
											onChange: (e) => setState((s) => ({
												...s,
												outputDir: e.target.value
											})),
											value: state.outputDir
										})]
									})
								]
							}),
							buildOutput && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
									className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground",
									children: "Build Output"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
									className: "rounded-xl border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-4 py-3 font-mono text-xs leading-relaxed text-foreground/80",
									children: buildOutput
								})]
							}),
							testOutput && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
									className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground",
									children: "Test Results"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
									className: "rounded-xl border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-4 py-3 font-mono text-xs leading-relaxed text-foreground/80",
									children: testOutput
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
									className: "mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
									children: "Developer Options"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "space-y-3",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
										className: "flex items-center justify-between",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-sm font-medium",
											children: "Developer Mode"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
											className: "text-xs text-muted-foreground",
											children: "Enable verbose logging and debug endpoints"
										})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
											checked: state.devMode,
											onCheckedChange: (v) => setState((s) => ({
												...s,
												devMode: v
											}))
										})]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
										className: "flex items-center justify-between",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-sm font-medium",
											children: "Hot Reload"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
											className: "text-xs text-muted-foreground",
											children: "Automatically reload extension on file changes"
										})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
											checked: state.hotReload,
											onCheckedChange: (v) => setState((s) => ({
												...s,
												hotReload: v
											}))
										})]
									})]
								})]
							})
						]
					})
				]
			})]
		})
	});
}
//#endregion
export { ExtensionSdkView };

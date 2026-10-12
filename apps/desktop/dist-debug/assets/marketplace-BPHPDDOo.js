import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { An as Dialog, C as Select, D as SelectValue, Di as notify, E as SelectTrigger, Fn as DialogTitle, Ia as Codicon, La as Button, Mn as DialogDescription, Nn as DialogFooter, O as Badge, Pn as DialogHeader, Ra as cn, T as SelectItem, ao as require_jsx_runtime, jn as DialogContent, ki as useI18n, oo as require_react, vt as SearchField, w as SelectContent } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/app/marketplace/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var CATEGORIES = [
	"AI",
	"Coding",
	"Productivity",
	"Automation",
	"Research",
	"DevTools",
	"Security",
	"Vision",
	"Speech",
	"Translation",
	"Database",
	"Cloud",
	"Email",
	"Communication",
	"Filesystem",
	"Utilities"
];
var SORT_OPTIONS = [
	"popularity",
	"downloads",
	"latest",
	"verified"
];
var SAMPLE_PLUGINS = [
	{
		id: "aether-code-analyzer",
		name: "Code Analyzer",
		description: "Static analysis and linting for 40+ languages with real-time feedback",
		icon: "code",
		author: {
			name: "AetherOS Labs",
			url: "https://aetheros.dev"
		},
		version: "2.1.0",
		license: "MIT",
		homepage: "https://github.com/aetheros/code-analyzer",
		category: "Coding",
		rating: 4.8,
		downloads: 15234,
		verified: true,
		featured: true,
		trending: true,
		installed: true,
		enabled: true,
		versions: [{
			version: "2.1.0",
			changelog: "Added Rust support, improved performance",
			date: "2026-06-15",
			requires: ["core>=0.16"]
		}, {
			version: "2.0.0",
			changelog: "Major refactor, new API",
			date: "2026-05-01",
			requires: ["core>=0.15"]
		}],
		dependencies: [{
			name: "core",
			version: ">=0.16",
			optional: false
		}, {
			name: "language-server-protocol",
			version: ">=1.0",
			optional: true
		}],
		permissions: [{
			name: "file:read",
			description: "Read source files for analysis",
			required: true
		}, {
			name: "file:write",
			description: "Write lint fixes",
			required: false
		}],
		reviews: [{
			id: "r1",
			author: "dev42",
			rating: 5,
			comment: "Essential tool for any developer",
			date: "2026-06-20"
		}],
		screenshots: [],
		tags: [
			"linting",
			"static-analysis",
			"developer-tools"
		]
	},
	{
		id: "aether-search-assistant",
		name: "Search Assistant",
		description: "Intelligent web search with result summarization and source tracking",
		icon: "globe",
		author: { name: "AetherOS Labs" },
		version: "1.3.2",
		license: "MIT",
		category: "AI",
		rating: 4.6,
		downloads: 28901,
		verified: true,
		featured: true,
		trending: false,
		installed: false,
		enabled: false,
		versions: [{
			version: "1.3.2",
			changelog: "Fixed rate limiting issues",
			date: "2026-06-10",
			requires: ["core>=0.15"]
		}],
		dependencies: [{
			name: "core",
			version: ">=0.15",
			optional: false
		}],
		permissions: [{
			name: "network:http",
			description: "Make web search requests",
			required: true
		}],
		reviews: [],
		screenshots: [],
		tags: [
			"search",
			"web",
			"ai"
		]
	},
	{
		id: "aether-task-automation",
		name: "Task Automation",
		description: "Visual workflow builder with 200+ integrations and triggers",
		icon: "zap",
		author: { name: "AetherOS Labs" },
		version: "3.0.1",
		license: "Apache-2.0",
		category: "Automation",
		rating: 4.7,
		downloads: 42100,
		verified: true,
		featured: false,
		trending: true,
		installed: false,
		enabled: false,
		versions: [{
			version: "3.0.1",
			changelog: "New triggers: file change, webhook",
			date: "2026-06-01",
			requires: ["core>=0.16"]
		}],
		dependencies: [{
			name: "core",
			version: ">=0.16",
			optional: false
		}, {
			name: "aether-scheduler",
			version: ">=1.0",
			optional: true
		}],
		permissions: [{
			name: "file:*",
			description: "Read and write files for workflow actions",
			required: true
		}, {
			name: "network:http",
			description: "Make HTTP requests to integrations",
			required: true
		}],
		reviews: [],
		screenshots: [],
		tags: [
			"automation",
			"workflow",
			"integrations"
		]
	},
	{
		id: "aether-vision-analyzer",
		name: "Vision Analyzer",
		description: "Image recognition, OCR, and object detection using local models",
		icon: "photo",
		author: { name: "AetherOS Labs" },
		version: "1.0.0",
		license: "MIT",
		category: "Vision",
		rating: 4.3,
		downloads: 8900,
		verified: true,
		featured: false,
		trending: false,
		installed: false,
		enabled: false,
		versions: [{
			version: "1.0.0",
			changelog: "Initial release",
			date: "2026-05-20",
			requires: ["core>=0.15"]
		}],
		dependencies: [{
			name: "core",
			version: ">=0.15",
			optional: false
		}],
		permissions: [{
			name: "file:read",
			description: "Read image files",
			required: true
		}, {
			name: "hardware:gpu",
			description: "Access GPU for model inference",
			required: false
		}],
		reviews: [],
		screenshots: [],
		tags: [
			"vision",
			"ocr",
			"image"
		]
	},
	{
		id: "aether-database-gateway",
		name: "Database Gateway",
		description: "Connect to PostgreSQL, MySQL, SQLite, and MongoDB with query builder",
		icon: "database",
		author: { name: "AetherOS Labs" },
		version: "2.2.1",
		license: "MIT",
		category: "Database",
		rating: 4.5,
		downloads: 12400,
		verified: true,
		featured: false,
		trending: false,
		installed: false,
		enabled: false,
		versions: [{
			version: "2.2.1",
			changelog: "Added MongoDB support",
			date: "2026-06-18",
			requires: ["core>=0.16"]
		}],
		dependencies: [{
			name: "core",
			version: ">=0.16",
			optional: false
		}],
		permissions: [{
			name: "network:tcp",
			description: "Connect to database servers",
			required: true
		}, {
			name: "file:read",
			description: "Read SQLite databases",
			required: true
		}],
		reviews: [],
		screenshots: [],
		tags: [
			"database",
			"sql",
			"nosql"
		]
	},
	{
		id: "aether-cloud-deploy",
		name: "Cloud Deploy",
		description: "One-click deployment to AWS, GCP, Azure, and DigitalOcean",
		icon: "cloud",
		author: { name: "AetherOS Labs" },
		version: "1.1.0",
		license: "MIT",
		category: "Cloud",
		rating: 4.2,
		downloads: 6700,
		verified: false,
		featured: false,
		trending: false,
		installed: false,
		enabled: false,
		versions: [{
			version: "1.1.0",
			changelog: "Added Azure support",
			date: "2026-06-05",
			requires: ["core>=0.15"]
		}],
		dependencies: [{
			name: "core",
			version: ">=0.15",
			optional: false
		}, {
			name: "aether-terminal",
			version: ">=1.0",
			optional: true
		}],
		permissions: [{
			name: "network:http",
			description: "Communicate with cloud provider APIs",
			required: true
		}, {
			name: "secret:env",
			description: "Access cloud provider credentials",
			required: true
		}],
		reviews: [],
		screenshots: [],
		tags: [
			"cloud",
			"deployment",
			"devops"
		]
	},
	{
		id: "aether-translate",
		name: "Translate Plus",
		description: "Real-time translation across 120+ languages with dialect detection",
		icon: "language",
		author: { name: "AetherOS Labs" },
		version: "2.0.0",
		license: "MIT",
		category: "Translation",
		rating: 4.4,
		downloads: 32100,
		verified: true,
		featured: false,
		trending: true,
		installed: false,
		enabled: false,
		versions: [{
			version: "2.0.0",
			changelog: "Added offline translation mode",
			date: "2026-06-12",
			requires: ["core>=0.16"]
		}],
		dependencies: [{
			name: "core",
			version: ">=0.16",
			optional: false
		}],
		permissions: [{
			name: "network:http",
			description: "Fetch translation models",
			required: true
		}, {
			name: "file:read",
			description: "Read offline model files",
			required: false
		}],
		reviews: [],
		screenshots: [],
		tags: [
			"translation",
			"language",
			"i18n"
		]
	},
	{
		id: "aether-security-scan",
		name: "Security Scanner",
		description: "Vulnerability scanning, dependency auditing, and secret detection",
		icon: "shield",
		author: { name: "AetherOS Labs" },
		version: "1.5.0",
		license: "MIT",
		category: "Security",
		rating: 4.9,
		downloads: 19800,
		verified: true,
		featured: true,
		trending: true,
		installed: false,
		enabled: false,
		versions: [{
			version: "1.5.0",
			changelog: "Added real-time monitoring",
			date: "2026-06-20",
			requires: ["core>=0.16"]
		}],
		dependencies: [{
			name: "core",
			version: ">=0.16",
			optional: false
		}],
		permissions: [{
			name: "file:read",
			description: "Scan files for vulnerabilities",
			required: true
		}, {
			name: "network:http",
			description: "Check vulnerability databases",
			required: true
		}],
		reviews: [],
		screenshots: [],
		tags: [
			"security",
			"audit",
			"vulnerability"
		]
	},
	{
		id: "aether-voice-control",
		name: "Voice Control",
		description: "Hands-free operation with wake word, commands, and dictation",
		icon: "mic",
		author: { name: "AetherOS Labs" },
		version: "1.2.1",
		license: "MIT",
		category: "Speech",
		rating: 4.1,
		downloads: 15400,
		verified: false,
		featured: false,
		trending: false,
		installed: false,
		enabled: false,
		versions: [{
			version: "1.2.1",
			changelog: "Improved wake word detection",
			date: "2026-06-08",
			requires: ["core>=0.15"]
		}],
		dependencies: [{
			name: "core",
			version: ">=0.15",
			optional: false
		}],
		permissions: [{
			name: "hardware:audio",
			description: "Access microphone for voice input",
			required: true
		}],
		reviews: [],
		screenshots: [],
		tags: [
			"voice",
			"speech",
			"dictation"
		]
	},
	{
		id: "aether-email-hub",
		name: "Email Hub",
		description: "Unified inbox for Gmail, Outlook, and IMAP with AI-powered replies",
		icon: "mail",
		author: { name: "AetherOS Labs" },
		version: "1.0.3",
		license: "MIT",
		category: "Email",
		rating: 4,
		downloads: 9100,
		verified: false,
		featured: false,
		trending: false,
		installed: false,
		enabled: false,
		versions: [{
			version: "1.0.3",
			changelog: "Bug fixes",
			date: "2026-06-14",
			requires: ["core>=0.15"]
		}],
		dependencies: [{
			name: "core",
			version: ">=0.15",
			optional: false
		}],
		permissions: [{
			name: "network:http",
			description: "Connect to email servers",
			required: true
		}, {
			name: "secret:oauth",
			description: "Store OAuth tokens for email providers",
			required: true
		}],
		reviews: [],
		screenshots: [],
		tags: [
			"email",
			"communication",
			"inbox"
		]
	},
	{
		id: "aether-file-manager",
		name: "File Manager Pro",
		description: "Advanced file operations, sync, compression, and preview for any format",
		icon: "folder",
		author: { name: "AetherOS Labs" },
		version: "3.2.0",
		license: "MIT",
		category: "Filesystem",
		rating: 4.6,
		downloads: 45200,
		verified: true,
		featured: false,
		trending: false,
		installed: false,
		enabled: false,
		versions: [{
			version: "3.2.0",
			changelog: "Added cloud sync support",
			date: "2026-06-22",
			requires: ["core>=0.16"]
		}],
		dependencies: [{
			name: "core",
			version: ">=0.16",
			optional: false
		}],
		permissions: [{
			name: "file:*",
			description: "Full filesystem access",
			required: true
		}, {
			name: "network:http",
			description: "Sync with cloud storage",
			required: false
		}],
		reviews: [],
		screenshots: [],
		tags: [
			"files",
			"sync",
			"compression"
		]
	},
	{
		id: "aether-productivity-suite",
		name: "Productivity Suite",
		description: "Todo lists, notes, calendar, and project tracking in one place",
		icon: "checklist",
		author: { name: "AetherOS Labs" },
		version: "2.3.0",
		license: "MIT",
		category: "Productivity",
		rating: 4.5,
		downloads: 56e3,
		verified: true,
		featured: true,
		trending: false,
		installed: false,
		enabled: false,
		versions: [{
			version: "2.3.0",
			changelog: "Calendar integration",
			date: "2026-06-19",
			requires: ["core>=0.16"]
		}],
		dependencies: [{
			name: "core",
			version: ">=0.16",
			optional: false
		}],
		permissions: [{
			name: "file:read",
			description: "Read notes and todo files",
			required: true
		}, {
			name: "file:write",
			description: "Write notes and todo files",
			required: true
		}],
		reviews: [],
		screenshots: [],
		tags: [
			"productivity",
			"todo",
			"notes"
		]
	}
];
function MarketplaceView({ onPluginSelect, onBack }) {
	const { t } = useI18n();
	const [query, setQuery] = (0, import_react.useState)("");
	const [activeCategory, setActiveCategory] = (0, import_react.useState)(null);
	const [sortBy, setSortBy] = (0, import_react.useState)("popularity");
	const [plugins, setPlugins] = (0, import_react.useState)(SAMPLE_PLUGINS);
	const [selectedPlugin, setSelectedPlugin] = (0, import_react.useState)(null);
	const [installingId, setInstallingId] = (0, import_react.useState)(null);
	const [showFeatured, setShowFeatured] = (0, import_react.useState)(true);
	const filteredPlugins = (0, import_react.useMemo)(() => {
		const q = query.trim().toLowerCase();
		return plugins.filter((p) => {
			if (activeCategory && p.category !== activeCategory) return false;
			if (!q) return true;
			return p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q) || p.author.name.toLowerCase().includes(q) || p.tags.some((tag) => tag.includes(q));
		}).sort((a, b) => {
			switch (sortBy) {
				case "downloads": return b.downloads - a.downloads;
				case "latest": return new Date(b.versions[0]?.date || 0).getTime() - new Date(a.versions[0]?.date || 0).getTime();
				case "verified": return (b.verified ? 1 : 0) - (a.verified ? 1 : 0);
				default: return b.rating - a.rating || b.downloads - a.downloads;
			}
		});
	}, [
		plugins,
		query,
		activeCategory,
		sortBy
	]);
	const featuredPlugins = (0, import_react.useMemo)(() => plugins.filter((p) => p.featured), [plugins]);
	const trendingPlugins = (0, import_react.useMemo)(() => plugins.filter((p) => p.trending), [plugins]);
	const categoryCounts = (0, import_react.useMemo)(() => {
		const counts = /* @__PURE__ */ new Map();
		for (const p of plugins) counts.set(p.category, (counts.get(p.category) || 0) + 1);
		return counts;
	}, [plugins]);
	const handleInstall = (0, import_react.useCallback)(async (plugin) => {
		setInstallingId(plugin.id);
		setPlugins((current) => current.map((p) => p.id === plugin.id ? {
			...p,
			installProgress: 0
		} : p));
		for (let i = 0; i <= 100; i += 20) {
			await new Promise((r) => setTimeout(r, 200));
			setPlugins((current) => current.map((p) => p.id === plugin.id ? {
				...p,
				installProgress: i
			} : p));
		}
		await new Promise((r) => setTimeout(r, 500));
		setPlugins((current) => current.map((p) => p.id === plugin.id ? {
			...p,
			installed: true,
			enabled: true,
			installProgress: void 0
		} : p));
		setInstallingId(null);
		notify({
			kind: "success",
			title: "Plugin Installed",
			message: `${plugin.name} v${plugin.version} installed successfully`
		});
	}, []);
	const handleUninstall = (0, import_react.useCallback)(async (plugin) => {
		setPlugins((current) => current.map((p) => p.id === plugin.id ? {
			...p,
			installed: false,
			enabled: false
		} : p));
		notify({
			kind: "success",
			title: "Plugin Removed",
			message: `${plugin.name} has been removed`
		});
	}, []);
	const handleToggleEnable = (0, import_react.useCallback)((plugin) => {
		setPlugins((current) => current.map((p) => p.id === plugin.id ? {
			...p,
			enabled: !p.enabled
		} : p));
	}, []);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageHeader, {
			className: "w-full",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Plugin Marketplace" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Discover and install plugins to extend AetherOS" })] })
		}),
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex h-full gap-4",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("aside", {
				className: "w-48 shrink-0 space-y-1",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mb-2 text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground",
						children: "Categories"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: cn("flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-left text-xs transition-colors", activeCategory === null ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"),
						onClick: () => setActiveCategory(null),
						type: "button",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "All Plugins" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-[0.6rem] text-muted-foreground",
							children: plugins.length
						})]
					}),
					CATEGORIES.map((category) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: cn("flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-left text-xs transition-colors", activeCategory === category ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"),
						onClick: () => setActiveCategory(activeCategory === category ? null : category),
						type: "button",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: category }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-[0.6rem] text-muted-foreground",
							children: categoryCounts.get(category) || 0
						})]
					}, category))
				]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0 flex-1 space-y-4 overflow-y-auto",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SearchField, {
							containerClassName: "flex-1 max-w-md",
							onChange: setQuery,
							placeholder: "Search plugins...",
							value: query
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
							onValueChange: setSortBy,
							value: sortBy,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
								className: "h-8 w-36 text-xs",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: SORT_OPTIONS.map((opt) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
								value: opt,
								children: opt.charAt(0).toUpperCase() + opt.slice(1)
							}, opt)) })]
						})]
					}),
					showFeatured && !query && !activeCategory && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground",
								children: "Featured"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "grid gap-3 sm:grid-cols-2 lg:grid-cols-3",
								children: featuredPlugins.slice(0, 3).map((plugin) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(FeaturedPluginCard, {
									installing: installingId === plugin.id,
									onInstall: () => void handleInstall(plugin),
									onSelect: () => setSelectedPlugin(plugin),
									plugin
								}, plugin.id))
							}),
							trendingPlugins.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "pt-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
								children: "Trending"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "flex gap-3 overflow-x-auto pb-2",
								children: trendingPlugins.slice(0, 6).map((plugin) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TrendingPluginCard, {
									onSelect: () => setSelectedPlugin(plugin),
									plugin
								}, plugin.id))
							})] })
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-1",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
								className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground",
								children: [activeCategory || "All Plugins", /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "ml-1 text-muted-foreground/60",
									children: [
										"(",
										filteredPlugins.length,
										")"
									]
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
								children: filteredPlugins.map((plugin) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PluginCard, {
									installing: installingId === plugin.id,
									onInstall: () => void handleInstall(plugin),
									onSelect: () => setSelectedPlugin(plugin),
									onToggleEnable: () => handleToggleEnable(plugin),
									onUninstall: () => void handleUninstall(plugin),
									plugin
								}, plugin.id))
							}),
							filteredPlugins.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "grid min-h-52 place-items-center text-center",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: "text-muted-foreground/40",
										name: "search",
										size: "2rem"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "mt-2 text-sm font-medium text-muted-foreground",
										children: "No plugins found"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "mt-1 text-xs text-muted-foreground/60",
										children: "Try adjusting your search or filters"
									})
								] })
							})
						]
					})
				]
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PluginDetailDialog, {
			installing: installingId === selectedPlugin?.id,
			onClose: () => setSelectedPlugin(null),
			onInstall: () => selectedPlugin && void handleInstall(selectedPlugin),
			onToggleEnable: () => selectedPlugin && handleToggleEnable(selectedPlugin),
			onUninstall: () => {
				if (selectedPlugin) {
					handleUninstall(selectedPlugin);
					setSelectedPlugin(null);
				}
			},
			open: selectedPlugin !== null,
			plugin: selectedPlugin
		})]
	});
}
function FeaturedPluginCard({ installing, onInstall, onSelect, plugin }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		className: "group relative flex flex-col overflow-hidden rounded-xl border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) text-left transition-all hover:border-(--ui-stroke-secondary) hover:shadow-sm",
		onClick: onSelect,
		type: "button",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "bg-gradient-to-br from-primary/5 to-primary/10 p-4",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PluginIcon, { category: plugin.category })
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex flex-1 flex-col gap-1.5 p-3",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "truncate text-sm font-medium",
						children: plugin.name
					}), plugin.verified && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "shrink-0 text-primary",
						name: "verified",
						size: "0.75rem"
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "line-clamp-2 text-xs text-muted-foreground",
					children: plugin.description
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-auto flex items-center justify-between pt-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-1 text-[0.65rem] text-muted-foreground",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "star",
								size: "0.65rem"
							}),
							plugin.rating,
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "ml-1",
								children: "·"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "download",
								size: "0.65rem"
							}),
							(plugin.downloads / 1e3).toFixed(1),
							"k"
						]
					}), plugin.installed ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						className: "text-[0.6rem]",
						variant: "muted",
						children: "Installed"
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						className: "text-[0.6rem]",
						variant: "default",
						children: installing ? `Installing ${plugin.installProgress}%` : "Install"
					})]
				})
			]
		})]
	});
}
function TrendingPluginCard({ onSelect, plugin }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		className: "flex shrink-0 items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 text-left text-xs transition-colors hover:bg-accent/60",
		onClick: onSelect,
		type: "button",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PluginIcon, { category: plugin.category }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex items-center gap-1.5",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "truncate text-sm font-medium",
						children: plugin.name
					})
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
					className: "text-muted-foreground",
					children: ["by ", plugin.author.name]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
				className: "shrink-0 text-[0.55rem]",
				variant: "default",
				children: "Trending"
			})
		]
	});
}
function PluginCard({ installing, onInstall, onSelect, onToggleEnable, onUninstall, plugin }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "group relative flex flex-col rounded-xl border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) transition-all hover:border-(--ui-stroke-secondary) hover:shadow-sm",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
			className: "flex flex-col p-3 text-left",
			onClick: onSelect,
			type: "button",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex items-start justify-between gap-2",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2.5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PluginIcon, { category: plugin.category }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-1.5",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "truncate text-sm font-medium",
									children: plugin.name
								}), plugin.verified && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "shrink-0 text-primary",
									name: "verified",
									size: "0.65rem"
								})]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								className: "text-[0.6rem] text-muted-foreground",
								children: ["v", plugin.version]
							})]
						})]
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-2 line-clamp-2 text-xs text-muted-foreground",
					children: plugin.description
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-2 flex items-center gap-2 text-[0.6rem] text-muted-foreground",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: plugin.author.name }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "·" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "star",
							size: "0.6rem"
						}),
						plugin.rating,
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "·" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "download",
							size: "0.6rem"
						}),
						(plugin.downloads / 1e3).toFixed(1),
						"k"
					]
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex items-center gap-1 border-t border-(--ui-stroke-tertiary) px-3 py-2",
			children: plugin.installed ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				className: "flex-1 text-xs",
				onClick: onToggleEnable,
				size: "sm",
				variant: plugin.enabled ? "default" : "outline",
				children: plugin.enabled ? "Enabled" : "Disabled"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				className: "flex-1 text-xs text-muted-foreground hover:text-destructive",
				onClick: onUninstall,
				size: "sm",
				variant: "ghost",
				children: "Remove"
			})] }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				className: "flex-1 text-xs",
				disabled: installing,
				onClick: onInstall,
				size: "sm",
				children: installing ? `Installing ${plugin.installProgress}%` : "Install"
			})
		})]
	});
}
function PluginDetailDialog({ installing, onClose, onInstall, onToggleEnable, onUninstall, open, plugin }) {
	if (!plugin) return null;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dialog, {
		onOpenChange: (v) => !v && onClose(),
		open,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, {
			className: "max-w-2xl",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogHeader, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PluginIcon, { category: plugin.category }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, { children: plugin.name }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogDescription, { children: plugin.description })] })]
				}) }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "max-h-[60vh] space-y-5 overflow-y-auto px-1",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex flex-wrap gap-3 text-xs text-muted-foreground",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "font-medium text-foreground",
										children: "Version:"
									}),
									" ",
									plugin.version
								] }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "font-medium text-foreground",
										children: "Author:"
									}),
									" ",
									plugin.author.name
								] }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "font-medium text-foreground",
										children: "License:"
									}),
									" ",
									plugin.license
								] }),
								plugin.homepage && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("a", {
									className: "flex items-center gap-1 text-primary hover:underline",
									href: plugin.homepage,
									rel: "noreferrer",
									target: "_blank",
									children: ["Homepage ", /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: "link-external",
										size: "0.65rem"
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "font-medium text-foreground",
										children: "Rating:"
									}),
									" ",
									plugin.rating,
									" / 5"
								] }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "font-medium text-foreground",
										children: "Downloads:"
									}),
									" ",
									plugin.downloads.toLocaleString()
								] })
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
							className: "mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
							children: "Description"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-xs leading-relaxed text-foreground/80",
							children: plugin.longDescription || plugin.description
						})] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
							className: "mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
							children: "Tags"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex flex-wrap gap-1.5",
							children: plugin.tags.map((tag) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								variant: "outline",
								children: tag
							}, tag))
						})] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
							className: "mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
							children: "Permissions"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "space-y-1",
							children: plugin.permissions.map((perm) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-start gap-2 rounded-md bg-(--ui-bg-quinary) px-2.5 py-1.5",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: "mt-0.5 shrink-0 text-muted-foreground",
										name: perm.required ? "lock" : "unlock",
										size: "0.75rem"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-xs font-medium",
										children: perm.name
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-[0.65rem] text-muted-foreground",
										children: perm.description
									})] }),
									perm.required ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: "ml-auto shrink-0 text-[0.55rem]",
										variant: "default",
										children: "Required"
									}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: "ml-auto shrink-0 text-[0.55rem]",
										variant: "outline",
										children: "Optional"
									})
								]
							}, perm.name))
						})] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
							className: "mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
							children: "Dependencies"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "space-y-1",
							children: plugin.dependencies.map((dep) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-2 text-xs",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: "package",
										size: "0.75rem"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "font-medium",
										children: dep.name
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "text-muted-foreground",
										children: [
											"(",
											dep.version,
											")"
										]
									}),
									dep.optional && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: "text-[0.55rem]",
										variant: "outline",
										children: "Optional"
									})
								]
							}, dep.name))
						})] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
							className: "mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
							children: "Version History"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "space-y-1.5",
							children: plugin.versions.map((v) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "rounded-md border border-(--ui-stroke-tertiary) px-2.5 py-1.5",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center justify-between",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "text-xs font-medium",
										children: ["v", v.version]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-[0.6rem] text-muted-foreground",
										children: v.date
									})]
								}), v.changelog && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "mt-0.5 text-[0.65rem] text-muted-foreground",
									children: v.changelog
								})]
							}, v.version))
						})] }),
						plugin.reviews.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
							className: "mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
							children: "Reviews"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "space-y-1.5",
							children: plugin.reviews.map((review) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "rounded-md bg-(--ui-bg-quinary) px-2.5 py-1.5",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center justify-between",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-xs font-medium",
										children: review.author
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "flex items-center gap-1 text-[0.6rem] text-amber-500",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
											name: "star",
											size: "0.6rem"
										}), review.rating]
									})]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "mt-0.5 text-[0.65rem] text-muted-foreground",
									children: review.comment
								})]
							}, review.id))
						})] })
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogFooter, { children: plugin.installed ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: onToggleEnable,
					size: "sm",
					variant: plugin.enabled ? "outline" : "default",
					children: plugin.enabled ? "Disable" : "Enable"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: onUninstall,
					size: "sm",
					variant: "destructive",
					children: "Remove"
				})] }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					disabled: installing,
					onClick: onInstall,
					size: "sm",
					children: installing ? `Installing ${plugin.installProgress}%` : `Install v${plugin.version}`
				}) })
			]
		})
	});
}
function PluginIcon({ category, className }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		className: cn("flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary", className),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
			name: {
				"AI": "brain",
				"Coding": "code",
				"Productivity": "checklist",
				"Automation": "zap",
				"Research": "book",
				"DevTools": "tools",
				"Security": "shield",
				"Vision": "eye",
				"Speech": "mic",
				"Translation": "globe",
				"Database": "database",
				"Cloud": "cloud",
				"Email": "mail",
				"Communication": "comment",
				"Filesystem": "folder",
				"Utilities": "wrench"
			}[category] || "package",
			size: "1rem"
		})
	});
}
//#endregion
export { MarketplaceView };

import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Di as notify, Ia as Codicon, La as Button, P as Switch, Pa as LogView, Ra as cn, ao as require_jsx_runtime, ki as useI18n, oo as require_react } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/app/developer-tools/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var INITIAL_LOGS = [
	{
		id: "l1",
		timestamp: Date.now() - 5e3,
		level: "info",
		source: "core",
		message: "Session manager initialized"
	},
	{
		id: "l2",
		timestamp: Date.now() - 4e3,
		level: "info",
		source: "gateway",
		message: "Gateway connection established"
	},
	{
		id: "l3",
		timestamp: Date.now() - 3e3,
		level: "warn",
		source: "plugin:code-analyzer",
		message: "Deprecated API used: readFileSync"
	},
	{
		id: "l4",
		timestamp: Date.now() - 2e3,
		level: "debug",
		source: "mcp:filesystem",
		message: "List directory: /home/user/projects"
	},
	{
		id: "l5",
		timestamp: Date.now() - 1e3,
		level: "error",
		source: "plugin:search-assistant",
		message: "Rate limit exceeded, retrying in 30s"
	},
	{
		id: "l6",
		timestamp: Date.now(),
		level: "info",
		source: "core",
		message: "Plugin marketplace index updated"
	}
];
var INITIAL_METRICS = [
	{
		label: "Memory",
		value: 342,
		unit: "MB",
		max: 1024
	},
	{
		label: "CPU",
		value: 12,
		unit: "%",
		max: 100
	},
	{
		label: "Extensions",
		value: 5,
		unit: "running",
		max: 20
	},
	{
		label: "MCP Servers",
		value: 3,
		unit: "connected",
		max: 10
	}
];
var INITIAL_INSPECTOR = {
	id: "root",
	name: "AetherOS Runtime",
	type: "store",
	children: [
		{
			id: "plugins",
			name: "Plugins",
			type: "store",
			children: [
				{
					id: "p1",
					name: "Code Analyzer",
					type: "plugin",
					value: "v2.1.0 • enabled"
				},
				{
					id: "p2",
					name: "Search Assistant",
					type: "plugin",
					value: "v1.3.2 • disabled"
				},
				{
					id: "p3",
					name: "Task Automation",
					type: "plugin",
					value: "v3.0.1 • enabled"
				}
			]
		},
		{
			id: "tools",
			name: "Registered Tools",
			type: "store",
			children: [
				{
					id: "t1",
					name: "read_file",
					type: "tool",
					value: "core"
				},
				{
					id: "t2",
					name: "write_file",
					type: "tool",
					value: "core"
				},
				{
					id: "t3",
					name: "web_search",
					type: "tool",
					value: "core"
				},
				{
					id: "t4",
					name: "terminal",
					type: "tool",
					value: "core"
				},
				{
					id: "t5",
					name: "mcp_call",
					type: "tool",
					value: "mcp-bridge"
				},
				{
					id: "t6",
					name: "analyze_code",
					type: "tool",
					value: "plugin:code-analyzer"
				}
			]
		},
		{
			id: "hooks",
			name: "Registered Hooks",
			type: "store",
			children: [
				{
					id: "h1",
					name: "session:start",
					type: "hook",
					value: "2 handlers"
				},
				{
					id: "h2",
					name: "session:end",
					type: "hook",
					value: "1 handler"
				},
				{
					id: "h3",
					name: "tool:before",
					type: "hook",
					value: "3 handlers"
				},
				{
					id: "h4",
					name: "tool:after",
					type: "hook",
					value: "3 handlers"
				},
				{
					id: "h5",
					name: "message:send",
					type: "hook",
					value: "1 handler"
				}
			]
		},
		{
			id: "stores",
			name: "State Stores",
			type: "store",
			children: [
				{
					id: "s1",
					name: "session",
					type: "store",
					value: "1 active session"
				},
				{
					id: "s2",
					name: "plugins",
					type: "store",
					value: "3 plugins tracked"
				},
				{
					id: "s3",
					name: "mcp",
					type: "store",
					value: "5 servers tracked"
				},
				{
					id: "s4",
					name: "cron",
					type: "store",
					value: "8 jobs scheduled"
				}
			]
		}
	]
};
var LOG_LEVEL_COLORS = {
	debug: "text-muted-foreground",
	info: "text-sky-500",
	warn: "text-amber-500",
	error: "text-red-500"
};
function DeveloperToolsView() {
	const { t } = useI18n();
	const [activeTab, setActiveTab] = (0, import_react.useState)("console");
	const [logs, setLogs] = (0, import_react.useState)(INITIAL_LOGS);
	const [logFilter, setLogFilter] = (0, import_react.useState)("all");
	const [logSource, setLogSource] = (0, import_react.useState)("all");
	const [autoScroll, setAutoScroll] = (0, import_react.useState)(true);
	const [metrics, setMetrics] = (0, import_react.useState)(INITIAL_METRICS);
	const [expandedInspector, setExpandedInspector] = (0, import_react.useState)(new Set([
		"root",
		"plugins",
		"tools",
		"hooks",
		"stores"
	]));
	const [liveReload, setLiveReload] = (0, import_react.useState)(false);
	(0, import_react.useEffect)(() => {
		if (!liveReload) return;
		const interval = setInterval(() => {
			setMetrics((current) => current.map((m) => ({
				...m,
				value: m.label === "Memory" ? Math.floor(Math.random() * 512) + 128 : m.label === "CPU" ? Math.floor(Math.random() * 40) + 2 : m.label === "Extensions" ? Math.floor(Math.random() * 8) + 2 : Math.floor(Math.random() * 5) + 1
			})));
			setLogs((current) => [...current.slice(-50), {
				id: `l-${Date.now()}`,
				timestamp: Date.now(),
				level: [
					"debug",
					"info",
					"warn",
					"error"
				][Math.floor(Math.random() * 4)],
				source: [
					"core",
					"gateway",
					"plugin:code-analyzer",
					"mcp:filesystem"
				][Math.floor(Math.random() * 4)],
				message: `Live metric sample at ${(/* @__PURE__ */ new Date()).toLocaleTimeString()}`
			}]);
		}, 3e3);
		return () => clearInterval(interval);
	}, [liveReload]);
	const filteredLogs = (0, import_react.useMemo)(() => {
		return logs.filter((l) => {
			if (logFilter !== "all" && l.level !== logFilter) return false;
			if (logSource !== "all" && l.source !== logSource) return false;
			return true;
		});
	}, [
		logs,
		logFilter,
		logSource
	]);
	const logSources = (0, import_react.useMemo)(() => {
		const sources = new Set(logs.map((l) => l.source));
		return Array.from(sources).sort();
	}, [logs]);
	const sourceCounts = (0, import_react.useMemo)(() => {
		const counts = {};
		for (const l of logs) counts[l.source] = (counts[l.source] || 0) + 1;
		return counts;
	}, [logs]);
	const handleClearLogs = (0, import_react.useCallback)(() => {
		setLogs([]);
		notify({
			kind: "success",
			title: "Console Cleared",
			message: "Log buffer cleared"
		});
	}, []);
	const toggleInspector = (0, import_react.useCallback)((id) => {
		setExpandedInspector((prev) => {
			const next = new Set(prev);
			if (next.has(id)) next.delete(id);
			else next.add(id);
			return next;
		});
	}, []);
	const renderInspectorNode = (node, depth = 0) => {
		const hasChildren = node.children && node.children.length > 0;
		const isExpanded = expandedInspector.has(node.id);
		return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: cn("flex items-center gap-1.5 rounded-sm px-1 py-0.5 text-xs hover:bg-accent/60", depth > 0 && "ml-4"),
			style: { paddingLeft: `${depth * 12 + 4}px` },
			children: [
				hasChildren ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					className: "flex items-center text-muted-foreground hover:text-foreground",
					onClick: () => toggleInspector(node.id),
					type: "button",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "transition-transform",
						name: "chevron-right",
						size: "0.6rem",
						style: { transform: isExpanded ? "rotate(90deg)" : void 0 }
					})
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "w-3" }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
					className: cn("shrink-0", node.type === "plugin" ? "text-primary" : node.type === "tool" ? "text-sky-500" : node.type === "hook" ? "text-amber-500" : "text-muted-foreground"),
					name: {
						plugin: "extensions",
						tool: "zap",
						hook: "link",
						store: "database"
					}[node.type] || "circle",
					size: "0.75rem"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "font-medium",
					children: node.name
				}),
				node.value && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
					className: "text-muted-foreground",
					children: ["— ", node.value]
				})
			]
		}), hasChildren && isExpanded && node.children.map((child) => renderInspectorNode(child, depth + 1))] }, node.id);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageHeader, {
			className: "w-full",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Developer Tools" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Debug, inspect, and monitor AetherOS internals" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "flex items-center gap-1.5 text-xs text-muted-foreground",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
					checked: liveReload,
					onCheckedChange: setLiveReload
				}), "Live Refresh"]
			})]
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex h-full flex-col gap-0",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary)",
					children: [
						"console",
						"metrics",
						"inspector"
					].map((tab) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: cn("flex items-center gap-1.5 border-b-2 px-4 py-2 text-xs font-medium transition-colors", activeTab === tab ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"),
						onClick: () => setActiveTab(tab),
						type: "button",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: tab === "console" ? "terminal" : tab === "metrics" ? "chart" : "search",
							size: "0.875rem"
						}), tab.charAt(0).toUpperCase() + tab.slice(1)]
					}, tab))
				}),
				activeTab === "console" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex min-h-0 flex-1 flex-col",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex shrink-0 items-center gap-2 border-b border-(--ui-stroke-tertiary) px-3 py-1.5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex gap-1",
							children: [
								"all",
								"debug",
								"info",
								"warn",
								"error"
							].map((level) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: cn("rounded-md px-2 py-0.5 text-[0.6rem] font-medium transition-colors", logFilter === level ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground"),
								onClick: () => setLogFilter(level),
								type: "button",
								children: level === "all" ? "All" : level.charAt(0).toUpperCase() + level.slice(1)
							}, level))
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "ml-auto flex items-center gap-1.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "flex items-center gap-1 text-[0.6rem] text-muted-foreground",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
									checked: autoScroll,
									onCheckedChange: setAutoScroll
								}), "Auto-scroll"]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								"aria-label": "Clear logs",
								className: "text-[0.6rem] text-muted-foreground",
								onClick: handleClearLogs,
								size: "icon-xs",
								variant: "ghost",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									name: "trash",
									size: "0.75rem"
								})
							})]
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex min-h-0 flex-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "w-36 shrink-0 border-r border-(--ui-stroke-tertiary) px-2 py-1",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "mb-1 text-[0.55rem] font-semibold uppercase tracking-wider text-muted-foreground",
									children: "Sources"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
									className: cn("flex w-full items-center justify-between rounded-sm px-1.5 py-0.5 text-[0.6rem] transition-colors", logSource === "all" ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground"),
									onClick: () => setLogSource("all"),
									type: "button",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "All Sources" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-muted-foreground/60",
										children: logs.length
									})]
								}),
								logSources.map((source) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
									className: cn("flex w-full items-center justify-between rounded-sm px-1.5 py-0.5 text-[0.6rem] transition-colors", logSource === source ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground"),
									onClick: () => setLogSource(source),
									type: "button",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "truncate",
										children: source
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-muted-foreground/60",
										children: sourceCounts[source]
									})]
								}, source))
							]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(LogView, {
							className: "flex-1 border-0 rounded-none max-h-full",
							children: filteredLogs.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-muted-foreground/60",
								children: "No log entries match the filter"
							}) : filteredLogs.map((log) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex gap-2 py-0.5",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: cn("shrink-0 text-[0.55rem] font-semibold uppercase", LOG_LEVEL_COLORS[log.level]),
										children: log.level
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "shrink-0 text-[0.55rem] text-muted-foreground/60 tabular-nums",
										children: new Date(log.timestamp).toLocaleTimeString()
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "shrink-0 text-[0.55rem] text-muted-foreground/40",
										children: [
											"[",
											log.source,
											"]"
										]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-foreground/80",
										children: log.message
									})
								]
							}, log.id))
						})]
					})]
				}),
				activeTab === "metrics" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex-1 space-y-4 overflow-y-auto p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "grid gap-4 sm:grid-cols-2 lg:grid-cols-4",
						children: metrics.map((metric) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center justify-between",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-xs font-medium text-muted-foreground",
										children: metric.label
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: metric.label === "Memory" ? "database" : metric.label === "CPU" ? "cpu" : metric.label === "Extensions" ? "extensions" : "server",
										size: "0.875rem"
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "mt-2 flex items-baseline gap-1",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-2xl font-semibold tabular-nums",
										children: metric.value
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-xs text-muted-foreground",
										children: metric.unit
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "mt-3 h-1.5 overflow-hidden rounded-full bg-(--ui-bg-quinary)",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: cn("h-full rounded-full transition-all", metric.value / metric.max > .8 ? "bg-red-500" : metric.value / metric.max > .5 ? "bg-amber-500" : "bg-emerald-500"),
										style: { width: `${Math.min(metric.value / metric.max * 100, 100)}%` }
									})
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "mt-1 text-right text-[0.55rem] text-muted-foreground",
									children: [
										metric.max,
										" ",
										metric.unit,
										" max"
									]
								})
							]
						}, metric.label))
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-4 sm:grid-cols-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
									className: "mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
									children: "Error Rate"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "flex items-end gap-1",
									style: { height: 80 },
									children: [
										12,
										8,
										15,
										5,
										3,
										9,
										7,
										4,
										6,
										2,
										1,
										3,
										5,
										8,
										4,
										2,
										6,
										3,
										1,
										0,
										2,
										4,
										3,
										1
									].map((v, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: cn("flex-1 rounded-t-sm transition-all", v > 10 ? "bg-red-500" : v > 5 ? "bg-amber-500" : "bg-emerald-500"),
										style: { height: `${v / 15 * 100}%` },
										title: `${v} errors`
									}, i))
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "mt-1 text-[0.55rem] text-muted-foreground",
									children: "Last 24 hours (hourly)"
								})
							]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
								className: "mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
								children: "Plugin Activity"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-2",
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "w-28 truncate text-xs text-muted-foreground",
												children: "Code Analyzer"
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
												className: "h-2 flex-1 overflow-hidden rounded-full bg-(--ui-bg-quinary)",
												children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
													className: "h-full rounded-full bg-primary",
													style: { width: "80%" }
												})
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "w-10 text-right text-xs tabular-nums text-muted-foreground",
												children: "80%"
											})
										]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-2",
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "w-28 truncate text-xs text-muted-foreground",
												children: "Search Assistant"
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
												className: "h-2 flex-1 overflow-hidden rounded-full bg-(--ui-bg-quinary)",
												children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
													className: "h-full rounded-full bg-primary",
													style: { width: "45%" }
												})
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "w-10 text-right text-xs tabular-nums text-muted-foreground",
												children: "45%"
											})
										]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-2",
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "w-28 truncate text-xs text-muted-foreground",
												children: "Task Automation"
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
												className: "h-2 flex-1 overflow-hidden rounded-full bg-(--ui-bg-quinary)",
												children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
													className: "h-full rounded-full bg-primary",
													style: { width: "30%" }
												})
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "w-10 text-right text-xs tabular-nums text-muted-foreground",
												children: "30%"
											})
										]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-2",
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "w-28 truncate text-xs text-muted-foreground",
												children: "MCP Servers"
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
												className: "h-2 flex-1 overflow-hidden rounded-full bg-(--ui-bg-quinary)",
												children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
													className: "h-full rounded-full bg-primary",
													style: { width: "60%" }
												})
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "w-10 text-right text-xs tabular-nums text-muted-foreground",
												children: "60%"
											})
										]
									})
								]
							})]
						})]
					})]
				}),
				activeTab === "inspector" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex-1 overflow-y-auto p-4",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mx-auto max-w-2xl rounded-xl border border-(--ui-stroke-tertiary) px-3 py-2",
						children: renderInspectorNode(INITIAL_INSPECTOR)
					})
				})
			]
		})
	});
}
//#endregion
export { DeveloperToolsView };

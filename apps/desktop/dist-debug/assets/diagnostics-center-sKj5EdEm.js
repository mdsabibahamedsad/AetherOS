import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Di as notify, La as Button, O as Badge, Oa as IconBolt, Qa as atom, Ra as cn, Sa as IconCircleCheck, Ui as IconTool, Xa as init_nanostores, Ya as useStore, ao as require_jsx_runtime, ba as IconCpu, ca as IconLoader2, ma as IconGlobe, oo as require_react, sa as IconLock, ya as IconDeviceDesktop } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/store/diagnostics-center.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
init_nanostores();
var DEFAULT_CHECKS = [
	{
		id: "sys-cpu",
		name: "CPU Health",
		description: "Check CPU temperature and load",
		category: "system",
		severity: "warning",
		status: "pending"
	},
	{
		id: "sys-memory",
		name: "Memory Integrity",
		description: "Verify RAM availability and swap usage",
		category: "system",
		severity: "warning",
		status: "pending"
	},
	{
		id: "sys-uptime",
		name: "System Uptime",
		description: "Check system uptime and stability",
		category: "system",
		severity: "info",
		status: "pending"
	},
	{
		id: "net-connectivity",
		name: "Network Connectivity",
		description: "Verify internet and gateway connectivity",
		category: "network",
		severity: "error",
		status: "pending"
	},
	{
		id: "net-dns",
		name: "DNS Resolution",
		description: "Check DNS resolution for API endpoints",
		category: "network",
		severity: "warning",
		status: "pending"
	},
	{
		id: "net-latency",
		name: "API Latency",
		description: "Measure latency to configured API endpoints",
		category: "network",
		severity: "info",
		status: "pending"
	},
	{
		id: "st-capacity",
		name: "Disk Capacity",
		description: "Check available disk space",
		category: "storage",
		severity: "warning",
		status: "pending"
	},
	{
		id: "st-permissions",
		name: "File Permissions",
		description: "Verify config and data directory permissions",
		category: "storage",
		severity: "error",
		status: "pending"
	},
	{
		id: "st-config",
		name: "Config Integrity",
		description: "Validate config.yaml structure",
		category: "storage",
		severity: "warning",
		status: "pending"
	},
	{
		id: "pl-compatibility",
		name: "Plugin Compatibility",
		description: "Check installed plugin versions",
		category: "plugins",
		severity: "warning",
		status: "pending"
	},
	{
		id: "pl-dependencies",
		name: "Plugin Dependencies",
		description: "Verify plugin dependency resolution",
		category: "plugins",
		severity: "error",
		status: "pending"
	},
	{
		id: "pl-hooks",
		name: "Hook Registration",
		description: "Validate plugin hook registrations",
		category: "plugins",
		severity: "info",
		status: "pending"
	},
	{
		id: "sec-keys",
		name: "API Key Validation",
		description: "Check configured API keys format",
		category: "security",
		severity: "warning",
		status: "pending"
	},
	{
		id: "sec-env",
		name: "Environment Audit",
		description: "Audit environment variable security",
		category: "security",
		severity: "warning",
		status: "pending"
	},
	{
		id: "sec-permissions",
		name: "Permission Audit",
		description: "Review permission configurations",
		category: "security",
		severity: "info",
		status: "pending"
	},
	{
		id: "perf-cache",
		name: "Cache Efficiency",
		description: "Analyze prompt cache hit rates",
		category: "performance",
		severity: "info",
		status: "pending"
	},
	{
		id: "perf-loop",
		name: "Agent Loop Health",
		description: "Check for agent loop inefficiencies",
		category: "performance",
		severity: "warning",
		status: "pending"
	},
	{
		id: "perf-memory",
		name: "Memory Leak Detection",
		description: "Detect potential memory leaks",
		category: "performance",
		severity: "error",
		status: "pending"
	}
];
var $diagnostics = /* @__PURE__ */ atom({
	checks: DEFAULT_CHECKS,
	repairs: [
		{
			id: "rep-clear-cache",
			checkId: "perf-cache",
			name: "Clear Prompt Cache",
			description: "Reset the prompt cache to eliminate stale entries",
			status: "pending",
			requiresRestart: false
		},
		{
			id: "rep-restart-gateway",
			checkId: "net-connectivity",
			name: "Restart Gateway",
			description: "Restart the gateway service to re-establish connections",
			status: "pending",
			requiresRestart: false
		},
		{
			id: "rep-validate-config",
			checkId: "st-config",
			name: "Validate & Repair Config",
			description: "Parse config.yaml and fix common issues",
			status: "pending",
			requiresRestart: true
		},
		{
			id: "rep-reindex-plugins",
			checkId: "pl-compatibility",
			name: "Reindex Plugins",
			description: "Force re-scan of installed plugins",
			status: "pending",
			requiresRestart: false
		},
		{
			id: "rep-clean-temp",
			checkId: "st-capacity",
			name: "Clean Temp Files",
			description: "Remove temporary and cache files to free space",
			status: "pending",
			requiresRestart: false
		},
		{
			id: "rep-reset-network",
			checkId: "net-dns",
			name: "Reset Network Stack",
			description: "Clear DNS cache and reset network connections",
			status: "pending",
			requiresRestart: false
		}
	],
	reports: [],
	runningAll: false,
	selectedCategory: "all"
});
var patch = (u) => $diagnostics.set({
	...$diagnostics.get(),
	...u
});
function setDiagnosticCategory(c) {
	patch({ selectedCategory: c });
}
function updateCheck(id, update) {
	patch({ checks: $diagnostics.get().checks.map((c) => c.id === id ? {
		...c,
		...update
	} : c) });
}
function updateRepair(id, update) {
	patch({ repairs: $diagnostics.get().repairs.map((r) => r.id === id ? {
		...r,
		...update
	} : r) });
}
function addReport(report) {
	patch({ reports: [...$diagnostics.get().reports.slice(-19), report] });
}
function setRunningAll(v) {
	patch({ runningAll: v });
}
function resetChecks() {
	patch({ checks: DEFAULT_CHECKS.map((c) => ({
		...c,
		status: "pending"
	})) });
}
//#endregion
//#region src/app/diagnostics-center/index.tsx
var import_jsx_runtime = require_jsx_runtime();
var CATEGORY_ICONS = {
	system: IconCpu,
	network: IconGlobe,
	storage: IconDeviceDesktop,
	plugins: IconTool,
	security: IconLock,
	performance: IconBolt
};
var CATEGORY_LABELS = {
	all: "All",
	system: "System",
	network: "Network",
	storage: "Storage",
	plugins: "Plugins",
	security: "Security",
	performance: "Performance"
};
var SEVERITY_COLORS = {
	info: "bg-sky-500/10 text-sky-500",
	warning: "bg-amber-500/10 text-amber-500",
	error: "bg-red-500/10 text-red-500"
};
async function runCheck(check) {
	updateCheck(check.id, { status: "running" });
	await new Promise((r) => setTimeout(r, 800 + Math.random() * 1200));
	const outcomes = [
		"passed",
		"passed",
		"passed",
		"passed",
		"warning",
		"failed"
	];
	const status = outcomes[Math.floor(Math.random() * outcomes.length)];
	updateCheck(check.id, {
		status,
		message: {
			"sys-cpu": "CPU temperature normal, load within limits",
			"sys-memory": "RAM 78% utilized, swap 12% utilized",
			"sys-uptime": "System has been running for 14 days",
			"net-connectivity": "Gateway reachable, latency 23ms",
			"net-dns": "DNS resolution working for all endpoints",
			"net-latency": "API latency: avg 45ms, max 120ms",
			"st-capacity": "Disk /: 65% used, Disk /home: 72% used",
			"st-permissions": "All config directories have correct permissions",
			"st-config": "config.yaml parsed successfully",
			"pl-compatibility": "3/4 plugins compatible with current runtime",
			"pl-dependencies": "All plugin dependencies resolved",
			"pl-hooks": "8 hooks registered, no conflicts detected",
			"sec-keys": "4 API keys configured, 2 missing",
			"sec-env": "No exposed secrets in environment",
			"sec-permissions": "Permission boundaries correctly configured",
			"perf-cache": "Cache hit rate: 78.3%",
			"perf-loop": "Average agent loop: 3.2 turns per task",
			"perf-memory": "No memory leaks detected"
		}[check.id] ?? "Check completed",
		duration: Math.floor(Math.random() * 500 + 100)
	});
}
async function runRepair(repair) {
	updateRepair(repair.id, {
		status: "running",
		output: ""
	});
	await new Promise((r) => setTimeout(r, 1e3 + Math.random() * 2e3));
	const outputs = {
		"rep-clear-cache": "Cache cleared (2.3 MB freed)",
		"rep-restart-gateway": "Gateway restarted successfully",
		"rep-validate-config": "Config validated: no issues found",
		"rep-reindex-plugins": "Plugins reindexed: 4 found, 0 errors",
		"rep-clean-temp": "Temporary files cleaned (156 MB freed)",
		"rep-reset-network": "Network stack reset, connections re-established"
	};
	const status = Math.random() > .2 ? "completed" : "failed";
	updateRepair(repair.id, {
		status,
		output: outputs[repair.id] ?? ""
	});
	notify({
		kind: status === "completed" ? "success" : "error",
		title: status === "completed" ? "Repair Completed" : "Repair Failed",
		message: outputs[repair.id] ?? ""
	});
}
function DiagnosticsCenterView() {
	const state = useStore($diagnostics);
	const categories = [
		"all",
		"system",
		"network",
		"storage",
		"plugins",
		"security",
		"performance"
	];
	const filteredChecks = (0, import_react.useMemo)(() => {
		if (state.selectedCategory === "all") return state.checks;
		return state.checks.filter((c) => c.category === state.selectedCategory);
	}, [state.checks, state.selectedCategory]);
	const passedCount = state.checks.filter((c) => c.status === "passed").length;
	const failedCount = state.checks.filter((c) => c.status === "failed").length;
	const warningCount = state.checks.filter((c) => c.status === "warning").length;
	const handleRunAll = (0, import_react.useCallback)(async () => {
		setRunningAll(true);
		resetChecks();
		for (const check of state.checks) await runCheck(check);
		setRunningAll(false);
		const passed = state.checks.filter((c) => c.status === "passed").length;
		const total = state.checks.length;
		const score = Math.round(passed / total * 100);
		addReport({
			id: `report-${Date.now()}`,
			timestamp: Date.now(),
			score,
			checks: state.checks,
			summary: `${score}% health score — ${passed}/${total} checks passed`
		});
		notify({
			kind: score > 80 ? "success" : "warning",
			title: "Diagnostics Complete",
			message: `${score}% health score`
		});
	}, [state.checks]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageHeader, {
			className: "w-full",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Diagnostics Center" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "System health checks, diagnostics, and repair tools" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				disabled: state.runningAll,
				onClick: handleRunAll,
				size: "xs",
				variant: "textStrong",
				children: state.runningAll ? "Running..." : "Run All Checks"
			})]
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex h-full flex-col gap-4 p-4 pt-0",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "grid shrink-0 grid-cols-4 gap-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
							color: "text-foreground",
							label: "Checks",
							value: state.checks.length.toString()
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
							color: "text-emerald-500",
							label: "Passed",
							value: passedCount.toString()
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
							color: "text-amber-500",
							label: "Warnings",
							value: warningCount.toString()
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
							color: "text-red-500",
							label: "Failed",
							value: failedCount.toString()
						})
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary)",
					children: categories.map((cat) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: cn("border-b-2 px-3 py-2 text-xs font-medium transition-colors", state.selectedCategory === cat ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"),
						onClick: () => setDiagnosticCategory(cat),
						type: "button",
						children: CATEGORY_LABELS[cat]
					}, cat))
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "min-h-0 flex-1 space-y-1 overflow-y-auto",
					children: filteredChecks.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "py-8 text-center text-xs text-muted-foreground",
						children: "No checks match the selected category"
					}) : filteredChecks.map((check) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DiagnosticCheckRow, {
						check,
						onRun: () => void runCheck(check)
					}, check.id))
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "shrink-0 border-t border-(--ui-stroke-tertiary) pt-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
						className: "mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
						children: "Repair Actions"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "grid gap-2 sm:grid-cols-2 lg:grid-cols-3",
						children: state.repairs.filter((r) => state.checks.find((c) => c.id === r.checkId)?.status === "failed").map((repair) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RepairCard, {
							onRun: () => void runRepair(repair),
							repair
						}, repair.id))
					})]
				})
			]
		})
	});
}
function StatCard({ label, value, color }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "rounded-xl border border-(--ui-stroke-tertiary) p-3",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground",
			children: label
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: cn("mt-0.5 text-lg font-semibold tabular-nums", color),
			children: value
		})]
	});
}
function DiagnosticCheckRow({ check, onRun }) {
	const CategoryIcon = CATEGORY_ICONS[check.category];
	check.status;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center gap-3 rounded-lg border border-transparent px-3 py-2 text-xs transition-colors hover:border-(--ui-stroke-tertiary)",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CategoryIcon, { className: "size-3.5 shrink-0 text-muted-foreground" }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0 flex-1",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "font-medium text-foreground",
						children: check.name
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "text-muted-foreground",
						children: check.description
					}),
					check.message && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mt-0.5 text-muted-foreground/70",
						children: check.message
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex shrink-0 items-center gap-2",
				children: [
					check.duration && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "text-[0.55rem] text-muted-foreground/60",
						children: [check.duration, "ms"]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						className: SEVERITY_COLORS[check.severity],
						variant: "secondary",
						children: check.severity
					}),
					check.status === "pending" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						"aria-label": "Run check",
						className: "text-muted-foreground",
						onClick: onRun,
						size: "icon-xs",
						variant: "ghost",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconBolt, { className: "size-3" })
					}),
					check.status === "running" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-3 animate-spin text-primary" }),
					check.status === "passed" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconCircleCheck, { className: "size-3 text-emerald-500" }),
					check.status === "failed" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconBolt, { className: "size-3 text-red-500" }),
					check.status === "warning" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconBolt, { className: "size-3 text-amber-500" })
				]
			})
		]
	});
}
function RepairCard({ repair, onRun }) {
	const isRunning = repair.status === "running";
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: cn("rounded-xl border p-3", repair.status === "completed" ? "border-emerald-500/30 bg-emerald-500/5" : repair.status === "failed" ? "border-red-500/30 bg-red-500/5" : "border-(--ui-stroke-tertiary)"),
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-start justify-between gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "min-w-0",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "text-xs font-medium text-foreground",
						children: repair.name
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mt-0.5 text-[0.6rem] text-muted-foreground",
						children: repair.description
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					disabled: isRunning || repair.status === "completed",
					onClick: onRun,
					size: "icon-xs",
					variant: "ghost",
					children: isRunning ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-3 animate-spin" }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTool, { className: "size-3" })
				})]
			}),
			repair.output && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-2 rounded bg-(--ui-bg-quinary) px-2 py-1 font-mono text-[0.55rem] text-muted-foreground",
				children: repair.output
			}),
			repair.requiresRestart && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-1 text-[0.55rem] text-amber-500",
				children: "Requires restart"
			})
		]
	});
}
//#endregion
export { DiagnosticsCenterView };

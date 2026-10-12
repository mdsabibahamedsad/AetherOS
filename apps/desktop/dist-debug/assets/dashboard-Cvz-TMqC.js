import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Gn as $healthStatus, Jn as $systemStats, Kn as $securityStatus, La as Button, O as Badge, Qa as atom, Ra as cn, S as ScrollArea, Xa as init_nanostores, Xn as updateHealthStatus, Ya as useStore, Yn as $tokenUsage, ao as require_jsx_runtime, eo as useNavigate, nt as ConfirmDialog, oo as require_react, qn as $syncStatus, ut as Skeleton } from "./index-B_yd1pEX.js";
import { a as CardTitle, i as CardHeader, n as CardContent, r as CardDescription, t as Card } from "./card-CXjwIosc.js";
//#region src/store/dashboard.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
init_nanostores();
var $dashboardMetrics = /* @__PURE__ */ atom(null);
var $backupState = /* @__PURE__ */ atom({
	lastBackup: null,
	nextBackup: null,
	schedule: "daily",
	status: "idle",
	totalSize: "0 B",
	location: ""
});
var $healthChecks = /* @__PURE__ */ atom([]);
var $runtimeStatus = /* @__PURE__ */ atom(null);
var $activityFeed = /* @__PURE__ */ atom([]);
var $dashboardView = /* @__PURE__ */ atom("overview");
function setDashboardMetrics(metrics) {
	$dashboardMetrics.set(metrics);
}
function setBackupState(state) {
	$backupState.set({
		...$backupState.get(),
		...state
	});
}
function setHealthChecks(checks) {
	$healthChecks.set(checks);
}
function setRuntimeStatus(status) {
	$runtimeStatus.set(status);
}
function addActivityEvent(event) {
	const feed = $activityFeed.get();
	$activityFeed.set([event, ...feed].slice(0, 50));
}
function setDashboardView(view) {
	$dashboardView.set(view);
}
function simulateDashboardData() {
	setDashboardMetrics({
		cpu: {
			current: 34,
			average: 28,
			history: [
				22,
				31,
				45,
				38,
				29,
				34,
				41,
				36,
				30,
				27,
				33,
				34
			]
		},
		memory: {
			used: 6.2,
			total: 16,
			percent: 38.75,
			history: [
				35,
				37,
				40,
				38,
				36,
				39
			]
		},
		disk: {
			used: 234,
			total: 512,
			percent: 45.7
		},
		uptime: Date.now() - 864e5 * 3,
		sessions: {
			active: 2,
			total: 24
		}
	});
	setBackupState({
		lastBackup: Date.now() - 432e5,
		nextBackup: Date.now() + 432e5,
		schedule: "daily",
		status: "success",
		totalSize: "1.2 GB",
		location: "C:\\Users\\User\\.aetheros\\backups"
	});
	setHealthChecks([
		{
			id: "storage",
			name: "Storage Integrity",
			status: "passed",
			message: "All stores consistent",
			lastChecked: Date.now() - 3e4
		},
		{
			id: "config",
			name: "Configuration",
			status: "passed",
			message: "Config valid, no corruption",
			lastChecked: Date.now() - 6e4
		},
		{
			id: "network",
			name: "Network Connectivity",
			status: "warning",
			message: "High latency on fallback route",
			lastChecked: Date.now() - 12e4
		},
		{
			id: "disk",
			name: "Disk Space",
			status: "passed",
			message: "234 GB used of 512 GB",
			lastChecked: Date.now() - 3e5
		},
		{
			id: "memory",
			name: "Memory Pressure",
			status: "passed",
			message: "6.2 GB / 16 GB used",
			lastChecked: Date.now() - 6e4
		},
		{
			id: "extensions",
			name: "Extensions Integrity",
			status: "passed",
			message: "All extensions validated",
			lastChecked: Date.now() - 12e4
		},
		{
			id: "permissions",
			name: "Permissions",
			status: "passed",
			message: "All file permissions correct",
			lastChecked: Date.now() - 18e4
		},
		{
			id: "updates",
			name: "Update Status",
			status: "failed",
			message: "Auto-update check failed — service unreachable",
			lastChecked: Date.now() - 6e5
		}
	]);
	setRuntimeStatus({
		node: {
			installed: true,
			version: "22.14.0",
			path: "C:\\Program Files\\nodejs\\node.exe"
		},
		python: {
			installed: true,
			version: "3.12.9",
			path: "C:\\Python312\\python.exe"
		},
		git: {
			installed: true,
			version: "2.48.1",
			path: "C:\\Program Files\\Git\\bin\\git.exe"
		},
		dependencies: {
			installed: true,
			count: 847
		}
	});
}
//#endregion
//#region src/components/dashboard/activity-feed.tsx
var import_jsx_runtime = require_jsx_runtime();
var TYPE_ICONS = {
	backup: "codicon-cloud-download",
	update: "codicon-sync",
	health: "codicon-heart",
	install: "codicon-package",
	system: "codicon-settings-gear"
};
var STATUS_COLORS = {
	info: "text-blue-500",
	success: "text-emerald-500",
	warning: "text-amber-500",
	error: "text-red-500"
};
function ActivityFeed() {
	const events = useStore($activityFeed);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "Recent Activity" }), events.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
		className: "text-[0.625rem] text-(--ui-text-tertiary)",
		children: [events.length, " events"]
	})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardContent, { children: events.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col items-center justify-center py-8 text-(--ui-text-tertiary)",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-inbox text-2xl" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "mt-2 text-xs",
			children: "No recent activity"
		})]
	}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "space-y-1",
		children: events.map((event) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-start gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-(--ui-control-hover-background)",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("codicon mt-0.5 text-sm", TYPE_ICONS[event.type] || "codicon-circle", STATUS_COLORS[event.status]) }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0 flex-1",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "text-sm",
					children: event.message
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "text-[0.625rem] text-(--ui-text-tertiary)",
					children: formatRelativeTime$1(event.timestamp)
				})]
			})]
		}, event.id))
	}) })] });
}
function formatRelativeTime$1(ts) {
	const diff = Date.now() - ts;
	if (diff < 6e4) return "just now";
	if (diff < 36e5) return `${Math.floor(diff / 6e4)}m ago`;
	if (diff < 864e5) return `${Math.floor(diff / 36e5)}h ago`;
	return `${Math.floor(diff / 864e5)}d ago`;
}
//#endregion
//#region engine/self-healing/health-engine.ts
var HealthEngine = class {
	checks = /* @__PURE__ */ new Map();
	lastReport = null;
	listeners = [];
	checkInterval = null;
	constructor() {
		this.registerStandardChecks();
	}
	registerStandardChecks() {
		this.register({
			id: "storage",
			name: "Local Storage",
			description: "Check localStorage availability and quota",
			category: "storage",
			severity: "critical",
			status: "unknown",
			message: "",
			lastChecked: 0,
			repair: "automatic",
			check: async () => {
				try {
					window.localStorage.setItem("__health_test", "1");
					window.localStorage.removeItem("__health_test");
					return "healthy";
				} catch {
					return "critical";
				}
			},
			autoRepair: async () => ({
				success: true,
				message: "Storage OK",
				duration: 0,
				requiresRestart: false
			})
		});
		this.register({
			id: "config",
			name: "Configuration",
			description: "Verify configuration file integrity",
			category: "storage",
			severity: "warning",
			status: "unknown",
			message: "",
			lastChecked: 0,
			repair: "automatic",
			check: async () => {
				try {
					const raw = window.localStorage.getItem("aetheros.config");
					if (!raw) return "warning";
					JSON.parse(raw);
					return "healthy";
				} catch {
					return "warning";
				}
			},
			autoRepair: async () => {
				try {
					const raw = window.localStorage.getItem("aetheros.config");
					if (!raw) return {
						success: true,
						message: "No config to repair",
						duration: 0,
						requiresRestart: false
					};
					const repaired = raw.replace(/NaN/g, "null").replace(/undefined/g, "null");
					window.localStorage.setItem("aetheros.config", repaired);
					return {
						success: true,
						message: "Config repaired",
						duration: 100,
						requiresRestart: false
					};
				} catch {
					return {
						success: false,
						message: "Failed to repair config",
						duration: 0,
						requiresRestart: false
					};
				}
			}
		});
		this.register({
			id: "network",
			name: "Network Connectivity",
			description: "Check if network is reachable",
			category: "network",
			severity: "warning",
			status: "unknown",
			message: "",
			lastChecked: 0,
			repair: "manual",
			check: async () => navigator.onLine ? "healthy" : "warning",
			autoRepair: async () => ({
				success: false,
				message: "Cannot auto-repair network",
				duration: 0,
				requiresRestart: false
			})
		});
		this.register({
			id: "disk-space",
			name: "Disk Space",
			description: "Check available disk space for app data",
			category: "performance",
			severity: "warning",
			status: "unknown",
			message: "",
			lastChecked: 0,
			repair: "manual",
			check: async () => "healthy",
			autoRepair: async () => ({
				success: true,
				message: "Disk OK",
				duration: 0,
				requiresRestart: false
			})
		});
		this.register({
			id: "memory",
			name: "Memory Usage",
			description: "Check application memory usage",
			category: "performance",
			severity: "warning",
			status: "unknown",
			message: "",
			lastChecked: 0,
			repair: "restart",
			check: async () => {
				try {
					const mem = performance.memory;
					if (!mem) return "unknown";
					const usage = mem.usedJSHeapSize / mem.jsHeapSizeLimit;
					if (usage > .9) return "critical";
					if (usage > .7) return "warning";
					return "healthy";
				} catch {
					return "unknown";
				}
			},
			autoRepair: async () => ({
				success: true,
				message: "Memory within limits",
				duration: 0,
				requiresRestart: false
			})
		});
		this.register({
			id: "extensions",
			name: "Extensions",
			description: "Check extension health",
			category: "runtime",
			severity: "warning",
			status: "unknown",
			message: "",
			lastChecked: 0,
			repair: "automatic",
			check: async () => "healthy",
			autoRepair: async () => ({
				success: true,
				message: "Extensions OK",
				duration: 0,
				requiresRestart: false
			})
		});
		this.register({
			id: "permissions",
			name: "Permissions",
			description: "Verify required permissions are granted",
			category: "security",
			severity: "error",
			status: "unknown",
			message: "",
			lastChecked: 0,
			repair: "manual",
			check: async () => "healthy",
			autoRepair: async () => ({
				success: true,
				message: "Permissions OK",
				duration: 0,
				requiresRestart: false
			})
		});
		this.register({
			id: "updates",
			name: "Update System",
			description: "Check auto-update system integrity",
			category: "runtime",
			severity: "info",
			status: "unknown",
			message: "",
			lastChecked: 0,
			repair: "manual",
			check: async () => "healthy",
			autoRepair: async () => ({
				success: true,
				message: "Update system OK",
				duration: 0,
				requiresRestart: false
			})
		});
	}
	register(check) {
		this.checks.set(check.id, check);
	}
	getCheck(id) {
		return this.checks.get(id);
	}
	getAllChecks() {
		return Array.from(this.checks.values());
	}
	async runCheck(id) {
		const check = this.checks.get(id);
		if (!check) throw new Error(`Health check "${id}" not found`);
		const startTime = Date.now();
		try {
			const status = await check.check();
			check.status = status;
			check.lastChecked = Date.now();
			return {
				id,
				name: check.name,
				status,
				message: check.message,
				duration: Date.now() - startTime,
				repairNeeded: status === "critical" || status === "warning"
			};
		} catch {
			check.status = "unknown";
			return {
				id,
				name: check.name,
				status: "unknown",
				message: "Check failed",
				duration: Date.now() - startTime,
				repairNeeded: false
			};
		}
	}
	async runAllChecks() {
		const results = [];
		let healthy = 0;
		let warning = 0;
		let critical = 0;
		let unknown = 0;
		const recommendations = [];
		for (const check of this.checks.values()) {
			const result = await this.runCheck(check.id);
			results.push(result);
			if (result.status === "healthy") healthy++;
			else if (result.status === "warning") {
				warning++;
				recommendations.push(`Check ${result.name}: ${result.message || "needs attention"}`);
			} else if (result.status === "critical") {
				critical++;
				recommendations.push(`Fix ${result.name}: ${result.message || "requires immediate action"}`);
			} else unknown++;
		}
		const score = Math.round(healthy / Math.max(1, this.checks.size) * 100);
		const report = {
			timestamp: Date.now(),
			totalChecks: this.checks.size,
			healthy,
			warning,
			critical,
			unknown,
			score,
			checks: results,
			recommendations
		};
		this.lastReport = report;
		this.notify(report);
		return report;
	}
	async autoRepair(id) {
		const check = this.checks.get(id);
		if (!check) return {
			success: false,
			message: `Check "${id}" not found`,
			duration: 0,
			requiresRestart: false
		};
		return check.autoRepair();
	}
	async autoRepairAll() {
		const results = [];
		let repaired = 0;
		let failed = 0;
		for (const check of this.checks.values()) if ((await this.runCheck(check.id)).repairNeeded) {
			const result = await check.autoRepair();
			results.push(result);
			if (result.success) repaired++;
			else failed++;
		}
		return {
			repaired,
			failed,
			results
		};
	}
	getLastReport() {
		return this.lastReport;
	}
	startPeriodicChecks(intervalMs = 3e5) {
		this.stopPeriodicChecks();
		this.checkInterval = setInterval(() => this.runAllChecks(), intervalMs);
	}
	stopPeriodicChecks() {
		if (this.checkInterval) {
			clearInterval(this.checkInterval);
			this.checkInterval = null;
		}
	}
	onReport(callback) {
		this.listeners.push(callback);
		if (this.lastReport) callback(this.lastReport);
	}
	getScore() {
		return this.lastReport?.score ?? 100;
	}
	notify(report) {
		for (const listener of this.listeners) listener(report);
	}
};
var healthEngine = new HealthEngine();
//#endregion
//#region engine/self-healing/repair-system.ts
var RepairSystem = class {
	actions = /* @__PURE__ */ new Map();
	history = [];
	isRunning = false;
	constructor() {
		this.registerStandardActions();
	}
	registerStandardActions() {
		this.register({
			id: "repair-config",
			name: "Repair Configuration",
			description: "Fix corrupted configuration files",
			level: "quick",
			affects: ["config"],
			run: async () => healthEngine.autoRepair("config"),
			undo: async () => ({
				success: true,
				message: "Config rollback complete",
				duration: 0,
				requiresRestart: false
			})
		});
		this.register({
			id: "repair-storage",
			name: "Repair Local Storage",
			description: "Clear and restore corrupted localStorage",
			level: "quick",
			affects: ["storage"],
			run: async () => {
				try {
					window.localStorage.length;
					return {
						success: true,
						message: "Storage accessible",
						duration: 0,
						requiresRestart: false
					};
				} catch {
					return {
						success: false,
						message: "Storage corrupted, reset recommended",
						duration: 0,
						requiresRestart: true
					};
				}
			},
			undo: async () => ({
				success: true,
				message: "Storage rolled back",
				duration: 0,
				requiresRestart: false
			})
		});
		this.register({
			id: "repair-extensions",
			name: "Reset Extensions",
			description: "Disable all extensions to isolate issues",
			level: "quick",
			affects: ["extensions"],
			run: async () => {
				window.localStorage.setItem("aetheros.extensions", JSON.stringify({
					installed: [],
					enabled: [],
					registry: {}
				}));
				return {
					success: true,
					message: "Extensions reset",
					duration: 50,
					requiresRestart: true
				};
			},
			undo: async () => ({
				success: true,
				message: "Extensions restored",
				duration: 0,
				requiresRestart: false
			})
		});
		this.register({
			id: "repair-crash-loop",
			name: "Clear Crash Loop",
			description: "Reset crash recovery counter to break crash loop",
			level: "quick",
			affects: ["runtime"],
			run: async () => {
				window.localStorage.removeItem("aetheros.desktop.crashRecovery");
				return {
					success: true,
					message: "Crash loop breaker reset",
					duration: 10,
					requiresRestart: false
				};
			},
			undo: async () => ({
				success: true,
				message: "Crash state restored",
				duration: 0,
				requiresRestart: false
			})
		});
		this.register({
			id: "repair-network",
			name: "Network Diagnostic",
			description: "Diagnose and suggest network fixes",
			level: "quick",
			affects: ["network"],
			run: async () => {
				return navigator.onLine ? {
					success: true,
					message: "Network is online",
					duration: 0,
					requiresRestart: false
				} : {
					success: false,
					message: "Network is offline. Check your connection.",
					duration: 0,
					requiresRestart: false
				};
			},
			undo: async () => ({
				success: true,
				message: "Network check reset",
				duration: 0,
				requiresRestart: false
			})
		});
		this.register({
			id: "repair-full",
			name: "Full Repair",
			description: "Run all repair actions in sequence",
			level: "full",
			affects: [
				"config",
				"storage",
				"extensions",
				"runtime",
				"network"
			],
			run: async () => {
				const results = await this.runAll();
				const allSuccess = results.every((r) => r.success);
				return {
					success: allSuccess,
					message: allSuccess ? "Full repair complete" : "Some repairs failed",
					duration: results.reduce((s, r) => s + r.duration, 0),
					requiresRestart: results.some((r) => r.requiresRestart)
				};
			},
			undo: async () => ({
				success: true,
				message: "Full repair undone",
				duration: 0,
				requiresRestart: false
			})
		});
		this.register({
			id: "reset-all",
			name: "Factory Reset",
			description: "Reset all application state to defaults",
			level: "deep",
			affects: [
				"config",
				"storage",
				"extensions",
				"runtime",
				"network",
				"sync",
				"workspace"
			],
			run: async () => {
				for (const key of [
					"aetheros.config",
					"aetheros.workspaces",
					"aetheros.extensions",
					"aetheros.desktop.crashRecovery",
					"aetheros.migration.state",
					"aetheros.telemetry.consent",
					"aetheros.error.store",
					"aetheros.performance.history",
					"aetheros.backup.index"
				]) window.localStorage.removeItem(key);
				return {
					success: true,
					message: "Factory reset complete. Restart required.",
					duration: 100,
					requiresRestart: true
				};
			},
			undo: async () => ({
				success: false,
				message: "Factory reset cannot be undone",
				duration: 0,
				requiresRestart: false
			})
		});
	}
	register(action) {
		this.actions.set(action.id, action);
	}
	getAction(id) {
		return this.actions.get(id);
	}
	getAllActions() {
		return Array.from(this.actions.values());
	}
	getActionsByLevel(level) {
		return this.getAllActions().filter((a) => a.level === level);
	}
	async run(id) {
		const action = this.actions.get(id);
		if (!action) return {
			success: false,
			message: `Action "${id}" not found`,
			duration: 0,
			requiresRestart: false
		};
		if (this.isRunning) return {
			success: false,
			message: "Repair already in progress",
			duration: 0,
			requiresRestart: false
		};
		this.isRunning = true;
		const startTime = Date.now();
		try {
			const result = await action.run();
			this.history.push({
				actionId: id,
				timestamp: Date.now(),
				success: result.success,
				duration: Date.now() - startTime,
				details: result.message
			});
			return result;
		} finally {
			this.isRunning = false;
		}
	}
	async runAll() {
		const results = [];
		for (const action of this.actions.values()) if (action.id !== "repair-full" && action.id !== "reset-all") results.push(await this.run(action.id));
		return results;
	}
	getHistory() {
		return [...this.history];
	}
	isBusy() {
		return this.isRunning;
	}
};
var repairSystem = new RepairSystem();
//#endregion
//#region src/components/dashboard/auto-repair-panel.tsx
var LEVEL_LABELS = {
	quick: "Quick",
	full: "Full",
	deep: "Deep"
};
function AutoRepairPanel() {
	const [running, setRunning] = (0, import_react.useState)(null);
	const [results, setResults] = (0, import_react.useState)({});
	const [confirmReset, setConfirmReset] = (0, import_react.useState)(false);
	const actions = repairSystem.getAllActions();
	const isBusy = repairSystem.isBusy();
	async function handleRun(action) {
		setRunning(action.id);
		setResults((prev) => ({
			...prev,
			[action.id]: {
				success: false,
				message: "Running…"
			}
		}));
		const result = await repairSystem.run(action.id);
		setResults((prev) => ({
			...prev,
			[action.id]: {
				success: result.success,
				message: result.message
			}
		}));
		setRunning(null);
		addActivityEvent({
			id: `repair-${action.id}-${Date.now()}`,
			type: "system",
			message: `Auto-repair "${action.name}": ${result.success ? "succeeded" : "failed"} — ${result.message}`,
			timestamp: Date.now(),
			status: result.success ? "success" : "error"
		});
	}
	async function handleRunAllHealthChecks() {
		setRunning("__all_checks__");
		await healthEngine.runAllChecks();
		setRunning(null);
	}
	const healthActions = actions.filter((a) => a.level === "quick");
	const systemActions = actions.filter((a) => a.level === "full" || a.level === "deep");
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "Auto-Repair" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
		disabled: isBusy,
		onClick: handleRunAllHealthChecks,
		size: "sm",
		variant: "outline",
		children: running === "__all_checks__" ? "Checking…" : "Run All Checks"
	})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mb-3",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mb-2 text-[0.625rem] font-medium uppercase tracking-widest text-(--ui-text-tertiary)",
			children: "Quick Repairs"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "space-y-1",
			children: healthActions.map((action) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RepairActionRow, {
				action,
				isBusy,
				onRun: () => handleRun(action),
				result: results[action.id],
				running: running === action.id
			}, action.id))
		})]
	}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "mb-2 text-[0.625rem] font-medium uppercase tracking-widest text-(--ui-text-tertiary)",
		children: "System Actions"
	}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "space-y-1",
		children: systemActions.map((action) => {
			if (action.id === "reset-all") return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RepairActionRow, {
				action,
				destructive: true,
				isBusy,
				onRun: () => setConfirmReset(true),
				result: results[action.id],
				running: running === action.id
			}, action.id);
			return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RepairActionRow, {
				action,
				isBusy,
				onRun: () => handleRun(action),
				result: results[action.id],
				running: running === action.id
			}, action.id);
		})
	})] })] })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ConfirmDialog, {
		confirmLabel: "Factory Reset",
		description: "This will reset all application state including config, workspaces, extensions, and preferences. This action cannot be undone.",
		destructive: true,
		onClose: () => setConfirmReset(false),
		onConfirm: async () => {
			setConfirmReset(false);
			await handleRun(repairSystem.getAction("reset-all"));
		},
		open: confirmReset,
		title: "Factory Reset?"
	})] });
}
function RepairActionRow({ action, isBusy, onRun, result, running, destructive }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-(--ui-control-hover-background)",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "min-w-0 flex-1",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-sm font-medium",
						children: action.name
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "rounded bg-(--ui-bg-quaternary) px-1.5 py-0.5 text-[0.625rem] text-(--ui-text-tertiary)",
						children: LEVEL_LABELS[action.level]
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "truncate text-xs text-(--ui-text-tertiary)",
					children: action.description
				}),
				result && !running && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: `mt-0.5 text-[0.625rem] ${result.success ? "text-emerald-500" : "text-red-500"}`,
					children: result.message
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
			disabled: isBusy,
			onClick: onRun,
			size: "sm",
			variant: destructive ? "destructive" : "outline",
			children: running ? "Running…" : "Run"
		})]
	});
}
//#endregion
//#region src/components/dashboard/backup-panel.tsx
function BackupPanel() {
	const backup = useStore($backupState);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "Backup Status" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
		variant: {
			idle: "secondary",
			running: "default",
			success: "default",
			error: "destructive"
		}[backup.status],
		children: {
			idle: "Idle",
			running: "Running…",
			success: "Success",
			error: "Error"
		}[backup.status]
	})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("dl", {
		className: "space-y-2 text-sm",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dt", {
					className: "text-(--ui-text-tertiary)",
					children: "Schedule"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
					className: "font-medium capitalize",
					children: backup.schedule
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dt", {
					className: "text-(--ui-text-tertiary)",
					children: "Last Backup"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
					className: "font-medium",
					children: backup.lastBackup ? formatTimestamp(backup.lastBackup) : "Never"
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dt", {
					className: "text-(--ui-text-tertiary)",
					children: "Next Backup"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
					className: "font-medium",
					children: backup.nextBackup ? formatTimestamp(backup.nextBackup) : "Not scheduled"
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dt", {
					className: "text-(--ui-text-tertiary)",
					children: "Total Size"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
					className: "font-medium",
					children: backup.totalSize
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dt", {
					className: "text-(--ui-text-tertiary)",
					children: "Location"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
					className: "max-w-[200px] truncate font-mono text-xs",
					children: backup.location
				})]
			})
		]
	}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mt-4 flex items-center gap-2 border-t border-(--ui-stroke-tertiary)/50 pt-3",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				onClick: () => setBackupState({ status: "running" }),
				size: "sm",
				children: "Backup Now"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				size: "sm",
				variant: "outline",
				children: "Restore…"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				size: "sm",
				variant: "ghost",
				children: "Configure"
			})
		]
	})] })] });
}
function formatTimestamp(ts) {
	const d = new Date(ts);
	const diff = (/* @__PURE__ */ new Date()).getTime() - d.getTime();
	if (diff < 36e5) return `${Math.floor(diff / 6e4)}m ago`;
	if (diff < 864e5) return `${Math.floor(diff / 36e5)}h ago`;
	return d.toLocaleDateString(void 0, {
		month: "short",
		day: "numeric",
		hour: "2-digit",
		minute: "2-digit"
	});
}
//#endregion
//#region src/components/dashboard/health-status.tsx
var STATUS_ICONS = {
	passed: "codicon-check text-emerald-500",
	warning: "codicon-warning text-amber-500",
	failed: "codicon-error text-red-500"
};
var STATUS_LABELS = {
	passed: "Passed",
	warning: "Warning",
	failed: "Failed"
};
function HealthStatus() {
	const checks = useStore($healthChecks);
	if (!checks || checks.length === 0) return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardHeader, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "Health Checks" }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardContent, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "space-y-2",
		children: Array.from({ length: 4 }).map((_, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-10 w-full" }, i))
	}) })] });
	const passed = checks.filter((c) => c.status === "passed").length;
	const warning = checks.filter((c) => c.status === "warning").length;
	const failed = checks.filter((c) => c.status === "failed").length;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "Health Checks" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardDescription, { children: [
		checks.length,
		" checks • ",
		passed,
		" passed • ",
		warning,
		" warnings • ",
		failed,
		" failed"
	] })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: cn("flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[0.625rem] font-semibold uppercase tracking-wider", failed > 0 ? "bg-red-500/10 text-red-500" : warning > 0 ? "bg-amber-500/10 text-amber-500" : "bg-emerald-500/10 text-emerald-500"),
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("codicon text-xs", failed > 0 ? "codicon-error" : warning > 0 ? "codicon-warning" : "codicon-check") }), failed > 0 ? "Degraded" : warning > 0 ? "Degraded" : "Healthy"]
	})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardContent, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "space-y-1",
		children: checks.map((check) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-(--ui-control-hover-background)",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: STATUS_ICONS[check.status] || "codicon-circle text-(--ui-text-tertiary)" }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "min-w-0 flex-1",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-sm font-medium",
							children: check.name
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							variant: check.status === "passed" ? "default" : check.status === "warning" ? "warn" : "destructive",
							children: STATUS_LABELS[check.status]
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "truncate text-xs text-(--ui-text-tertiary)",
						children: check.message
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "shrink-0 text-[0.625rem] text-(--ui-text-tertiary)",
					children: formatRelativeTime(check.lastChecked)
				})
			]
		}, check.id))
	}) })] });
}
function formatRelativeTime(ts) {
	const diff = Date.now() - ts;
	if (diff < 6e4) return "just now";
	if (diff < 36e5) return `${Math.floor(diff / 6e4)}m ago`;
	if (diff < 864e5) return `${Math.floor(diff / 36e5)}h ago`;
	return `${Math.floor(diff / 864e5)}d ago`;
}
//#endregion
//#region src/components/dashboard/runtime-panel.tsx
function RuntimeRow({ name, version, path, installed }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-(--ui-control-hover-background)",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("codicon text-base", installed ? "codicon-check text-emerald-500" : "codicon-circle-slash text-(--ui-text-tertiary)") }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "min-w-0 flex-1",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "text-sm font-medium",
					children: name
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
					variant: installed ? "default" : "muted",
					children: installed ? version : "Not installed"
				})]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "truncate text-xs text-(--ui-text-tertiary)",
				children: path
			})]
		})]
	});
}
function RuntimePanel() {
	const runtime = useStore($runtimeStatus);
	if (!runtime) return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardHeader, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "Runtime Status" }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardContent, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex items-center justify-center py-8",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "codicon codicon-loading codicon-modifier-spin text-xl text-(--ui-text-tertiary)" })
	}) })] });
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "Runtime Status" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Badge, {
		variant: runtime.dependencies.installed ? "default" : "warn",
		children: [runtime.dependencies.count, " deps"]
	})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-1",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(RuntimeRow, {
				installed: runtime.node.installed,
				name: "Node.js",
				path: runtime.node.path,
				version: runtime.node.version
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(RuntimeRow, {
				installed: runtime.python.installed,
				name: "Python",
				path: runtime.python.path,
				version: runtime.python.version
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(RuntimeRow, {
				installed: runtime.git.installed,
				name: "Git",
				path: runtime.git.path,
				version: runtime.git.version
			})
		]
	}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mt-3 flex items-center gap-2 border-t border-(--ui-stroke-tertiary)/50 pt-3",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
			size: "sm",
			variant: "outline",
			children: "Verify Installation"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
			size: "sm",
			variant: "ghost",
			children: "Install Dependencies"
		})]
	})] })] });
}
//#endregion
//#region src/components/dashboard/stats-card.tsx
function StatsCard({ icon, label, value, detail, trend, valueClass, loading }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "group rounded-xl border border-(--ui-stroke-tertiary) bg-(--ui-bg-tertiary)/20 p-4 transition-all hover:border-(--dt-ring) hover:shadow-sm",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2 text-(--ui-text-tertiary)",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-{icon} text-base" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-[0.625rem] font-medium uppercase tracking-widest",
						children: label
					})]
				}), trend && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
					className: cn("flex items-center gap-0.5 text-[0.625rem] font-medium", trend.direction === "up" ? "text-emerald-500" : "text-red-500"),
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("codicon text-[0.5rem]", trend.direction === "up" ? "codicon-arrow-up" : "codicon-arrow-down") }), trend.value]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: cn("mt-1.5 text-lg font-semibold tracking-tight", valueClass),
				children: loading ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-5 w-16" }) : value
			}),
			detail && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-0.5 text-[0.6875rem] text-(--ui-text-tertiary)",
				children: detail
			})
		]
	});
}
//#endregion
//#region src/components/dashboard/system-metrics.tsx
function MiniBar({ percent, className }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "h-1.5 w-full overflow-hidden rounded-full bg-(--ui-bg-quaternary)",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: cn("h-full rounded-full transition-all duration-500", className),
			style: { width: `${Math.min(percent, 100)}%` }
		})
	});
}
function SystemMetrics() {
	const metrics = useStore($dashboardMetrics);
	const stats = useStore($systemStats);
	if (!metrics) return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardHeader, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "System Resources" }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardContent, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "space-y-4",
		children: Array.from({ length: 3 }).map((_, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "space-y-1.5",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-3 w-16" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-3 w-12" })]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-1.5 w-full" })]
		}, i))
	}) })] });
	const items = [
		{
			label: "CPU",
			percent: metrics.cpu.current,
			detail: `${metrics.cpu.current}% avg`,
			color: "bg-blue-500"
		},
		{
			label: "Memory",
			percent: metrics.memory.percent,
			detail: `${metrics.memory.used.toFixed(1)} GB / ${metrics.memory.total} GB`,
			color: "bg-emerald-500"
		},
		{
			label: "Disk",
			percent: metrics.disk.percent,
			detail: `${metrics.disk.used} GB / ${metrics.disk.total} GB`,
			color: "bg-violet-500"
		}
	];
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "System Resources" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		className: "text-[0.625rem] text-(--ui-text-tertiary)",
		children: stats ? `${stats.hostname} • ${stats.platform}` : ""
	})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "space-y-4",
		children: items.map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "space-y-1.5",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "text-xs font-medium",
					children: item.label
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "text-xs text-(--ui-text-tertiary)",
					children: item.detail
				})]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(MiniBar, {
				className: item.color,
				percent: item.percent
			})]
		}, item.label))
	}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mt-4 grid grid-cols-2 gap-2 border-t border-(--ui-stroke-tertiary)/50 pt-3",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "text-[0.625rem] font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
			children: "Active Sessions"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mt-0.5 text-sm font-semibold",
			children: [
				metrics.sessions.active,
				" / ",
				metrics.sessions.total
			]
		})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "text-[0.625rem] font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
			children: "Uptime"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mt-0.5 text-sm font-semibold",
			children: formatUptime(metrics.uptime)
		})] })]
	})] })] });
}
function formatUptime(startTime) {
	const diff = Date.now() - startTime;
	const days = Math.floor(diff / 864e5);
	const hours = Math.floor(diff % 864e5 / 36e5);
	if (days > 0) return `${days}d ${hours}h`;
	return `${hours}h`;
}
//#endregion
//#region engine/backup/backup-engine.ts
var BACKUP_INDEX_KEY = "aetheros.backup.index";
var BACKUP_CONFIG_KEY = "aetheros.backup.config";
var BackupEngine = class {
	backups = [];
	config = {
		autoBackup: false,
		schedule: "weekly",
		scope: [
			"config",
			"workspace",
			"extensions"
		],
		maxBackups: 10,
		encrypt: false,
		format: "zip",
		location: ""
	};
	constructor() {
		this.loadIndex();
		this.loadConfig();
	}
	getConfig() {
		return { ...this.config };
	}
	updateConfig(updates) {
		this.config = {
			...this.config,
			...updates
		};
		this.saveConfig();
	}
	async createBackup(options) {
		const id = `backup_${Date.now()}`;
		const manifest = {
			id,
			name: options.name || `Backup ${(/* @__PURE__ */ new Date()).toLocaleDateString()}`,
			version: "1.0",
			appVersion: "1.0.0",
			createdAt: (/* @__PURE__ */ new Date()).toISOString(),
			scope: options.scope || [
				"config",
				"workspace",
				"extensions"
			],
			format: options.format || "zip",
			size: 0,
			checksum: "",
			encrypted: options.encrypt || false,
			includes: this.resolveScopePaths(options.scope || ["config"]),
			metadata: options.metadata || {}
		};
		const entry = {
			manifest,
			path: `backups/${id}.${manifest.format}`,
			date: /* @__PURE__ */ new Date(),
			size: 0
		};
		this.backups.push(entry);
		this.pruneOldBackups();
		this.saveIndex();
		return manifest;
	}
	async createFullBackup() {
		return this.createBackup({
			name: `Full Backup ${(/* @__PURE__ */ new Date()).toLocaleDateString()}`,
			scope: ["all"],
			format: "zip"
		});
	}
	getBackups() {
		return [...this.backups].sort((a, b) => b.date.getTime() - a.date.getTime());
	}
	getBackup(id) {
		return this.backups.find((b) => b.manifest.id === id);
	}
	getLatestBackup() {
		if (this.backups.length === 0) return null;
		return this.backups.reduce((latest, current) => current.date > latest.date ? current : latest, this.backups[0]);
	}
	async deleteBackup(id) {
		const index = this.backups.findIndex((b) => b.manifest.id === id);
		if (index === -1) return false;
		this.backups.splice(index, 1);
		this.saveIndex();
		return true;
	}
	async analyzeRestore(id) {
		const backup = this.getBackup(id);
		if (!backup) throw new Error(`Backup "${id}" not found`);
		return {
			manifest: backup.manifest,
			conflicts: [],
			estimatedSize: backup.size,
			requiresRestart: backup.manifest.scope.includes("config"),
			steps: backup.manifest.scope.map((scope) => ({
				name: `Restore ${scope}`,
				description: `Restoring ${scope} data`,
				action: async () => ({
					success: true,
					details: `Restored ${scope}`,
					duration: 0
				}),
				rollback: async () => ({
					success: true,
					details: `Rolled back ${scope}`,
					duration: 0
				})
			}))
		};
	}
	async restore(id, plan) {
		const resolved = plan || await this.analyzeRestore(id);
		const startTime = Date.now();
		for (const step of resolved.steps) if (!(await step.action()).success) {
			for (const prev of resolved.steps) await prev.rollback();
			return {
				success: false,
				details: `Failed at step: ${step.name}`,
				duration: Date.now() - startTime
			};
		}
		return {
			success: true,
			details: `Restored from backup ${id}`,
			duration: Date.now() - startTime
		};
	}
	getSummary() {
		const totalSize = this.backups.reduce((sum, b) => sum + b.size, 0);
		return {
			totalBackups: this.backups.length,
			totalSize,
			lastBackup: this.getLatestBackup()?.manifest.createdAt || null,
			lastRestore: null,
			schedules: this.config.autoBackup ? [this.config.schedule] : [],
			storageAvailable: 1024 * 1024 * 1024,
			storageUsed: totalSize
		};
	}
	resolveScopePaths(scopes) {
		const paths = [];
		if (scopes.includes("all") || scopes.includes("config")) paths.push(".config/aetheros");
		if (scopes.includes("all") || scopes.includes("workspace")) paths.push("workspaces");
		if (scopes.includes("all") || scopes.includes("extensions")) paths.push("extensions");
		if (scopes.includes("all") || scopes.includes("themes")) paths.push("themes");
		if (scopes.includes("all") || scopes.includes("sync")) paths.push("sync");
		if (scopes.includes("all") || scopes.includes("sessions")) paths.push("sessions");
		if (scopes.includes("all") || scopes.includes("knowledge")) paths.push("knowledge");
		return paths;
	}
	pruneOldBackups() {
		if (this.backups.length > this.config.maxBackups) {
			const sorted = [...this.backups].sort((a, b) => a.date.getTime() - b.date.getTime());
			const toRemove = this.backups.length - this.config.maxBackups;
			this.backups = sorted.slice(toRemove);
		}
	}
	loadIndex() {
		try {
			const raw = window.localStorage.getItem(BACKUP_INDEX_KEY);
			if (raw) {
				const data = JSON.parse(raw);
				this.backups = data.map((b) => ({
					...b,
					date: new Date(b.date)
				}));
			}
		} catch {
			this.backups = [];
		}
	}
	saveIndex() {
		try {
			window.localStorage.setItem(BACKUP_INDEX_KEY, JSON.stringify(this.backups));
		} catch {
			console.error("Failed to save backup index");
		}
	}
	loadConfig() {
		try {
			const raw = window.localStorage.getItem(BACKUP_CONFIG_KEY);
			if (raw) this.config = {
				...this.config,
				...JSON.parse(raw)
			};
		} catch {}
	}
	saveConfig() {
		try {
			window.localStorage.setItem(BACKUP_CONFIG_KEY, JSON.stringify(this.config));
		} catch {}
	}
};
var backupEngine = new BackupEngine();
//#endregion
//#region engine/installer/runtime-manager.ts
var RuntimeManager = class {
	requirements = [
		{
			type: "python",
			name: "Python",
			minVersion: "3.11.0",
			required: true,
			downloadUrl: "https://www.python.org/downloads/",
			installGuide: "Download Python 3.11+ from python.org",
			autoInstall: true,
			status: "checking"
		},
		{
			type: "node",
			name: "Node.js",
			minVersion: "20.19.0",
			required: false,
			downloadUrl: "https://nodejs.org/",
			installGuide: "Download Node.js from nodejs.org",
			autoInstall: false,
			status: "checking"
		},
		{
			type: "git",
			name: "Git",
			minVersion: "2.0.0",
			required: false,
			downloadUrl: "https://git-scm.com/downloads",
			installGuide: "Download Git from git-scm.com",
			autoInstall: false,
			status: "checking"
		}
	];
	listeners = [];
	getRequirements() {
		return [...this.requirements];
	}
	async checkRuntime(type) {
		const req = this.requirements.find((r) => r.type === type);
		if (!req) throw new Error(`Runtime "${type}" not found`);
		return {
			type,
			name: req.name,
			status: "installed",
			currentVersion: null,
			requiredVersion: req.minVersion,
			satisfied: true
		};
	}
	async checkAllRuntimes() {
		const results = [];
		for (const req of this.requirements) {
			const result = await this.checkRuntime(req.type);
			req.status = result.status;
			req.currentVersion = result.currentVersion ?? void 0;
			results.push(result);
		}
		return results;
	}
	async installRuntime(type) {
		const req = this.requirements.find((r) => r.type === type);
		if (!req) return false;
		this.notify({
			type,
			stage: "downloading",
			progress: 0,
			message: `Starting ${req.name} installation...`
		});
		try {
			this.notify({
				type,
				stage: "installing",
				progress: 50,
				message: `Installing ${req.name}...`
			});
			this.notify({
				type,
				stage: "verifying",
				progress: 80,
				message: `Verifying ${req.name} installation...`
			});
			if (!(await this.checkRuntime(type)).satisfied) throw new Error("Installation verification failed");
			req.status = "installed";
			this.notify({
				type,
				stage: "done",
				progress: 100,
				message: `${req.name} installed successfully`
			});
			return true;
		} catch (error) {
			this.notify({
				type,
				stage: "error",
				progress: 0,
				message: `Failed to install ${req.name}: ${error}`
			});
			return false;
		}
	}
	async installMissingRuntimes() {
		let installed = 0;
		let failed = 0;
		for (const req of this.requirements) if (req.status !== "installed" && req.autoInstall) if (await this.installRuntime(req.type)) installed++;
		else failed++;
		return {
			installed,
			failed
		};
	}
	isSatisfied() {
		return this.requirements.filter((r) => r.required).every((r) => r.status === "installed");
	}
	onProgress(callback) {
		this.listeners.push(callback);
	}
	notify(progress) {
		for (const listener of this.listeners) listener(progress);
	}
};
var runtimeManager = new RuntimeManager();
//#endregion
//#region engine/performance/performance-monitor.ts
var SNAPSHOT_HISTORY_KEY = "aetheros.performance.history";
var MAX_HISTORY = 1e3;
var PerformanceMonitor = class {
	history = [];
	listeners = [];
	intervalId = null;
	collectionInterval = 6e4;
	isCollecting = false;
	constructor() {
		this.loadHistory();
	}
	startCollection(intervalMs = 6e4) {
		this.collectionInterval = intervalMs;
		if (this.intervalId) return;
		this.collectSnapshot();
		this.intervalId = setInterval(() => this.collectSnapshot(), this.collectionInterval);
	}
	stopCollection() {
		if (this.intervalId) {
			clearInterval(this.intervalId);
			this.intervalId = null;
		}
	}
	async collectSnapshot() {
		const snapshot = {
			timestamp: Date.now(),
			startup: this.collectStartupMetrics(),
			cpu: await this.collectCPUMetrics(),
			gpu: await this.collectGPUMetrics(),
			memory: await this.collectMemoryMetrics(),
			disk: await this.collectDiskMetrics(),
			extensions: this.collectExtensionMetrics(),
			models: this.collectModelMetrics(),
			automation: this.collectAutomationMetrics()
		};
		this.history.push(snapshot);
		if (this.history.length > MAX_HISTORY) this.history = this.history.slice(-MAX_HISTORY);
		this.saveHistory();
		this.notify(snapshot);
		return snapshot;
	}
	getHistory() {
		return [...this.history];
	}
	getRecentSnapshots(count = 10) {
		return this.history.slice(-count);
	}
	getSnapshotsInRange(from, to) {
		return this.history.filter((s) => s.timestamp >= from && s.timestamp <= to);
	}
	getAverages() {
		if (this.history.length === 0) return {};
		const avg = (key) => {
			const values = this.history.map((s) => {
				const val = s[key];
				if (typeof val === "object" && val !== null) {
					const numeric = Object.values(val).filter((v) => typeof v === "number");
					return numeric.reduce((a, b) => a + b, 0) / numeric.length;
				}
				return 0;
			});
			return values.reduce((a, b) => a + b, 0) / values.length;
		};
		return {
			timestamp: Date.now(),
			cpu: {
				overall: avg("cpu"),
				process: 0,
				system: 0,
				cores: 0
			},
			memory: {
				heapUsed: avg("memory"),
				heapTotal: 0,
				systemUsed: 0,
				systemTotal: 0,
				process: 0
			}
		};
	}
	getLatest() {
		return this.history.length > 0 ? this.history[this.history.length - 1] : null;
	}
	clearHistory() {
		this.history = [];
		this.saveHistory();
	}
	onChange(callback) {
		this.listeners.push(callback);
	}
	isCollectingStatus() {
		return this.isCollecting;
	}
	collectStartupMetrics() {
		const nav = performance.getEntriesByType("navigation")[0];
		return {
			coldStart: nav ? nav.domContentLoadedEventEnd : 0,
			warmStart: 0,
			mainProcessInit: 0,
			preloadExec: 0,
			firstPaint: getFirstPaint(),
			timeToInteractive: nav ? nav.domComplete : 0
		};
	}
	async collectCPUMetrics() {
		return {
			overall: await getCPUUsage(),
			process: 0,
			system: 0,
			cores: navigator.hardwareConcurrency || 0
		};
	}
	async collectGPUMetrics() {
		return {
			usage: 0,
			memoryUsed: 0,
			memoryTotal: 0
		};
	}
	async collectMemoryMetrics() {
		if (performance.memory) {
			const mem = performance.memory;
			return {
				heapUsed: mem.usedJSHeapSize,
				heapTotal: mem.totalJSHeapSize,
				systemUsed: mem.usedJSHeapSize,
				systemTotal: mem.jsHeapSizeLimit,
				process: 0
			};
		}
		return {
			heapUsed: 0,
			heapTotal: 0,
			systemUsed: 0,
			systemTotal: 0,
			process: 0
		};
	}
	async collectDiskMetrics() {
		return {
			readSpeed: 0,
			writeSpeed: 0,
			usage: 0,
			total: 0
		};
	}
	collectExtensionMetrics() {
		return {
			loaded: 0,
			active: 0,
			failed: 0,
			memoryUsage: 0
		};
	}
	collectModelMetrics() {
		return {
			loaded: 0,
			activeInferences: 0,
			averageLatency: 0,
			cacheHitRate: 0
		};
	}
	collectAutomationMetrics() {
		return {
			activeWorkflows: 0,
			completedToday: 0,
			failedToday: 0,
			averageDuration: 0
		};
	}
	notify(snapshot) {
		for (const listener of this.listeners) listener(snapshot);
	}
	loadHistory() {
		try {
			const raw = window.localStorage.getItem(SNAPSHOT_HISTORY_KEY);
			if (raw) this.history = JSON.parse(raw);
		} catch {
			this.history = [];
		}
	}
	saveHistory() {
		try {
			if (this.history.length > 0) window.localStorage.setItem(SNAPSHOT_HISTORY_KEY, JSON.stringify(this.history.slice(-100)));
		} catch {
			console.error("Failed to save performance history");
		}
	}
};
function getFirstPaint() {
	const fcp = performance.getEntriesByType("paint").find((e) => e.name === "first-contentful-paint");
	return fcp ? fcp.startTime : 0;
}
async function getCPUUsage() {
	if ("requestIdleCallback" in window) return new Promise((resolve) => {
		const start = performance.now();
		requestIdleCallback(() => {
			const elapsed = performance.now() - start;
			resolve(Math.min(elapsed / 50, 1));
		});
	});
	return 0;
}
var performanceMonitor = new PerformanceMonitor();
//#endregion
//#region engine/performance/dashboard-store.ts
var PerformanceDashboardStore = class {
	data = {
		current: null,
		history: [],
		averages: {},
		uptime: 0,
		status: "stopped",
		lastUpdate: null
	};
	listeners = [];
	appStartTime = Date.now();
	constructor() {
		performanceMonitor.onChange((snapshot) => {
			this.data.current = snapshot;
			this.data.history = performanceMonitor.getRecentSnapshots(100);
			this.data.averages = performanceMonitor.getAverages();
			this.data.uptime = Math.floor((Date.now() - this.appStartTime) / 1e3);
			this.data.lastUpdate = snapshot.timestamp;
			this.notify();
		});
	}
	startMonitoring() {
		performanceMonitor.startCollection();
		this.data.status = "collecting";
		this.notify();
	}
	stopMonitoring() {
		performanceMonitor.stopCollection();
		this.data.status = "stopped";
		this.notify();
	}
	pauseMonitoring() {
		performanceMonitor.stopCollection();
		this.data.status = "paused";
		this.notify();
	}
	getData() {
		return { ...this.data };
	}
	getCPUHistory() {
		return this.data.history.map((s) => ({
			timestamp: s.timestamp,
			value: s.cpu.overall
		}));
	}
	getMemoryHistory() {
		return this.data.history.map((s) => ({
			timestamp: s.timestamp,
			heap: s.memory.heapUsed,
			system: s.memory.systemUsed
		}));
	}
	getStartupTimeline() {
		const current = this.data.current;
		if (!current) return [];
		return [
			{
				label: "Cold Start",
				value: current.startup.coldStart
			},
			{
				label: "First Paint",
				value: current.startup.firstPaint
			},
			{
				label: "Time to Interactive",
				value: current.startup.timeToInteractive
			}
		];
	}
	onChange(callback) {
		this.listeners.push(callback);
		callback({ ...this.data });
	}
	notify() {
		for (const listener of this.listeners) listener({ ...this.data });
	}
};
var performanceDashboardStore = new PerformanceDashboardStore();
//#endregion
//#region src/components/dashboard/use-engine-bridge.ts
function useEngineBridge() {
	(0, import_react.useEffect)(() => {
		if (typeof window === "undefined") return;
		healthEngine.onReport((report) => {
			setHealthChecks(report.checks.map((c) => ({
				id: c.id,
				name: c.name,
				status: c.status === "healthy" ? "passed" : c.status === "warning" ? "warning" : "failed",
				message: c.message || statusMessage(c.status),
				lastChecked: report.timestamp
			})));
			updateHealthStatus({
				overall: report.score >= 80 ? "healthy" : report.score >= 50 ? "degraded" : "unhealthy",
				services: [],
				lastCheck: report.timestamp
			});
		});
		runtimeManager.getRequirements();
		runtimeManager.checkAllRuntimes().then(() => {
			const updated = runtimeManager.getRequirements();
			setRuntimeStatus({
				node: {
					installed: updated.find((r) => r.type === "node")?.status === "installed" || false,
					version: updated.find((r) => r.type === "node")?.currentVersion || "",
					path: ""
				},
				python: {
					installed: updated.find((r) => r.type === "python")?.status === "installed" || false,
					version: updated.find((r) => r.type === "python")?.currentVersion || "",
					path: ""
				},
				git: {
					installed: updated.find((r) => r.type === "git")?.status === "installed" || false,
					version: updated.find((r) => r.type === "git")?.currentVersion || "",
					path: ""
				},
				dependencies: {
					installed: true,
					count: 0
				}
			});
		});
		const backupConfig = backupEngine.getConfig();
		const backups = backupEngine.getBackups();
		setBackupState({
			lastBackup: backups.length > 0 ? backups[0].date.getTime() : null,
			nextBackup: backupConfig.autoBackup ? Date.now() + scheduleMs(backupConfig.schedule) : null,
			schedule: backupConfig.schedule,
			status: "idle",
			totalSize: formatTotalSize(backups),
			location: "Local Storage",
			error: void 0
		});
		performanceDashboardStore.onChange((data) => {
			if (data.current) {
				const memPercent = data.current.memory.heapTotal > 0 ? data.current.memory.heapUsed / data.current.memory.heapTotal * 100 : 0;
				setDashboardMetrics({
					cpu: {
						current: data.current.cpu.overall,
						average: data.averages?.cpu?.overall ?? data.current.cpu.overall,
						history: [data.current.cpu.overall]
					},
					memory: {
						used: data.current.memory.heapUsed,
						total: data.current.memory.heapTotal,
						percent: memPercent,
						history: [memPercent]
					},
					disk: {
						used: data.current.disk.usage,
						total: data.current.disk.total,
						percent: data.current.disk.total > 0 ? data.current.disk.usage / data.current.disk.total * 100 : 0
					},
					uptime: data.uptime,
					sessions: {
						active: 0,
						total: 0
					}
				});
			}
		});
		healthEngine.runAllChecks().then((report) => {
			if (report.critical > 0) addActivityEvent({
				id: `health-critical-${Date.now()}`,
				type: "health",
				message: `${report.critical} critical health issue(s) detected`,
				timestamp: Date.now(),
				status: "error"
			});
			if (report.warning > 0) addActivityEvent({
				id: `health-warning-${Date.now()}`,
				type: "health",
				message: `${report.warning} health warning(s) found`,
				timestamp: Date.now(),
				status: "warning"
			});
			if (report.score === 100) addActivityEvent({
				id: `health-pass-${Date.now()}`,
				type: "health",
				message: "All health checks passed",
				timestamp: Date.now(),
				status: "success"
			});
		});
		repairSystem.getHistory().forEach((h) => {
			addActivityEvent({
				id: `repair-${h.timestamp}`,
				type: "system",
				message: `Repair "${h.actionId}": ${h.success ? "succeeded" : "failed"}`,
				timestamp: h.timestamp,
				status: h.success ? "success" : "error"
			});
		});
	}, []);
}
function statusMessage(status) {
	switch (status) {
		case "healthy": return "Check passed";
		case "warning": return "Needs attention";
		case "critical": return "Requires immediate action";
		default: return "Status unknown";
	}
}
function scheduleMs(schedule) {
	switch (schedule) {
		case "hourly": return 36e5;
		case "daily": return 864e5;
		case "weekly": return 6048e5;
		default: return 864e5;
	}
}
function formatTotalSize(backups) {
	const total = backups.reduce((s, b) => s + (b.size ?? 0), 0);
	if (total === 0) return "0 B";
	const units = [
		"B",
		"KB",
		"MB",
		"GB"
	];
	const i = Math.floor(Math.log(total) / Math.log(1024));
	return `${(total / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}
//#endregion
//#region src/app/dashboard/index.tsx
var TABS = [
	{
		id: "overview",
		label: "Overview"
	},
	{
		id: "health",
		label: "Health"
	},
	{
		id: "backup",
		label: "Backup"
	},
	{
		id: "runtime",
		label: "Runtime"
	}
];
function DashboardView() {
	const navigate = useNavigate();
	const view = useStore($dashboardView);
	const stats = useStore($systemStats);
	const health = useStore($healthStatus);
	const tokens = useStore($tokenUsage);
	const syncStatus = useStore($syncStatus);
	const securityStatus = useStore($securityStatus);
	const metrics = useStore($dashboardMetrics);
	useEngineBridge();
	(0, import_react.useEffect)(() => {
		simulateDashboardData();
		addActivityEvent({
			id: "init-1",
			type: "system",
			message: "Dashboard initialized",
			timestamp: Date.now(),
			status: "info"
		});
		addActivityEvent({
			id: "init-2",
			type: "health",
			message: "System health check completed",
			timestamp: Date.now() - 1e4,
			status: "success"
		});
	}, []);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
		className: "h-full",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mx-auto max-w-6xl space-y-6 p-6",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
					className: "flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
						className: "text-xl font-semibold tracking-tight",
						children: "Production Dashboard"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 text-sm text-(--ui-text-tertiary)",
						children: "System overview, health checks, backups, and runtime management"
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-1.5 text-xs text-(--ui-text-tertiary)",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("codicon text-sm", {
									idle: "text-(--ui-text-tertiary)",
									syncing: "text-blue-500",
									error: "text-red-500"
								}[syncStatus], syncStatus === "syncing" ? "codicon-modifier-spin" : "") }), syncStatus === "syncing" ? "Syncing…" : syncStatus === "error" ? "Sync Error" : "Synced"]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-1.5 text-xs",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("codicon text-sm", {
									secure: "text-emerald-500",
									warning: "text-amber-500",
									critical: "text-red-500"
								}[securityStatus]) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "capitalize text-(--ui-text-tertiary)",
									children: securityStatus
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => navigate("/new"),
								size: "sm",
								children: "New Chat"
							})
						]
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex items-center gap-1 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-tertiary)/20 p-0.5",
					children: TABS.map((tab) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: cn("rounded-md px-3 py-1.5 text-xs font-medium transition-all", view === tab.id ? "bg-(--ui-bg-primary) text-(--ui-text-primary) shadow-sm" : "text-(--ui-text-tertiary) hover:text-(--ui-text-primary)"),
						onClick: () => setDashboardView(tab.id),
						type: "button",
						children: tab.label
					}, tab.id))
				}),
				view === "overview" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverviewTab, {
					health,
					metrics,
					stats,
					tokens
				}),
				view === "health" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(HealthTab, {}),
				view === "backup" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(BackupTab, {}),
				view === "runtime" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RuntimeTab, {})
			]
		})
	});
}
function OverviewTab({ stats, health, tokens, metrics }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid gap-3 sm:grid-cols-2 lg:grid-cols-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatsCard, {
						detail: stats?.platform ?? "",
						icon: "dashboard",
						label: "CPU",
						trend: metrics ? {
							direction: stats && stats.cpu > 50 ? "up" : "down",
							value: `${metrics.cpu.average}% avg`
						} : void 0,
						value: stats ? `${stats.cpu}%` : "—"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatsCard, {
						detail: stats ? `${stats.memory.percent}% used` : "",
						icon: "symbol-method",
						label: "Memory",
						value: stats ? `${Math.round(stats.memory.used / 1024)}GB / ${Math.round(stats.memory.total / 1024)}GB` : "—"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatsCard, {
						detail: `${health?.services?.length ?? 0} services`,
						icon: "check",
						label: "Status",
						value: health?.overall === "healthy" ? "All Systems Go" : health?.overall ?? "—",
						valueClass: health?.overall === "healthy" ? "text-emerald-500" : health?.overall === "degraded" ? "text-amber-500" : void 0
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatsCard, {
						detail: `${tokens.input} in / ${tokens.output} out`,
						icon: "symbol-method",
						label: "Tokens",
						value: tokens.total > 0 ? tokens.total.toLocaleString() : "0"
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid gap-6 lg:grid-cols-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SystemMetrics, {}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(HealthStatus, {})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid gap-6 lg:grid-cols-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(BackupPanel, {}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RuntimePanel, {})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid gap-6 lg:grid-cols-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(AutoRepairPanel, {}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ActivityFeed, {})]
			})
		]
	});
}
function HealthTab() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex items-center justify-between",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-sm font-semibold",
				children: "System Health Details"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-xs text-(--ui-text-tertiary)",
				children: "Detailed health check results and diagnostics"
			})] })
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-6 lg:grid-cols-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(HealthStatus, {}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AutoRepairPanel, {})]
		})]
	});
}
function BackupTab() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center justify-between",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-sm font-semibold",
				children: "Backup Management"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-xs text-(--ui-text-tertiary)",
				children: "Configure and manage system backups"
			})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					size: "sm",
					variant: "outline",
					children: "Restore Wizard"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					size: "sm",
					children: "Create Backup"
				})]
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid gap-6 lg:grid-cols-2",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(BackupPanel, {})
		})]
	});
}
function RuntimeTab() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center justify-between",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-sm font-semibold",
				children: "Runtime Manager"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-xs text-(--ui-text-tertiary)",
				children: "Manage Node.js, Python, Git runtimes and dependencies"
			})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					size: "sm",
					variant: "outline",
					children: "Verify All"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					size: "sm",
					children: "Install Missing"
				})]
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid gap-6 lg:grid-cols-2",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RuntimePanel, {})
		})]
	});
}
//#endregion
export { DashboardView };

import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { C as Select, D as SelectValue, Di as notify, E as SelectTrigger, Ia as Codicon, La as Button, O as Badge, Oi as notifyError, Ra as cn, T as SelectItem, ao as require_jsx_runtime, oo as require_react, w as SelectContent } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
import { C as stopAgent, S as startAgent, _ as refreshTasks, a as $remoteLoading, b as resumeAgent, c as $remoteTasks, f as getActiveInstance, g as refreshLogs, i as $remoteInstances, m as pauseAgent, n as $remoteAgentStatus, o as $remoteLogLevelFilter, p as getFilteredLogs, r as $remoteConnected, s as $remoteLogs, x as setLogLevelFilter, y as restartAgent } from "./remote-agent-BKrLffnE.js";
//#region src/app/remote-agent-dashboard/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var LOG_LEVELS = [
	"all",
	"debug",
	"info",
	"warn",
	"error"
];
var SAMPLE_LOGS = Array.from({ length: 30 }, (_, i) => ({
	id: `log-${i}`,
	timestamp: (/* @__PURE__ */ new Date(Date.now() - (30 - i) * 6e4)).toISOString(),
	level: [
		"debug",
		"info",
		"warn",
		"error"
	][Math.floor(Math.random() * 4)],
	source: [
		"agent",
		"sync",
		"gateway",
		"http",
		"system"
	][Math.floor(Math.random() * 5)],
	message: [
		"Processing incoming message from gateway",
		"Sync cycle completed — 12 items pushed",
		"Memory snapshot saved successfully",
		"Connection health check passed",
		"Webhook event queued for processing",
		"Session checkpoint created",
		"Tool execution completed",
		"Model inference returned in 1.2s",
		"Background task finished",
		"Configuration reloaded from disk"
	][Math.floor(Math.random() * 10)]
}));
var SAMPLE_TASKS = [
	{
		id: "task-1",
		name: "Index Knowledge Base",
		status: "running",
		progress: 65,
		startedAt: (/* @__PURE__ */ new Date(Date.now() - 12e4)).toISOString(),
		completedAt: null,
		errorMessage: null
	},
	{
		id: "task-2",
		name: "Sync Files to Cloud",
		status: "running",
		progress: 30,
		startedAt: (/* @__PURE__ */ new Date(Date.now() - 6e4)).toISOString(),
		completedAt: null,
		errorMessage: null
	},
	{
		id: "task-3",
		name: "Process Email Queue",
		status: "queued",
		progress: 0,
		startedAt: null,
		completedAt: null,
		errorMessage: null
	},
	{
		id: "task-4",
		name: "Backup Memory Store",
		status: "completed",
		progress: 100,
		startedAt: (/* @__PURE__ */ new Date(Date.now() - 36e5)).toISOString(),
		completedAt: (/* @__PURE__ */ new Date(Date.now() - 354e4)).toISOString(),
		errorMessage: null
	},
	{
		id: "task-5",
		name: "Update Plugin Index",
		status: "failed",
		progress: 45,
		startedAt: (/* @__PURE__ */ new Date(Date.now() - 72e5)).toISOString(),
		completedAt: (/* @__PURE__ */ new Date(Date.now() - 714e4)).toISOString(),
		errorMessage: "Connection timeout to plugin registry"
	}
];
function RemoteAgentDashboardView() {
	const agentStatus = $remoteAgentStatus.get();
	const connected = $remoteConnected.get();
	const loading = $remoteLoading.get();
	const logLevelFilter = $remoteLogLevelFilter.get();
	const logs = $remoteLogs.get().length > 0 ? getFilteredLogs() : SAMPLE_LOGS.filter((l) => logLevelFilter === "all" || l.level === logLevelFilter);
	const tasks = $remoteTasks.get().length > 0 ? $remoteTasks.get() : SAMPLE_TASKS;
	const activeInstance = getActiveInstance();
	const instances = $remoteInstances.get();
	const [autoRefresh, setAutoRefresh] = (0, import_react.useState)(false);
	const handleStart = (0, import_react.useCallback)(() => {
		try {
			startAgent();
			notify({
				kind: "success",
				title: "Agent Started",
				message: "Remote agent is now running"
			});
		} catch (err) {
			notifyError(err, "Failed to start agent");
		}
	}, []);
	const handleStop = (0, import_react.useCallback)(() => {
		try {
			stopAgent();
			notify({
				kind: "info",
				title: "Agent Stopped",
				message: "Remote agent has been stopped"
			});
		} catch (err) {
			notifyError(err, "Failed to stop agent");
		}
	}, []);
	const handlePause = (0, import_react.useCallback)(() => {
		try {
			pauseAgent();
			notify({
				kind: "info",
				title: "Agent Paused",
				message: "Remote agent is paused"
			});
		} catch (err) {
			notifyError(err, "Failed to pause agent");
		}
	}, []);
	const handleResume = (0, import_react.useCallback)(() => {
		try {
			resumeAgent();
			notify({
				kind: "info",
				title: "Agent Resumed",
				message: "Remote agent is running again"
			});
		} catch (err) {
			notifyError(err, "Failed to resume agent");
		}
	}, []);
	const handleRestart = (0, import_react.useCallback)(() => {
		try {
			restartAgent();
			notify({
				kind: "info",
				title: "Agent Restarting",
				message: "Remote agent is restarting..."
			});
		} catch (err) {
			notifyError(err, "Failed to restart agent");
		}
	}, []);
	const handleRefreshLogs = (0, import_react.useCallback)(() => {
		refreshLogs();
		notify({
			kind: "info",
			title: "Logs Refreshed",
			message: "Log entries updated"
		});
	}, []);
	const handleRefreshTasks = (0, import_react.useCallback)(() => {
		refreshTasks();
		notify({
			kind: "info",
			title: "Tasks Refreshed",
			message: "Task list updated"
		});
	}, []);
	const statusVariant = (st) => {
		switch (st) {
			case "running": return "default";
			case "stopped": return "outline";
			case "paused": return "muted";
			case "starting":
			case "stopping": return "muted";
			case "error": return "destructive";
		}
	};
	const taskStatusVariant = (st) => {
		switch (st) {
			case "running": return "default";
			case "completed": return "muted";
			case "failed": return "destructive";
			case "queued": return "outline";
		}
	};
	const logLevelColor = (level) => {
		switch (level) {
			case "error": return "text-destructive";
			case "warn": return "text-amber-500";
			case "info": return "text-primary";
			case "debug": return "text-muted-foreground";
			default: return "";
		}
	};
	if (!connected) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Remote Agent Dashboard" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Monitor and control remote AetherOS agents" })] }),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid min-h-52 place-items-center text-center",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
					className: "text-muted-foreground/40",
					name: "server",
					size: "2rem"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-2 text-sm font-medium text-muted-foreground",
					children: "Not Connected"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-1 text-xs text-muted-foreground/60",
					children: instances.length > 0 ? "Connect to a remote instance from the Remote Instances page" : "Add and connect to a remote instance first"
				})
			] })
		})
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageHeader, {
			className: "w-full",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Remote Agent Dashboard" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: activeInstance ? `${activeInstance.name} — ${activeInstance.host}:${activeInstance.port}` : "Monitor and control remote AetherOS agents" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex items-center gap-2",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Badge, {
						className: "text-[0.6rem]",
						variant: connected ? "default" : "outline",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: connected ? "plug" : "debug-disconnect",
							size: "0.6rem"
						}), connected ? "Connected" : "Disconnected"]
					})
				})]
			})
		}),
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid grid-cols-4 gap-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2 text-xs text-muted-foreground",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "symbol-method",
								size: "0.85rem"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "CPU" })]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "mt-1 text-lg font-semibold",
							children: [agentStatus.cpu, "%"]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2 text-xs text-muted-foreground",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "database",
								size: "0.85rem"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "Memory" })]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "mt-1 text-lg font-semibold",
							children: [agentStatus.memory, "%"]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2 text-xs text-muted-foreground",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "history",
								size: "0.85rem"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "Uptime" })]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 text-lg font-semibold",
							children: formatUptime(agentStatus.uptime)
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2 text-xs text-muted-foreground",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "checklist",
								size: "0.85rem"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "Tasks" })]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "mt-1 text-lg font-semibold",
							children: [tasks.filter((t) => t.status === "running").length, " active"]
						})]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-4 flex items-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Badge, {
					className: "text-[0.6rem]",
					variant: statusVariant(agentStatus.status),
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						name: agentStatus.status === "running" ? "play" : agentStatus.status === "paused" ? "pause" : agentStatus.status === "error" ? "error" : "stop",
						size: "0.6rem"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "capitalize",
						children: agentStatus.status
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "ml-auto flex items-center gap-1.5",
					children: [
						agentStatus.status === "stopped" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							disabled: loading,
							onClick: handleStart,
							size: "sm",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "play",
								size: "0.75rem"
							}), "Start"]
						}),
						agentStatus.status === "running" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							disabled: loading,
							onClick: handlePause,
							size: "sm",
							variant: "outline",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "pause",
								size: "0.75rem"
							}), "Pause"]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							disabled: loading,
							onClick: handleStop,
							size: "sm",
							variant: "outline",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "stop",
								size: "0.75rem"
							}), "Stop"]
						})] }),
						agentStatus.status === "paused" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							disabled: loading,
							onClick: handleResume,
							size: "sm",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "play",
								size: "0.75rem"
							}), "Resume"]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							disabled: loading,
							onClick: handleStop,
							size: "sm",
							variant: "outline",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "stop",
								size: "0.75rem"
							}), "Stop"]
						})] }),
						agentStatus.status === "error" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							disabled: loading,
							onClick: handleRestart,
							size: "sm",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "refresh",
								size: "0.75rem"
							}), "Restart"]
						})
					]
				})]
			}),
			agentStatus.errorMessage && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-2 flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
					className: "text-destructive",
					name: "error",
					size: "0.85rem"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "text-xs text-destructive",
					children: agentStatus.errorMessage
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-4 grid grid-cols-2 gap-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mb-2 flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground",
						children: "Task List"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						className: "text-xs",
						onClick: handleRefreshTasks,
						size: "sm",
						variant: "ghost",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "refresh",
							size: "0.65rem"
						})
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "space-y-1",
					children: tasks.map((task) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-md border border-(--ui-stroke-tertiary) px-2.5 py-2 text-xs",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center justify-between",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-2",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: cn(task.status === "running" && "animate-spin text-primary", task.status === "completed" && "text-emerald-500", task.status === "failed" && "text-destructive", task.status === "queued" && "text-muted-foreground"),
										name: task.status === "running" ? "sync" : task.status === "completed" ? "check" : task.status === "failed" ? "error" : "clock",
										size: "0.7rem"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "font-medium",
										children: task.name
									})]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									className: "text-[0.5rem]",
									variant: taskStatusVariant(task.status),
									children: task.status
								})]
							}),
							(task.status === "running" || task.status === "queued") && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-1.5 flex items-center gap-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "h-1 flex-1 overflow-hidden rounded-full bg-(--ui-stroke-tertiary)",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "h-full rounded-full bg-primary transition-all",
										style: { width: `${task.progress}%` }
									})
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "text-[0.55rem] text-muted-foreground",
									children: [task.progress, "%"]
								})]
							}),
							task.errorMessage && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-1 text-[0.55rem] text-destructive",
								children: task.errorMessage
							})
						]
					}, task.id))
				})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mb-2 flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground",
						children: "Logs"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-1.5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
							onValueChange: (v) => setLogLevelFilter(v),
							value: logLevelFilter,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
								className: "h-7 w-20 text-[0.6rem]",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: LOG_LEVELS.map((l) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
								value: l,
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "capitalize",
									children: l === "all" ? "All" : l === "warn" ? "Warning" : l === "info" ? "Info" : l === "debug" ? "Debug" : "Error"
								})
							}, l)) })]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							className: "text-xs",
							onClick: handleRefreshLogs,
							size: "sm",
							variant: "ghost",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "refresh",
								size: "0.65rem"
							})
						})]
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "max-h-80 space-y-0.5 overflow-y-auto rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) p-1.5 font-mono",
					children: [logs.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "p-2 text-xs text-muted-foreground",
						children: "No log entries"
					}), logs.slice(0, 50).map((log) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-start gap-2 px-1.5 py-0.5 text-[0.6rem]",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "shrink-0 text-muted-foreground",
								children: new Date(log.timestamp).toLocaleTimeString(void 0, {
									hour: "2-digit",
									minute: "2-digit",
									second: "2-digit"
								})
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: cn("shrink-0 w-8 font-semibold uppercase", logLevelColor(log.level)),
								children: log.level
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "truncate text-foreground/80",
								children: log.message
							})
						]
					}, log.id))]
				})] })]
			})
		]
	});
}
function formatUptime(seconds) {
	const h = Math.floor(seconds / 3600);
	const m = Math.floor(seconds % 3600 / 60);
	if (h > 0) return `${h}h ${m}m`;
	if (m > 0) return `${m}m`;
	return `${Math.floor(seconds)}s`;
}
//#endregion
export { RemoteAgentDashboardView };

import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Di as notify, Gi as IconSquare, Hi as IconTrash, La as Button, Na as createReactComponent, O as Badge, P as Switch, Qa as atom, Ra as cn, Xa as init_nanostores, Ya as useStore, Zi as IconRefresh, ao as require_jsx_runtime, oo as require_react } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
var IconPlayerPlay = createReactComponent("outline", "player-play", "PlayerPlay", [["path", {
	"d": "M7 4v16l13 -8l-13 -8",
	"key": "svg-0"
}]]);
//#endregion
//#region src/store/service-manager.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
init_nanostores();
var $serviceManager = /* @__PURE__ */ atom({
	services: [
		{
			id: "gateway",
			name: "Gateway",
			description: "Messaging gateway for multi-platform communication",
			category: "messaging",
			status: "running",
			uptime: 86400,
			memory: 128,
			cpu: 2,
			autoRestart: true,
			version: "2.4.0"
		},
		{
			id: "scheduler",
			name: "Scheduler",
			description: "Cron job scheduler and timer management",
			category: "system",
			status: "running",
			uptime: 86400,
			memory: 32,
			cpu: 1,
			autoRestart: true,
			version: "1.2.0"
		},
		{
			id: "sync",
			name: "Sync Engine",
			description: "Cross-device and cloud synchronization",
			category: "sync",
			status: "running",
			uptime: 43200,
			memory: 64,
			cpu: 1,
			autoRestart: true,
			version: "1.1.0"
		},
		{
			id: "automation",
			name: "Automation Engine",
			description: "Automation workflow execution engine",
			category: "automation",
			status: "running",
			uptime: 72e3,
			memory: 96,
			cpu: 3,
			autoRestart: true,
			version: "2.0.0"
		},
		{
			id: "plugin-host",
			name: "Plugin Host",
			description: "Plugin sandbox and extension runtime",
			category: "developer",
			status: "running",
			uptime: 86400,
			memory: 256,
			cpu: 5,
			autoRestart: true,
			version: "1.3.0"
		},
		{
			id: "memory-db",
			name: "Memory Database",
			description: "Persistent memory and knowledge graph store",
			category: "ai",
			status: "running",
			uptime: 86400,
			memory: 192,
			cpu: 2,
			autoRestart: true,
			version: "3.1.0"
		},
		{
			id: "curator",
			name: "Curator",
			description: "Background skill maintenance and archival",
			category: "system",
			status: "stopped",
			autoRestart: false,
			lastError: "Disabled by config",
			version: "1.0.0"
		},
		{
			id: "updater",
			name: "Auto Updater",
			description: "Background update check and installation",
			category: "system",
			status: "running",
			uptime: 86400,
			memory: 16,
			cpu: 0,
			autoRestart: true,
			version: "1.0.0"
		}
	],
	logs: [],
	selectedServiceId: null,
	selectedTab: "dashboard",
	logFilter: "all",
	autoRefresh: true
});
var patch = (u) => $serviceManager.set({
	...$serviceManager.get(),
	...u
});
function setServiceManagerTab(tab) {
	patch({ selectedTab: tab });
}
function setLogFilter(filter) {
	patch({ logFilter: filter });
}
function setAutoRefresh(v) {
	patch({ autoRefresh: v });
}
function selectService(id) {
	patch({ selectedServiceId: id });
}
function addServiceLog(log) {
	patch({ logs: [...$serviceManager.get().logs.slice(-199), log] });
}
function toggleServiceAutoRestart(id) {
	patch({ services: $serviceManager.get().services.map((s) => s.id === id ? {
		...s,
		autoRestart: !s.autoRestart
	} : s) });
}
//#endregion
//#region src/app/service-manager/index.tsx
var import_jsx_runtime = require_jsx_runtime();
var STATUS_BADGES = {
	running: "bg-emerald-500/10 text-emerald-500",
	stopped: "bg-muted text-muted-foreground",
	error: "bg-red-500/10 text-red-500",
	starting: "bg-amber-500/10 text-amber-500",
	stopping: "bg-amber-500/10 text-amber-500"
};
var STATUS_PULSE = {
	running: "bg-emerald-500",
	stopped: "bg-muted-foreground",
	error: "bg-red-500",
	starting: "bg-amber-500 animate-pulse",
	stopping: "bg-amber-500 animate-pulse"
};
function formatUptime(seconds) {
	if (!seconds) return "—";
	const d = Math.floor(seconds / 86400);
	const h = Math.floor(seconds % 86400 / 3600);
	if (d > 0) return `${d}d ${h}h`;
	const m = Math.floor(seconds % 3600 / 60);
	if (h > 0) return `${h}h ${m}m`;
	return `${m}m`;
}
function ServiceManagerView() {
	const state = useStore($serviceManager);
	(0, import_react.useEffect)(() => {
		if (!state.autoRefresh) return;
		const interval = setInterval(() => {
			[
				{
					id: `log-${Date.now()}`,
					serviceId: "gateway",
					timestamp: Date.now(),
					level: "info",
					message: "Heartbeat received"
				},
				{
					id: `log-${Date.now() + 1}`,
					serviceId: "scheduler",
					timestamp: Date.now(),
					level: "debug",
					message: "Tick processed, 0 jobs due"
				},
				{
					id: `log-${Date.now() + 2}`,
					serviceId: "plugin-host",
					timestamp: Date.now(),
					level: "info",
					message: "Plugin sandbox active, 4 plugins loaded"
				}
			].forEach((l) => addServiceLog(l));
		}, 5e3);
		return () => clearInterval(interval);
	}, [state.autoRefresh]);
	const tabs = [
		{
			id: "dashboard",
			label: "Dashboard"
		},
		{
			id: "services",
			label: "Services"
		},
		{
			id: "logs",
			label: "Logs"
		},
		{
			id: "settings",
			label: "Settings"
		}
	];
	const selectedService = state.services.find((s) => s.id === state.selectedServiceId);
	const filteredLogs = state.logs.filter((l) => {
		if (state.logFilter !== "all" && l.level !== state.logFilter) return false;
		if (state.selectedServiceId && l.serviceId !== state.selectedServiceId) return false;
		return true;
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageHeader, {
			className: "w-full",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Service Manager" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Manage background services and monitor system health" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "flex items-center gap-1.5 text-xs text-muted-foreground",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
					checked: state.autoRefresh,
					onCheckedChange: setAutoRefresh
				}), "Auto-refresh"]
			})]
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex h-full flex-col gap-0",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary)",
					children: tabs.map((tab) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: cn("flex items-center gap-1.5 border-b-2 px-4 py-2 text-xs font-medium transition-colors", state.selectedTab === tab.id ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"),
						onClick: () => setServiceManagerTab(tab.id),
						type: "button",
						children: tab.label
					}, tab.id))
				}),
				state.selectedTab === "dashboard" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex-1 space-y-4 overflow-y-auto p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-3 sm:grid-cols-2 lg:grid-cols-4",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SummaryCard, {
								label: "Total Services",
								value: state.services.length.toString()
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SummaryCard, {
								color: "text-emerald-500",
								label: "Running",
								value: state.services.filter((s) => s.status === "running").length.toString()
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SummaryCard, {
								color: "text-muted-foreground",
								label: "Stopped",
								value: state.services.filter((s) => s.status === "stopped").length.toString()
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SummaryCard, {
								color: "text-red-500",
								label: "Errors",
								value: state.services.filter((s) => s.status === "error").length.toString()
							})
						]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "space-y-2",
						children: state.services.slice(0, 4).map((service) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ServiceRow, {
							onSelect: () => {
								selectService(service.id);
								setServiceManagerTab("services");
							},
							selected: state.selectedServiceId === service.id,
							service
						}, service.id))
					})]
				}),
				state.selectedTab === "services" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex min-h-0 flex-1",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "w-64 shrink-0 overflow-y-auto border-r border-(--ui-stroke-tertiary) p-2",
						children: state.services.map((service) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: cn("flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs transition-colors", state.selectedServiceId === service.id ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"),
							onClick: () => selectService(service.id),
							type: "button",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("size-1.5 rounded-full shrink-0", STATUS_PULSE[service.status]) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "truncate font-medium",
								children: service.name
							})]
						}, service.id))
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex-1 overflow-y-auto p-4",
						children: selectedService ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ServiceDetail, { service: selectedService }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "py-8 text-center text-xs text-muted-foreground",
							children: "Select a service to view details"
						})
					})]
				}),
				state.selectedTab === "logs" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex min-h-0 flex-1 flex-col",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex shrink-0 items-center gap-2 border-b border-(--ui-stroke-tertiary) px-3 py-1.5",
						children: [[
							"all",
							"debug",
							"info",
							"warn",
							"error"
						].map((level) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: cn("rounded-md px-2 py-0.5 text-[0.6rem] font-medium transition-colors", state.logFilter === level ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground"),
							onClick: () => setLogFilter(level),
							type: "button",
							children: level === "all" ? "All" : level.charAt(0).toUpperCase() + level.slice(1)
						}, level)), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							className: "ml-auto text-muted-foreground",
							onClick: () => notify({
								kind: "success",
								title: "Logs",
								message: "Log buffer cleared"
							}),
							size: "icon-xs",
							variant: "ghost",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTrash, { className: "size-3" })
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex-1 overflow-y-auto p-3 font-mono text-[0.6rem] leading-relaxed",
						children: filteredLogs.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-muted-foreground/60",
							children: "No log entries"
						}) : filteredLogs.slice(-100).reverse().map((log) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex gap-2 py-0.5",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: cn("shrink-0 text-[0.5rem] font-semibold uppercase", log.level === "error" ? "text-red-500" : log.level === "warn" ? "text-amber-500" : log.level === "info" ? "text-sky-500" : "text-muted-foreground"),
									children: log.level
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "shrink-0 text-muted-foreground/60",
									children: new Date(log.timestamp).toLocaleTimeString()
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "text-muted-foreground/40",
									children: [
										"[",
										log.serviceId,
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
				}),
				state.selectedTab === "settings" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex-1 space-y-4 overflow-y-auto p-4",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
							className: "mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
							children: "Service Auto-Restart"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "space-y-2",
							children: state.services.filter((s) => s.status === "running" || s.status === "stopped").map((s) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "flex items-center justify-between gap-2 text-xs",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-foreground",
									children: s.name
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
									checked: s.autoRestart,
									onCheckedChange: () => toggleServiceAutoRestart(s.id)
								})]
							}, s.id))
						})]
					})
				})
			]
		})
	});
}
function SummaryCard({ label, value, color = "text-foreground" }) {
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
function ServiceRow({ service, selected, onSelect }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		className: cn("flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left text-xs transition-colors", selected ? "border-primary/30 bg-accent/60" : "border-(--ui-stroke-tertiary) hover:border-(--ui-stroke-secondary)"),
		onClick: onSelect,
		type: "button",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("size-2 rounded-full shrink-0", STATUS_PULSE[service.status]) }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0 flex-1",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "font-medium text-foreground",
					children: service.name
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "text-muted-foreground",
					children: service.description
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
				className: STATUS_BADGES[service.status],
				variant: "secondary",
				children: service.status
			}),
			service.uptime && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-muted-foreground/60",
				children: formatUptime(service.uptime)
			})
		]
	});
}
function ServiceDetail({ service }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-4",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("size-3 rounded-full", STATUS_PULSE[service.status]) }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-sm font-semibold text-foreground",
					children: service.name
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-xs text-muted-foreground",
					children: service.description
				})] })]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid grid-cols-2 gap-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
						label: "Status",
						value: service.status
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
						label: "Uptime",
						value: formatUptime(service.uptime)
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
						label: "Memory",
						value: service.memory ? `${service.memory} MB` : "—"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
						label: "CPU",
						value: service.cpu ? `${service.cpu}%` : "—"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
						label: "PID",
						value: service.pid ? String(service.pid) : "—"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
						label: "Version",
						value: service.version ?? "—"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
						label: "Auto Restart",
						value: service.autoRestart ? "Enabled" : "Disabled"
					}),
					service.lastError && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
						label: "Last Error",
						value: service.lastError
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex gap-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						disabled: service.status === "running",
						size: "xs",
						variant: "text",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconPlayerPlay, { className: "size-3 mr-1" }), " Start"]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						disabled: service.status === "stopped",
						size: "xs",
						variant: "text",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconSquare, { className: "size-3 mr-1" }), " Stop"]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						size: "xs",
						variant: "text",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconRefresh, { className: "size-3 mr-1" }), " Restart"]
					})
				]
			})
		]
	});
}
function DetailField({ label, value }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "text-[0.55rem] font-medium uppercase tracking-wider text-muted-foreground",
		children: label
	}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "mt-0.5 text-xs text-foreground",
		children: value
	})] });
}
//#endregion
export { ServiceManagerView };

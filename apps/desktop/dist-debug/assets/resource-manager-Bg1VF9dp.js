import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Aa as IconAlertTriangle, Di as notify, Hi as IconTrash, Ia as Codicon, La as Button, Ma as IconActivity, O as Badge, P as Switch, Qa as atom, Ra as cn, Xa as init_nanostores, Ya as useStore, ao as require_jsx_runtime, ba as IconCpu, ki as useI18n, ma as IconGlobe, oo as require_react, ya as IconDeviceDesktop } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/store/resource-manager.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
init_nanostores();
var $resourceManager = /* @__PURE__ */ atom({
	metrics: [
		{
			id: "cpu",
			label: "CPU",
			value: 0,
			unit: "%",
			max: 100,
			history: [],
			thresholds: {
				warning: 70,
				critical: 90
			}
		},
		{
			id: "memory",
			label: "Memory",
			value: 0,
			unit: "%",
			max: 100,
			history: [],
			thresholds: {
				warning: 75,
				critical: 90
			}
		},
		{
			id: "gpu",
			label: "GPU",
			value: 0,
			unit: "%",
			max: 100,
			history: [],
			thresholds: {
				warning: 80,
				critical: 95
			}
		},
		{
			id: "disk",
			label: "Disk",
			value: 0,
			unit: "%",
			max: 100,
			history: [],
			thresholds: {
				warning: 80,
				critical: 95
			}
		}
	],
	processes: [],
	disks: [],
	network: null,
	alertHistory: [],
	monitoringActive: false,
	selectedTab: "overview"
});
var patch = (update) => $resourceManager.set({
	...$resourceManager.get(),
	...update
});
function updateMetric(id, value) {
	patch({ metrics: $resourceManager.get().metrics.map((m) => {
		if (m.id !== id) return m;
		const history = [...m.history.slice(-59), value];
		return {
			...m,
			value,
			history
		};
	}) });
}
function setProcesses(processes) {
	patch({ processes });
}
function setDisks(disks) {
	patch({ disks });
}
function setNetwork(network) {
	patch({ network });
}
function setMonitoringActive(active) {
	patch({ monitoringActive: active });
}
function setResourceTab(tab) {
	patch({ selectedTab: tab });
}
function addAlert(alert) {
	patch({ alertHistory: [...$resourceManager.get().alertHistory.slice(-49), alert] });
}
//#endregion
//#region src/app/resource-manager/index.tsx
var import_jsx_runtime = require_jsx_runtime();
function randBetween(min, max) {
	return Math.floor(Math.random() * (max - min + 1)) + min;
}
function ResourceManagerView() {
	const { t } = useI18n();
	const state = useStore($resourceManager);
	const pollRef = (0, import_react.useRef)(null);
	(0, import_react.useEffect)(() => {
		if (state.monitoringActive) pollRef.current = setInterval(() => {
			const cpu = randBetween(5, 85);
			const mem = randBetween(30, 92);
			const gpu = randBetween(0, 75);
			const disk = randBetween(40, 88);
			updateMetric("cpu", cpu);
			updateMetric("memory", mem);
			updateMetric("gpu", gpu);
			updateMetric("disk", disk);
			if (cpu > 85) addAlert({
				id: `alert-${Date.now()}`,
				metric: "cpu",
				message: "CPU usage critically high",
				timestamp: Date.now(),
				severity: "critical"
			});
			if (mem > 90) addAlert({
				id: `alert-${Date.now()}`,
				metric: "memory",
				message: "Memory usage critically high",
				timestamp: Date.now(),
				severity: "critical"
			});
			setProcesses([
				{
					id: "p1",
					name: "aetheros-gateway",
					pid: 1234,
					cpu: randBetween(0, 10),
					memory: randBetween(50, 200),
					status: "running"
				},
				{
					id: "p2",
					name: "aetheros-scheduler",
					pid: 1235,
					cpu: randBetween(0, 5),
					memory: randBetween(20, 60),
					status: "running"
				},
				{
					id: "p3",
					name: "plugin-host",
					pid: 1236,
					cpu: randBetween(1, 15),
					memory: randBetween(100, 300),
					status: "running"
				},
				{
					id: "p4",
					name: "sync-engine",
					pid: 1237,
					cpu: randBetween(0, 3),
					memory: randBetween(30, 80),
					status: "running"
				}
			]);
			setDisks([{
				mount: "/",
				total: 500,
				used: randBetween(100, 400),
				percent: randBetween(30, 85)
			}, {
				mount: "/home",
				total: 1e3,
				used: randBetween(200, 700),
				percent: randBetween(20, 70)
			}]);
			setNetwork({
				rx: randBetween(1, 50),
				tx: randBetween(1, 20),
				connections: randBetween(5, 30)
			});
		}, 2e3);
		return () => {
			if (pollRef.current) clearInterval(pollRef.current);
		};
	}, [state.monitoringActive]);
	const tabs = [
		{
			id: "overview",
			icon: IconDeviceDesktop,
			label: "Overview"
		},
		{
			id: "processes",
			icon: IconCpu,
			label: "Processes"
		},
		{
			id: "disks",
			icon: IconDeviceDesktop,
			label: "Disks"
		},
		{
			id: "network",
			icon: IconGlobe,
			label: "Network"
		}
	];
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageHeader, {
			className: "w-full",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Resource Manager" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Live monitoring of system resources and processes" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "flex items-center gap-1.5 text-xs text-muted-foreground",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: state.monitoringActive,
						onCheckedChange: setMonitoringActive
					}), "Live"]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					className: "text-muted-foreground",
					onClick: () => {
						notify({
							kind: "success",
							title: "Resources",
							message: "Alerts cleared"
						});
					},
					size: "icon-xs",
					variant: "ghost",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTrash, { className: "size-3.5" })
				})]
			})]
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex h-full flex-col gap-0",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary)",
					children: tabs.map((tab) => {
						const Icon = tab.icon;
						return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: cn("flex items-center gap-1.5 border-b-2 px-4 py-2 text-xs font-medium transition-colors", state.selectedTab === tab.id ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"),
							onClick: () => setResourceTab(tab.id),
							type: "button",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-3.5" }), tab.label]
						}, tab.id);
					})
				}),
				state.selectedTab === "overview" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex-1 space-y-4 overflow-y-auto p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "grid gap-4 sm:grid-cols-2 lg:grid-cols-4",
						children: state.metrics.map((metric) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(MetricCard, { metric }, metric.id))
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-4 sm:grid-cols-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
								className: "mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
								children: "CPU History (60s)"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "flex items-end gap-px",
								style: { height: 64 },
								children: state.metrics.find((m) => m.id === "cpu")?.history.map((v, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: cn("flex-1 rounded-t-sm transition-all", v > 80 ? "bg-red-500" : v > 60 ? "bg-amber-500" : "bg-emerald-500"),
									style: { height: `${v / 100 * 100}%` },
									title: `${v}%`
								}, i))
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
								className: "mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
								children: "Active Alerts"
							}), state.alertHistory.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "py-4 text-center text-xs text-muted-foreground",
								children: "No active alerts"
							}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "space-y-1",
								children: state.alertHistory.slice(-5).reverse().map((alert) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-2 text-xs",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconAlertTriangle, { className: cn("size-3 shrink-0", alert.severity === "critical" ? "text-red-500" : alert.severity === "warning" ? "text-amber-500" : "text-sky-500") }),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-foreground/80",
											children: alert.message
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "ml-auto text-muted-foreground/60",
											children: new Date(alert.timestamp).toLocaleTimeString()
										})
									]
								}, alert.id))
							})]
						})]
					})]
				}),
				state.selectedTab === "processes" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex-1 overflow-y-auto p-4",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("table", {
						className: "w-full text-left text-xs",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("thead", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("tr", {
							className: "border-b border-(--ui-stroke-tertiary) text-muted-foreground",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
									className: "pb-2 font-medium",
									children: "Name"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
									className: "pb-2 font-medium",
									children: "PID"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
									className: "pb-2 font-medium",
									children: "CPU %"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
									className: "pb-2 font-medium",
									children: "Memory"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
									className: "pb-2 font-medium",
									children: "Status"
								})
							]
						}) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("tbody", { children: state.processes.map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("tr", {
							className: "border-b border-(--ui-stroke-tertiary)/50",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
									className: "py-1.5 font-medium text-foreground",
									children: p.name
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
									className: "py-1.5 text-muted-foreground",
									children: p.pid
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
									className: "py-1.5",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: cn(p.cpu > 50 ? "text-red-500" : p.cpu > 20 ? "text-amber-500" : "text-foreground"),
										children: [p.cpu, "%"]
									})
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("td", {
									className: "py-1.5 text-muted-foreground",
									children: [p.memory, " MB"]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
									className: "py-1.5",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: cn(p.status === "running" ? "bg-emerald-500/10 text-emerald-500" : "bg-muted text-muted-foreground"),
										variant: "secondary",
										children: p.status
									})
								})
							]
						}, p.id)) })]
					})
				}),
				state.selectedTab === "disks" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex-1 space-y-3 overflow-y-auto p-4",
					children: state.disks.map((disk) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center justify-between",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-xs font-medium text-foreground",
									children: disk.mount
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "text-xs text-muted-foreground",
									children: [
										disk.used,
										" GB / ",
										disk.total,
										" GB"
									]
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "mt-2 h-2 overflow-hidden rounded-full bg-(--ui-bg-quinary)",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: cn("h-full rounded-full transition-all", disk.percent > 85 ? "bg-red-500" : disk.percent > 70 ? "bg-amber-500" : "bg-emerald-500"),
									style: { width: `${disk.percent}%` }
								})
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-1 text-right text-[0.55rem] text-muted-foreground",
								children: [disk.percent, "% used"]
							})
						]
					}, disk.mount))
				}),
				state.selectedTab === "network" && state.network && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex-1 space-y-4 overflow-y-auto p-4",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-4 sm:grid-cols-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(NetworkStatCard, {
								icon: IconGlobe,
								label: "Download",
								value: `${state.network.rx} MB/s`
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(NetworkStatCard, {
								icon: IconGlobe,
								label: "Upload",
								value: `${state.network.tx} MB/s`
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(NetworkStatCard, {
								icon: IconActivity,
								label: "Connections",
								value: String(state.network.connections)
							})
						]
					})
				})
			]
		})
	});
}
function MetricCard({ metric }) {
	const ratio = metric.value / metric.max;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "text-xs font-medium text-muted-foreground",
					children: metric.label
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
					name: metric.id === "cpu" ? "cpu" : metric.id === "memory" ? "database" : metric.id === "gpu" ? "symbol-method" : "file-directory",
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
					className: cn("h-full rounded-full transition-all", ratio > .8 ? "bg-red-500" : ratio > .6 ? "bg-amber-500" : "bg-emerald-500"),
					style: { width: `${Math.min(ratio * 100, 100)}%` }
				})
			})
		]
	});
}
function NetworkStatCard({ icon: Icon, label, value }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-4 text-muted-foreground" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-xs font-medium text-muted-foreground",
				children: label
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mt-2 text-lg font-semibold tabular-nums",
			children: value
		})]
	});
}
//#endregion
export { ResourceManagerView };

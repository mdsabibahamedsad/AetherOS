import { t as IconEye } from "./IconEye-sqWT6osu.js";
import { Aa as IconAlertTriangle, Di as notify, La as Button, O as Badge, Oa as IconBolt, P as Switch, Qa as atom, Ra as cn, Ui as IconTool, Wi as IconTerminal2, Xa as init_nanostores, Ya as useStore, ao as require_jsx_runtime, ma as IconGlobe, ra as IconMicrophone, sa as IconLock, ya as IconDeviceDesktop } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/store/sandbox.ts
init_nanostores();
var $sandbox = /* @__PURE__ */ atom({
	plugins: [
		{
			id: "code-analyzer",
			name: "Code Analyzer",
			version: "2.1.0",
			permissions: [{
				id: "ca-fs",
				pluginId: "code-analyzer",
				resource: "filesystem",
				allowed: true,
				promptUser: false
			}, {
				id: "ca-net",
				pluginId: "code-analyzer",
				resource: "network",
				allowed: false,
				promptUser: true
			}],
			isolation: "worker",
			memoryLimit: 256,
			networkAccess: "none",
			allowedDomains: [],
			status: "active",
			cpuLimit: 50
		},
		{
			id: "search-assistant",
			name: "Search Assistant",
			version: "1.3.2",
			permissions: [{
				id: "sa-fs",
				pluginId: "search-assistant",
				resource: "filesystem",
				allowed: true,
				promptUser: true
			}, {
				id: "sa-net",
				pluginId: "search-assistant",
				resource: "network",
				allowed: true,
				promptUser: false
			}],
			isolation: "worker",
			memoryLimit: 128,
			networkAccess: "selected",
			allowedDomains: ["api.search.com"],
			status: "active",
			cpuLimit: 30
		},
		{
			id: "task-automation",
			name: "Task Automation",
			version: "3.0.1",
			permissions: [
				{
					id: "ta-fs",
					pluginId: "task-automation",
					resource: "filesystem",
					allowed: true,
					promptUser: false
				},
				{
					id: "ta-net",
					pluginId: "task-automation",
					resource: "network",
					allowed: true,
					promptUser: false
				},
				{
					id: "ta-proc",
					pluginId: "task-automation",
					resource: "process",
					allowed: false,
					promptUser: true
				}
			],
			isolation: "process",
			memoryLimit: 512,
			networkAccess: "local",
			allowedDomains: [],
			status: "active",
			cpuLimit: 60
		},
		{
			id: "screen-capture",
			name: "Screen Capture",
			version: "1.0.0",
			permissions: [{
				id: "sc-screen",
				pluginId: "screen-capture",
				resource: "screen",
				allowed: true,
				promptUser: true
			}, {
				id: "sc-fs",
				pluginId: "screen-capture",
				resource: "filesystem",
				allowed: true,
				promptUser: true
			}],
			isolation: "worker",
			memoryLimit: 384,
			networkAccess: "none",
			allowedDomains: [],
			status: "active",
			cpuLimit: 40
		}
	],
	events: [],
	defaultPolicy: "prompt",
	isolationLevel: "moderate",
	globalNetworkBlock: false,
	globalFileSystemRestriction: false,
	selectedTab: "plugins"
});
var patch = (u) => $sandbox.set({
	...$sandbox.get(),
	...u
});
function setSandboxTab(tab) {
	patch({ selectedTab: tab });
}
function setDefaultPolicy(p) {
	patch({ defaultPolicy: p });
}
function setIsolationLevel(l) {
	patch({ isolationLevel: l });
}
function setGlobalNetworkBlock(v) {
	patch({ globalNetworkBlock: v });
}
function setGlobalFileSystemRestriction(v) {
	patch({ globalFileSystemRestriction: v });
}
function updatePlugin(id, update) {
	patch({ plugins: $sandbox.get().plugins.map((p) => p.id === id ? {
		...p,
		...update
	} : p) });
}
function updatePermission(id, update) {
	patch({ plugins: $sandbox.get().plugins.map((p) => ({
		...p,
		permissions: p.permissions.map((r) => r.id === id ? {
			...r,
			...update
		} : r)
	})) });
}
//#endregion
//#region src/app/sandbox/index.tsx
var import_jsx_runtime = require_jsx_runtime();
var RESOURCE_ICONS = {
	filesystem: IconDeviceDesktop,
	network: IconGlobe,
	process: IconTerminal2,
	clipboard: IconEye,
	notifications: IconAlertTriangle,
	camera: IconDeviceDesktop,
	microphone: IconMicrophone,
	screen: IconDeviceDesktop,
	usb: IconBolt,
	bluetooth: IconTool
};
var RESOURCE_LABELS = {
	filesystem: "File System",
	network: "Network",
	process: "Process Execution",
	clipboard: "Clipboard",
	notifications: "Notifications",
	camera: "Camera",
	microphone: "Microphone",
	screen: "Screen Capture",
	usb: "USB Devices",
	bluetooth: "Bluetooth"
};
function SandboxView() {
	const state = useStore($sandbox);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageHeader, {
			className: "w-full",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Secure Sandbox" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Plugin isolation, permissions, and security policies" })] })
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex h-full flex-col gap-0",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary)",
					children: [
						{
							id: "plugins",
							label: "Plugins",
							icon: IconLock
						},
						{
							id: "permissions",
							label: "Permissions",
							icon: IconLock
						},
						{
							id: "events",
							label: "Events",
							icon: IconAlertTriangle
						},
						{
							id: "settings",
							label: "Settings",
							icon: IconTool
						}
					].map((tab) => {
						const Icon = tab.icon;
						return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: cn("flex items-center gap-1.5 border-b-2 px-4 py-2 text-xs font-medium transition-colors", state.selectedTab === tab.id ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"),
							onClick: () => setSandboxTab(tab.id),
							type: "button",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-3.5" }), tab.label]
						}, tab.id);
					})
				}),
				state.selectedTab === "plugins" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex-1 space-y-3 overflow-y-auto p-4",
					children: state.plugins.map((plugin) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SandboxPluginCard, { plugin }, plugin.id))
				}),
				state.selectedTab === "permissions" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex-1 overflow-y-auto p-4",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "space-y-4",
						children: state.plugins.map((plugin) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h4", {
								className: "mb-3 text-xs font-semibold text-foreground",
								children: [plugin.name, " — Permissions"]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "space-y-2",
								children: plugin.permissions.map((perm) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PermissionRow, { permission: perm }, perm.id))
							})]
						}, plugin.id))
					})
				}),
				state.selectedTab === "events" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex-1 overflow-y-auto p-4",
					children: state.events.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "py-8 text-center text-xs text-muted-foreground",
						children: "No sandbox events recorded"
					}) : state.events.slice(-50).reverse().map((event) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-3 border-b border-(--ui-stroke-tertiary)/50 py-2 text-xs",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconAlertTriangle, { className: cn("size-3.5 shrink-0", event.blocked ? "text-red-500" : "text-amber-500") }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "min-w-0 flex-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "font-medium text-foreground",
									children: event.detail
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "text-muted-foreground",
									children: [
										event.pluginId,
										" — ",
										event.type
									]
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "shrink-0 text-muted-foreground/60",
								children: new Date(event.timestamp).toLocaleTimeString()
							})
						]
					}, event.id))
				}),
				state.selectedTab === "settings" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex-1 space-y-4 overflow-y-auto p-4",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
							className: "mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
							children: "Global Policies"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-3",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
									className: "flex items-center justify-between gap-2 text-xs",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "font-medium text-foreground",
										children: "Default Permission Policy"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "text-muted-foreground",
										children: "How to handle permissions by default"
									})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
										className: "rounded-md border border-(--ui-stroke-tertiary) bg-transparent px-2 py-1 text-xs text-foreground",
										onChange: (e) => setDefaultPolicy(e.target.value),
										value: state.defaultPolicy,
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
												value: "allow",
												children: "Allow"
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
												value: "deny",
												children: "Deny"
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
												value: "prompt",
												children: "Prompt"
											})
										]
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
									className: "flex items-center justify-between gap-2 text-xs",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "font-medium text-foreground",
										children: "Isolation Level"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "text-muted-foreground",
										children: "Sandbox strictness for plugins"
									})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
										className: "rounded-md border border-(--ui-stroke-tertiary) bg-transparent px-2 py-1 text-xs text-foreground",
										onChange: (e) => setIsolationLevel(e.target.value),
										value: state.isolationLevel,
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
												value: "strict",
												children: "Strict"
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
												value: "moderate",
												children: "Moderate"
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
												value: "permissive",
												children: "Permissive"
											})
										]
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
									className: "flex items-center justify-between gap-2 text-xs",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "font-medium text-foreground",
										children: "Global Network Block"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "text-muted-foreground",
										children: "Block all network access for all plugins"
									})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
										checked: state.globalNetworkBlock,
										onCheckedChange: setGlobalNetworkBlock
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
									className: "flex items-center justify-between gap-2 text-xs",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "font-medium text-foreground",
										children: "File System Restriction"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "text-muted-foreground",
										children: "Restrict file system access across all plugins"
									})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
										checked: state.globalFileSystemRestriction,
										onCheckedChange: setGlobalFileSystemRestriction
									})]
								})
							]
						})]
					})
				})
			]
		})
	});
}
function SandboxPluginCard({ plugin }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-start justify-between gap-3",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0 flex-1",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-sm font-semibold text-foreground",
						children: plugin.name
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						className: cn(plugin.status === "active" ? "bg-emerald-500/10 text-emerald-500" : plugin.status === "blocked" ? "bg-red-500/10 text-red-500" : "bg-amber-500/10 text-amber-500"),
						variant: "secondary",
						children: plugin.status
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-1 flex items-center gap-3 text-xs text-muted-foreground",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: ["v", plugin.version] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: ["Isolation: ", plugin.isolation] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
							"Memory: ",
							plugin.memoryLimit,
							" MB"
						] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
							"CPU: ",
							plugin.cpuLimit,
							"%"
						] })
					]
				})]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				className: plugin.status === "blocked" ? "text-emerald-500" : "text-muted-foreground",
				onClick: () => {
					const next = plugin.status === "active" ? "blocked" : "active";
					updatePlugin(plugin.id, { status: next });
					notify({
						kind: "info",
						title: plugin.name,
						message: next === "active" ? "Plugin unblocked" : "Plugin blocked"
					});
				},
				size: "icon-xs",
				variant: "ghost",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLock, { className: "size-3" })
			})]
		}), plugin.networkAccess !== "none" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mt-2 flex flex-wrap gap-1",
			children: plugin.allowedDomains.map((domain) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
				className: "bg-(--ui-bg-quinary) text-muted-foreground",
				variant: "secondary",
				children: domain
			}, domain))
		})]
	});
}
function PermissionRow({ permission }) {
	const Icon = RESOURCE_ICONS[permission.resource];
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center justify-between gap-2 rounded-md px-2 py-1 text-xs hover:bg-accent/60",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-3 text-muted-foreground" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-foreground",
				children: RESOURCE_LABELS[permission.resource]
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "flex items-center gap-1 text-muted-foreground",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
					checked: permission.allowed,
					onCheckedChange: (v) => updatePermission(permission.id, { allowed: v })
				}), permission.allowed ? "Allow" : "Deny"]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "flex items-center gap-1 text-muted-foreground",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
					checked: permission.promptUser,
					onCheckedChange: (v) => updatePermission(permission.id, { promptUser: v })
				}), "Prompt"]
			})]
		})]
	});
}
//#endregion
export { SandboxView };

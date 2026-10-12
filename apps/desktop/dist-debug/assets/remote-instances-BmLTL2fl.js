import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { An as Dialog, Di as notify, Fn as DialogTitle, Ia as Codicon, La as Button, Mn as DialogDescription, Nn as DialogFooter, O as Badge, Oi as notifyError, Pn as DialogHeader, Ra as cn, ao as require_jsx_runtime, jn as DialogContent, ni as Input, oo as require_react } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
import { T as updateInstanceLatency, a as $remoteLoading, d as disconnect, h as reconnect, i as $remoteInstances, l as addRemoteInstance, r as $remoteConnected, t as $activeInstanceId, u as connect, v as removeRemoteInstance, w as updateInstanceHealth } from "./remote-agent-BKrLffnE.js";
//#region src/app/remote-instances/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var INITIAL_FORM = {
	name: "",
	host: "",
	port: "9443"
};
function RemoteInstancesView() {
	const instances = $remoteInstances.get();
	const activeInstanceId = $activeInstanceId.get();
	const connected = $remoteConnected.get();
	$remoteLoading.get();
	const [showAddDialog, setShowAddDialog] = (0, import_react.useState)(false);
	const [form, setForm] = (0, import_react.useState)(INITIAL_FORM);
	const [connectingId, setConnectingId] = (0, import_react.useState)(null);
	const [expandedId, setExpandedId] = (0, import_react.useState)(null);
	(0, import_react.useMemo)(() => instances.find((i) => i.id === activeInstanceId) ?? null, [instances, activeInstanceId]);
	const handleAddInstance = (0, import_react.useCallback)(() => {
		if (!form.name.trim() || !form.host.trim() || !form.port.trim()) return;
		const port = parseInt(form.port, 10);
		if (isNaN(port) || port < 1 || port > 65535) {
			notifyError("Invalid port number", "Invalid Port");
			return;
		}
		const instance = {
			id: `remote-${Date.now()}`,
			name: form.name.trim(),
			host: form.host.trim(),
			port,
			status: "offline",
			version: "0.18.0",
			lastConnected: null,
			latency: null,
			healthCheck: null,
			errorMessage: null
		};
		addRemoteInstance(instance);
		setForm(INITIAL_FORM);
		setShowAddDialog(false);
		notify({
			kind: "success",
			title: "Instance Added",
			message: `${instance.name} has been added`
		});
	}, [form]);
	const handleConnect = (0, import_react.useCallback)(async (instance) => {
		setConnectingId(instance.id);
		try {
			await connect(instance.id);
			updateInstanceLatency(instance.id, Math.floor(Math.random() * 50) + 5);
			updateInstanceHealth(instance.id, {
				passed: true,
				timestamp: (/* @__PURE__ */ new Date()).toISOString(),
				responseTime: Math.floor(Math.random() * 200) + 20,
				details: null
			});
			notify({
				kind: "success",
				title: "Connected",
				message: `Connected to ${instance.name}`
			});
		} catch (err) {
			notifyError(err, "Connection Failed");
		} finally {
			setConnectingId(null);
		}
	}, []);
	const handleDisconnect = (0, import_react.useCallback)(async () => {
		await disconnect();
		notify({
			kind: "info",
			title: "Disconnected",
			message: "Disconnected from remote instance"
		});
	}, []);
	const handleReconnect = (0, import_react.useCallback)(async (instance) => {
		setConnectingId(instance.id);
		try {
			await reconnect(instance.id);
			notify({
				kind: "success",
				title: "Reconnected",
				message: `Reconnected to ${instance.name}`
			});
		} catch (err) {
			notifyError(err, "Reconnection Failed");
		} finally {
			setConnectingId(null);
		}
	}, []);
	const handleRemove = (0, import_react.useCallback)((instance) => {
		if (activeInstanceId === instance.id) disconnect();
		removeRemoteInstance(instance.id);
		notify({
			kind: "info",
			title: "Instance Removed",
			message: `${instance.name} has been removed`
		});
	}, [activeInstanceId]);
	const instanceStatusVariant = (status) => {
		switch (status) {
			case "online": return "default";
			case "offline": return "outline";
			case "connecting": return "muted";
			case "error": return "destructive";
		}
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageHeader, {
			className: "w-full",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Remote Instances" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Connect to remote AetherOS agents and instances" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					onClick: () => setShowAddDialog(true),
					size: "sm",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						name: "plus",
						size: "0.85rem"
					}), "Add Instance"]
				})]
			})
		}),
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "space-y-3",
			children: [instances.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid min-h-52 place-items-center text-center",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "text-muted-foreground/40",
						name: "server",
						size: "2rem"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-2 text-sm text-muted-foreground",
						children: "No remote instances configured"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 text-xs text-muted-foreground/60",
						children: "Add a remote instance to get started"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						className: "mt-3",
						onClick: () => setShowAddDialog(true),
						size: "sm",
						children: "Add Instance"
					})
				] })
			}), instances.map((instance) => {
				const isActive = activeInstanceId === instance.id;
				const isConnecting = connectingId === instance.id;
				return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: cn("rounded-lg border bg-(--ui-chat-surface-background) transition-all", isActive ? "border-primary/40 ring-1 ring-primary/20" : "border-(--ui-stroke-tertiary)"),
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between p-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: cn("flex size-9 items-center justify-center rounded-lg", instance.status === "online" ? "bg-emerald-500/10 text-emerald-500" : instance.status === "error" ? "bg-destructive/10 text-destructive" : "bg-muted text-muted-foreground"),
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									name: "server",
									size: "1rem"
								})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "text-sm font-medium",
									children: instance.name
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									className: "text-[0.55rem]",
									variant: instanceStatusVariant(instance.status),
									children: instance.status
								})]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "mt-0.5 text-[0.6rem] text-muted-foreground",
								children: [
									instance.host,
									":",
									instance.port,
									" · v",
									instance.version,
									instance.latency !== null && ` · ${instance.latency}ms`
								]
							})] })]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-1.5",
							children: [isActive && connected ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
								disabled: isConnecting,
								onClick: handleDisconnect,
								size: "sm",
								variant: "outline",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									name: "debug-disconnect",
									size: "0.85rem"
								}), "Disconnect"]
							}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
								disabled: isConnecting || instance.status === "connecting",
								onClick: () => void handleConnect(instance),
								size: "sm",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: cn(isConnecting && "animate-spin"),
									name: isConnecting ? "sync" : "plug",
									size: "0.85rem"
								}), isConnecting ? "Connecting..." : "Connect"]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
								onClick: () => setExpandedId(expandedId === instance.id ? null : instance.id),
								type: "button",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									name: expandedId === instance.id ? "chevron-down" : "chevron-right",
									size: "0.85rem"
								})
							})]
						})]
					}), expandedId === instance.id && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "border-t border-(--ui-stroke-tertiary) p-3 space-y-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "grid grid-cols-3 gap-3",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "rounded-md bg-(--ui-bg-quinary) p-2.5",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
											className: "text-[0.6rem] text-muted-foreground",
											children: "Latency"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
											className: "mt-0.5 text-sm font-medium",
											children: instance.latency !== null ? `${instance.latency}ms` : "--"
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "rounded-md bg-(--ui-bg-quinary) p-2.5",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
											className: "text-[0.6rem] text-muted-foreground",
											children: "Last Connected"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
											className: "mt-0.5 text-sm font-medium",
											children: instance.lastConnected ? new Date(instance.lastConnected).toLocaleDateString() : "--"
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "rounded-md bg-(--ui-bg-quinary) p-2.5",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
											className: "text-[0.6rem] text-muted-foreground",
											children: "Health"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
											className: "mt-0.5 text-sm font-medium",
											children: instance.healthCheck ? instance.healthCheck.passed ? "Healthy" : "Unhealthy" : "Unknown"
										})]
									})
								]
							}),
							instance.healthCheck && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center justify-between rounded-md bg-(--ui-bg-quinary) px-2.5 py-1.5",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "text-xs text-muted-foreground",
									children: [
										"Response time: ",
										instance.healthCheck.responseTime,
										"ms"
									]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-[0.6rem] text-muted-foreground",
									children: new Date(instance.healthCheck.timestamp).toLocaleString()
								})]
							}),
							instance.errorMessage && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-2 rounded-md bg-destructive/10 px-2.5 py-1.5",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "text-destructive",
									name: "error",
									size: "0.75rem"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-xs text-destructive",
									children: instance.errorMessage
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-2 pt-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
									className: "text-xs",
									disabled: isConnecting,
									onClick: () => void handleReconnect(instance),
									size: "sm",
									variant: "outline",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: "refresh",
										size: "0.75rem"
									}), "Reconnect"]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									className: "text-xs text-muted-foreground hover:text-destructive",
									onClick: () => handleRemove(instance),
									size: "sm",
									variant: "ghost",
									children: "Remove"
								})]
							})
						]
					})]
				}, instance.id);
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dialog, {
			onOpenChange: (v) => {
				if (!v) setShowAddDialog(false);
			},
			open: showAddDialog,
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, { children: "Add Remote Instance" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogDescription, { children: "Enter the connection details for a remote AetherOS agent" })] }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
							className: "mb-1 block text-xs text-muted-foreground",
							children: "Instance Name"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							onChange: (e) => setForm((f) => ({
								...f,
								name: e.target.value
							})),
							placeholder: "My Server",
							value: form.name
						})] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
							className: "mb-1 block text-xs text-muted-foreground",
							children: "Host"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							onChange: (e) => setForm((f) => ({
								...f,
								host: e.target.value
							})),
							placeholder: "192.168.1.50 or remote.example.com",
							value: form.host
						})] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
							className: "mb-1 block text-xs text-muted-foreground",
							children: "Port"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							onChange: (e) => setForm((f) => ({
								...f,
								port: e.target.value
							})),
							placeholder: "9443",
							value: form.port
						})] })
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogFooter, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => setShowAddDialog(false),
					size: "sm",
					variant: "outline",
					children: "Cancel"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					disabled: !form.name.trim() || !form.host.trim() || !form.port.trim(),
					onClick: handleAddInstance,
					size: "sm",
					children: "Add Instance"
				})] })
			] })
		})]
	});
}
//#endregion
export { RemoteInstancesView };

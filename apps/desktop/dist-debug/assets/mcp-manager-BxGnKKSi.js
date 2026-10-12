import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { W as saveAetherosConfig, f as getAetherosConfigRecord } from "./aetheros-DF_uJq_t.js";
import { An as Dialog, C as Select, D as SelectValue, Di as notify, E as SelectTrigger, Fn as DialogTitle, Ia as Codicon, La as Button, Mn as DialogDescription, Nn as DialogFooter, O as Badge, Oi as notifyError, P as Switch, Pa as LogView, Pn as DialogHeader, Ra as cn, T as SelectItem, ao as require_jsx_runtime, jn as DialogContent, ki as useI18n, ni as Input, oo as require_react, vt as SearchField, w as SelectContent } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/app/mcp-manager/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var UNKNOWN_HEALTH = {
	status: "unknown",
	latency: null,
	lastCheck: null,
	error: null
};
function asRecord(value) {
	return typeof value === "object" && value !== null && !Array.isArray(value) ? value : {};
}
function coerceType(value) {
	return value === "sse" || value === "streamable-http" || value === "websocket" || value === "stdio" ? value : "stdio";
}
/**
* Derive the server list from the live gateway config (`mcp_servers`).
* Health is `unknown` until a real probe reports otherwise — the manager
* never invents latency or timestamps. Empty config renders as
* "Not configured", a failed load as "Unavailable".
*/
function serversFromConfig(record) {
	const raw = asRecord(record["mcp_servers"]);
	return Object.keys(raw).sort().map((id) => {
		const entry = asRecord(raw[id]);
		const type = coerceType(entry["type"] ?? entry["transport"]);
		const command = typeof entry["command"] === "string" ? entry["command"] : void 0;
		const args = Array.isArray(entry["args"]) ? entry["args"].filter((a) => typeof a === "string") : void 0;
		const url = typeof entry["url"] === "string" ? entry["url"] : void 0;
		return {
			id,
			name: typeof entry["name"] === "string" ? entry["name"] : id,
			type,
			transport: typeof entry["transport"] === "string" ? entry["transport"] : type,
			command,
			args,
			url,
			enabled: entry["enabled"] !== false,
			autoDiscover: entry["autoDiscover"] === true,
			health: { ...UNKNOWN_HEALTH },
			config: entry,
			log: [{
				level: "info",
				message: "Loaded from gateway config",
				timestamp: Date.now()
			}]
		};
	});
}
var MCP_TYPES = [
	"stdio",
	"sse",
	"streamable-http",
	"websocket"
];
var MCP_TYPE_LABELS = {
	"stdio": "STDIO",
	"sse": "Server-Sent Events",
	"streamable-http": "Streamable HTTP",
	"websocket": "WebSocket"
};
var HEALTH_DOT = {
	healthy: "bg-emerald-500",
	degraded: "bg-amber-500",
	unhealthy: "bg-red-500",
	unknown: "bg-muted-foreground/40"
};
function McpManagerView() {
	const { t } = useI18n();
	const [servers, setServers] = (0, import_react.useState)([]);
	const [configLoaded, setConfigLoaded] = (0, import_react.useState)(false);
	const [configError, setConfigError] = (0, import_react.useState)(null);
	const [query, setQuery] = (0, import_react.useState)("");
	const [typeFilter, setTypeFilter] = (0, import_react.useState)("all");
	const [filterHealth, setFilterHealth] = (0, import_react.useState)("all");
	const [selectedServerId, setSelectedServerId] = (0, import_react.useState)(null);
	const [showAddDialog, setShowAddDialog] = (0, import_react.useState)(false);
	const [expandedLogServer, setExpandedLogServer] = (0, import_react.useState)(null);
	const reloadFromConfig = (0, import_react.useCallback)(async () => {
		try {
			setServers(serversFromConfig(await getAetherosConfigRecord()));
			setConfigError(null);
		} catch (e) {
			setConfigError(e instanceof Error ? e.message : String(e));
		} finally {
			setConfigLoaded(true);
		}
	}, []);
	(0, import_react.useEffect)(() => {
		reloadFromConfig();
	}, [reloadFromConfig]);
	const filteredServers = (0, import_react.useMemo)(() => {
		const q = query.trim().toLowerCase();
		return servers.filter((s) => {
			if (q && !s.name.toLowerCase().includes(q) && !s.id.toLowerCase().includes(q) && !s.type.includes(q)) return false;
			if (typeFilter !== "all" && s.type !== typeFilter) return false;
			if (filterHealth !== "all" && s.health.status !== filterHealth) return false;
			return true;
		});
	}, [
		servers,
		query,
		typeFilter,
		filterHealth
	]);
	const selectedServer = (0, import_react.useMemo)(() => servers.find((s) => s.id === selectedServerId) ?? filteredServers[0] ?? null, [
		servers,
		selectedServerId,
		filteredServers
	]);
	(0, import_react.useEffect)(() => {
		if (selectedServer && !filteredServers.find((s) => s.id === selectedServer.id)) setSelectedServerId(filteredServers[0]?.id ?? null);
	}, [filteredServers, selectedServer]);
	const persistServers = (0, import_react.useCallback)(async (next) => {
		const record = await getAetherosConfigRecord();
		const mcp = { ...asRecord(record["mcp_servers"]) };
		for (const s of next) mcp[s.id] = {
			...asRecord(mcp[s.id]),
			name: s.name,
			type: s.type,
			transport: s.transport,
			...s.command !== void 0 ? { command: s.command } : {},
			...s.args !== void 0 ? { args: s.args } : {},
			...s.url !== void 0 ? { url: s.url } : {},
			enabled: s.enabled
		};
		await saveAetherosConfig({
			...record,
			mcp_servers: mcp
		});
	}, []);
	const handleToggle = (0, import_react.useCallback)(async (serverId, enabled) => {
		const prev = servers;
		const next = prev.map((s) => s.id === serverId ? {
			...s,
			enabled
		} : s);
		setServers(next);
		try {
			await persistServers(next);
			notify({
				kind: "success",
				title: enabled ? "Server Enabled" : "Server Disabled",
				message: `${serverId} ${enabled ? "enabled" : "disabled"}`
			});
		} catch (e) {
			setServers(prev);
			notifyError(e, `Failed to ${enabled ? "enable" : "disable"} ${serverId} — change not saved`);
		}
	}, [persistServers, servers]);
	const handleRefresh = (0, import_react.useCallback)(async (serverId) => {
		await reloadFromConfig();
		setServers((current) => current.map((s) => s.id === serverId ? {
			...s,
			log: [...s.log, {
				level: "info",
				message: "Re-read from gateway config — live health probing not available",
				timestamp: Date.now()
			}]
		} : s));
		notify({
			kind: "info",
			title: "Config Reloaded",
			message: `${serverId} re-read from gateway config`
		});
	}, [reloadFromConfig]);
	const handleAddServer = (0, import_react.useCallback)(async (server) => {
		const newServer = {
			id: server.id || `mcp-${Date.now()}`,
			name: server.name || "New Server",
			type: server.type || "stdio",
			transport: server.transport || (server.type === "stdio" ? "stdio" : "sse"),
			command: server.command,
			args: server.args,
			url: server.url,
			enabled: true,
			autoDiscover: false,
			health: { ...UNKNOWN_HEALTH },
			config: {},
			log: [{
				level: "info",
				message: "Server added — saved to gateway config",
				timestamp: Date.now()
			}]
		};
		const next = [...servers, newServer];
		setServers(next);
		try {
			await persistServers(next);
			setShowAddDialog(false);
			notify({
				kind: "success",
				title: "Server Added",
				message: `${newServer.name} saved to gateway config`
			});
		} catch (e) {
			setServers(servers);
			notifyError(e, `Failed to save ${newServer.name} — change not saved`);
		}
	}, [persistServers, servers]);
	const handleRemoveServer = (0, import_react.useCallback)(async (serverId) => {
		const prev = servers;
		setServers(prev.filter((s) => s.id !== serverId));
		if (selectedServerId === serverId) setSelectedServerId(null);
		try {
			const record = await getAetherosConfigRecord();
			const mcp = { ...asRecord(record["mcp_servers"]) };
			delete mcp[serverId];
			await saveAetherosConfig({
				...record,
				mcp_servers: mcp
			});
			notify({
				kind: "success",
				title: "Server Removed",
				message: `Server ${serverId} removed from gateway config`
			});
		} catch (e) {
			setServers(prev);
			notifyError(e, `Failed to remove ${serverId} — change not saved`);
		}
	}, [selectedServerId, servers]);
	const handleExportConfig = (0, import_react.useCallback)(() => {
		const config = servers.map((s) => ({
			name: s.name,
			type: s.type,
			transport: s.transport,
			command: s.command,
			args: s.args,
			url: s.url,
			enabled: s.enabled,
			config: s.config
		}));
		const blob = new Blob([JSON.stringify(config, null, 2)], { type: "application/json" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = "mcp-servers.json";
		a.click();
		URL.revokeObjectURL(url);
		notify({
			kind: "success",
			title: "Config Exported",
			message: "MCP server config exported"
		});
	}, [servers]);
	const handleImportConfig = (0, import_react.useCallback)(() => {
		const input = document.createElement("input");
		input.type = "file";
		input.accept = ".json";
		input.onchange = async (e) => {
			const file = e.target.files?.[0];
			if (!file) return;
			try {
				const text = await file.text();
				const imported = JSON.parse(text);
				if (Array.isArray(imported)) {
					setServers((current) => [...current, ...imported.map((s) => ({
						id: `mcp-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
						name: s.name || "Imported Server",
						type: s.type || "stdio",
						transport: s.transport || "stdio",
						command: s.command,
						args: s.args,
						url: s.url,
						enabled: s.enabled ?? true,
						autoDiscover: false,
						health: {
							status: "unknown",
							latency: null,
							lastCheck: null,
							error: null
						},
						config: s.config || {},
						log: [{
							level: "info",
							message: "Imported from config",
							timestamp: Date.now()
						}]
					}))]);
					notify({
						kind: "success",
						title: "Config Imported",
						message: `${imported.length} server(s) imported`
					});
				} else notifyError(/* @__PURE__ */ new Error("Invalid format"), "Expected an array of server configs");
			} catch (err) {
				notifyError(err, "Failed to import config");
			}
		};
		input.click();
	}, []);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageHeader, {
			className: "w-full",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "MCP Manager" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Manage Model Context Protocol servers and connections" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						className: "text-xs",
						onClick: handleImportConfig,
						size: "sm",
						variant: "outline",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "mr-1",
							name: "file",
							size: "0.75rem"
						}), " Import"]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						className: "text-xs",
						onClick: handleExportConfig,
						size: "sm",
						variant: "outline",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "mr-1",
							name: "export",
							size: "0.75rem"
						}), " Export"]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						className: "text-xs",
						onClick: () => setShowAddDialog(true),
						size: "sm",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "mr-1",
							name: "plus",
							size: "0.75rem"
						}), " Add Server"]
					})
				]
			})]
		}),
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex h-full gap-4",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "w-72 shrink-0 space-y-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SearchField, {
						containerClassName: "w-full",
						onChange: setQuery,
						placeholder: "Search servers...",
						value: query
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
							onValueChange: (v) => setTypeFilter(v),
							value: typeFilter,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
								className: "h-7 flex-1 text-xs",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
								value: "all",
								children: "All Types"
							}), MCP_TYPES.map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
								value: t,
								children: MCP_TYPE_LABELS[t]
							}, t))] })]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
							onValueChange: (v) => setFilterHealth(v),
							value: filterHealth,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
								className: "h-7 flex-1 text-xs",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "all",
									children: "All Health"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "healthy",
									children: "Healthy"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "degraded",
									children: "Degraded"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "unhealthy",
									children: "Unhealthy"
								})
							] })]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-0.5",
						children: [filteredServers.map((server) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: cn("flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors", selectedServer?.id === server.id ? "bg-accent text-accent-foreground" : "hover:bg-accent/60"),
							onClick: () => setSelectedServerId(server.id),
							type: "button",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("size-2 shrink-0 rounded-full", HEALTH_DOT[server.health.status]) }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "min-w-0 flex-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-1.5",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "truncate text-sm font-medium",
										children: server.name
									}), !server.enabled && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: "text-[0.55rem]",
										variant: "muted",
										children: "Off"
									})]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-1.5 text-[0.6rem] text-muted-foreground",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: "text-[0.55rem]",
										variant: "outline",
										children: MCP_TYPE_LABELS[server.type]
									}), server.health.latency !== null && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [server.health.latency, "ms"] })]
								})]
							})]
						}, server.id)), filteredServers.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "px-2 py-6 text-center text-xs text-muted-foreground",
							children: !configLoaded ? "Loading gateway config…" : configError ? `Unavailable — gateway config could not be loaded (${configError})` : query ? "No servers match your search" : "Not configured — no MCP servers in gateway config"
						})]
					})
				]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "min-w-0 flex-1 overflow-y-auto",
				children: selectedServer ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-start justify-between",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-3",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("mt-1 size-3 shrink-0 rounded-full", HEALTH_DOT[selectedServer.health.status]) }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
											className: "text-lg font-semibold",
											children: selectedServer.name
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "flex flex-wrap items-center gap-2 text-xs text-muted-foreground",
											children: [
												/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
													variant: "outline",
													children: MCP_TYPE_LABELS[selectedServer.type]
												}),
												/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: selectedServer.transport }),
												selectedServer.command && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
													className: "font-mono",
													children: [
														selectedServer.command,
														" ",
														selectedServer.args?.join(" ")
													]
												}),
												selectedServer.url && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
													className: "font-mono",
													children: selectedServer.url
												})
											]
										})] })]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-1.5",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
											onClick: () => void handleRefresh(selectedServer.id),
											size: "sm",
											title: "Re-read this server from the gateway config (live health probing is not available)",
											variant: "outline",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
												className: "mr-1",
												name: "refresh",
												size: "0.75rem"
											}), "Refresh"]
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
											className: "text-muted-foreground hover:text-destructive",
											onClick: () => void handleRemoveServer(selectedServer.id),
											size: "sm",
											variant: "ghost",
											children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
												name: "trash",
												size: "0.875rem"
											})
										})]
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "mt-4 grid grid-cols-3 gap-3",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "rounded-md bg-(--ui-bg-quinary) px-3 py-2",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
												className: "text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground",
												children: "Status"
											}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
												className: "mt-0.5 flex items-center gap-1.5 text-sm font-medium",
												children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("size-2 rounded-full", HEALTH_DOT[selectedServer.health.status]) }), selectedServer.health.status.charAt(0).toUpperCase() + selectedServer.health.status.slice(1)]
											})]
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "rounded-md bg-(--ui-bg-quinary) px-3 py-2",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
												className: "text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground",
												children: "Latency"
											}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
												className: "mt-0.5 text-sm font-medium tabular-nums",
												children: selectedServer.health.latency !== null ? `${selectedServer.health.latency}ms` : "—"
											})]
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "rounded-md bg-(--ui-bg-quinary) px-3 py-2",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
												className: "text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground",
												children: "Last Check"
											}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
												className: "mt-0.5 text-sm font-medium tabular-nums",
												children: selectedServer.health.lastCheck ? new Date(selectedServer.health.lastCheck).toLocaleTimeString() : "—"
											})]
										})
									]
								}),
								selectedServer.health.error && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "mt-3 flex items-start gap-2 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: "mt-0.5 shrink-0",
										name: "error",
										size: "0.875rem"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: selectedServer.health.error })]
								})
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center justify-between rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-3",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									name: "server",
									size: "1rem"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-sm font-medium",
									children: selectedServer.name
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "text-xs text-muted-foreground",
									children: selectedServer.autoDiscover ? "Auto-discovered" : "Manual configuration"
								})] })]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
								checked: selectedServer.enabled,
								onCheckedChange: (checked) => void handleToggle(selectedServer.id, checked)
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border border-(--ui-stroke-tertiary)",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: "flex w-full items-center justify-between px-4 py-2.5 text-left",
								onClick: () => setExpandedLogServer(expandedLogServer === selectedServer.id ? null : selectedServer.id),
								type: "button",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-2",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
											name: "terminal",
											size: "0.875rem"
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-sm font-medium",
											children: "Server Log"
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Badge, {
											className: "text-[0.55rem]",
											variant: "muted",
											children: [selectedServer.log.length, " entries"]
										})
									]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "text-muted-foreground transition-transform",
									name: "chevron-down",
									size: "0.875rem",
									style: { transform: expandedLogServer === selectedServer.id ? "rotate(180deg)" : void 0 }
								})]
							}), expandedLogServer === selectedServer.id && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(LogView, {
								className: "max-h-48 border-0 border-t border-(--ui-stroke-tertiary) rounded-none",
								children: selectedServer.log.map((entry, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex gap-2 py-0.5",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: cn("shrink-0 text-[0.55rem] font-semibold uppercase", entry.level === "error" ? "text-red-500" : entry.level === "warn" ? "text-amber-500" : "text-muted-foreground"),
											children: entry.level
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-muted-foreground/60",
											children: new Date(entry.timestamp).toLocaleTimeString()
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: entry.message })
									]
								}, i))
							})]
						}),
						Object.keys(selectedServer.config).length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
								className: "mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
								children: "Configuration"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "space-y-1.5",
								children: Object.entries(selectedServer.config).map(([key, value]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-2 text-xs",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "font-medium text-foreground",
										children: [key, ":"]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-muted-foreground",
										children: String(value)
									})]
								}, key))
							})]
						})
					]
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid min-h-52 place-items-center text-center",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-muted-foreground/40",
							name: "server",
							size: "2rem"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-2 text-sm font-medium text-muted-foreground",
							children: "No server selected"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-1 text-xs text-muted-foreground/60",
							children: "Select a server or add a new one"
						})
					] })
				})
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AddServerDialog, {
			onAdd: handleAddServer,
			onClose: () => setShowAddDialog(false),
			open: showAddDialog
		})]
	});
}
function AddServerDialog({ onAdd, onClose, open }) {
	const [name, setName] = (0, import_react.useState)("");
	const [type, setType] = (0, import_react.useState)("stdio");
	const [command, setCommand] = (0, import_react.useState)("");
	const [args, setArgs] = (0, import_react.useState)("");
	const [url, setUrl] = (0, import_react.useState)("");
	const [saving, setSaving] = (0, import_react.useState)(false);
	const [error, setError] = (0, import_react.useState)(null);
	(0, import_react.useEffect)(() => {
		if (!open) {
			setName("");
			setType("stdio");
			setCommand("");
			setArgs("");
			setUrl("");
			setError(null);
		}
	}, [open]);
	const handleSubmit = async (e) => {
		e.preventDefault();
		if (!name.trim()) {
			setError("Server name is required");
			return;
		}
		if (type === "stdio" && !command.trim()) {
			setError("Command is required for STDIO servers");
			return;
		}
		if (type !== "stdio" && !url.trim()) {
			setError("URL is required for this server type");
			return;
		}
		setSaving(true);
		onAdd({
			id: `mcp-${name.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}`,
			name: name.trim(),
			type,
			transport: type === "stdio" ? "stdio" : type === "websocket" ? "ws" : type === "sse" ? "sse" : "http",
			command: type === "stdio" ? command.trim() : void 0,
			args: type === "stdio" ? args.split(/\s+/).filter(Boolean) : void 0,
			url: type !== "stdio" ? url.trim() : void 0
		});
		setSaving(false);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dialog, {
		onOpenChange: (v) => !v && !saving && onClose(),
		open,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, {
			className: "max-w-md",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, { children: "Add MCP Server" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogDescription, { children: "Configure a new Model Context Protocol server" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("form", {
				className: "grid gap-4",
				onSubmit: handleSubmit,
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-1.5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
							className: "text-xs font-medium text-foreground",
							htmlFor: "mcp-name",
							children: "Server Name"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							autoFocus: true,
							id: "mcp-name",
							onChange: (e) => setName(e.target.value),
							placeholder: "My Server",
							value: name
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-1.5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
							className: "text-xs font-medium text-foreground",
							htmlFor: "mcp-type",
							children: "Server Type"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
							onValueChange: (v) => setType(v),
							value: type,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
								className: "h-9",
								id: "mcp-type",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: MCP_TYPES.map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
								value: t,
								children: MCP_TYPE_LABELS[t]
							}, t)) })]
						})]
					}),
					type === "stdio" ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-1.5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
							className: "text-xs font-medium text-foreground",
							htmlFor: "mcp-command",
							children: "Command"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							id: "mcp-command",
							onChange: (e) => setCommand(e.target.value),
							placeholder: "npx",
							value: command
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-1.5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
							className: "text-xs font-medium text-foreground",
							htmlFor: "mcp-args",
							children: "Arguments"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							id: "mcp-args",
							onChange: (e) => setArgs(e.target.value),
							placeholder: "-y @modelcontextprotocol/server-filesystem",
							value: args
						})]
					})] }) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-1.5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
							className: "text-xs font-medium text-foreground",
							htmlFor: "mcp-url",
							children: "Server URL"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							id: "mcp-url",
							onChange: (e) => setUrl(e.target.value),
							placeholder: type === "websocket" ? "ws://localhost:8080/mcp" : "http://localhost:3000/mcp",
							value: url
						})]
					}),
					error && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-start gap-2 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "mt-0.5 shrink-0",
							name: "error",
							size: "0.75rem"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: error })]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogFooter, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: saving,
						onClick: onClose,
						type: "button",
						variant: "outline",
						children: "Cancel"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: saving,
						type: "submit",
						children: saving ? "Adding..." : "Add Server"
					})] })
				]
			})]
		})
	});
}
//#endregion
export { McpManagerView };

import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { t as $gateway } from "./gateway-D1xRY-ux.js";
import { O as Badge, S as ScrollArea, Ya as useStore, ao as require_jsx_runtime, oo as require_react } from "./index-B_yd1pEX.js";
import { t as Card } from "./card-CXjwIosc.js";
import { t as EmptyState } from "./empty-state-DbK8L0dQ.js";
//#region src/lib/extension-client.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
async function extensionList(requestGateway, opts = {}) {
	return (await requestGateway("extension.list", { ...opts })).extensions ?? [];
}
async function extensionInfo(requestGateway, id) {
	return (await requestGateway("extension.info", { id })).extension ?? {};
}
async function extensionInstall(requestGateway, source) {
	return requestGateway("extension.install", { source });
}
async function extensionUninstall(requestGateway, id) {
	return requestGateway("extension.uninstall", { id });
}
async function extensionEnable(requestGateway, id) {
	await requestGateway("extension.enable", { id });
}
async function extensionDisable(requestGateway, id) {
	await requestGateway("extension.disable", { id });
}
async function extensionVerify(requestGateway, id) {
	return requestGateway("extension.verify", { id });
}
async function extensionPermissions(requestGateway, id) {
	return requestGateway("extension.permissions", { id });
}
async function extensionRevoke(requestGateway, id) {
	await requestGateway("extension.revoke", { id });
}
async function extensionQuarantine(requestGateway, id, reason) {
	await requestGateway("extension.quarantine", {
		id,
		reason
	});
}
async function extensionEvents(requestGateway) {
	return (await requestGateway("extension.events", {})).events ?? [];
}
//#endregion
//#region src/app/extensions-center/index.tsx
var import_jsx_runtime = require_jsx_runtime();
function useGateway() {
	const client = useStore($gateway);
	return client?.request?.bind(client) ?? null;
}
function ExtensionsCenter() {
	const requestGateway = useGateway();
	const [tab, setTab] = (0, import_react.useState)("installed");
	const [query, setQuery] = (0, import_react.useState)("");
	const [exts, setExts] = (0, import_react.useState)([]);
	const [selected, setSelected] = (0, import_react.useState)("");
	const [detail, setDetail] = (0, import_react.useState)(null);
	const [perms, setPerms] = (0, import_react.useState)(null);
	const [verify, setVerify] = (0, import_react.useState)(null);
	const [events, setEvents] = (0, import_react.useState)([]);
	const [installSrc, setInstallSrc] = (0, import_react.useState)("");
	const [installResult, setInstallResult] = (0, import_react.useState)(null);
	const [status, setStatus] = (0, import_react.useState)("idle");
	const [error, setError] = (0, import_react.useState)("");
	async function refresh() {
		if (!requestGateway) return;
		setStatus("loading");
		try {
			setExts(await extensionList(requestGateway, { query: query || void 0 }));
			setEvents(await extensionEvents(requestGateway));
			setStatus("idle");
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setStatus("error");
		}
	}
	(0, import_react.useEffect)(() => {
		if (requestGateway) refresh();
	}, [requestGateway !== null]);
	if (requestGateway === null) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
		className: "h-full",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mx-auto max-w-4xl p-6",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
				description: "Connect the gateway to manage real extensions.",
				icon: "package",
				title: "Extension backend unavailable"
			})
		})
	});
	async function inspect(id) {
		if (!requestGateway) return;
		setSelected(id);
		setTab("detail");
		try {
			setDetail(await extensionInfo(requestGateway, id));
			setPerms(await extensionPermissions(requestGateway, id));
			setVerify(await extensionVerify(requestGateway, id));
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setStatus("error");
		}
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
		className: "h-full",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mx-auto max-w-7xl space-y-6 p-6",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "p-6",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "text-2xl font-semibold tracking-tight",
							children: "Extensions Center"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-(--ui-text-tertiary) mb-4",
							children: "Live extension platform state. Only metadata that exists is shown."
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mb-3 flex gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								className: "flex-1 border px-2 py-1 text-xs",
								onChange: (e) => setQuery(e.target.value),
								placeholder: "Search extensions…",
								value: query
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "text-xs underline",
								onClick: () => void refresh(),
								children: status === "loading" ? "Loading…" : "Search"
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mb-3 flex gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								className: "flex-1 border px-2 py-1 text-xs",
								onChange: (e) => setInstallSrc(e.target.value),
								placeholder: "Install from .aetherext path or directory…",
								value: installSrc
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "text-xs underline",
								onClick: () => requestGateway && installSrc.trim() && extensionInstall(requestGateway, installSrc.trim()).then((r) => {
									setInstallResult(r);
									refresh();
								}).catch((e) => {
									setError(String(e));
									setStatus("error");
								}),
								children: "Install"
							})]
						}),
						installResult && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
							className: "mb-3 whitespace-pre-wrap text-[11px]",
							children: JSON.stringify(installResult, null, 2)
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex gap-2 text-xs",
							children: [
								"installed",
								"detail",
								"security",
								"events"
							].map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: tab === t ? "font-semibold underline" : "text-(--ui-text-tertiary)",
								onClick: () => setTab(t),
								children: t
							}, t))
						})
					]
				}),
				status === "error" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "p-4 text-xs text-red-400",
					children: ["Extension request failed: ", error]
				}),
				tab === "installed" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Card, {
					className: "p-4",
					children: exts.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: "Install one from a package path above.",
						icon: "package",
						title: "No extensions"
					}) : exts.map((e) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "border-b border-(--ui-border) px-2 py-1.5 text-xs last:border-0",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "flex-1 truncate text-left font-medium underline",
									onClick: () => void inspect(e.id),
									children: e.id
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									className: "text-[8px]",
									variant: "outline",
									children: String(e.manifest?.extension_type ?? "")
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									className: "text-[8px]",
									variant: "outline",
									children: e.installed_version || "—"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									className: "text-[8px]",
									variant: "outline",
									children: e.state
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									className: "text-[8px]",
									variant: "outline",
									children: e.trust_level
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "underline",
									onClick: () => requestGateway && void extensionEnable(requestGateway, e.id).then(() => void refresh()),
									children: "Enable"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "underline",
									onClick: () => requestGateway && void extensionDisable(requestGateway, e.id).then(() => void refresh()),
									children: "Disable"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "text-red-400 underline",
									onClick: () => requestGateway && void extensionUninstall(requestGateway, e.id).then(() => void refresh()),
									children: "Uninstall"
								})
							]
						})
					}, e.id))
				}),
				tab === "detail" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Card, {
					className: "p-4",
					children: !detail ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: "Select an extension to inspect manifest, trust, health.",
						icon: "info",
						title: "Nothing selected"
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
						className: "whitespace-pre-wrap text-[11px]",
						children: JSON.stringify(detail, null, 2)
					})
				}),
				tab === "security" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Card, {
					className: "p-4",
					children: !selected ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: "Select one to review permissions and integrity.",
						icon: "shield",
						title: "No extension selected"
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex gap-2 text-xs",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "underline",
								onClick: () => requestGateway && void extensionRevoke(requestGateway, selected).then(() => void inspect(selected)),
								children: "Revoke all grants"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "text-red-400 underline",
								onClick: () => requestGateway && void extensionQuarantine(requestGateway, selected, "manual quarantine").then(() => void refresh()),
								children: "Quarantine"
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
							className: "whitespace-pre-wrap text-[11px]",
							children: JSON.stringify({
								permissions: perms,
								verify
							}, null, 2)
						})]
					})
				}),
				tab === "events" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Card, {
					className: "p-4",
					children: events.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: "Install/enable/disable actions appear here.",
						icon: "activity",
						title: "No extension events"
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "space-y-1 text-xs",
						children: events.map((e, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "border-b border-(--ui-border) py-1 last:border-0",
							children: [
								String(e.kind ?? ""),
								" — ",
								String(e.extension ?? ""),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "ml-2 text-[10px] text-(--ui-text-tertiary)",
									children: (/* @__PURE__ */ new Date(Number(e.at ?? 0) * 1e3)).toLocaleTimeString()
								})
							]
						}, i))
					})
				})
			]
		})
	});
}
//#endregion
export { ExtensionsCenter };

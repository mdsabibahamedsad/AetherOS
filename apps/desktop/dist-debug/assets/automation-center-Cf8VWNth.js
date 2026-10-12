import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { t as $gateway } from "./gateway-D1xRY-ux.js";
import { O as Badge, S as ScrollArea, Ya as useStore, ao as require_jsx_runtime, oo as require_react } from "./index-B_yd1pEX.js";
import { t as Card } from "./card-CXjwIosc.js";
import { t as EmptyState } from "./empty-state-DbK8L0dQ.js";
//#region src/lib/automation-client.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
async function automationSearch(requestGateway, opts = {}) {
	return (await requestGateway("automation.search", { ...opts })).automations ?? [];
}
async function automationPreview(requestGateway, id) {
	return (await requestGateway("automation.preview", { id })).preview ?? {};
}
async function automationEnable(requestGateway, id) {
	await requestGateway("automation.enable", { id });
}
async function automationDisable(requestGateway, id) {
	await requestGateway("automation.disable", { id });
}
async function automationDelete(requestGateway, id) {
	await requestGateway("automation.delete", { id });
}
async function automationRun(requestGateway, id, dryRun = false) {
	return (await requestGateway("automation.run", {
		id,
		dry_run: dryRun
	})).run ?? {};
}
async function automationRuns(requestGateway, id = "", limit = 50) {
	return (await requestGateway("automation.runs", {
		id,
		limit
	})).runs ?? [];
}
async function automationBuild(requestGateway, text) {
	return requestGateway("automation.build", { text });
}
async function automationHealth(requestGateway) {
	const res = await requestGateway("automation.health", {});
	return {
		...res.health ?? {},
		metrics: res.metrics ?? {}
	};
}
async function automationStopAll(requestGateway) {
	await requestGateway("automation.stop_all", {});
}
//#endregion
//#region src/app/automation-center/index.tsx
var import_jsx_runtime = require_jsx_runtime();
function useGateway() {
	const client = useStore($gateway);
	return client?.request?.bind(client) ?? null;
}
function AutomationCenter() {
	const requestGateway = useGateway();
	const [tab, setTab] = (0, import_react.useState)("overview");
	const [autos, setAutos] = (0, import_react.useState)([]);
	const [runs, setRuns] = (0, import_react.useState)([]);
	const [health, setHealth] = (0, import_react.useState)(null);
	const [selected, setSelected] = (0, import_react.useState)("");
	const [preview, setPreview] = (0, import_react.useState)(null);
	const [nlText, setNlText] = (0, import_react.useState)("");
	const [built, setBuilt] = (0, import_react.useState)(null);
	const [status, setStatus] = (0, import_react.useState)("idle");
	const [error, setError] = (0, import_react.useState)("");
	async function refresh() {
		if (!requestGateway) return;
		setStatus("loading");
		try {
			setAutos(await automationSearch(requestGateway));
			setRuns(await automationRuns(requestGateway));
			setHealth(await automationHealth(requestGateway));
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
				description: "Connect the gateway to manage live automations.",
				icon: "zap",
				title: "Automation backend unavailable"
			})
		})
	});
	async function inspect(id) {
		if (!requestGateway) return;
		setSelected(id);
		try {
			setPreview(await automationPreview(requestGateway, id));
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
							children: "Automation Center"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-(--ui-text-tertiary) mb-4",
							children: "Live autonomous operations. Every value comes from the backend."
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex gap-2 text-xs",
							children: [
								[
									"overview",
									"automations",
									"runs",
									"builder"
								].map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: tab === t ? "font-semibold underline" : "text-(--ui-text-tertiary)",
									onClick: () => setTab(t),
									children: t
								}, t)),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "flex-1" }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "underline",
									onClick: () => void refresh(),
									children: "Refresh"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "text-red-400 underline",
									onClick: () => requestGateway && void automationStopAll(requestGateway).then(() => void refresh()),
									children: "Stop all"
								})
							]
						})
					]
				}),
				status === "error" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "p-4 text-xs text-red-400",
					children: ["Automation request failed: ", error]
				}),
				tab === "overview" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Card, {
					className: "p-4",
					children: !health ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: status === "loading" ? "Loading…" : "Press Refresh.",
						icon: "activity",
						title: "No health data"
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
						className: "whitespace-pre-wrap text-[11px]",
						children: JSON.stringify(health, null, 2)
					})
				}),
				tab === "automations" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Card, {
					className: "p-4",
					children: autos.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: "Build one in the builder tab.",
						icon: "zap",
						title: "No automations"
					}) : autos.map((a) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "border-b border-(--ui-border) px-2 py-1.5 text-xs last:border-0",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "flex-1 truncate text-left font-medium underline",
									onClick: () => void inspect(a.id),
									children: a.name
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									className: "text-[8px]",
									variant: "outline",
									children: a.auto_type
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									className: "text-[8px]",
									variant: "outline",
									children: a.enabled ? "active" : "draft"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "underline",
									onClick: () => requestGateway && void automationEnable(requestGateway, a.id).then(() => void refresh()),
									children: "Enable"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "underline",
									onClick: () => requestGateway && void automationDisable(requestGateway, a.id).then(() => void refresh()),
									children: "Disable"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "underline",
									onClick: () => requestGateway && void automationRun(requestGateway, a.id, true).then((r) => setPreview({ dry_run: r })),
									children: "Dry-run"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "underline",
									onClick: () => requestGateway && void automationRun(requestGateway, a.id).then(() => void refresh()),
									children: "Run now"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "text-red-400 underline",
									onClick: () => requestGateway && void automationDelete(requestGateway, a.id).then(() => void refresh()),
									children: "Delete"
								})
							]
						}), selected === a.id && preview && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
							className: "mt-1 whitespace-pre-wrap text-[11px] text-(--ui-text-tertiary)",
							children: JSON.stringify(preview, null, 2)
						})]
					}, a.id))
				}),
				tab === "runs" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Card, {
					className: "p-4",
					children: runs.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: "Runs appear here with states, durations and costs.",
						icon: "clock",
						title: "No runs yet"
					}) : runs.map((r, i) => {
						const run = r;
						return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "border-b border-(--ui-border) py-1 text-xs last:border-0",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "font-medium",
									children: String(run.run_id ?? "").slice(0, 8)
								}),
								" — ",
								String(run.state ?? ""),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "ml-2 text-(--ui-text-tertiary)",
									children: [
										"trigger: ",
										String(run.trigger_kind ?? ""),
										" steps: ",
										Array.isArray(run.steps) ? run.steps.length : 0
									]
								}),
								run.error ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "ml-2 text-red-400",
									children: String(run.error)
								}) : null
							]
						}, String(run.run_id ?? i));
					})
				}),
				tab === "builder" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mb-3 flex gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							className: "flex-1 border px-2 py-1 text-xs",
							onChange: (e) => setNlText(e.target.value),
							placeholder: "e.g. \"Every Friday research AI agent developments and send me a summary\"",
							value: nlText
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "text-xs underline",
							onClick: () => requestGateway && nlText.trim() && automationBuild(requestGateway, nlText.trim()).then(setBuilt).catch((e) => {
								setError(String(e));
								setStatus("error");
							}),
							children: "Build plan"
						})]
					}), !built ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: "A draft plan preview appears here. Nothing activates without approval.",
						icon: "plus",
						title: "Describe an automation"
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
						className: "whitespace-pre-wrap text-[11px]",
						children: JSON.stringify(built, null, 2)
					})]
				})
			]
		})
	});
}
//#endregion
export { AutomationCenter };

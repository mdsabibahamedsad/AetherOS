import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { t as $gateway } from "./gateway-D1xRY-ux.js";
import { O as Badge, S as ScrollArea, Ya as useStore, ao as require_jsx_runtime, oo as require_react } from "./index-B_yd1pEX.js";
import { t as Card } from "./card-CXjwIosc.js";
import { t as EmptyState } from "./empty-state-DbK8L0dQ.js";
//#region src/lib/memory2-client.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
async function memorySearch(requestGateway, query, opts = {}) {
	return (await requestGateway("memory2.search", {
		query,
		top_k: opts.top_k ?? 8,
		mode: opts.mode ?? "hybrid",
		...opts.project_id ? { project_id: opts.project_id } : {}
	})).included ?? [];
}
async function memoryTimeline(requestGateway, opts = {}) {
	return (await requestGateway("memory2.timeline", {
		days: opts.days ?? 30,
		limit: opts.limit ?? 100,
		...opts.project_id ? { project_id: opts.project_id } : {}
	})).items ?? [];
}
async function memoryHealth(requestGateway) {
	return requestGateway("memory2.health", {});
}
async function memoryProject(requestGateway, projectId) {
	return (await requestGateway("memory2.project", { project_id: projectId })).project ?? {};
}
async function memoryExplain(requestGateway, id) {
	return (await requestGateway("memory2.explain", { id })).explanation ?? {};
}
async function memoryForget(requestGateway, opts) {
	return requestGateway("memory2.forget", { ...opts });
}
//#endregion
//#region src/app/memory/index.tsx
var import_jsx_runtime = require_jsx_runtime();
function useGateway() {
	const client = useStore($gateway);
	return client?.request?.bind(client) ?? null;
}
function MemoryView() {
	const requestGateway = useGateway();
	const [tab, setTab] = (0, import_react.useState)("search");
	const [query, setQuery] = (0, import_react.useState)("");
	const [projectId, setProjectId] = (0, import_react.useState)("");
	const [hits, setHits] = (0, import_react.useState)([]);
	const [timeline, setTimeline] = (0, import_react.useState)([]);
	const [project, setProject] = (0, import_react.useState)(null);
	const [health, setHealth] = (0, import_react.useState)(null);
	const [selectedId, setSelectedId] = (0, import_react.useState)("");
	const [explanation, setExplanation] = (0, import_react.useState)(null);
	const [status, setStatus] = (0, import_react.useState)("idle");
	const [error, setError] = (0, import_react.useState)("");
	const unavailable = requestGateway === null;
	async function runSearch() {
		if (!requestGateway || !query.trim()) return;
		setStatus("loading");
		try {
			setHits(await memorySearch(requestGateway, query, { project_id: projectId || void 0 }));
			setStatus("idle");
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setStatus("error");
		}
	}
	async function loadTimeline() {
		if (!requestGateway) return;
		setStatus("loading");
		try {
			setTimeline(await memoryTimeline(requestGateway, { project_id: projectId || void 0 }));
			setStatus("idle");
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setStatus("error");
		}
	}
	async function loadProject() {
		if (!requestGateway || !projectId.trim()) return;
		setStatus("loading");
		try {
			setProject(await memoryProject(requestGateway, projectId.trim()));
			setStatus("idle");
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setStatus("error");
		}
	}
	async function loadHealth() {
		if (!requestGateway) return;
		setStatus("loading");
		try {
			setHealth(await memoryHealth(requestGateway));
			setStatus("idle");
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setStatus("error");
		}
	}
	async function inspect(id) {
		if (!requestGateway) return;
		setSelectedId(id);
		try {
			setExplanation(await memoryExplain(requestGateway, id));
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setStatus("error");
		}
	}
	async function forget(id) {
		if (!requestGateway) return;
		try {
			await memoryForget(requestGateway, { id });
			setHits((h) => h.filter((x) => x.id !== id));
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setStatus("error");
		}
	}
	(0, import_react.useEffect)(() => {
		if (tab === "timeline" && requestGateway) loadTimeline();
		if (tab === "health" && requestGateway) loadHealth();
	}, [tab]);
	if (unavailable) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
		className: "h-full",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mx-auto max-w-4xl p-6",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
				description: "Connect the gateway to browse Memory 2.0.",
				icon: "database",
				title: "Memory backend unavailable"
			})
		})
	});
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
							children: "Memory Center"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-(--ui-text-tertiary) mb-4",
							children: "Live Memory 2.0 state. Every value below comes from the backend."
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex gap-2 text-xs",
							children: [
								"search",
								"timeline",
								"project",
								"inspector",
								"health"
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
					children: ["Memory request failed: ", error]
				}),
				tab === "search" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex gap-2 mb-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								className: "flex-1 border px-2 py-1 text-xs",
								onChange: (e) => setQuery(e.target.value),
								placeholder: "Search memories, e.g. \"Why did we choose Electron?\"",
								value: query
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								className: "border px-2 py-1 text-xs",
								onChange: (e) => setProjectId(e.target.value),
								placeholder: "Project filter (optional)",
								value: projectId
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "text-xs underline",
								onClick: () => void runSearch(),
								children: status === "loading" ? "Searching…" : "Search"
							})
						]
					}), hits.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: "Run a search to see live memory hits with scores.",
						icon: "search",
						title: "No results"
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "space-y-2",
						children: hits.map((h) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "border-b border-(--ui-border) px-2 py-1.5 text-xs last:border-0",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-2",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "flex-1 truncate font-medium",
											children: h.summary || h.content
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
											className: "text-[8px]",
											variant: "outline",
											children: h.type
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Badge, {
											className: "text-[8px]",
											variant: "outline",
											children: ["score ", h.score.toFixed(2)]
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
											className: "text-[8px]",
											variant: "outline",
											children: h.confidence_band
										}),
										h.conflicted && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
											className: "text-[8px]",
											variant: "outline",
											children: "conflicted"
										})
									]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "text-[10px] text-(--ui-text-tertiary)",
									children: h.explanation
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex gap-2 text-[10px]",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
										className: "underline",
										onClick: () => {
											setTab("inspector");
											inspect(h.id);
										},
										children: "Inspect"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
										className: "underline text-red-400",
										onClick: () => void forget(h.id),
										children: "Forget"
									})]
								})
							]
						}, h.id))
					})]
				}),
				tab === "timeline" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "mb-3 text-sm font-medium",
						children: "Timeline (live)"
					}), timeline.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: "Memories will appear here as they are created.",
						icon: "clock",
						title: "No timeline entries"
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "space-y-1 text-xs",
						children: timeline.map((t, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "border-b border-(--ui-border) py-1 last:border-0",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-(--ui-text-tertiary)",
									children: (/* @__PURE__ */ new Date(t.created_at * 1e3)).toLocaleString()
								}),
								" — ",
								String(t.summary ?? ""),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									className: "ml-2 text-[8px]",
									variant: "outline",
									children: String(t.type ?? "")
								})
							]
						}, String(t.id ?? i)))
					})]
				}),
				tab === "project" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mb-3 flex gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							className: "flex-1 border px-2 py-1 text-xs",
							onChange: (e) => setProjectId(e.target.value),
							placeholder: "Project id",
							value: projectId
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "text-xs underline",
							onClick: () => void loadProject(),
							children: "Load"
						})]
					}), !project ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: "Enter a project id to see its live memory panel.",
						icon: "folder",
						title: "No project loaded"
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
						className: "whitespace-pre-wrap text-[11px]",
						children: JSON.stringify(project, null, 2)
					})]
				}),
				tab === "inspector" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "mb-3 text-sm font-medium",
						children: "Memory Inspector"
					}), !explanation ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: selectedId ? `Loading ${selectedId}…` : "Select Inspect on a search hit.",
						icon: "info",
						title: "Nothing selected"
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
						className: "whitespace-pre-wrap text-[11px]",
						children: JSON.stringify(explanation, null, 2)
					})]
				}),
				tab === "health" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "mb-3 text-sm font-medium",
						children: "Memory Health (measured)"
					}), !health ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: status === "loading" ? "Loading…" : "Open this tab to query live health.",
						icon: "activity",
						title: "Not loaded"
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
						className: "whitespace-pre-wrap text-[11px]",
						children: JSON.stringify(health, null, 2)
					})]
				})
			]
		})
	});
}
//#endregion
export { MemoryView };

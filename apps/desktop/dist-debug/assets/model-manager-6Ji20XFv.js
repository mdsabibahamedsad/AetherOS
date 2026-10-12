import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { C as Select, D as SelectValue, E as SelectTrigger, La as Button, O as Badge, Qa as atom, Ra as cn, T as SelectItem, Xa as init_nanostores, Ya as useStore, ao as require_jsx_runtime, ni as Input, oo as require_react, w as SelectContent } from "./index-B_yd1pEX.js";
//#region src/store/provider-manager.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
init_nanostores();
var ROLE_LABELS = {
	default: "Default",
	coding: "Coding",
	reasoning: "Reasoning",
	vision: "Vision",
	embedding: "Embedding",
	speech: "Speech",
	fast: "Fast",
	"long-context": "Long Context"
};
var ROUTER_TASKS = [
	{
		id: "default",
		label: "Default Chat"
	},
	{
		id: "coding",
		label: "Coding"
	},
	{
		id: "reasoning",
		label: "Reasoning"
	},
	{
		id: "vision",
		label: "Vision"
	},
	{
		id: "embedding",
		label: "Embedding"
	},
	{
		id: "voice",
		label: "Voice"
	},
	{
		id: "automation",
		label: "Automation"
	},
	{
		id: "research",
		label: "Research"
	}
];
var $providerManager = /* @__PURE__ */ atom({
	providers: [],
	models: [],
	healthHistory: [],
	routerRules: ROUTER_TASKS.map((t) => ({
		task: t.id,
		taskLabel: t.label,
		provider: null,
		model: null,
		enabled: true,
		priority: ROUTER_TASKS.findIndex((x) => x.id === t.id)
	})),
	testerResults: [],
	settings: {
		timeout: 3e4,
		retries: 3,
		fallbackProvider: null,
		preferredProvider: null,
		streaming: true,
		parallelRequests: false,
		caching: true,
		compression: true,
		maxConcurrency: 5
	},
	selectedProvider: null,
	searchQuery: "",
	modelFilterProvider: null,
	modelFilterRole: null,
	modelSort: "name",
	sortAsc: true,
	showHiddenModels: false,
	localScanning: false,
	localModels: []
});
var patch = (update) => $providerManager.set({
	...$providerManager.get(),
	...update
});
function setProviders(providers) {
	patch({ providers });
}
function updateProvider(slug, update) {
	patch({ providers: $providerManager.get().providers.map((p) => p.slug === slug ? {
		...p,
		...update
	} : p) });
}
function setSelectedProvider(slug) {
	patch({ selectedProvider: slug });
}
function setModels(models) {
	patch({ models });
}
function toggleModelFavorite(modelId) {
	patch({ models: $providerManager.get().models.map((m) => m.id === modelId ? {
		...m,
		favorite: !m.favorite
	} : m) });
}
function toggleModelPin(modelId) {
	patch({ models: $providerManager.get().models.map((m) => m.id === modelId ? {
		...m,
		pinned: !m.pinned
	} : m) });
}
function toggleModelHidden(modelId) {
	patch({ models: $providerManager.get().models.map((m) => m.id === modelId ? {
		...m,
		hidden: !m.hidden,
		pinned: false
	} : m) });
}
function setSearchQuery(query) {
	patch({ searchQuery: query });
}
function setModelFilterProvider(slug) {
	patch({ modelFilterProvider: slug });
}
function setModelFilterRole(role) {
	patch({ modelFilterRole: role });
}
function setModelSort(sort) {
	patch({ modelSort: sort });
}
function toggleSortAsc() {
	patch({ sortAsc: !$providerManager.get().sortAsc });
}
function setShowHiddenModels(show) {
	patch({ showHiddenModels: show });
}
function addHealthEvent(event) {
	patch({ healthHistory: [$providerManager.get().healthHistory, event].flat().slice(-100) });
	updateProvider(event.provider, {
		health: event.status,
		latencyMs: event.latencyMs
	});
}
function updateRouterRule(task, update) {
	patch({ routerRules: $providerManager.get().routerRules.map((r) => r.task === task ? {
		...r,
		...update
	} : r) });
}
function addTesterResult(result) {
	patch({ testerResults: [$providerManager.get().testerResults, result].flat().slice(-50) });
}
function updateSettings(update) {
	patch({ settings: {
		...$providerManager.get().settings,
		...update
	} });
}
//#endregion
//#region src/app/provider-manager/model-manager.tsx
var import_jsx_runtime = require_jsx_runtime();
var ROLE_OPTIONS = [{
	value: "all",
	label: "All Roles"
}, ...Object.entries(ROLE_LABELS).map(([key, label]) => ({
	value: key,
	label
}))];
function ModelTableRow({ model, onFavorite, onPin, onHide }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: cn("flex items-center gap-3 rounded-lg border px-4 py-2.5 text-sm transition-all hover:bg-accent/30", model.hidden && "opacity-40"),
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
				className: "shrink-0 text-muted-foreground hover:text-yellow-500",
				onClick: onFavorite,
				type: "button",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
					className: cn("h-4 w-4", model.favorite && "fill-yellow-500 text-yellow-500"),
					fill: model.favorite ? "currentColor" : "none",
					stroke: "currentColor",
					strokeWidth: 2,
					viewBox: "0 0 24 24",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" })
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
				className: cn("shrink-0 text-muted-foreground hover:text-blue-500", model.pinned && "text-blue-500"),
				onClick: onPin,
				type: "button",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
					className: "h-4 w-4 rotate-45",
					fill: "none",
					stroke: "currentColor",
					strokeWidth: 2,
					viewBox: "0 0 24 24",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2z" })
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: cn("h-2 w-2 shrink-0 rounded-full", model.speed === "fast" ? "bg-green-500" : model.capabilities.reasoning ? "bg-purple-500" : "bg-blue-400") }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0 flex-1",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "font-mono text-sm truncate",
						children: model.name
					}), model.pricing?.free && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						className: "text-[10px] h-5 border-green-500/30 text-green-600 shrink-0",
						variant: "outline",
						children: "Free"
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "text-xs text-muted-foreground",
					children: model.providerName
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-1.5",
				children: [
					model.capabilities.vision && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						className: "text-[10px] h-5",
						variant: "secondary",
						children: "Vision"
					}),
					model.capabilities.reasoning && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						className: "text-[10px] h-5",
						variant: "secondary",
						children: "Reason"
					}),
					model.capabilities.functionCalling && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						className: "text-[10px] h-5",
						variant: "outline",
						children: "FC"
					})
				]
			}),
			model.pricing && !model.pricing.free && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
				className: "shrink-0 text-xs text-muted-foreground font-mono",
				children: [
					"$",
					model.pricing.input,
					"/M"
				]
			}),
			model.contextLength && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
				className: "shrink-0 text-xs text-muted-foreground font-mono",
				children: [(model.contextLength / 1e3).toFixed(0), "K"]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex items-center gap-1",
				children: model.roles.slice(0, 2).map((role) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
					className: "text-[10px] h-5",
					variant: "secondary",
					children: ROLE_LABELS[role]
				}, role))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
				className: "shrink-0 text-muted-foreground/50 hover:text-destructive",
				onClick: onHide,
				type: "button",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
					className: "h-3.5 w-3.5",
					fill: "none",
					stroke: "currentColor",
					strokeWidth: 2,
					viewBox: "0 0 24 24",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" })
				})
			})
		]
	});
}
function ModelManager() {
	const state = useStore($providerManager);
	const providers = (0, import_react.useMemo)(() => {
		const seen = /* @__PURE__ */ new Set();
		return state.models.map((m) => ({
			slug: m.provider,
			name: m.providerName
		})).filter((p) => {
			const k = p.slug;
			if (seen.has(k)) return false;
			seen.add(k);
			return true;
		}).sort((a, b) => a.name.localeCompare(b.name));
	}, [state.models]);
	const filtered = (0, import_react.useMemo)(() => {
		let list = [...state.models];
		if (state.searchQuery) {
			const q = state.searchQuery.toLowerCase();
			list = list.filter((m) => m.name.toLowerCase().includes(q) || m.providerName.toLowerCase().includes(q));
		}
		if (state.modelFilterProvider) list = list.filter((m) => m.provider === state.modelFilterProvider);
		if (state.modelFilterRole) list = list.filter((m) => m.roles.includes(state.modelFilterRole));
		if (!state.showHiddenModels) list = list.filter((m) => !m.hidden);
		const sortKey = state.modelSort;
		list.sort((a, b) => {
			let cmp = 0;
			if (sortKey === "name") cmp = a.name.localeCompare(b.name);
			else if (sortKey === "provider") cmp = a.providerName.localeCompare(b.providerName);
			else if (sortKey === "context") cmp = (a.contextLength ?? 0) - (b.contextLength ?? 0);
			else if (sortKey === "latency") cmp = (a.latencyMs ?? 999999) - (b.latencyMs ?? 999999);
			return state.sortAsc ? cmp : -cmp;
		});
		return list;
	}, [
		state.models,
		state.searchQuery,
		state.modelFilterProvider,
		state.modelFilterRole,
		state.modelSort,
		state.sortAsc,
		state.showHiddenModels
	]);
	const modelCount = filtered.length;
	const favoriteCount = filtered.filter((m) => m.favorite).length;
	const pinnedCount = filtered.filter((m) => m.pinned).length;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-1 flex-col overflow-hidden",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex shrink-0 items-center gap-3 border-b px-6 py-3",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
					className: "max-w-xs font-mono text-sm",
					onChange: (e) => setSearchQuery(e.target.value),
					placeholder: "Search models...",
					value: state.searchQuery
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
					onValueChange: (v) => setModelFilterProvider(v === "all" ? null : v),
					value: state.modelFilterProvider ?? "all",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
						className: "w-40",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: "All providers" })
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
						value: "all",
						children: "All Providers"
					}), providers.map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
						value: p.slug,
						children: p.name
					}, p.slug))] })]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
					onValueChange: (v) => setModelFilterRole(v === "all" ? null : v),
					value: state.modelFilterRole ?? "all",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
						className: "w-36",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: "All roles" })
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: ROLE_OPTIONS.map((o) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
						value: o.value,
						children: o.label
					}, o.value)) })]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
					onValueChange: (v) => setModelSort(v),
					value: state.modelSort,
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
						className: "w-32",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
							value: "name",
							children: "Name"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
							value: "provider",
							children: "Provider"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
							value: "context",
							children: "Context"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
							value: "latency",
							children: "Latency"
						})
					] })]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					"aria-label": "Toggle sort order",
					className: "shrink-0",
					onClick: toggleSortAsc,
					size: "icon",
					variant: "ghost",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
						className: cn("h-4 w-4 transition-transform", !state.sortAsc && "rotate-180"),
						fill: "none",
						stroke: "currentColor",
						strokeWidth: 2,
						viewBox: "0 0 24 24",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M8 3v12M12 3l-4 4M8 7l-4-4M16 21V9M16 17l-4 4M20 17l-4-4" })
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "ml-auto flex items-center gap-3 text-xs text-muted-foreground",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [modelCount, " models"] }),
						favoriteCount > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [favoriteCount, " ★"] }),
						pinnedCount > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [pinnedCount, " 📌"] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
							className: "flex items-center gap-1.5 cursor-pointer",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								checked: state.showHiddenModels,
								className: "rounded",
								onChange: (e) => setShowHiddenModels(e.target.checked),
								type: "checkbox"
							}), "Show hidden"]
						})
					]
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex-1 overflow-y-auto p-4",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-1.5",
				children: filtered.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "py-12 text-center text-sm text-muted-foreground",
					children: "No models match your filters"
				}) : filtered.map((model) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ModelTableRow, {
					model,
					onFavorite: () => toggleModelFavorite(model.id),
					onHide: () => toggleModelHidden(model.id),
					onPin: () => toggleModelPin(model.id)
				}, model.id))
			})
		})]
	});
}
//#endregion
export { addTesterResult as a, setSelectedProvider as c, updateSettings as d, addHealthEvent as i, updateProvider as l, $providerManager as n, setModels as o, ROUTER_TASKS as r, setProviders as s, ModelManager as t, updateRouterRule as u };

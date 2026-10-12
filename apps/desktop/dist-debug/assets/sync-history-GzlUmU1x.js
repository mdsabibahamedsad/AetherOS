import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { C as Select, D as SelectValue, Di as notify, E as SelectTrigger, Ia as Codicon, La as Button, O as Badge, Ra as cn, T as SelectItem, ao as require_jsx_runtime, oo as require_react, vt as SearchField, w as SelectContent } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
import { d as clearSyncHistory, i as $syncHistory } from "./sync-RdGmYJXp.js";
//#region src/app/sync-history/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var SAMPLE_EVENTS = Array.from({ length: 45 }, (_, i) => ({
	id: `sample-${i}`,
	scope: [
		"messages",
		"sessions",
		"memory",
		"files",
		"config",
		"knowledge",
		"plugins",
		"skills"
	][Math.floor(Math.random() * 8)],
	type: [
		"push",
		"pull",
		"conflict",
		"error"
	][Math.floor(Math.random() * 4)],
	status: [
		"success",
		"failed",
		"pending"
	][Math.floor(Math.random() * 3)],
	timestamp: (/* @__PURE__ */ new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1e3)).toISOString(),
	itemsCount: Math.floor(Math.random() * 50) + 1,
	errorMessage: void 0,
	deviceId: `device-${Math.floor(Math.random() * 3) + 1}`
})).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
var SCOPES = [
	"all",
	"messages",
	"sessions",
	"memory",
	"files",
	"config",
	"knowledge",
	"plugins",
	"skills"
];
var STATUSES = [
	"all",
	"success",
	"failed",
	"pending"
];
var PAGE_SIZE = 10;
function SyncHistoryView() {
	const storeHistory = $syncHistory.get();
	const events = storeHistory.length > 0 ? storeHistory : SAMPLE_EVENTS;
	const [search, setSearch] = (0, import_react.useState)("");
	const [scopeFilter, setScopeFilter] = (0, import_react.useState)("all");
	const [statusFilter, setStatusFilter] = (0, import_react.useState)("all");
	const [page, setPage] = (0, import_react.useState)(1);
	const filteredEvents = (0, import_react.useMemo)(() => {
		const q = search.trim().toLowerCase();
		return events.filter((e) => {
			if (scopeFilter !== "all" && e.scope !== scopeFilter) return false;
			if (statusFilter !== "all" && e.status !== statusFilter) return false;
			if (q && !e.scope.toLowerCase().includes(q) && !e.type.toLowerCase().includes(q) && !e.id.toLowerCase().includes(q)) return false;
			return true;
		});
	}, [
		events,
		search,
		scopeFilter,
		statusFilter
	]);
	const totalPages = Math.max(1, Math.ceil(filteredEvents.length / PAGE_SIZE));
	const paginatedEvents = filteredEvents.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
	const handleExport = (0, import_react.useCallback)(() => {
		const data = JSON.stringify(filteredEvents, null, 2);
		const blob = new Blob([data], { type: "application/json" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `sync-history-${(/* @__PURE__ */ new Date()).toISOString().slice(0, 10)}.json`;
		a.click();
		URL.revokeObjectURL(url);
		notify({
			kind: "success",
			title: "Exported",
			message: `Exported ${filteredEvents.length} events`
		});
	}, [filteredEvents]);
	const handleClear = (0, import_react.useCallback)(() => {
		clearSyncHistory();
		notify({
			kind: "info",
			title: "History Cleared",
			message: "Sync history has been cleared"
		});
	}, []);
	const handlePageChange = (0, import_react.useCallback)((newPage) => {
		setPage(Math.max(1, Math.min(newPage, totalPages)));
	}, [totalPages]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageHeader, {
			className: "w-full",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Sync History" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Review past synchronization activity" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						className: "text-xs",
						onClick: handleExport,
						size: "sm",
						variant: "outline",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "download",
							size: "0.75rem"
						}), "Export"]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						className: "text-xs",
						disabled: events.length === 0,
						onClick: handleClear,
						size: "sm",
						variant: "ghost",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "trash",
							size: "0.75rem"
						}), "Clear"]
					})]
				})]
			})
		}),
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SearchField, {
						containerClassName: "flex-1 max-w-xs",
						onChange: (v) => {
							setSearch(v);
							setPage(1);
						},
						placeholder: "Search history...",
						value: search
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
						onValueChange: (v) => {
							setScopeFilter(v);
							setPage(1);
						},
						value: scopeFilter,
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
							className: "h-8 w-32 text-xs",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: SCOPES.map((s) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
							value: s,
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "capitalize",
								children: s
							})
						}, s)) })]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
						onValueChange: (v) => {
							setStatusFilter(v);
							setPage(1);
						},
						value: statusFilter,
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
							className: "h-8 w-28 text-xs",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: STATUSES.map((s) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
							value: s,
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "capitalize",
								children: s === "failed" ? "Failed" : s === "pending" ? "Pending" : s === "all" ? "All Status" : "Success"
							})
						}, s)) })]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-4 space-y-1",
				children: [paginatedEvents.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid min-h-40 place-items-center text-center",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-muted-foreground/40",
							name: "history",
							size: "2rem"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-2 text-sm text-muted-foreground",
							children: "No sync events found"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-xs text-muted-foreground/60",
							children: "Try adjusting filters"
						})
					] })
				}), paginatedEvents.map((event, i) => {
					const date = new Date(event.timestamp);
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [(i === 0 || new Date(paginatedEvents[i - 1]?.timestamp ?? 0).toDateString() !== date.toDateString()) && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "sticky top-0 z-10 bg-(--ui-app-background) py-1 text-[0.6rem] font-semibold uppercase tracking-wider text-muted-foreground",
						children: date.toLocaleDateString(void 0, {
							weekday: "long",
							month: "long",
							day: "numeric",
							year: "numeric"
						})
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between rounded-md px-2.5 py-1.5 text-xs transition-colors hover:bg-accent/30",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2.5 min-w-0",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: cn("flex size-6 shrink-0 items-center justify-center rounded", event.status === "success" ? "bg-emerald-500/10 text-emerald-500" : event.status === "failed" ? "bg-destructive/10 text-destructive" : "bg-muted text-muted-foreground"),
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									name: event.type === "push" ? "arrow-up" : event.type === "pull" ? "arrow-down" : event.type === "conflict" ? "warning" : "error",
									size: "0.65rem"
								})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "min-w-0",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-1.5",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "truncate font-medium capitalize",
										children: event.scope
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: "shrink-0 text-[0.5rem]",
										variant: event.status === "failed" ? "destructive" : event.status === "pending" ? "muted" : "outline",
										children: event.status
									})]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
									className: "text-[0.6rem] text-muted-foreground",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "capitalize",
											children: event.type
										}),
										event.deviceId && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [" · ", event.deviceId] }),
										/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
											" · ",
											event.itemsCount,
											" items"
										] })
									]
								})]
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "shrink-0 text-[0.6rem] text-muted-foreground",
							children: date.toLocaleTimeString(void 0, {
								hour: "2-digit",
								minute: "2-digit"
							})
						})]
					})] }, event.id);
				})]
			}),
			totalPages > 1 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-4 flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
					className: "text-[0.6rem] text-muted-foreground",
					children: [
						"Page ",
						page,
						" of ",
						totalPages,
						" (",
						filteredEvents.length,
						" events)"
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-1",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							disabled: page <= 1,
							onClick: () => handlePageChange(page - 1),
							size: "sm",
							variant: "ghost",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "chevron-left",
								size: "0.75rem"
							})
						}),
						Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
							const pageNum = Math.max(1, Math.min(page - 2, totalPages - 4)) + i;
							if (pageNum > totalPages) return null;
							return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								className: cn("min-w-7 px-1 text-xs", pageNum === page && "bg-primary/10 text-primary"),
								onClick: () => handlePageChange(pageNum),
								size: "sm",
								variant: "ghost",
								children: pageNum
							}, pageNum);
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							disabled: page >= totalPages,
							onClick: () => handlePageChange(page + 1),
							size: "sm",
							variant: "ghost",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "chevron-right",
								size: "0.75rem"
							})
						})
					]
				})]
			})
		]
	});
}
//#endregion
export { SyncHistoryView };

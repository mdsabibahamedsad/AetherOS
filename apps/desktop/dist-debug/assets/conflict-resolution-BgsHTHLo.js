import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Di as notify, Ia as Codicon, La as Button, O as Badge, Ra as cn, ao as require_jsx_runtime, oo as require_react } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
import { p as resolveConflict, t as $syncConflicts } from "./sync-RdGmYJXp.js";
//#region src/app/conflict-resolution/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var RESOLVED_SAMPLE = [{
	id: "resolved-1",
	scope: "files",
	filePath: "notes/project-plan.md",
	localVersion: "## Updated plan\n\n- Task A completed\n- Task B in progress",
	remoteVersion: "## Updated plan\n\n- Task A in progress\n- Task B completed",
	localModifiedAt: "2026-07-20T10:00:00Z",
	remoteModifiedAt: "2026-07-20T10:30:00Z",
	status: "resolved",
	resolution: "merged",
	resolvedAt: "2026-07-21T08:00:00Z"
}, {
	id: "resolved-2",
	scope: "config",
	filePath: "config/themes.json",
	localVersion: "{\"theme\": \"dark\"}",
	remoteVersion: "{\"theme\": \"light\"}",
	localModifiedAt: "2026-07-19T14:00:00Z",
	remoteModifiedAt: "2026-07-19T15:00:00Z",
	status: "resolved",
	resolution: "keep-local",
	resolvedAt: "2026-07-20T09:00:00Z"
}];
function ConflictResolutionView() {
	const unresolvedConflicts = $syncConflicts.get();
	const [selectedConflict, setSelectedConflict] = (0, import_react.useState)(null);
	const [showResolved, setShowResolved] = (0, import_react.useState)(false);
	const [resolvedHistory] = (0, import_react.useState)(RESOLVED_SAMPLE);
	const handleResolve = (0, import_react.useCallback)((conflict, resolution) => {
		resolveConflict(conflict.id, resolution);
		if (selectedConflict?.id === conflict.id) setSelectedConflict(null);
		notify({
			kind: "success",
			title: "Conflict Resolved",
			message: `Resolution: ${resolution}`
		});
	}, [selectedConflict]);
	const handleResolveAllLocal = (0, import_react.useCallback)(() => {
		for (const c of unresolvedConflicts) resolveConflict(c.id, "keep-local");
		setSelectedConflict(null);
		notify({
			kind: "success",
			title: "All Resolved",
			message: `Resolved ${unresolvedConflicts.length} conflicts — kept local versions`
		});
	}, [unresolvedConflicts]);
	const handleResolveAllRemote = (0, import_react.useCallback)(() => {
		for (const c of unresolvedConflicts) resolveConflict(c.id, "keep-remote");
		setSelectedConflict(null);
		notify({
			kind: "success",
			title: "All Resolved",
			message: `Resolved ${unresolvedConflicts.length} conflicts — kept remote versions`
		});
	}, [unresolvedConflicts]);
	const resolutionColor = (r) => {
		switch (r) {
			case "keep-local": return "text-blue-500";
			case "keep-remote": return "text-purple-500";
			case "merged": return "text-emerald-500";
			default: return "text-muted-foreground";
		}
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageHeader, {
			className: "w-full",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Conflict Resolution" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Review and resolve synchronization conflicts" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						className: "text-xs",
						disabled: unresolvedConflicts.length === 0,
						onClick: handleResolveAllLocal,
						size: "sm",
						variant: "outline",
						children: "Keep All Local"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						className: "text-xs",
						disabled: unresolvedConflicts.length === 0,
						onClick: handleResolveAllRemote,
						size: "sm",
						variant: "outline",
						children: "Keep All Remote"
					})]
				})]
			})
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex gap-4",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "w-80 shrink-0 space-y-1",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mb-2 flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
							className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground",
							children: [
								"Unresolved (",
								unresolvedConflicts.length,
								")"
							]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "text-[0.6rem] text-primary hover:underline",
							onClick: () => setShowResolved(!showResolved),
							type: "button",
							children: showResolved ? "Hide Resolved" : `Show Resolved (${resolvedHistory.length})`
						})]
					}),
					unresolvedConflicts.length === 0 && !showResolved && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "grid min-h-32 place-items-center text-center",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-muted-foreground/40",
							name: "check",
							size: "1.5rem"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 text-xs text-muted-foreground",
							children: "No conflicts"
						})] })
					}),
					unresolvedConflicts.map((conflict) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: cn("w-full rounded-md border px-2.5 py-2 text-left text-xs transition-colors", selectedConflict?.id === conflict.id ? "border-primary/40 bg-primary/5" : "border-(--ui-stroke-tertiary) hover:bg-accent/30"),
						onClick: () => setSelectedConflict(conflict),
						type: "button",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-1.5",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "text-amber-500",
									name: "warning",
									size: "0.7rem"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "truncate font-medium",
									children: conflict.filePath
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-0.5 text-[0.6rem] text-muted-foreground",
								children: conflict.scope
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-1 flex gap-2 text-[0.55rem] text-muted-foreground",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: ["Local: ", new Date(conflict.localModifiedAt).toLocaleDateString()] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: ["Remote: ", new Date(conflict.remoteModifiedAt).toLocaleDateString()] })]
							})
						]
					}, conflict.id)),
					showResolved && resolvedHistory.map((conflict) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-2.5 py-2 text-xs",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-1.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								className: "text-emerald-500",
								name: "check",
								size: "0.7rem"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "truncate font-medium",
								children: conflict.filePath
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-1 flex items-center gap-2 text-[0.6rem]",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: cn("font-medium capitalize", resolutionColor(conflict.resolution)),
								children: conflict.resolution?.replace("-", " ")
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-muted-foreground",
								children: conflict.resolvedAt ? new Date(conflict.resolvedAt).toLocaleString() : ""
							})]
						})]
					}, conflict.id))
				]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "min-w-0 flex-1",
				children: selectedConflict ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center justify-between",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "text-sm font-medium",
								children: selectedConflict.filePath
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "text-xs text-muted-foreground",
								children: ["Scope: ", selectedConflict.scope]
							})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								variant: "destructive",
								children: "Unresolved"
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "grid grid-cols-2 gap-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "rounded-lg border border-(--ui-stroke-tertiary)",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center justify-between border-b border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-3 py-1.5",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "flex items-center gap-1.5 text-xs font-medium",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
											name: "device-desktop",
											size: "0.75rem"
										}), "Local Version"]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-[0.6rem] text-muted-foreground",
										children: new Date(selectedConflict.localModifiedAt).toLocaleString()
									})]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
									className: "max-h-60 overflow-auto p-3 text-xs leading-relaxed",
									children: selectedConflict.localVersion
								})]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "rounded-lg border border-(--ui-stroke-tertiary)",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center justify-between border-b border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-3 py-1.5",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "flex items-center gap-1.5 text-xs font-medium",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
											name: "cloud",
											size: "0.75rem"
										}), "Remote Version"]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-[0.6rem] text-muted-foreground",
										children: new Date(selectedConflict.remoteModifiedAt).toLocaleString()
									})]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
									className: "max-h-60 overflow-auto p-3 text-xs leading-relaxed",
									children: selectedConflict.remoteVersion
								})]
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
									className: "text-xs",
									onClick: () => handleResolve(selectedConflict, "keep-local"),
									size: "sm",
									variant: "default",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: "check",
										size: "0.75rem"
									}), "Keep Local"]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
									className: "text-xs",
									onClick: () => handleResolve(selectedConflict, "keep-remote"),
									size: "sm",
									variant: "outline",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: "check",
										size: "0.75rem"
									}), "Keep Remote"]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
									className: "text-xs",
									onClick: () => handleResolve(selectedConflict, "merged"),
									size: "sm",
									variant: "outline",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: "git-merge",
										size: "0.75rem"
									}), "Merge"]
								})
							]
						})
					]
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid min-h-64 place-items-center text-center",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-muted-foreground/40",
							name: "warning",
							size: "2rem"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-2 text-sm text-muted-foreground",
							children: "Select a conflict to review"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-xs text-muted-foreground/60",
							children: "Choose from the list on the left"
						})
					] })
				})
			})]
		})
	});
}
//#endregion
export { ConflictResolutionView };

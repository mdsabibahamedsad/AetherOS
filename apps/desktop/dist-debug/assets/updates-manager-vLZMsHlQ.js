import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Di as notify, Ia as Codicon, La as Button, O as Badge, P as Switch, Ra as cn, ao as require_jsx_runtime, ki as useI18n, oo as require_react } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/app/updates-manager/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var AVAILABLE_UPDATES = [
	{
		id: "aetheros-core",
		name: "AetherOS Core",
		type: "core",
		currentVersion: "0.16.0",
		latestVersion: "0.16.2",
		changelog: "## 0.16.2\n- Fixed memory leak in session manager\n- Improved prompt caching performance\n- Updated model provider SDK\n\n## 0.16.1\n- Hotfix for gateway reconnection\n- Fixed cron job scheduling edge case",
		publishedAt: "2026-07-20T10:00:00Z",
		size: "12.4 MB",
		severity: "critical",
		installed: false,
		autoUpdate: true
	},
	{
		id: "code-analyzer",
		name: "Code Analyzer",
		type: "plugin",
		currentVersion: "2.1.0",
		latestVersion: "2.2.0",
		changelog: "## 2.2.0\n- Added Rust language support\n- Improved type inference\n- 20% faster analysis for large files\n- Fixed false positives in null checks",
		publishedAt: "2026-07-19T14:30:00Z",
		size: "3.2 MB",
		severity: "important",
		installed: true,
		autoUpdate: true
	},
	{
		id: "search-assistant",
		name: "Search Assistant",
		type: "plugin",
		currentVersion: "1.3.2",
		latestVersion: "1.4.0",
		changelog: "## 1.4.0\n- Added DuckDuckGo support\n- Improved result relevance ranking\n- Custom search engine configuration\n- Fixed rate limit handling",
		publishedAt: "2026-07-18T09:00:00Z",
		size: "1.8 MB",
		severity: "optional",
		installed: true,
		autoUpdate: true
	},
	{
		id: "filesystem-mcp",
		name: "Filesystem MCP",
		type: "mcp",
		currentVersion: "1.0.0",
		latestVersion: "1.1.0",
		changelog: "## 1.1.0\n- Added glob pattern support\n- Improved large directory listing performance\n- New file search tool",
		publishedAt: "2026-07-17T16:45:00Z",
		size: "0.5 MB",
		severity: "important",
		installed: true,
		autoUpdate: false
	},
	{
		id: "github-mcp",
		name: "GitHub MCP",
		type: "mcp",
		currentVersion: "2.0.0",
		latestVersion: "2.1.0",
		changelog: "## 2.1.0\n- GitHub Actions integration\n- Pull request review tool\n- Repository statistics endpoint",
		publishedAt: "2026-07-16T11:20:00Z",
		size: "0.8 MB",
		severity: "optional",
		installed: true,
		autoUpdate: true
	},
	{
		id: "vision-analyzer",
		name: "Vision Analyzer",
		type: "extension",
		currentVersion: "1.0.0",
		latestVersion: "1.1.0",
		changelog: "## 1.1.0\n- Added support for WebP format\n- Improved OCR accuracy\n- Batch processing mode\n- Lower memory usage",
		publishedAt: "2026-07-15T08:00:00Z",
		size: "4.1 MB",
		severity: "important",
		installed: true,
		autoUpdate: true
	}
];
var RECENTLY_UPDATED = [
	{
		id: "task-automation",
		name: "Task Automation",
		type: "plugin",
		version: "3.0.1",
		updatedAt: "2026-07-14T10:00:00Z"
	},
	{
		id: "database-gateway",
		name: "Database Gateway",
		type: "plugin",
		version: "2.2.1",
		updatedAt: "2026-07-13T15:30:00Z"
	},
	{
		id: "voice-control",
		name: "Voice Control",
		type: "plugin",
		version: "1.2.1",
		updatedAt: "2026-07-12T09:45:00Z"
	},
	{
		id: "translate-plus",
		name: "Translate Plus",
		type: "extension",
		version: "2.0.0",
		updatedAt: "2026-07-11T14:20:00Z"
	},
	{
		id: "email-hub",
		name: "Email Hub",
		type: "plugin",
		version: "1.0.3",
		updatedAt: "2026-07-10T11:00:00Z"
	}
];
var TYPE_ICONS = {
	core: "aetheros",
	plugin: "extensions",
	mcp: "server",
	extension: "package"
};
var SEVERITY_STYLES = {
	critical: "bg-red-500/10 text-red-600 dark:text-red-400",
	important: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
	optional: "bg-sky-500/10 text-sky-600 dark:text-sky-400"
};
function UpdatesManagerView() {
	const { t } = useI18n();
	const [updates, setUpdates] = (0, import_react.useState)(AVAILABLE_UPDATES);
	const [filter, setFilter] = (0, import_react.useState)("all");
	const [selectedUpdateId, setSelectedUpdateId] = (0, import_react.useState)(null);
	const [updatingIds, setUpdatingIds] = (0, import_react.useState)(/* @__PURE__ */ new Set());
	const [updatingAll, setUpdatingAll] = (0, import_react.useState)(false);
	const [autoUpdateGlobal, setAutoUpdateGlobal] = (0, import_react.useState)(true);
	const filteredUpdates = (0, import_react.useMemo)(() => {
		return filter === "all" ? updates : updates.filter((u) => u.type === filter);
	}, [updates, filter]);
	const selectedUpdate = (0, import_react.useMemo)(() => updates.find((u) => u.id === selectedUpdateId) ?? filteredUpdates[0] ?? null, [
		updates,
		selectedUpdateId,
		filteredUpdates
	]);
	const pendingCount = updates.filter((u) => !u.installed).length;
	const criticalCount = updates.filter((u) => !u.installed && u.severity === "critical").length;
	const handleUpdate = (0, import_react.useCallback)(async (item) => {
		setUpdatingIds((prev) => new Set(prev).add(item.id));
		await new Promise((r) => setTimeout(r, 2e3));
		setUpdates((current) => current.map((u) => u.id === item.id ? {
			...u,
			installed: true,
			currentVersion: u.latestVersion
		} : u));
		setUpdatingIds((prev) => {
			const next = new Set(prev);
			next.delete(item.id);
			return next;
		});
		notify({
			kind: "success",
			title: "Update Installed",
			message: `${item.name} updated to v${item.latestVersion}`
		});
	}, []);
	const handleUpdateAll = (0, import_react.useCallback)(async () => {
		setUpdatingAll(true);
		const pending = updates.filter((u) => !u.installed);
		for (const item of pending) {
			await new Promise((r) => setTimeout(r, 800));
			setUpdates((current) => current.map((u) => u.id === item.id ? {
				...u,
				installed: true,
				currentVersion: u.latestVersion
			} : u));
		}
		setUpdatingAll(false);
		notify({
			kind: "success",
			title: "All Updates Installed",
			message: `${pending.length} update(s) applied`
		});
	}, [updates]);
	const handleToggleAutoUpdate = (0, import_react.useCallback)((itemId) => {
		setUpdates((current) => current.map((u) => u.id === itemId ? {
			...u,
			autoUpdate: !u.autoUpdate
		} : u));
	}, []);
	const formatDate = (iso) => {
		return new Date(iso).toLocaleDateString(void 0, {
			month: "short",
			day: "numeric",
			year: "numeric"
		});
	};
	const formatRelativeDate = (iso) => {
		const diff = Date.now() - new Date(iso).getTime();
		const days = Math.floor(diff / 864e5);
		if (days === 0) return "Today";
		if (days === 1) return "Yesterday";
		if (days < 7) return `${days} days ago`;
		return formatDate(iso);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageHeader, {
			className: "w-full",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Updates & Upgrades" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: pendingCount > 0 ? `${pendingCount} update${pendingCount > 1 ? "s" : ""} available${criticalCount > 0 ? ` (${criticalCount} critical)` : ""}` : "All components are up to date" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "flex items-center gap-1.5 text-xs text-muted-foreground",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: autoUpdateGlobal,
						onCheckedChange: setAutoUpdateGlobal
					}), "Auto-Update"]
				}), pendingCount > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					className: "text-xs",
					disabled: updatingAll,
					onClick: () => void handleUpdateAll(),
					size: "sm",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: cn("mr-1", updatingAll && "animate-spin"),
						name: updatingAll ? "loading" : "cloud-download",
						size: "0.75rem"
					}), updatingAll ? "Updating..." : `Update All (${pendingCount})`]
				})]
			})]
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex h-full gap-4",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "w-64 shrink-0 space-y-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex gap-1",
						children: [
							"all",
							"core",
							"plugin",
							"mcp",
							"extension"
						].map((type) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: cn("rounded-md px-2 py-1 text-[0.6rem] font-medium transition-colors", filter === type ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground"),
							onClick: () => setFilter(type),
							type: "button",
							children: type === "all" ? "All" : type.charAt(0).toUpperCase() + type.slice(1)
						}, type))
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "space-y-0.5",
						children: filteredUpdates.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "px-2 py-6 text-center text-xs text-muted-foreground",
							children: "No updates available"
						}) : filteredUpdates.map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: cn("flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors", selectedUpdate?.id === item.id ? "bg-accent text-accent-foreground" : "hover:bg-accent/60"),
							onClick: () => setSelectedUpdateId(item.id),
							type: "button",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "flex size-7 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: TYPE_ICONS[item.type],
										size: "0.75rem"
									})
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "min-w-0 flex-1",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-1.5",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "truncate text-sm font-medium",
											children: item.name
										}), item.installed && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
											className: "shrink-0 text-emerald-500",
											name: "check",
											size: "0.65rem"
										})]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "text-[0.6rem] text-muted-foreground",
										children: item.installed ? `v${item.currentVersion}` : `v${item.currentVersion} → v${item.latestVersion}`
									})]
								}),
								!item.installed && item.severity && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									className: cn("shrink-0 text-[0.55rem]", SEVERITY_STYLES[item.severity]),
									children: item.severity
								})
							]
						}, item.id))
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "border-t border-(--ui-stroke-tertiary) pt-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
							className: "mb-2 text-[0.6rem] font-semibold uppercase tracking-wider text-muted-foreground",
							children: "Recently Updated"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "space-y-0.5",
							children: RECENTLY_UPDATED.map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-2.5 px-2.5 py-1.5",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "flex size-6 shrink-0 items-center justify-center rounded-md bg-(--ui-bg-quinary) text-muted-foreground",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
											name: TYPE_ICONS[item.type],
											size: "0.65rem"
										})
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "min-w-0 flex-1",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
											className: "truncate text-xs font-medium",
											children: item.name
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "text-[0.55rem] text-muted-foreground",
											children: ["v", item.version]
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "shrink-0 text-[0.55rem] text-muted-foreground",
										children: formatRelativeDate(item.updatedAt)
									})
								]
							}, item.id))
						})]
					})
				]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "min-w-0 flex-1 overflow-y-auto",
				children: selectedUpdate ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-start justify-between",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-3",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
											name: TYPE_ICONS[selectedUpdate.type],
											size: "1.25rem"
										})
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
										className: "text-lg font-semibold",
										children: selectedUpdate.name
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex flex-wrap items-center gap-2 text-xs text-muted-foreground",
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
												variant: "outline",
												children: selectedUpdate.type
											}),
											selectedUpdate.severity && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
												className: SEVERITY_STYLES[selectedUpdate.severity],
												children: selectedUpdate.severity
											}),
											selectedUpdate.size && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: selectedUpdate.size }),
											/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: ["Published ", formatDate(selectedUpdate.publishedAt)] })
										]
									})] })]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-1.5",
									children: [!selectedUpdate.installed ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
										className: "text-xs",
										disabled: updatingIds.has(selectedUpdate.id),
										onClick: () => void handleUpdate(selectedUpdate),
										size: "sm",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
											className: cn("mr-1", updatingIds.has(selectedUpdate.id) && "animate-spin"),
											name: updatingIds.has(selectedUpdate.id) ? "loading" : "cloud-download",
											size: "0.75rem"
										}), updatingIds.has(selectedUpdate.id) ? "Installing..." : `Update to v${selectedUpdate.latestVersion}`]
									}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: "text-xs",
										variant: "default",
										children: "Up to date"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
										className: "flex items-center gap-1 text-[0.6rem] text-muted-foreground",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
											checked: selectedUpdate.autoUpdate,
											onCheckedChange: () => handleToggleAutoUpdate(selectedUpdate.id)
										}), "Auto"]
									})]
								})]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "mt-4 grid grid-cols-3 gap-4",
								children: [
									{
										label: "Current Version",
										value: `v${selectedUpdate.currentVersion}`
									},
									{
										label: "Latest Version",
										value: `v${selectedUpdate.latestVersion}`
									},
									{
										label: "Release Date",
										value: formatDate(selectedUpdate.publishedAt)
									}
								].map((stat) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "rounded-md bg-(--ui-bg-quinary) px-3 py-2",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground",
										children: stat.label
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "mt-0.5 text-sm font-medium tabular-nums",
										children: stat.value
									})]
								}, stat.label))
							})]
						}),
						!selectedUpdate.installed && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
								className: "mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
								children: "Version Comparison"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-4",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex-1 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
											className: "text-[0.6rem] font-medium text-muted-foreground",
											children: "Current"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "mt-0.5 text-lg font-semibold",
											children: ["v", selectedUpdate.currentVersion]
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: "text-muted-foreground/40",
										name: "arrow-right",
										size: "1.25rem"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex-1 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
											className: "text-[0.6rem] font-medium text-primary",
											children: "Latest"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "mt-0.5 text-lg font-semibold text-primary",
											children: ["v", selectedUpdate.latestVersion]
										})]
									})
								]
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border border-(--ui-stroke-tertiary) overflow-hidden",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "border-b border-(--ui-stroke-tertiary) px-4 py-2.5",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h4", {
									className: "flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: "note",
										size: "0.75rem"
									}), "Changelog"]
								})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "px-4 py-3",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
									className: "font-mono text-xs leading-relaxed text-foreground/80 whitespace-pre-wrap",
									children: selectedUpdate.changelog
								})
							})]
						})
					]
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid min-h-52 place-items-center text-center",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-muted-foreground/40",
							name: "check",
							size: "2rem"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-2 text-sm font-medium text-muted-foreground",
							children: "All up to date"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-1 text-xs text-muted-foreground/60",
							children: [
								updates.length,
								" ",
								updates.length === 1 ? "component is" : "components are",
								" at the latest version"
							]
						})
					] })
				})
			})]
		})
	});
}
//#endregion
export { UpdatesManagerView };

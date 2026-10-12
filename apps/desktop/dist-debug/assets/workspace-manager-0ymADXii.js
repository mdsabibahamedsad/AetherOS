import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Di as notify, Hi as IconTrash, Ia as Codicon, La as Button, Ma as IconActivity, O as Badge, Qa as atom, Qi as IconPlus, Ra as cn, Ui as IconTool, Vi as IconUsers, Xa as init_nanostores, Xi as IconSearch, Ya as useStore, ao as require_jsx_runtime, ha as IconFolderOpen, oo as require_react, ua as IconLayersIntersect2 } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/store/workspace-manager.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
init_nanostores();
var $workspaceManager = /* @__PURE__ */ atom({
	layouts: [
		{
			id: "default",
			name: "Default Layout",
			tabs: [
				{
					id: "tab-chat",
					title: "Chat",
					type: "session",
					icon: "comment-discussion",
					pinned: true
				},
				{
					id: "tab-terminal",
					title: "Terminal",
					type: "terminal",
					icon: "terminal"
				},
				{
					id: "tab-files",
					title: "Files",
					type: "file",
					icon: "file-directory"
				}
			],
			activeTabId: "tab-chat"
		},
		{
			id: "dev",
			name: "Development",
			tabs: [
				{
					id: "dev-editor",
					title: "Editor",
					type: "session",
					icon: "code",
					pinned: true
				},
				{
					id: "dev-terminal",
					title: "Terminal",
					type: "terminal",
					icon: "terminal",
					pinned: true
				},
				{
					id: "dev-preview",
					title: "Preview",
					type: "preview",
					icon: "browser"
				}
			],
			activeTabId: "dev-editor",
			splitDirection: "horizontal",
			splitPosition: 50
		},
		{
			id: "monitor",
			name: "Monitoring",
			tabs: [
				{
					id: "mon-logs",
					title: "Logs",
					type: "session",
					icon: "output",
					pinned: true
				},
				{
					id: "mon-metrics",
					title: "Metrics",
					type: "file",
					icon: "dashboard"
				},
				{
					id: "mon-terminal",
					title: "Terminal",
					type: "terminal",
					icon: "terminal"
				}
			],
			activeTabId: "mon-logs"
		}
	],
	activeLayoutId: "default",
	groups: [
		{
			id: "work",
			name: "Work",
			sessionIds: [],
			color: "#3B82F6"
		},
		{
			id: "personal",
			name: "Personal",
			sessionIds: [],
			color: "#10B981"
		},
		{
			id: "research",
			name: "Research",
			sessionIds: [],
			color: "#8B5CF6"
		}
	],
	shortcuts: [
		{
			id: "sc-proj",
			name: "Main Project",
			path: "/home/user/projects/main",
			type: "project",
			lastOpened: Date.now()
		},
		{
			id: "sc-docs",
			name: "Documentation",
			path: "/home/user/docs",
			type: "folder",
			lastOpened: Date.now() - 864e5
		},
		{
			id: "sc-config",
			name: "Config Editor",
			path: "/home/user/.aetheros/config.yaml",
			type: "file",
			lastOpened: Date.now() - 1728e5
		}
	],
	selectedTab: "layouts",
	searchQuery: ""
});
var patch = (u) => $workspaceManager.set({
	...$workspaceManager.get(),
	...u
});
function setWorkspaceTab(tab) {
	patch({ selectedTab: tab });
}
function setWorkspaceSearch(q) {
	patch({ searchQuery: q });
}
function setActiveLayout(id) {
	patch({ activeLayoutId: id });
}
function addLayout(layout) {
	patch({ layouts: [...$workspaceManager.get().layouts, layout] });
}
function removeLayout(id) {
	patch({ layouts: $workspaceManager.get().layouts.filter((l) => l.id !== id) });
}
function removeGroup(id) {
	patch({ groups: $workspaceManager.get().groups.filter((g) => g.id !== id) });
}
//#endregion
//#region src/app/workspace-manager/index.tsx
var import_jsx_runtime = require_jsx_runtime();
var TYPE_ICONS = {
	session: IconActivity,
	file: Codicon,
	terminal: IconTool,
	preview: IconActivity,
	settings: IconTool
};
var TYPE_LABELS = {
	session: "Chat Session",
	file: "File",
	terminal: "Terminal",
	preview: "Preview",
	settings: "Settings"
};
function WorkspaceManagerView() {
	const state = useStore($workspaceManager);
	const tabs = [
		{
			id: "layouts",
			label: "Layouts",
			icon: IconLayersIntersect2
		},
		{
			id: "sessions",
			label: "Session Groups",
			icon: IconUsers
		},
		{
			id: "shortcuts",
			label: "Shortcuts",
			icon: IconFolderOpen
		}
	];
	const filteredShortcuts = (0, import_react.useMemo)(() => {
		const q = state.searchQuery.toLowerCase();
		if (!q) return state.shortcuts;
		return state.shortcuts.filter((s) => s.name.toLowerCase().includes(q) || s.path.toLowerCase().includes(q));
	}, [state.shortcuts, state.searchQuery]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageHeader, {
			className: "w-full",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Workspace Manager" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Manage layouts, session groups, and workspace shortcuts" })] })
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex h-full flex-col gap-0",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary)",
					children: tabs.map((tab) => {
						const Icon = tab.icon;
						return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: cn("flex items-center gap-1.5 border-b-2 px-4 py-2 text-xs font-medium transition-colors", state.selectedTab === tab.id ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"),
							onClick: () => setWorkspaceTab(tab.id),
							type: "button",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-3.5" }), tab.label]
						}, tab.id);
					})
				}),
				state.selectedTab === "layouts" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex-1 space-y-3 overflow-y-auto p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "grid gap-3 sm:grid-cols-2 lg:grid-cols-3",
						children: state.layouts.map((layout) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(LayoutCard, {
							isActive: layout.id === state.activeLayoutId,
							layout
						}, layout.id))
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						className: "w-full",
						onClick: () => {
							const id = `layout-${Date.now()}`;
							addLayout({
								id,
								name: "New Layout",
								tabs: [{
									id: `tab-${id}`,
									title: "New Tab",
									type: "session"
								}],
								activeTabId: null
							});
							notify({
								kind: "success",
								title: "Layout",
								message: "New layout created"
							});
						},
						size: "xs",
						variant: "text",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconPlus, { className: "size-3 mr-1" }), " New Layout"]
					})]
				}),
				state.selectedTab === "sessions" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex-1 space-y-3 overflow-y-auto p-4",
					children: state.groups.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "py-8 text-center text-xs text-muted-foreground",
						children: "No session groups created"
					}) : state.groups.map((group) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-3",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "size-3 rounded-full shrink-0",
									style: { backgroundColor: group.color }
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "min-w-0 flex-1",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "text-xs font-medium text-foreground",
										children: group.name
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "text-[0.6rem] text-muted-foreground",
										children: [group.sessionIds.length, " sessions"]
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									className: "text-muted-foreground hover:text-red-500",
									onClick: () => {
										removeGroup(group.id);
										notify({
											kind: "info",
											title: "Group",
											message: "Group removed"
										});
									},
									size: "icon-xs",
									variant: "ghost",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTrash, { className: "size-3" })
								})
							]
						})
					}, group.id))
				}),
				state.selectedTab === "shortcuts" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex min-h-0 flex-1 flex-col",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex shrink-0 items-center gap-2 border-b border-(--ui-stroke-tertiary) px-3 py-1.5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconSearch, { className: "size-3 text-muted-foreground" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							className: "min-w-0 flex-1 bg-transparent text-xs text-foreground outline-none placeholder:text-muted-foreground/60",
							onChange: (e) => setWorkspaceSearch(e.target.value),
							placeholder: "Search shortcuts...",
							value: state.searchQuery
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex-1 space-y-1 overflow-y-auto p-4",
						children: filteredShortcuts.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "py-8 text-center text-xs text-muted-foreground",
							children: state.searchQuery ? "No shortcuts match your search" : "No workspace shortcuts"
						}) : filteredShortcuts.map((sc) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-3 rounded-lg px-3 py-2 text-xs transition-colors hover:bg-accent/60",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconFolderOpen, { className: "size-3.5 shrink-0 text-muted-foreground" }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "min-w-0 flex-1",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "font-medium text-foreground",
										children: sc.name
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "text-muted-foreground",
										children: sc.path
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									variant: "secondary",
									children: sc.type
								}),
								sc.lastOpened && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "shrink-0 text-muted-foreground/60",
									children: formatRelative(sc.lastOpened)
								})
							]
						}, sc.id))
					})]
				})
			]
		})
	});
}
function LayoutCard({ layout, isActive }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: cn("rounded-xl border p-4 transition-colors cursor-pointer", isActive ? "border-primary/40 bg-accent/30" : "border-(--ui-stroke-tertiary) hover:border-(--ui-stroke-secondary)"),
		onClick: () => {
			setActiveLayout(layout.id);
			notify({
				kind: "info",
				title: "Layout",
				message: `Switched to "${layout.name}" layout`
			});
		},
		role: "button",
		tabIndex: 0,
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
					className: "text-xs font-semibold text-foreground",
					children: layout.name
				}), isActive && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
					className: "bg-primary/10 text-primary",
					variant: "secondary",
					children: "Active"
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-2 space-y-1",
				children: layout.tabs.map((tab) => {
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2 text-[0.6rem] text-muted-foreground",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TYPE_ICONS[tab.type] || IconActivity, { className: "size-2.5 shrink-0" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "truncate",
								children: tab.title
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "ml-auto text-muted-foreground/60",
								children: TYPE_LABELS[tab.type]
							})
						]
					}, tab.id);
				})
			}),
			layout.splitDirection && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-2 text-[0.55rem] text-muted-foreground/60",
				children: [
					"Split: ",
					layout.splitDirection,
					" (",
					layout.splitPosition,
					"%)"
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-3 flex gap-1",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					className: "text-muted-foreground hover:text-red-500",
					onClick: (e) => {
						e.stopPropagation();
						removeLayout(layout.id);
						notify({
							kind: "info",
							title: "Layout",
							message: "Layout removed"
						});
					},
					size: "icon-xs",
					variant: "ghost",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTrash, { className: "size-3" })
				})
			})
		]
	});
}
function formatRelative(ts) {
	const diff = Date.now() - ts;
	if (diff < 6e4) return "now";
	if (diff < 36e5) return `${Math.floor(diff / 6e4)}m ago`;
	if (diff < 864e5) return `${Math.floor(diff / 36e5)}h ago`;
	return `${Math.floor(diff / 864e5)}d ago`;
}
//#endregion
export { WorkspaceManagerView };

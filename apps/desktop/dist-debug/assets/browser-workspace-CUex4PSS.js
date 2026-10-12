import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { C as Select, D as SelectValue, E as SelectTrigger, La as Button, O as Badge, Qa as atom, T as SelectItem, Xa as init_nanostores, Ya as useStore, Za as computed, ao as require_jsx_runtime, ni as Input, oo as require_react, w as SelectContent } from "./index-B_yd1pEX.js";
import { t as EmptyState } from "./empty-state-DbK8L0dQ.js";
import { t as formatTimestamp } from "./format-timestamp-DA7XesLP.js";
//#region src/lib/format-bytes.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
function formatBytes(bytes) {
	if (bytes === null || bytes === void 0 || Number.isNaN(bytes)) return "—";
	if (bytes < 0) return "—";
	if (bytes < 1024) return `${bytes} B`;
	const units = [
		"KB",
		"MB",
		"GB",
		"TB",
		"PB"
	];
	let value = bytes / 1024;
	let unit = units[0];
	for (const next of units) {
		unit = next;
		if (value < 1024 || next === "PB") break;
		value /= 1024;
	}
	const rounded = Math.round(value * 10) / 10;
	return `${new Intl.NumberFormat(void 0, { maximumFractionDigits: 1 }).format(rounded)} ${unit}`;
}
//#endregion
//#region src/store/browser-workspace.ts
init_nanostores();
var $browser = /* @__PURE__ */ atom({
	mode: "browse",
	tabs: [{
		id: "welcome",
		url: "about:blank",
		title: "Welcome",
		loading: false,
		pinned: false,
		group: "",
		secure: true,
		canGoBack: false,
		canGoForward: false
	}],
	activeTabId: "welcome",
	sidebarOpen: true,
	readerMode: false,
	pageZoom: 100,
	privateMode: false,
	sidebarWidth: 280,
	searchQuery: "",
	searchProvider: "Google",
	searchSuggestions: [],
	searchHistory: [],
	bookmarks: [],
	history: [],
	downloads: [],
	pageTitle: "",
	pageUrl: "",
	pageLoading: false
});
var $activeTab = /* @__PURE__ */ computed($browser, (state) => state.tabs.find((t) => t.id === state.activeTabId) ?? null);
var $pinnedTabs = /* @__PURE__ */ computed($browser, (state) => state.tabs.filter((t) => t.pinned));
var $unpinnedTabs = /* @__PURE__ */ computed($browser, (state) => state.tabs.filter((t) => !t.pinned));
function setBrowserMode(mode) {
	const state = $browser.get();
	$browser.set({
		...state,
		mode
	});
}
function addTab(url = "about:blank", pinned = false) {
	const state = $browser.get();
	const id = `tab_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
	const tab = {
		id,
		url,
		title: url === "about:blank" ? "New Tab" : url,
		loading: url !== "about:blank",
		pinned,
		group: "",
		secure: url.startsWith("https://"),
		canGoBack: false,
		canGoForward: false
	};
	$browser.set({
		...state,
		tabs: [...state.tabs, tab],
		activeTabId: id,
		pageLoading: tab.loading
	});
	return id;
}
function closeTab(tabId) {
	const state = $browser.get();
	const tabs = state.tabs.filter((t) => t.id !== tabId);
	let activeTabId = state.activeTabId;
	if (activeTabId === tabId) {
		const idx = state.tabs.findIndex((t) => t.id === tabId);
		if (tabs.length > 0) activeTabId = tabs[Math.min(idx, tabs.length - 1)].id;
	}
	$browser.set({
		...state,
		tabs,
		activeTabId
	});
}
function activateTab(tabId) {
	const state = $browser.get();
	const tab = state.tabs.find((t) => t.id === tabId);
	if (tab) $browser.set({
		...state,
		activeTabId: tabId,
		pageUrl: tab.url,
		pageTitle: tab.title,
		pageLoading: tab.loading
	});
}
function duplicateTab(tabId) {
	const original = $browser.get().tabs.find((t) => t.id === tabId);
	if (!original) return;
	const newId = addTab(original.url, false);
	const updated = $browser.get().tabs.map((t) => t.id === newId ? {
		...t,
		title: original.title
	} : t);
	$browser.set({
		...$browser.get(),
		tabs: updated
	});
}
function togglePinTab(tabId) {
	const state = $browser.get();
	const tabs = state.tabs.map((t) => t.id === tabId ? {
		...t,
		pinned: !t.pinned
	} : t);
	$browser.set({
		...state,
		tabs
	});
}
function updateTabUrl(tabId, url) {
	const state = $browser.get();
	const tabs = state.tabs.map((t) => t.id === tabId ? {
		...t,
		url,
		loading: true,
		secure: url.startsWith("https://")
	} : t);
	$browser.set({
		...state,
		tabs,
		pageUrl: url,
		pageLoading: true
	});
}
function updateTabTitle(tabId, title) {
	const state = $browser.get();
	const tabs = state.tabs.map((t) => t.id === tabId ? {
		...t,
		title,
		loading: false
	} : t);
	$browser.set({
		...state,
		tabs,
		pageTitle: title,
		pageLoading: false
	});
}
function updateTabNavState(tabId, canGoBack, canGoForward) {
	const state = $browser.get();
	const tabs = state.tabs.map((t) => t.id === tabId ? {
		...t,
		canGoBack,
		canGoForward
	} : t);
	$browser.set({
		...state,
		tabs
	});
}
function setTabLoading(tabId, loading) {
	const state = $browser.get();
	const tabs = state.tabs.map((t) => t.id === tabId ? {
		...t,
		loading
	} : t);
	$browser.set({
		...state,
		tabs,
		pageLoading: loading
	});
}
function toggleReaderMode() {
	const state = $browser.get();
	$browser.set({
		...state,
		readerMode: !state.readerMode
	});
}
function setPageZoom(zoom) {
	const state = $browser.get();
	$browser.set({
		...state,
		pageZoom: Math.max(25, Math.min(500, zoom))
	});
}
function togglePrivateMode() {
	const state = $browser.get();
	$browser.set({
		...state,
		privateMode: !state.privateMode
	});
}
function setSearchProvider(provider) {
	const state = $browser.get();
	$browser.set({
		...state,
		searchProvider: provider
	});
}
function addHistoryItem(url, title) {
	const state = $browser.get();
	const existing = state.history.find((h) => h.url === url);
	if (existing) {
		const history = state.history.map((h) => h.id === existing.id ? {
			...h,
			visitCount: h.visitCount + 1,
			visitTime: (/* @__PURE__ */ new Date()).toISOString()
		} : h);
		$browser.set({
			...state,
			history
		});
	} else {
		const item = {
			id: `hist_${Date.now()}`,
			url,
			title,
			visitTime: (/* @__PURE__ */ new Date()).toISOString(),
			visitCount: 1
		};
		$browser.set({
			...state,
			history: [item, ...state.history].slice(0, 1e4)
		});
	}
}
function clearHistory() {
	const state = $browser.get();
	$browser.set({
		...state,
		history: []
	});
}
function addBookmark(title, url, folder = "", tags = []) {
	const state = $browser.get();
	const bm = {
		id: `bm_${Date.now()}`,
		title,
		url,
		folder,
		tags,
		createdAt: (/* @__PURE__ */ new Date()).toISOString()
	};
	$browser.set({
		...state,
		bookmarks: [...state.bookmarks, bm]
	});
}
function removeBookmark(bookmarkId) {
	const state = $browser.get();
	$browser.set({
		...state,
		bookmarks: state.bookmarks.filter((b) => b.id !== bookmarkId)
	});
}
function removeDownload(id) {
	const state = $browser.get();
	$browser.set({
		...state,
		downloads: state.downloads.filter((d) => d.id !== id)
	});
}
function clearCompletedDownloads() {
	const state = $browser.get();
	$browser.set({
		...state,
		downloads: state.downloads.filter((d) => d.status !== "completed")
	});
}
function navigateBack() {
	const tab = $activeTab.get();
	if (tab?.canGoBack) updateTabNavState(tab.id, false, true);
}
function navigateForward() {
	const tab = $activeTab.get();
	if (tab?.canGoForward) updateTabNavState(tab.id, true, false);
}
function refreshPage() {
	const tab = $activeTab.get();
	if (tab) {
		setTabLoading(tab.id, true);
		setTimeout(() => setTabLoading(tab.id, false), 500);
	}
}
//#endregion
//#region src/store/browser-permissions.ts
init_nanostores();
var $browserPermissions = /* @__PURE__ */ atom({
	pendingRequests: [],
	grants: [],
	domainBlocklist: [],
	computerUseEnabled: false
});
function addPermissionRequest(permissionType, url, reason) {
	const state = $browserPermissions.get();
	const req = {
		id: `perm_${Date.now()}`,
		permissionType,
		url,
		reason,
		timestamp: (/* @__PURE__ */ new Date()).toISOString(),
		status: "pending"
	};
	$browserPermissions.set({
		...state,
		pendingRequests: [...state.pendingRequests, req]
	});
}
function grantPermission(requestId, duration = "once") {
	const state = $browserPermissions.get();
	const req = state.pendingRequests.find((r) => r.id === requestId);
	if (!req) return;
	const grant = {
		permissionType: req.permissionType,
		url: req.url,
		granted: true,
		duration,
		grantedAt: (/* @__PURE__ */ new Date()).toISOString()
	};
	$browserPermissions.set({
		...state,
		pendingRequests: state.pendingRequests.filter((r) => r.id !== requestId),
		grants: [...state.grants, grant]
	});
}
function denyPermission(requestId) {
	const state = $browserPermissions.get();
	$browserPermissions.set({
		...state,
		pendingRequests: state.pendingRequests.map((r) => r.id === requestId ? {
			...r,
			status: "denied"
		} : r)
	});
}
//#endregion
//#region src/app/browser-workspace/ai-assistant.tsx
var import_jsx_runtime = require_jsx_runtime();
var suggestions = [
	{
		label: "Summarize this page",
		prompt: "Summarize this page"
	},
	{
		label: "Extract emails",
		prompt: "Extract all emails from this page"
	},
	{
		label: "Extract links",
		prompt: "Extract all links from this page"
	},
	{
		label: "Find prices",
		prompt: "Find the cheapest option on this page"
	},
	{
		label: "Read article",
		prompt: "Read this article to me"
	},
	{
		label: "Compare pages",
		prompt: "Compare these pages"
	},
	{
		label: "Find docs",
		prompt: "Find the official documentation"
	},
	{
		label: "Analyze form",
		prompt: "Find the problem in this form"
	}
];
function BrowserAiAssistant() {
	const browser = useStore($browser);
	const permissions = useStore($browserPermissions);
	const [query, setQuery] = (0, import_react.useState)("");
	const [messages, setMessages] = (0, import_react.useState)([]);
	const [sidebarOpen, setSidebarOpen] = (0, import_react.useState)(true);
	const handleSubmit = () => {
		if (!query.trim()) return;
		const userMsg = {
			role: "user",
			content: query.trim()
		};
		setMessages((prev) => [...prev, userMsg]);
		let response = "";
		const q = query.toLowerCase();
		if (q.includes("summarize") || q.includes("summary")) response = `**Page Summary**\n\nCurrent page: ${browser.pageUrl || "No active page"}\nTitle: ${browser.pageTitle || "Untitled"}\n\nI can see the page content. Here is a summary of the key information...\n\n(This requires backend processing to analyze the actual page content.)`;
		else if (q.includes("email")) {
			response = `**Email Extraction**\n\nTo extract emails from ${browser.pageUrl || "the current page"}, I need permission to read the page content.`;
			addPermissionRequest("read_page", browser.pageUrl, "Extract email addresses");
		} else if (q.includes("link") || q.includes("url")) response = `**Link Extraction**\n\nExtracting all links from ${browser.pageUrl || "the current page"}...\n\n(This requires backend processing to parse the DOM.)`;
		else if (q.includes("price") || q.includes("cheapest") || q.includes("compare")) response = `**Price Analysis**\n\nSearching for prices and comparing options on this page...\n\n(This requires backend processing to extract and analyze pricing data.)`;
		else if (q.includes("translate")) response = `**Translation**\n\nThe page content can be translated using the AI translation system.\n\nSupported target languages include: Spanish, French, German, Chinese, Japanese, and more.`;
		else if (q.includes("read") || q.includes("article")) response = `**Article Reader**\n\nReading the article on ${browser.pageTitle || "this page"}...\n\n${browser.pageTitle ? `**${browser.pageTitle}**\n\n` : ""}(The full article content would be extracted and presented here.)`;
		else if (q.includes("documentation") || q.includes("docs")) response = `**Documentation Search**\n\nSearching for official documentation related to your query...\n\nI can search the web for the latest official documentation.`;
		else if (q.includes("form")) response = `**Form Analysis**\n\nAnalyzing forms on ${browser.pageUrl || "the current page"}...\n\n(This requires backend processing to inspect form elements.)`;
		else if (q.includes("search")) response = `**Web Search**\n\nI'll search for "${query.replace(/search/gi, "").trim()}" using ${browser.searchProvider}.\n\nNavigate to the search results to see them.`;
		else response = `**AI Browser Assistant**\n\nI can help you with the current page (${browser.pageUrl || "no page loaded"}). Here's what I can do:\n\n- **Summarize** this page\n- **Extract** emails, links, prices\n- **Compare** products or pages\n- **Find** documentation\n- **Translate** content\n- **Analyze** forms\n- **Search** the web\n\nWhat would you like me to do?`;
		setMessages((prev) => [...prev, {
			role: "assistant",
			content: response
		}]);
		setQuery("");
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: `${sidebarOpen ? "w-72" : "w-0"} border-l border-(--ui-border) bg-(--ui-surface-secondary) flex flex-col transition-all duration-200 overflow-hidden shrink-0`,
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center justify-between px-3 py-2 border-b border-(--ui-border)",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
				className: "text-xs font-medium flex items-center gap-1",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-comment-discussion" }), "AI Assistant"]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
				className: "p-0.5 hover:bg-(--ui-surface-hover) rounded",
				onClick: () => setSidebarOpen(!sidebarOpen),
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `codicon codicon-${sidebarOpen ? "panel-close" : "panel-open"} text-xs` })
			})]
		}), sidebarOpen && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex-1 overflow-auto p-3 space-y-2",
				children: [messages.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-1.5",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-(--ui-text-tertiary) mb-2",
						children: "Suggestions:"
					}), suggestions.map((s) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "block w-full text-left px-2 py-1.5 text-xs hover:bg-(--ui-surface-hover) rounded border border-(--ui-border)",
						onClick: () => {
							setQuery(s.prompt);
							setTimeout(() => handleSubmit(), 100);
						},
						children: s.label
					}, s.label))]
				}), messages.map((msg, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: `text-xs ${msg.role === "user" ? "text-(--ui-text)" : "text-(--ui-text-secondary)"}`,
					children: [msg.role === "user" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "font-medium block mb-0.5",
						children: "You:"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "whitespace-pre-wrap",
						children: msg.content
					})]
				}, i))]
			}),
			permissions.pendingRequests.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "px-3 py-2 border-t border-(--ui-border) bg-yellow-50",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-xs font-medium text-yellow-800 mb-1",
					children: "Permission Requested"
				}), permissions.pendingRequests.map((req) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "text-xs text-yellow-700 mb-1",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { children: req.reason }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-[10px] text-yellow-600",
							children: req.url
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex gap-1 mt-1",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "px-2 py-0.5 text-[10px] bg-green-600 text-white rounded hover:opacity-90",
									onClick: () => grantPermission(req.id, "once"),
									children: "Allow Once"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "px-2 py-0.5 text-[10px] bg-blue-600 text-white rounded hover:opacity-90",
									onClick: () => grantPermission(req.id, "session"),
									children: "Allow Session"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "px-2 py-0.5 text-[10px] bg-gray-400 text-white rounded hover:opacity-90",
									onClick: () => denyPermission(req.id),
									children: "Deny"
								})
							]
						})
					]
				}, req.id))]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "p-2 border-t border-(--ui-border)",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex gap-1",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						className: "flex-1 px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
						onChange: (e) => setQuery(e.target.value),
						onKeyDown: (e) => {
							if (e.key === "Enter") handleSubmit();
						},
						placeholder: "Ask about this page...",
						type: "text",
						value: query
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "px-2 py-1 bg-(--ui-accent) text-white text-xs rounded hover:opacity-90",
						onClick: handleSubmit,
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-send" })
					})]
				})
			})
		] })]
	});
}
//#endregion
//#region src/store/browser-automation.ts
init_nanostores();
var $browserAutomation = /* @__PURE__ */ atom({
	workflows: [],
	activeWorkflowId: "",
	executions: [],
	builderOpen: false,
	selectedNodeId: "",
	editingNode: false
});
function createWorkflow(name, description = "") {
	const state = $browserAutomation.get();
	const id = `wf_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
	const workflow = {
		id,
		name,
		description,
		nodes: [],
		schedule: "",
		status: "draft",
		createdAt: (/* @__PURE__ */ new Date()).toISOString(),
		updatedAt: (/* @__PURE__ */ new Date()).toISOString(),
		tags: []
	};
	$browserAutomation.set({
		...state,
		workflows: [...state.workflows, workflow],
		activeWorkflowId: id
	});
	return id;
}
function deleteWorkflow(id) {
	const state = $browserAutomation.get();
	const workflows = state.workflows.filter((w) => w.id !== id);
	const activeWorkflowId = state.activeWorkflowId === id ? workflows[0]?.id ?? "" : state.activeWorkflowId;
	$browserAutomation.set({
		...state,
		workflows,
		activeWorkflowId
	});
}
function setActiveWorkflow(id) {
	const state = $browserAutomation.get();
	$browserAutomation.set({
		...state,
		activeWorkflowId: id
	});
}
function setBuilderOpen(open) {
	const state = $browserAutomation.get();
	$browserAutomation.set({
		...state,
		builderOpen: open
	});
}
function setSelectedNode(nodeId) {
	const state = $browserAutomation.get();
	$browserAutomation.set({
		...state,
		selectedNodeId: nodeId
	});
}
function addNodeToWorkflow(workflowId, type, label = "") {
	const state = $browserAutomation.get();
	const wf = state.workflows.find((w) => w.id === workflowId);
	if (!wf) return null;
	const id = `node_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
	const node = {
		id,
		type,
		label: label || type.replace(/_/g, " "),
		config: {},
		position: {
			x: 100 + wf.nodes.length * 30,
			y: 100 + wf.nodes.length * 80
		},
		connections: []
	};
	const workflows = state.workflows.map((w) => w.id === workflowId ? {
		...w,
		nodes: [...w.nodes, node],
		updatedAt: (/* @__PURE__ */ new Date()).toISOString()
	} : w);
	$browserAutomation.set({
		...state,
		workflows,
		selectedNodeId: id
	});
	return id;
}
function removeNodeFromWorkflow(workflowId, nodeId) {
	const state = $browserAutomation.get();
	const workflows = state.workflows.map((w) => {
		if (w.id !== workflowId) return w;
		const nodes = w.nodes.filter((n) => n.id !== nodeId).map((n) => ({
			...n,
			connections: n.connections.filter((c) => c !== nodeId)
		}));
		return {
			...w,
			nodes,
			updatedAt: (/* @__PURE__ */ new Date()).toISOString()
		};
	});
	const selectedNodeId = state.selectedNodeId === nodeId ? "" : state.selectedNodeId;
	$browserAutomation.set({
		...state,
		workflows,
		selectedNodeId
	});
}
function connectNodes(workflowId, fromNodeId, toNodeId) {
	const state = $browserAutomation.get();
	const workflows = state.workflows.map((w) => {
		if (w.id !== workflowId) return w;
		const nodes = w.nodes.map((n) => n.id === fromNodeId && !n.connections.includes(toNodeId) ? {
			...n,
			connections: [...n.connections, toNodeId]
		} : n);
		return {
			...w,
			nodes,
			updatedAt: (/* @__PURE__ */ new Date()).toISOString()
		};
	});
	$browserAutomation.set({
		...state,
		workflows
	});
}
function updateNodeConfig(workflowId, nodeId, config) {
	const state = $browserAutomation.get();
	const workflows = state.workflows.map((w) => {
		if (w.id !== workflowId) return w;
		const nodes = w.nodes.map((n) => n.id === nodeId ? {
			...n,
			config: {
				...n.config,
				...config
			}
		} : n);
		return {
			...w,
			nodes,
			updatedAt: (/* @__PURE__ */ new Date()).toISOString()
		};
	});
	$browserAutomation.set({
		...state,
		workflows
	});
}
function setWorkflowSchedule(workflowId, schedule) {
	const state = $browserAutomation.get();
	const workflows = state.workflows.map((w) => w.id === workflowId ? {
		...w,
		schedule,
		updatedAt: (/* @__PURE__ */ new Date()).toISOString()
	} : w);
	$browserAutomation.set({
		...state,
		workflows
	});
}
function addExecution(execution) {
	const state = $browserAutomation.get();
	$browserAutomation.set({
		...state,
		executions: [...state.executions, execution]
	});
}
function updateExecution(id, updates) {
	const state = $browserAutomation.get();
	const executions = state.executions.map((e) => e.id === id ? {
		...e,
		...updates
	} : e);
	$browserAutomation.set({
		...state,
		executions
	});
}
//#endregion
//#region src/app/browser-workspace/automation-builder.tsx
var nodeTypes = [
	{
		type: "open_url",
		label: "Open Website",
		icon: "globe",
		category: "navigation"
	},
	{
		type: "search",
		label: "Search",
		icon: "search",
		category: "navigation"
	},
	{
		type: "click",
		label: "Click",
		icon: "mouse",
		category: "interaction"
	},
	{
		type: "type",
		label: "Type",
		icon: "keyboard",
		category: "interaction"
	},
	{
		type: "select",
		label: "Select",
		icon: "check",
		category: "interaction"
	},
	{
		type: "scroll",
		label: "Scroll",
		icon: "chevron-down",
		category: "interaction"
	},
	{
		type: "wait",
		label: "Wait",
		icon: "clock",
		category: "flow"
	},
	{
		type: "extract",
		label: "Extract Data",
		icon: "database",
		category: "data"
	},
	{
		type: "screenshot",
		label: "Screenshot",
		icon: "device-camera",
		category: "data"
	},
	{
		type: "navigate",
		label: "Navigate",
		icon: "arrow-left",
		category: "navigation"
	},
	{
		type: "condition",
		label: "Condition",
		icon: "git-branch",
		category: "flow"
	},
	{
		type: "loop",
		label: "Loop",
		icon: "repeat",
		category: "flow"
	},
	{
		type: "variable",
		label: "Variable",
		icon: "symbol-variable",
		category: "data"
	},
	{
		type: "download",
		label: "Download",
		icon: "cloud-download",
		category: "data"
	},
	{
		type: "webhook",
		label: "Webhook",
		icon: "link",
		category: "integration"
	},
	{
		type: "save_file",
		label: "Save File",
		icon: "save",
		category: "data"
	},
	{
		type: "send_notification",
		label: "Send Notification",
		icon: "bell",
		category: "integration"
	},
	{
		type: "filter",
		label: "Filter Results",
		icon: "filter",
		category: "data"
	}
];
var nodeCategories = [...new Set(nodeTypes.map((n) => n.category))];
function BrowserAutomationBuilder() {
	const browserAuto = useStore($browserAutomation);
	const [showNodePalette, setShowNodePalette] = (0, import_react.useState)(false);
	const [draggedNode, setDraggedNode] = (0, import_react.useState)(null);
	const [editingSchedule, setEditingSchedule] = (0, import_react.useState)(false);
	const [scheduleInput, setScheduleInput] = (0, import_react.useState)("");
	const activeWorkflow = browserAuto.workflows.find((w) => w.id === browserAuto.activeWorkflowId);
	if (!browserAuto.builderOpen) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex-1 overflow-auto",
		children: browserAuto.workflows.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex flex-col items-center justify-center h-full text-center p-8",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-run-all text-4xl text-(--ui-text-tertiary) mb-3" }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-lg font-semibold mb-1",
					children: "Web Automation"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm text-(--ui-text-tertiary) mb-4",
					children: "Create automated browser workflows"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					className: "px-4 py-2 bg-(--ui-accent) text-white text-sm rounded hover:opacity-90",
					onClick: () => setBuilderOpen(true),
					children: "Create Your First Workflow"
				})
			]
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "p-4",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between mb-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "text-sm font-medium",
						children: "Workflows"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "px-3 py-1 text-xs bg-(--ui-accent) text-white rounded hover:opacity-90",
						onClick: () => {
							setActiveWorkflow(createWorkflow(`Workflow ${browserAuto.workflows.length + 1}`));
						},
						children: "+ New"
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "space-y-2",
					children: browserAuto.workflows.map((wf) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: `flex items-center gap-2 px-3 py-2 text-xs border border-(--ui-border) rounded cursor-pointer hover:bg-(--ui-surface-hover) ${wf.id === browserAuto.activeWorkflowId ? "border-(--ui-accent) bg-(--ui-accent)/5" : ""}`,
						onClick: () => setActiveWorkflow(wf.id),
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-run-all text-(--ui-accent)" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex-1 min-w-0",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "truncate font-medium",
									children: wf.name
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "text-(--ui-text-tertiary)",
									children: [
										wf.nodes.length,
										" nodes ",
										wf.schedule ? `· ${wf.schedule}` : ""
									]
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: `px-1.5 py-0.5 rounded text-[10px] ${wf.status === "active" ? "bg-green-100 text-green-700" : wf.status === "draft" ? "bg-gray-100 text-gray-600" : "bg-yellow-100 text-yellow-700"}`,
								children: wf.status
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "p-0.5 hover:bg-(--ui-surface-hover) rounded opacity-0 hover:opacity-100",
								onClick: (e) => {
									e.stopPropagation();
									deleteWorkflow(wf.id);
								},
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-trash text-[10px]" })
							})
						]
					}, wf.id))
				}),
				browserAuto.executions.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-6",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-xs font-medium mb-2 text-(--ui-text-tertiary)",
						children: "Recent Executions"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "space-y-1",
						children: browserAuto.executions.slice(-5).reverse().map((ex) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2 px-2 py-1 text-xs text-(--ui-text-tertiary)",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `codicon codicon-${ex.status === "completed" ? "check" : ex.status === "failed" ? "error" : "clock"} ${ex.status === "completed" ? "text-green-600" : ex.status === "failed" ? "text-red-600" : ""}` }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "flex-1 truncate",
									children: ex.workflowId
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: ex.status })
							]
						}, ex.id))
					})]
				})
			]
		})
	});
	if (!activeWorkflow) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex-1 flex items-center justify-center text-sm text-(--ui-text-tertiary)",
		children: "Select or create a workflow to start building."
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-1 overflow-hidden",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "w-56 border-r border-(--ui-border) bg-(--ui-surface-secondary) flex flex-col",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "px-3 py-2 border-b border-(--ui-border) text-xs font-medium",
						children: activeWorkflow.name
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex-1 overflow-auto p-2 space-y-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-[10px] font-medium text-(--ui-text-tertiary) uppercase tracking-wider mb-1",
							children: "Nodes"
						}), activeWorkflow.nodes.map((node, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: `flex items-center gap-1.5 px-2 py-1 text-xs rounded cursor-pointer
                ${browserAuto.selectedNodeId === node.id ? "bg-(--ui-accent)/10 text-(--ui-accent)" : "hover:bg-(--ui-surface-hover)"}`,
							onClick: () => setSelectedNode(node.id),
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-{getNodeIcon(node.type)} text-[10px]" }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "truncate flex-1",
									children: node.label || node.type
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-[10px] text-(--ui-text-tertiary)",
									children: i + 1
								})
							]
						}, node.id))]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "p-2 border-t border-(--ui-border)",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: "w-full px-2 py-1 text-xs bg-(--ui-accent) text-white rounded hover:opacity-90 flex items-center gap-1 justify-center",
							onClick: () => setShowNodePalette(!showNodePalette),
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-add" }), " Add Node"]
						})
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex-1 relative overflow-auto bg-gray-50",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "absolute inset-0 p-8",
					children: activeWorkflow.nodes.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex flex-col items-center justify-center h-full text-sm text-(--ui-text-tertiary)",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-run-all text-3xl mb-2" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { children: "Add nodes to build your workflow" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "mt-2 px-3 py-1 text-xs bg-(--ui-accent) text-white rounded hover:opacity-90",
								onClick: () => setShowNodePalette(true),
								children: "Add First Node"
							})
						]
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "relative",
						children: activeWorkflow.nodes.map((node, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: `absolute p-3 border rounded shadow-sm bg-white cursor-pointer min-w-[160px]
                    ${browserAuto.selectedNodeId === node.id ? "border-(--ui-accent) ring-1 ring-(--ui-accent)" : "border-(--ui-border) hover:shadow"}`,
							onClick: () => setSelectedNode(node.id),
							style: {
								left: node.position.x,
								top: node.position.y
							},
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-1 text-xs font-medium mb-1",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `codicon codicon-${getNodeIcon(node.type)} text-(--ui-accent)` }), node.label]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "text-[10px] text-(--ui-text-tertiary)",
									children: node.type.replace(/_/g, " ")
								}),
								i < activeWorkflow.nodes.length - 1 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "absolute -bottom-4 left-1/2 -translate-x-1/2",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-arrow-down text-(--ui-text-tertiary)" })
								})
							]
						}, node.id))
					})
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "w-64 border-l border-(--ui-border) bg-(--ui-surface-secondary) flex flex-col",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "px-3 py-2 border-b border-(--ui-border) text-xs font-medium",
						children: "Config"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex-1 overflow-auto p-3",
						children: browserAuto.selectedNodeId ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(NodeConfigPanel, {
							nodeId: browserAuto.selectedNodeId,
							workflowId: activeWorkflow.id
						}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Select a node to configure"
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "p-3 border-t border-(--ui-border)",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded hover:bg-(--ui-surface-hover) mb-2",
								onClick: () => {
									setEditingSchedule(!editingSchedule);
									if (!editingSchedule) setScheduleInput(activeWorkflow.schedule);
								},
								children: activeWorkflow.schedule ? `Schedule: ${activeWorkflow.schedule}` : "Set Schedule"
							}),
							editingSchedule && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex gap-1 mb-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									className: "flex-1 px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
									onChange: (e) => setScheduleInput(e.target.value),
									placeholder: "daily, weekly, cron...",
									type: "text",
									value: scheduleInput
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "px-2 py-1 text-xs bg-(--ui-accent) text-white rounded",
									onClick: () => {
										setWorkflowSchedule(activeWorkflow.id, scheduleInput);
										setEditingSchedule(false);
									},
									children: "Set"
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: "w-full px-2 py-1 text-xs bg-green-600 text-white rounded hover:opacity-90 flex items-center gap-1 justify-center",
								onClick: () => {
									addExecution({
										id: `exec_${Date.now()}`,
										workflowId: activeWorkflow.id,
										status: "running",
										currentNodeId: "",
										results: {},
										errors: [],
										startedAt: (/* @__PURE__ */ new Date()).toISOString(),
										completedAt: ""
									});
									setTimeout(() => {
										updateExecution(`exec_${Date.now()}`, { status: "completed" });
									}, 2e3);
								},
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-play" }), " Run Workflow"]
							})
						]
					})
				]
			}),
			showNodePalette && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "absolute inset-0 bg-black/20 z-50 flex items-center justify-center",
				onClick: () => setShowNodePalette(false),
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "bg-(--ui-surface) rounded-lg shadow-xl border border-(--ui-border) w-96 max-h-[70vh] overflow-auto",
					onClick: (e) => e.stopPropagation(),
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "px-4 py-2 border-b border-(--ui-border) flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-sm font-medium",
							children: "Add Node"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "p-0.5 hover:bg-(--ui-surface-hover) rounded",
							onClick: () => setShowNodePalette(false),
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-close" })
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "p-4",
						children: nodeCategories.map((cat) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mb-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
								className: "text-[10px] font-medium text-(--ui-text-tertiary) uppercase tracking-wider mb-2",
								children: cat
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "grid grid-cols-2 gap-1",
								children: nodeTypes.filter((n) => n.category === cat).map((nt) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
									className: "flex items-center gap-1.5 px-2 py-1.5 text-xs rounded hover:bg-(--ui-surface-hover) border border-(--ui-border) text-left",
									onClick: () => {
										addNodeToWorkflow(activeWorkflow.id, nt.type, nt.label);
										setShowNodePalette(false);
									},
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `codicon codicon-${nt.icon} text-(--ui-accent)` }), nt.label]
								}, nt.type))
							})]
						}, cat))
					})]
				})
			})
		]
	});
}
function NodeConfigPanel({ workflowId, nodeId }) {
	const wf = useStore($browserAutomation).workflows.find((w) => w.id === workflowId);
	const node = wf?.nodes.find((n) => n.id === nodeId);
	if (!node) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "text-xs text-(--ui-text-tertiary)",
		children: "Node not found"
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-3",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "Label"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { label: e.target.value }),
				type: "text",
				value: node.label
			})] }),
			node.type === "open_url" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "URL"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { url: e.target.value }),
				placeholder: "https://example.com",
				type: "text"
			})] }),
			node.type === "search" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "Search Query"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { query: e.target.value }),
				placeholder: "Enter search query",
				type: "text"
			})] }),
			node.type === "click" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "CSS Selector"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { selector: e.target.value }),
				placeholder: ".button, #submit, a[href='...']",
				type: "text"
			})] }),
			(node.type === "type" || node.type === "select") && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "CSS Selector"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { selector: e.target.value }),
				placeholder: "input[name='...']",
				type: "text"
			})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "Text / Value"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { text: e.target.value }),
				placeholder: "Enter text",
				type: "text"
			})] })] }),
			node.type === "wait" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "Seconds"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				defaultValue: "1",
				min: "0.1",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { seconds: parseFloat(e.target.value) }),
				step: "0.1",
				type: "number"
			})] }),
			node.type === "extract" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "CSS Selector"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { selector: e.target.value }),
				placeholder: ".result, .price, table",
				type: "text"
			})] }),
			node.type === "condition" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "Expression"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { expression: e.target.value }),
				placeholder: "{{count}} > 0",
				type: "text"
			})] }),
			node.type === "loop" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "Max Iterations"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				defaultValue: "10",
				max: "100",
				min: "1",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { max_iterations: parseInt(e.target.value) }),
				type: "number"
			})] }),
			node.type === "download" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "File URL"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { url: e.target.value }),
				placeholder: "https://example.com/file.pdf",
				type: "text"
			})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "Destination Path"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { destination: e.target.value }),
				placeholder: "~/Downloads/file.pdf",
				type: "text"
			})] })] }),
			node.type === "save_file" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "Content"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none h-20 resize-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { content: e.target.value })
			})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "File Path"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { filepath: e.target.value }),
				placeholder: "/path/to/output.txt",
				type: "text"
			})] })] }),
			node.type === "webhook" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "Webhook URL"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { webhook_url: e.target.value }),
				placeholder: "https://hooks.example.com/...",
				type: "text"
			})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "Payload (JSON)"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none h-20 font-mono resize-none",
				onChange: (e) => {
					try {
						updateNodeConfig(workflowId, nodeId, { payload: JSON.parse(e.target.value) });
					} catch {}
				},
				placeholder: "{\"key\": \"value\"}"
			})] })] }),
			node.type === "variable" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "Name"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { name: e.target.value }),
				placeholder: "variable_name",
				type: "text"
			})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "Value"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { value: e.target.value }),
				placeholder: "Initial value",
				type: "text"
			})] })] }),
			node.type === "send_notification" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
				children: "Message"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none h-20 resize-none",
				onChange: (e) => updateNodeConfig(workflowId, nodeId, { message: e.target.value }),
				placeholder: "Workflow completed!"
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "pt-2 border-t border-(--ui-border)",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
					className: "text-[10px] font-medium text-(--ui-text-tertiary) block mb-0.5",
					children: "Connections"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("select", {
					className: "w-full px-2 py-1 text-xs border border-(--ui-border) rounded bg-(--ui-surface) outline-none",
					multiple: true,
					size: 3,
					children: wf?.nodes.filter((n) => n.id !== nodeId).map((n) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
						onClick: () => connectNodes(workflowId, nodeId, n.id),
						selected: node.connections.includes(n.id),
						value: n.id,
						children: n.label
					}, n.id))
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
				className: "w-full px-2 py-1 text-xs text-red-600 border border-red-200 rounded hover:bg-red-50",
				onClick: () => removeNodeFromWorkflow(workflowId, nodeId),
				children: "Delete Node"
			})
		]
	});
}
function getNodeIcon(type) {
	return nodeTypes.find((n) => n.type === type)?.icon ?? "gear";
}
//#endregion
//#region src/app/browser-workspace/index.tsx
var searchProviders = [
	"Google",
	"Bing",
	"DuckDuckGo",
	"Brave"
];
function BrowserView() {
	const browser = useStore($browser);
	const activeTab = useStore($activeTab);
	useStore($pinnedTabs);
	const unpinnedTabs = useStore($unpinnedTabs);
	const [urlInput, setUrlInput] = (0, import_react.useState)("");
	const [showProviderMenu, setShowProviderMenu] = (0, import_react.useState)(false);
	const [controlState, setControlState] = (0, import_react.useState)("user");
	const handleUrlSubmit = (0, import_react.useCallback)(() => {
		let url = urlInput.trim();
		if (!url) return;
		if (!url.startsWith("http://") && !url.startsWith("https://")) url = `https://${url}`;
		if (activeTab) {
			updateTabUrl(activeTab.id, url);
			updateTabTitle(activeTab.id, url);
			addHistoryItem(url, url);
			setTabLoading(activeTab.id, true);
			setTimeout(() => {
				updateTabTitle(activeTab.id, url);
				setTabLoading(activeTab.id, false);
			}, 1500);
		}
	}, [urlInput, activeTab]);
	const handleSearch = (0, import_react.useCallback)((query) => {
		if (!query.trim()) return;
		const provider = browser.searchProvider.toLowerCase();
		const searchUrl = provider === "google" ? `https://www.google.com/search?q=${encodeURIComponent(query)}` : provider === "bing" ? `https://www.bing.com/search?q=${encodeURIComponent(query)}` : provider === "duckduckgo" ? `https://duckduckgo.com/?q=${encodeURIComponent(query)}` : provider === "brave" ? `https://search.brave.com/search?q=${encodeURIComponent(query)}` : `https://www.google.com/search?q=${encodeURIComponent(query)}`;
		if (activeTab) {
			updateTabUrl(activeTab.id, searchUrl);
			addHistoryItem(searchUrl, query);
			setTabLoading(activeTab.id, true);
			setTimeout(() => {
				updateTabTitle(activeTab.id, query);
				setTabLoading(activeTab.id, false);
			}, 1500);
		}
	}, [activeTab, browser.searchProvider]);
	const handleKeyDown = (0, import_react.useCallback)((e) => {
		if (e.key === "Enter") handleUrlSubmit();
	}, [handleUrlSubmit]);
	if (browser.mode === "automation") return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col h-full",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(BrowserAutomationToolbar, {}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(BrowserAutomationBuilder, {})]
	});
	if (browser.mode === "settings") return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(BrowserSettingsView, {});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col h-full",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(BrowserNavigationBar, {
				canGoBack: activeTab?.canGoBack ?? false,
				canGoForward: activeTab?.canGoForward ?? false,
				controlState,
				loading: activeTab?.loading ?? false,
				onBack: navigateBack,
				onForward: navigateForward,
				onKeyDown: handleKeyDown,
				onRefresh: refreshPage,
				onSearch: handleSearch,
				onUrlSubmit: handleUrlSubmit,
				provider: browser.searchProvider,
				providers: searchProviders,
				setControlState,
				setProvider: setSearchProvider,
				setShowProviderMenu,
				setUrlInput,
				showProviderMenu,
				urlInput
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(BrowserTabBar, {
				activeTabId: browser.activeTabId,
				controlState,
				onClose: closeTab,
				onDuplicate: duplicateTab,
				onNewTab: () => addTab(),
				onPin: togglePinTab,
				onSelect: activateTab,
				tabs: unpinnedTabs
			}),
			browser.mode === "research" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ResearchToolbar, {}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-1 overflow-hidden",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex flex-1 flex flex-col overflow-hidden bg-white",
					children: [
						browser.mode === "browse" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(WebView, {
							loading: activeTab?.loading ?? false,
							readerMode: browser.readerMode,
							url: activeTab?.url ?? ""
						}),
						browser.mode === "research" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ResearchView, {}),
						browser.mode === "history" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(HistoryView, {}),
						browser.mode === "bookmarks" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(BookmarksView, {}),
						browser.mode === "downloads" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DownloadsView, {})
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(BrowserAiAssistant, {})]
			})
		]
	});
}
var CONTROL_LABEL = {
	user: "You control the browser",
	agent: "Agent is driving",
	approval: "Waiting for your approval",
	blocked: "Blocked by policy",
	untrusted: "Untrusted page"
};
function BrowserAutomationToolbar() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center gap-2 border-b border-(--ui-stroke-tertiary) px-3 py-2",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-xs font-medium",
				children: "Browser automation"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-[0.65rem] text-(--ui-text-tertiary)",
				children: "Agent-driven runs execute through backend tools."
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "flex-1" }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				onClick: () => setBrowserMode("browse"),
				size: "sm",
				variant: "secondary",
				children: "Back to browse"
			})
		]
	});
}
function BrowserSettingsView() {
	const browser = useStore($browser);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-2xl space-y-4 p-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
				children: "Browser settings"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "w-32 text-xs",
					children: "Search provider"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
					onValueChange: setSearchProvider,
					value: browser.searchProvider,
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
						className: "h-8 w-48 text-xs",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: [
						"Google",
						"Bing",
						"DuckDuckGo",
						"Brave"
					].map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
						value: p,
						children: p
					}, p)) })]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "w-32 text-xs",
						children: "Page zoom"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => setPageZoom(Math.max(50, browser.pageZoom - 10)),
						size: "sm",
						variant: "outline",
						children: "−"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "text-xs tabular-nums",
						children: [browser.pageZoom, "%"]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => setPageZoom(Math.min(200, browser.pageZoom + 10)),
						size: "sm",
						variant: "outline",
						children: "+"
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "w-32 text-xs",
					children: "Reader mode"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => toggleReaderMode(),
					size: "sm",
					variant: browser.readerMode ? "secondary" : "outline",
					children: browser.readerMode ? "On" : "Off"
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "w-32 text-xs",
					children: "Private mode"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => togglePrivateMode(),
					size: "sm",
					variant: browser.privateMode ? "secondary" : "outline",
					children: browser.privateMode ? "On" : "Off"
				})]
			})
		]
	});
}
function BrowserNavigationBar(props) {
	const { canGoBack, canGoForward, loading, controlState, onBack, onForward, onKeyDown, onRefresh, onSearch, onUrlSubmit, provider, providers, setProvider, setUrlInput, urlInput } = props;
	const [search, setSearch] = (0, import_react.useState)("");
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center gap-1.5 border-b border-(--ui-stroke-tertiary) px-3 py-2",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				"aria-label": "Back",
				disabled: !canGoBack,
				onClick: onBack,
				size: "icon",
				variant: "ghost",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-chevron-left" })
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				"aria-label": "Forward",
				disabled: !canGoForward,
				onClick: onForward,
				size: "icon",
				variant: "ghost",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-chevron-right" })
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				"aria-label": "Refresh",
				onClick: onRefresh,
				size: "icon",
				variant: "ghost",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-refresh" })
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
				className: "h-8 flex-1 font-mono text-xs",
				onChange: (e) => setUrlInput(e.target.value),
				onKeyDown,
				placeholder: "Enter URL, or search below",
				value: urlInput
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				onClick: onUrlSubmit,
				size: "sm",
				variant: "secondary",
				children: "Go"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
				className: "h-8 w-40 text-xs",
				onChange: (e) => setSearch(e.target.value),
				onKeyDown: (e) => {
					if (e.key === "Enter") onSearch(search);
				},
				placeholder: `Search ${provider}`,
				value: search
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
				onValueChange: setProvider,
				value: provider,
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
					className: "h-8 w-32 text-xs",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: providers.map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
					value: p,
					children: p
				}, p)) })]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
				className: "text-[0.55rem]",
				title: CONTROL_LABEL[controlState],
				variant: controlState === "user" ? "outline" : controlState === "approval" ? "warn" : "destructive",
				children: controlState
			})
		]
	});
}
function BrowserTabBar(props) {
	const { activeTabId, onClose, onDuplicate, onNewTab, onPin, onSelect, tabs } = props;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center gap-1 overflow-x-auto border-b border-(--ui-stroke-tertiary) px-2 py-1",
		role: "tablist",
		children: [tabs.map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			"aria-selected": t.id === activeTabId,
			className: `flex max-w-48 items-center gap-1 rounded-md px-2 py-1 text-xs ${t.id === activeTabId ? "bg-accent" : "hover:bg-accent/50"}`,
			role: "tab",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: "min-w-0 flex-1 truncate text-left",
					onClick: () => onSelect(t.id),
					title: t.url,
					type: "button",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `codicon ${t.loading ? "codicon-loading" : t.secure ? "codicon-lock" : "codicon-shield"} mr-1` }), t.title || t.url || "New tab"]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					"aria-label": `Pin ${t.title}`,
					className: "opacity-60 hover:opacity-100",
					onClick: () => onPin(t.id),
					type: "button",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-pin" })
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					"aria-label": `Duplicate ${t.title}`,
					className: "opacity-60 hover:opacity-100",
					onClick: () => onDuplicate(t.id),
					type: "button",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-copy" })
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					"aria-label": `Close ${t.title}`,
					className: "opacity-60 hover:opacity-100",
					onClick: () => onClose(t.id),
					type: "button",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-close" })
				})
			]
		}, t.id)), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
			"aria-label": "New tab",
			onClick: onNewTab,
			size: "sm",
			variant: "ghost",
			children: "+"
		})]
	});
}
function ResearchToolbar() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center gap-2 border-b border-(--ui-stroke-tertiary) bg-accent/30 px-3 py-1.5 text-xs",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "font-medium",
				children: "Research mode"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-(--ui-text-tertiary)",
				children: "Visited pages below become citable sources."
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "flex-1" }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				onClick: () => setBrowserMode("browse"),
				size: "sm",
				variant: "ghost",
				children: "Exit research"
			})
		]
	});
}
var WebviewTag = "webview";
function WebView({ loading, readerMode, url }) {
	const ref = (0, import_react.useRef)(null);
	const activeTabId = useStore($activeTab)?.id;
	(0, import_react.useEffect)(() => {
		const el = ref.current;
		if (!el?.addEventListener || !activeTabId) return;
		const start = () => setTabLoading(activeTabId, true);
		const stop = () => {
			setTabLoading(activeTabId, false);
			updateTabNavState(activeTabId, true, false);
		};
		el.addEventListener("did-start-loading", start);
		el.addEventListener("did-stop-loading", stop);
		return () => {
			el.removeEventListener?.("did-start-loading", start);
			el.removeEventListener?.("did-stop-loading", stop);
		};
	}, [activeTabId]);
	if (!url || url === "about:blank") return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
		description: "Enter a URL above to browse. Agent-driven pages appear here when automation runs.",
		icon: "globe",
		title: "No page loaded"
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "relative h-full w-full",
		children: [
			readerMode && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "absolute left-2 top-2 z-10 rounded bg-accent px-2 py-0.5 text-[0.6rem]",
				children: "Reader mode"
			}),
			loading && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "absolute left-2 top-2 z-10 rounded bg-accent px-2 py-0.5 text-[0.6rem]",
				children: "Loading…"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(WebviewTag, {
				className: "h-full w-full",
				partition: "persist:aetheros-browser",
				ref,
				src: url
			})
		]
	});
}
function ResearchView() {
	const sources = useStore($browser).history.slice(0, 20);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-3xl space-y-2 p-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
			className: "text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
			children: "Research sources"
		}), sources.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
			description: "Pages you visit in research mode are listed here as citable sources.",
			icon: "book",
			title: "No sources yet"
		}) : sources.map((s) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 text-xs",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "truncate font-medium",
					children: s.title || s.url
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "truncate font-mono text-(--ui-text-tertiary)",
					children: s.url
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "text-(--ui-text-tertiary)",
					children: [
						"visited ",
						formatTimestamp(s.visitTime),
						" · ",
						s.visitCount,
						"x"
					]
				})
			]
		}, s.id))]
	});
}
function HistoryView() {
	const browser = useStore($browser);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-3xl space-y-2 p-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center justify-between",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
				children: "History"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				onClick: () => clearHistory(),
				size: "sm",
				variant: "ghost",
				children: "Clear"
			})]
		}), browser.history.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
			description: "Visited pages appear here.",
			icon: "history",
			title: "No history"
		}) : browser.history.map((h) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 text-xs",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0 flex-1 truncate",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "font-medium",
					children: h.title || h.url
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "ml-2 font-mono text-(--ui-text-tertiary)",
					children: h.url
				})]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "shrink-0 text-(--ui-text-tertiary)",
				children: formatTimestamp(h.visitTime)
			})]
		}, h.id))]
	});
}
function BookmarksView() {
	const browser = useStore($browser);
	const [title, setTitle] = (0, import_react.useState)("");
	const [url, setUrl] = (0, import_react.useState)("");
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-3xl space-y-2 p-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
				children: "Bookmarks"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex gap-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						className: "h-8 flex-1 text-xs",
						onChange: (e) => setTitle(e.target.value),
						placeholder: "Title",
						value: title
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						className: "h-8 flex-1 font-mono text-xs",
						onChange: (e) => setUrl(e.target.value),
						placeholder: "https://…",
						value: url
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: !url.trim(),
						onClick: () => {
							addBookmark(title.trim() || url.trim(), url.trim());
							setTitle("");
							setUrl("");
						},
						size: "sm",
						variant: "secondary",
						children: "Add"
					})
				]
			}),
			browser.bookmarks.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
				description: "Save pages for quick access.",
				icon: "bookmark",
				title: "No bookmarks"
			}) : browser.bookmarks.map((b) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 text-xs",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "min-w-0 flex-1 truncate",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "font-medium",
						children: b.title
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "ml-2 font-mono text-(--ui-text-tertiary)",
						children: b.url
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => removeBookmark(b.id),
					size: "sm",
					variant: "ghost",
					children: "Remove"
				})]
			}, b.id))
		]
	});
}
function DownloadsView() {
	const browser = useStore($browser);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-3xl space-y-2 p-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center justify-between",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
				children: "Downloads"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				onClick: () => clearCompletedDownloads(),
				size: "sm",
				variant: "ghost",
				children: "Clear completed"
			})]
		}), browser.downloads.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
			description: "Files downloaded through the browser appear here with verification status.",
			icon: "cloud-download",
			title: "No downloads"
		}) : browser.downloads.map((d) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 text-xs",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "min-w-0 flex-1 truncate font-medium",
							children: d.filename
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							variant: "outline",
							children: d.status
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => removeDownload(d.id),
							size: "sm",
							variant: "ghost",
							children: "Remove"
						})
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "mt-1 truncate font-mono text-(--ui-text-tertiary)",
					children: d.url
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "text-(--ui-text-tertiary)",
					children: [
						formatBytes(d.downloadedSize),
						" / ",
						formatBytes(d.totalSize),
						" · scan: ",
						d.securityScanStatus || "pending"
					]
				})
			]
		}, d.id))]
	});
}
//#endregion
export { BrowserView };

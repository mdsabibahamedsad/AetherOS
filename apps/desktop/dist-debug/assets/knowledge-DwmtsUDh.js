import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Da as IconBrain, Ea as IconChartBar, Hi as IconTrash, Ki as IconSparkles, La as Button, Ma as IconActivity, N as StatusDot, Na as createReactComponent, O as Badge, Oa as IconBolt, P as Switch, Qa as atom, Ra as cn, Vi as IconUsers, Xa as init_nanostores, Xi as IconSearch, Ya as useStore, Yi as IconSend, Zi as IconRefresh, ao as require_jsx_runtime, ga as IconFileText, ha as IconFolderOpen, ia as IconMessageCircle, ka as IconArchive, la as IconLink, ma as IconGlobe, na as IconPackage, ni as Input, oo as require_react, pa as IconHash, sa as IconLock, ua as IconLayersIntersect2 } from "./index-B_yd1pEX.js";
import { n as ListRow } from "./primitives-BsyJey4v.js";
import { t as CREDENTIAL_CONTROL_CLASS } from "./credential-key-ui-CmZbeXXI.js";
var IconNotebook = createReactComponent("outline", "notebook", "Notebook", [
	["path", {
		"d": "M6 4h11a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-11a1 1 0 0 1 -1 -1v-14a1 1 0 0 1 1 -1m3 0v18",
		"key": "svg-0"
	}],
	["path", {
		"d": "M13 8l2 0",
		"key": "svg-1"
	}],
	["path", {
		"d": "M13 12l2 0",
		"key": "svg-2"
	}]
]);
//#endregion
//#region src/store/knowledge.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
init_nanostores();
var DEFAULT_SECURITY = {
	workspaceIsolation: true,
	encryption: true,
	permissionManagement: false,
	auditLogs: false
};
var DEFAULT_PROCESSING = {
	ocr: true,
	vision: false,
	speechToText: false,
	metadataExtraction: true,
	languageDetection: true,
	deduplication: true,
	chunking: true,
	embedding: true,
	indexing: true
};
var DEFAULT_RAG = {
	contextInjection: true,
	citation: true,
	sourceTracking: true,
	confidenceScore: false,
	multiDocumentRetrieval: true,
	maxContextChunks: 10,
	similarityThreshold: .7
};
var DEFAULT_COLLECTIONS = [
	{
		id: "col-general",
		name: "General Knowledge",
		description: "General purpose knowledge collection",
		documentCount: 0,
		color: "#3B82F6",
		icon: "book",
		createdAt: (/* @__PURE__ */ new Date()).toISOString(),
		updatedAt: (/* @__PURE__ */ new Date()).toISOString()
	},
	{
		id: "col-technical",
		name: "Technical Docs",
		description: "Technical documentation and references",
		documentCount: 0,
		color: "#10B981",
		icon: "code",
		createdAt: (/* @__PURE__ */ new Date()).toISOString(),
		updatedAt: (/* @__PURE__ */ new Date()).toISOString()
	},
	{
		id: "col-research",
		name: "Research",
		description: "Research papers and findings",
		documentCount: 0,
		color: "#8B5CF6",
		icon: "search",
		createdAt: (/* @__PURE__ */ new Date()).toISOString(),
		updatedAt: (/* @__PURE__ */ new Date()).toISOString()
	},
	{
		id: "col-projects",
		name: "Projects",
		description: "Project-related documents",
		documentCount: 0,
		color: "#F59E0B",
		icon: "folder",
		createdAt: (/* @__PURE__ */ new Date()).toISOString(),
		updatedAt: (/* @__PURE__ */ new Date()).toISOString()
	}
];
var DEFAULT_TAGS = [
	{
		id: "tag-important",
		name: "important",
		color: "#EF4444",
		documentCount: 0
	},
	{
		id: "tag-reference",
		name: "reference",
		color: "#3B82F6",
		documentCount: 0
	},
	{
		id: "tag-archived",
		name: "archived",
		color: "#6B7280",
		documentCount: 0
	},
	{
		id: "tag-draft",
		name: "draft",
		color: "#F59E0B",
		documentCount: 0
	},
	{
		id: "tag-final",
		name: "final",
		color: "#10B981",
		documentCount: 0
	}
];
var DEFAULT_STATS = {
	totalDocuments: 0,
	totalChunks: 0,
	totalBases: 0,
	totalStorage: 0,
	totalEmbeddings: 0,
	searchCount: 0,
	memoryUsage: 0,
	knowledgeUsage: 0,
	activeAgents: 0,
	documentsByType: [],
	documentsByStatus: [],
	recentSearches: []
};
var generateId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
var now = () => (/* @__PURE__ */ new Date()).toISOString();
var $knowledge = /* @__PURE__ */ atom({
	activeSection: "bases",
	searchQuery: "",
	searchType: "semantic",
	selectedBase: null,
	selectedDocument: null,
	selectedCollection: null,
	selectedMemoryType: "all",
	loading: false,
	bases: [],
	documents: [],
	chunks: [],
	memory: [{
		id: "mem-working",
		type: "working",
		content: "",
		summary: "Current session context",
		source: "system",
		agentId: null,
		sessionId: null,
		projectId: null,
		tags: [],
		pinned: false,
		createdAt: now(),
		updatedAt: now(),
		accessCount: 0,
		lastAccessed: null,
		relevanceScore: 1,
		ttl: 36e5
	}, {
		id: "mem-longterm-1",
		type: "long-term",
		content: "AetherOS is a personal AI agent platform",
		summary: "System overview",
		source: "system",
		agentId: null,
		sessionId: null,
		projectId: null,
		tags: ["reference"],
		pinned: true,
		createdAt: now(),
		updatedAt: now(),
		accessCount: 5,
		lastAccessed: now(),
		relevanceScore: .9,
		ttl: null
	}],
	collections: DEFAULT_COLLECTIONS,
	tags: DEFAULT_TAGS,
	searchResults: [],
	graphNodes: [],
	graphEdges: [],
	analytics: DEFAULT_STATS,
	syncJobs: [],
	security: DEFAULT_SECURITY,
	processing: DEFAULT_PROCESSING,
	rag: DEFAULT_RAG,
	recentDocuments: [],
	favoriteIds: [],
	sharedIds: []
});
var patch = (update) => $knowledge.set({
	...$knowledge.get(),
	...update
});
function setKnowledgeSection(section) {
	patch({ activeSection: section });
}
function setKnowledgeSearch(query) {
	patch({ searchQuery: query });
}
function setSearchType(type) {
	patch({ searchType: type });
}
function selectMemoryType(type) {
	patch({ selectedMemoryType: type });
}
function updateSecurity(update) {
	patch({ security: {
		...$knowledge.get().security,
		...update
	} });
}
function updateProcessing(update) {
	patch({ processing: {
		...$knowledge.get().processing,
		...update
	} });
}
function updateRAG(update) {
	patch({ rag: {
		...$knowledge.get().rag,
		...update
	} });
}
function addBase(base) {
	const newBase = {
		...base,
		id: generateId(),
		createdAt: now(),
		updatedAt: now(),
		documentCount: 0,
		chunkCount: 0
	};
	patch({ bases: [...$knowledge.get().bases, newBase] });
	updateAnalytics({ totalBases: $knowledge.get().bases.length + 1 });
}
function updateBase(id, update) {
	patch({ bases: $knowledge.get().bases.map((b) => b.id === id ? {
		...b,
		...update,
		updatedAt: now()
	} : b) });
}
function removeBase(id) {
	const state = $knowledge.get();
	const docsToRemove = state.documents.filter((d) => d.baseId === id);
	patch({
		bases: state.bases.filter((b) => b.id !== id),
		documents: state.documents.filter((d) => d.baseId !== id),
		chunks: state.chunks.filter((c) => c.baseId !== id),
		recentDocuments: state.recentDocuments.filter((rid) => !docsToRemove.some((d) => d.id === rid)),
		favoriteIds: state.favoriteIds.filter((fid) => !docsToRemove.some((d) => d.id === fid))
	});
}
function addDocument(doc) {
	const newDoc = {
		...doc,
		id: generateId(),
		createdAt: now(),
		updatedAt: now(),
		chunkCount: 0,
		progress: 0
	};
	const docs = [...$knowledge.get().documents, newDoc];
	patch({
		documents: docs,
		recentDocuments: [newDoc.id, ...$knowledge.get().recentDocuments].slice(0, 50)
	});
	updateAnalytics({ totalDocuments: docs.length });
}
function updateDocument(id, update) {
	patch({ documents: $knowledge.get().documents.map((d) => d.id === id ? {
		...d,
		...update,
		updatedAt: now()
	} : d) });
}
function removeDocument(id) {
	const state = $knowledge.get();
	const removed = state.documents.find((d) => d.id === id);
	if (!removed) return;
	const baseId = removed.baseId;
	patch({
		documents: state.documents.filter((d) => d.id !== id),
		chunks: state.chunks.filter((c) => c.documentId !== id),
		recentDocuments: state.recentDocuments.filter((rid) => rid !== id),
		favoriteIds: state.favoriteIds.filter((fid) => fid !== id)
	});
	updateBase(baseId, { documentCount: Math.max(0, (state.bases.find((b) => b.id === baseId)?.documentCount ?? 1) - 1) });
	updateAnalytics({ totalDocuments: state.documents.length - 1 });
}
function toggleFavorite(id) {
	const favs = $knowledge.get().favoriteIds;
	patch({ favoriteIds: favs.includes(id) ? favs.filter((f) => f !== id) : [...favs, id] });
}
function toggleDocumentFavorite(id) {
	toggleFavorite(id);
	updateDocument(id, { favorite: !$knowledge.get().documents.find((d) => d.id === id)?.favorite });
}
function archiveDocument(id) {
	updateDocument(id, { archived: true });
}
function restoreDocument(id) {
	updateDocument(id, { archived: false });
}
function addMemory(entry) {
	const newEntry = {
		...entry,
		id: generateId(),
		createdAt: now(),
		updatedAt: now(),
		accessCount: 0
	};
	patch({ memory: [...$knowledge.get().memory, newEntry] });
	updateAnalytics({ memoryUsage: $knowledge.get().memory.length + 1 });
}
function updateMemory(id, update) {
	patch({ memory: $knowledge.get().memory.map((m) => m.id === id ? {
		...m,
		...update,
		updatedAt: now(),
		accessCount: m.accessCount + 1,
		lastAccessed: now()
	} : m) });
}
function removeMemory(id) {
	patch({ memory: $knowledge.get().memory.filter((m) => m.id !== id) });
	updateAnalytics({ memoryUsage: $knowledge.get().memory.length - 1 });
}
function pinMemory(id) {
	updateMemory(id, { pinned: true });
}
function unpinMemory(id) {
	updateMemory(id, { pinned: false });
}
function addCollection(coll) {
	const newColl = {
		...coll,
		id: generateId(),
		createdAt: now(),
		updatedAt: now(),
		documentCount: 0
	};
	patch({ collections: [...$knowledge.get().collections, newColl] });
}
function removeCollection(id) {
	const docs = $knowledge.get().documents.map((d) => ({
		...d,
		collections: d.collections.filter((c) => c !== id)
	}));
	patch({
		collections: $knowledge.get().collections.filter((c) => c.id !== id),
		documents: docs
	});
}
function addTag(tag) {
	const newTag = {
		...tag,
		id: generateId(),
		documentCount: 0
	};
	patch({ tags: [...$knowledge.get().tags, newTag] });
}
function removeTag(id) {
	patch({ tags: $knowledge.get().tags.filter((t) => t.id !== id) });
}
function addSyncJob(job) {
	const newJob = {
		...job,
		id: generateId()
	};
	patch({ syncJobs: [...$knowledge.get().syncJobs, newJob] });
}
function updateSyncJob(id, update) {
	patch({ syncJobs: $knowledge.get().syncJobs.map((j) => j.id === id ? {
		...j,
		...update
	} : j) });
}
function triggerSync(baseId) {
	const existing = $knowledge.get().syncJobs.find((j) => j.baseId === baseId);
	if (existing) updateSyncJob(existing.id, {
		status: "syncing",
		progress: 0,
		error: null
	});
	else addSyncJob({
		baseId,
		status: "syncing",
		progress: 0,
		lastRun: null,
		error: null
	});
}
function addSearchResult(query, results) {
	patch({ searchResults: results });
	const state = $knowledge.get();
	const recentSearches = [{
		query,
		timestamp: now(),
		results: results.length
	}, ...state.analytics.recentSearches].slice(0, 20);
	updateAnalytics({
		searchCount: state.analytics.searchCount + 1,
		recentSearches
	});
}
function addGraphNode(node) {
	const newNode = {
		...node,
		id: generateId()
	};
	patch({ graphNodes: [...$knowledge.get().graphNodes, newNode] });
}
function updateAnalytics(update) {
	const current = $knowledge.get().analytics;
	patch({ analytics: {
		...current,
		...update
	} });
}
function getFilteredMemory() {
	const state = $knowledge.get();
	let entries = state.memory;
	if (state.selectedMemoryType !== "all") entries = entries.filter((e) => e.type === state.selectedMemoryType);
	const q = state.searchQuery.toLowerCase().trim();
	if (q) entries = entries.filter((e) => e.content.toLowerCase().includes(q) || e.summary?.toLowerCase().includes(q) || e.tags.some((t) => t.toLowerCase().includes(q)));
	return entries.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
}
function getFilteredBases() {
	const state = $knowledge.get();
	let bases = state.bases;
	const q = state.searchQuery.toLowerCase().trim();
	if (q) bases = bases.filter((b) => b.name.toLowerCase().includes(q) || b.description.toLowerCase().includes(q) || b.tags.some((t) => t.toLowerCase().includes(q)));
	return bases;
}
function getFilteredDocuments() {
	const state = $knowledge.get();
	let docs = state.documents;
	const q = state.searchQuery.toLowerCase().trim();
	if (q) docs = docs.filter((d) => d.name.toLowerCase().includes(q) || d.author?.toLowerCase().includes(q) || d.tags.some((t) => t.toLowerCase().includes(q)));
	return docs;
}
function getFavoriteDocuments() {
	return $knowledge.get().documents.filter((d) => d.favorite || $knowledge.get().favoriteIds.includes(d.id));
}
function getRecentDocuments() {
	const state = $knowledge.get();
	return state.recentDocuments.map((id) => state.documents.find((d) => d.id === id)).filter((d) => d !== void 0).slice(0, 20);
}
function getArchivedDocuments() {
	return $knowledge.get().documents.filter((d) => d.archived);
}
//#endregion
//#region src/app/knowledge/index.tsx
var import_jsx_runtime = require_jsx_runtime();
var SECTIONS = [
	{
		id: "bases",
		label: "Bases",
		icon: IconPackage
	},
	{
		id: "documents",
		label: "Documents",
		icon: IconFileText
	},
	{
		id: "search",
		label: "Search",
		icon: IconSearch
	},
	{
		id: "memory",
		label: "Memory",
		icon: IconBrain
	},
	{
		id: "collections",
		label: "Collections",
		icon: IconFolderOpen
	},
	{
		id: "tags",
		label: "Tags",
		icon: IconHash
	},
	{
		id: "favorites",
		label: "Favorites",
		icon: IconSparkles
	},
	{
		id: "recent",
		label: "Recent",
		icon: IconActivity
	},
	{
		id: "shared",
		label: "Shared",
		icon: IconSend
	},
	{
		id: "archived",
		label: "Archived",
		icon: IconArchive
	},
	{
		id: "graph",
		label: "Graph",
		icon: IconLayersIntersect2
	},
	{
		id: "analytics",
		label: "Analytics",
		icon: IconChartBar
	},
	{
		id: "sync",
		label: "Sync",
		icon: IconRefresh
	},
	{
		id: "settings",
		label: "Settings",
		icon: IconLock
	}
];
function formatBytes(bytes) {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
	if (bytes < 1073741824) return `${(bytes / 1048576).toFixed(1)} MB`;
	return `${(bytes / 1073741824).toFixed(2)} GB`;
}
function formatTime(t) {
	const d = new Date(t);
	const n = /* @__PURE__ */ new Date();
	if (d.toDateString() === n.toDateString()) return d.toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit"
	});
	return d.toLocaleDateString([], {
		month: "short",
		day: "numeric"
	});
}
var FILE_TYPE_COLORS = {
	pdf: "#EF4444",
	docx: "#3B82F6",
	txt: "#6B7280",
	md: "#10B981",
	csv: "#F59E0B",
	excel: "#22C55E",
	ppt: "#F97316",
	json: "#8B5CF6",
	yaml: "#06B6D4",
	xml: "#6366F1",
	html: "#EC4899",
	epub: "#A855F7",
	code: "#84CC16",
	zip: "#71717A",
	image: "#14B8A6",
	audio: "#F43F5E",
	video: "#8B5CF6"
};
var PROC_STATUS_TONES = {
	pending: "warn",
	processing: "warn",
	completed: "good",
	failed: "bad",
	skipped: "muted"
};
var SOURCE_ICONS = {
	"local-folder": IconFolderOpen,
	"git-repo": IconActivity,
	"github": IconActivity,
	"website": IconGlobe,
	"rss": IconHash,
	"notion": IconNotebook,
	"google-drive": IconActivity,
	"dropbox": IconActivity,
	"onedrive": IconActivity,
	"sharepoint": IconActivity,
	"s3": IconPackage,
	"webdav": IconLink,
	"custom-api": IconBolt
};
var MEMORY_ICONS = {
	working: IconBolt,
	conversation: IconMessageCircle,
	project: IconFolderOpen,
	"long-term": IconPackage,
	agent: IconBrain,
	shared: IconUsers,
	pinned: IconSparkles,
	temporary: IconActivity
};
var MEMORY_COLORS = {
	working: "#F59E0B",
	conversation: "#3B82F6",
	project: "#10B981",
	"long-term": "#8B5CF6",
	agent: "#EC4899",
	shared: "#06B6D4",
	pinned: "#EF4444",
	temporary: "#6B7280"
};
function KnowledgeView() {
	const state = useStore($knowledge);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full min-w-0 flex-col overflow-hidden bg-(--ui-chat-surface-background)",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
					className: "text-lg font-semibold tracking-tight",
					children: "Knowledge Hub"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
					className: "mt-0.5 text-xs text-(--ui-text-tertiary)",
					children: [
						state.bases.length,
						" bases · ",
						state.documents.length,
						" documents · ",
						(state.analytics.totalStorage / 1048576).toFixed(1),
						" MB"
					]
				})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [state.activeSection === "search" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex items-center gap-1",
						children: [
							"semantic",
							"hybrid",
							"keyword",
							"vector"
						].map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: cn("rounded px-1.5 py-0.5 text-[0.6rem] font-medium transition-colors", state.searchType === t ? "bg-primary/10 text-primary" : "text-(--ui-text-tertiary) hover:text-foreground"),
							onClick: () => setSearchType(t),
							type: "button",
							children: t
						}, t))
					}), state.activeSection !== "search" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						className: cn("h-7 w-48 text-xs", CREDENTIAL_CONTROL_CLASS),
						onChange: (e) => setKnowledgeSearch(e.target.value),
						placeholder: `Search ${state.activeSection}...`,
						value: state.searchQuery
					})]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex shrink-0 items-center gap-0.5 overflow-x-auto border-b border-(--ui-stroke-tertiary) px-3",
				children: SECTIONS.map((s) => {
					const Icon = s.icon;
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: cn("flex shrink-0 items-center gap-1.5 border-b-2 px-2.5 py-2 text-sm font-medium transition-colors", state.activeSection === s.id ? "border-primary text-foreground" : "border-transparent text-(--ui-text-secondary) hover:text-foreground"),
						onClick: () => setKnowledgeSection(s.id),
						type: "button",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-3.5" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "hidden sm:inline",
							children: s.label
						})]
					}, s.id);
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-h-0 flex-1 overflow-y-auto p-4",
				children: [
					state.activeSection === "bases" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(BasesPanel, {}),
					state.activeSection === "documents" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DocumentsPanel, {}),
					state.activeSection === "search" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SearchPanel, {}),
					state.activeSection === "memory" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(MemoryPanel, {}),
					state.activeSection === "collections" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CollectionsPanel, {}),
					state.activeSection === "tags" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TagsPanel, {}),
					state.activeSection === "favorites" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(FavoritesPanel, {}),
					state.activeSection === "recent" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RecentPanel, {}),
					state.activeSection === "shared" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SharedPanel, {}),
					state.activeSection === "archived" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ArchivedPanel, {}),
					state.activeSection === "graph" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(GraphPanel, {}),
					state.activeSection === "analytics" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AnalyticsPanel, {}),
					state.activeSection === "sync" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SyncPanel, {}),
					state.activeSection === "settings" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SettingsPanel, {})
				]
			})
		]
	});
}
function BasesPanel() {
	const state = useStore($knowledge);
	const filtered = getFilteredBases();
	const [showForm, setShowForm] = (0, import_react.useState)(false);
	const [name, setName] = (0, import_react.useState)("");
	const [desc, setDesc] = (0, import_react.useState)("");
	const [source, setSource] = (0, import_react.useState)("local-folder");
	const [url, setUrl] = (0, import_react.useState)("");
	const handleAdd = () => {
		if (!name.trim()) return;
		addBase({
			name: name.trim(),
			description: desc.trim(),
			source,
			sourceUrl: url,
			fileTypes: [
				"pdf",
				"txt",
				"md",
				"docx"
			],
			processingStatus: "pending",
			embeddingModel: "text-embedding-3-small",
			lastSync: null,
			syncInterval: 0,
			autoSync: false,
			archived: false,
			tags: [],
			workspaceId: "default",
			size: 0,
			error: null
		});
		setName("");
		setDesc("");
		setUrl("");
		setShowForm(false);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-5xl space-y-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
					className: "text-sm text-(--ui-text-tertiary)",
					children: [state.bases.length, " knowledge bases"]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => setShowForm(!showForm),
					size: "sm",
					variant: "textStrong",
					children: "+ New Base"
				})]
			}),
			showForm && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3 rounded-lg border border-(--ui-stroke-tertiary) p-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						className: "h-7 text-xs",
						onChange: (e) => setName(e.target.value),
						placeholder: "Base name...",
						value: name
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						className: "h-7 text-xs",
						onChange: (e) => setDesc(e.target.value),
						placeholder: "Description...",
						value: desc
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex flex-wrap gap-2",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
							className: CREDENTIAL_CONTROL_CLASS,
							onChange: (e) => setSource(e.target.value),
							value: source,
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "local-folder",
									children: "Local Folder"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "git-repo",
									children: "Git Repository"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "github",
									children: "GitHub"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "website",
									children: "Website"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "rss",
									children: "RSS"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "notion",
									children: "Notion"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "google-drive",
									children: "Google Drive"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "dropbox",
									children: "Dropbox"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "onedrive",
									children: "OneDrive"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "sharepoint",
									children: "SharePoint"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "s3",
									children: "S3"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "webdav",
									children: "WebDAV"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "custom-api",
									children: "Custom API"
								})
							]
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						className: "h-7 text-xs",
						onChange: (e) => setUrl(e.target.value),
						placeholder: "Source URL...",
						value: url
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex justify-end gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => setShowForm(false),
							size: "xs",
							variant: "ghost",
							children: "Cancel"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: handleAdd,
							size: "xs",
							variant: "textStrong",
							children: "Create"
						})]
					})
				]
			}),
			filtered.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col items-center justify-center py-24 text-center",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconPackage, { className: "mb-3 size-8 text-(--ui-text-tertiary)" }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm font-medium",
						children: "No knowledge bases"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 text-xs text-(--ui-text-tertiary)",
						children: "Create a knowledge base to start indexing documents"
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-2",
				children: filtered.map((base) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(BaseCard, { base }, base.id))
			})
		]
	});
}
function BaseCard({ base }) {
	const [expanded, setExpanded] = (0, import_react.useState)(false);
	const docs = useStore($knowledge).documents.filter((d) => d.baseId === base.id);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "rounded-lg border border-(--ui-stroke-tertiary) transition-colors hover:bg-(--chrome-action-hover)",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
			className: "flex w-full items-center gap-3 px-4 py-3 text-left",
			onClick: () => setExpanded(!expanded),
			type: "button",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "inline-flex size-8 items-center justify-center rounded-md bg-primary/10 text-primary",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SOURCE_ICONS[base.source] || IconFolderOpen, { className: "size-4" })
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "min-w-0 flex-1",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-sm font-medium",
									children: base.name
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									className: "px-1 py-0 text-[0.55rem]",
									variant: "muted",
									children: base.source.replace(/-/g, " ")
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone: PROC_STATUS_TONES[base.processingStatus] })
							]
						}),
						base.description && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-0.5 text-xs text-(--ui-text-tertiary)",
							children: base.description
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-1 flex items-center gap-3 text-[0.6rem] text-(--ui-text-tertiary)",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [base.documentCount, " docs"] }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [base.chunkCount, " chunks"] }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: formatBytes(base.size) }),
								base.lastSync && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: ["Synced ", formatTime(base.lastSync)] })
							]
						})
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex items-center gap-1",
					children: base.autoSync && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						className: "px-1 py-0 text-[0.5rem]",
						variant: "default",
						children: "Auto"
					})
				})
			]
		}), expanded && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "border-t border-(--ui-stroke-tertiary) px-4 py-3",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mb-3 flex items-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					onClick: () => triggerSync(base.id),
					size: "xs",
					variant: "outline",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconRefresh, { className: "size-3" }), " Sync"]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => {
						removeBase(base.id);
					},
					size: "xs",
					variant: "ghost",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTrash, { className: "size-3" })
				})]
			}), docs.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-1",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
					className: "text-[0.65rem] font-medium text-(--ui-text-tertiary)",
					children: [
						"Documents (",
						docs.length,
						")"
					]
				}), docs.slice(0, 5).map((doc) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2 rounded px-2 py-1 text-xs hover:bg-(--chrome-action-hover)",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone: PROC_STATUS_TONES[doc.status] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "min-w-0 flex-1 truncate",
							children: doc.name
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "text-(--ui-text-tertiary)",
							children: [doc.chunkCount, " chunks"]
						})
					]
				}, doc.id))]
			})]
		})]
	});
}
function DocumentsPanel() {
	const state = useStore($knowledge);
	const filtered = getFilteredDocuments();
	const [showForm, setShowForm] = (0, import_react.useState)(false);
	const [name, setName] = (0, import_react.useState)("");
	const [fileType, setFileType] = (0, import_react.useState)("pdf");
	const [baseId, setBaseId] = (0, import_react.useState)("");
	const handleAdd = () => {
		if (!name.trim()) return;
		addDocument({
			baseId: baseId || "default",
			name: name.trim(),
			fileType,
			size: 0,
			pageCount: 0,
			status: "pending",
			error: null,
			author: null,
			language: null,
			sourceUrl: "",
			checksum: "",
			metadata: {},
			tags: [],
			collections: [],
			favorite: false,
			archived: false,
			vectorized: false,
			indexed: false
		});
		setName("");
		setShowForm(false);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-6xl space-y-4",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
					className: "text-sm text-(--ui-text-tertiary)",
					children: [state.documents.length, " documents"]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => setShowForm(!showForm),
					size: "sm",
					variant: "textStrong",
					children: "+ Add Document"
				})]
			}),
			showForm && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-wrap items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) p-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						className: "h-7 w-60 text-xs",
						onChange: (e) => setName(e.target.value),
						placeholder: "File name...",
						value: name
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("select", {
						className: CREDENTIAL_CONTROL_CLASS,
						onChange: (e) => setFileType(e.target.value),
						value: fileType,
						children: [
							"pdf",
							"docx",
							"txt",
							"md",
							"csv",
							"excel",
							"ppt",
							"json",
							"yaml",
							"xml",
							"html",
							"epub",
							"code",
							"zip",
							"image",
							"audio",
							"video"
						].map((ft) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
							value: ft,
							children: ft.toUpperCase()
						}, ft))
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
						className: CREDENTIAL_CONTROL_CLASS,
						onChange: (e) => setBaseId(e.target.value),
						value: baseId,
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
							value: "",
							children: "Select base..."
						}), state.bases.map((b) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
							value: b.id,
							children: b.name
						}, b.id))]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: handleAdd,
						size: "xs",
						variant: "textStrong",
						children: "Add"
					})
				]
			}),
			filtered.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col items-center justify-center py-24 text-center",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconFileText, { className: "mb-3 size-8 text-(--ui-text-tertiary)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm font-medium",
					children: "No documents"
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3",
				children: filtered.map((doc) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DocumentCard, { doc }, doc.id))
			})
		]
	});
}
function DocumentCard({ doc }) {
	const knowledge = useStore($knowledge);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: cn("rounded-lg border border-(--ui-stroke-tertiary) p-3 transition-colors hover:bg-(--chrome-action-hover)", doc.archived && "opacity-60"),
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-start gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "inline-grid size-8 shrink-0 place-items-center rounded-md text-xs font-bold",
					style: {
						backgroundColor: `color-mix(in srgb, ${FILE_TYPE_COLORS[doc.fileType] ?? "#6B7280"} 16%, transparent)`,
						color: FILE_TYPE_COLORS[doc.fileType] ?? "#6B7280"
					},
					children: doc.fileType.toUpperCase()
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "min-w-0 flex-1",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "truncate text-sm font-medium",
								children: doc.name
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone: PROC_STATUS_TONES[doc.status] })]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-0.5 flex flex-wrap gap-1",
							children: doc.tags.map((tagId) => {
								const tag = knowledge.tags.find((t) => t.id === tagId);
								return tag ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "rounded bg-(--ui-row-active-background) px-1 py-0 text-[0.5rem] text-(--ui-text-tertiary)",
									children: tag.name
								}, tagId) : null;
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-1 flex items-center gap-2 text-[0.55rem] text-(--ui-text-tertiary)",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: formatBytes(doc.size) }),
								doc.pageCount > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [doc.pageCount, " pages"] }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [doc.chunkCount, " chunks"] }),
								doc.author && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: doc.author })
							]
						})
					]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-2 flex items-center gap-1",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => toggleDocumentFavorite(doc.id),
						size: "xs",
						variant: "ghost",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconSparkles, { className: cn("size-3", doc.favorite && "fill-amber-500 text-amber-500") })
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => archiveDocument(doc.id),
						size: "xs",
						variant: "ghost",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconArchive, { className: "size-3" })
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => {
							removeDocument(doc.id);
						},
						size: "xs",
						variant: "ghost",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTrash, { className: "size-3" })
					}),
					doc.status === "pending" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "ml-auto text-[0.55rem] text-(--ui-text-tertiary)",
						children: [doc.progress, "%"]
					})
				]
			}),
			doc.error && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-[0.6rem] text-destructive",
				children: doc.error
			})
		]
	});
}
function SearchPanel() {
	const state = useStore($knowledge);
	const [query, setQuery] = (0, import_react.useState)("");
	const [results, setResults] = (0, import_react.useState)([]);
	const handleSearch = () => {
		if (!query.trim()) return;
		const q = query.toLowerCase().trim();
		const mockResults = state.documents.filter((d) => d.name.toLowerCase().includes(q) || d.tags.some((t) => t.toLowerCase().includes(q))).slice(0, 10).map((d, i) => ({
			id: `sr-${i}`,
			documentId: d.id,
			baseId: d.baseId,
			chunkIndex: 0,
			content: d.name,
			score: 1 - i * .1,
			source: d.sourceUrl || d.name,
			documentName: d.name,
			fileType: d.fileType,
			highlights: [],
			metadata: d.metadata
		}));
		setResults(mockResults);
		addSearchResult(query.trim(), mockResults);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-4xl space-y-4",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
					className: "h-8 flex-1 text-xs",
					onChange: (e) => setQuery(e.target.value),
					onKeyDown: (e) => e.key === "Enter" && handleSearch(),
					placeholder: "Search across all knowledge bases...",
					value: query
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					onClick: handleSearch,
					size: "sm",
					variant: "textStrong",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconSearch, { className: "size-3.5" }), " Search"]
				})]
			}),
			results.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
				className: "text-xs text-(--ui-text-tertiary)",
				children: [results.length, " results"]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-2",
				children: results.map((r) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded-lg border border-(--ui-stroke-tertiary) p-3 transition-colors hover:bg-(--chrome-action-hover)",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "rounded bg-primary/10 px-1.5 py-0.5 text-[0.55rem] font-medium text-primary",
									children: r.fileType.toUpperCase()
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-sm font-medium",
									children: r.documentName
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "ml-auto text-[0.55rem] text-(--ui-text-tertiary)",
									children: [
										"Score: ",
										(r.score * 100).toFixed(0),
										"%"
									]
								})
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 text-xs text-(--ui-text-tertiary)",
							children: r.content
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-0.5 text-[0.55rem] text-(--ui-text-tertiary)",
							children: r.source
						})
					]
				}, r.id))
			})] }),
			results.length === 0 && query && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col items-center justify-center py-24 text-center",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconSearch, { className: "mb-3 size-8 text-(--ui-text-tertiary)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm font-medium",
					children: "No results"
				})]
			})
		]
	});
}
function MemoryPanel() {
	const state = useStore($knowledge);
	const filtered = getFilteredMemory();
	const [showForm, setShowForm] = (0, import_react.useState)(false);
	const [content, setContent] = (0, import_react.useState)("");
	const [memType, setMemType] = (0, import_react.useState)("working");
	const MEMORY_TYPES = [
		{
			id: "working",
			label: "Working"
		},
		{
			id: "conversation",
			label: "Conversation"
		},
		{
			id: "project",
			label: "Project"
		},
		{
			id: "long-term",
			label: "Long-Term"
		},
		{
			id: "agent",
			label: "Agent"
		},
		{
			id: "shared",
			label: "Shared"
		},
		{
			id: "pinned",
			label: "Pinned"
		},
		{
			id: "temporary",
			label: "Temporary"
		}
	];
	const handleAdd = () => {
		if (!content.trim()) return;
		addMemory({
			type: memType,
			content: content.trim(),
			summary: null,
			source: "manual",
			agentId: null,
			sessionId: null,
			projectId: null,
			tags: [],
			pinned: false,
			lastAccessed: null,
			relevanceScore: .5,
			ttl: memType === "temporary" ? 36e5 : null
		});
		setContent("");
		setShowForm(false);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-5xl space-y-4",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex flex-wrap gap-1",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: cn("rounded px-1.5 py-0.5 text-[0.6rem] font-medium transition-colors", state.selectedMemoryType === "all" ? "bg-primary/10 text-primary" : "text-(--ui-text-tertiary) hover:text-foreground"),
						onClick: () => selectMemoryType("all"),
						type: "button",
						children: [
							"All (",
							state.memory.length,
							")"
						]
					}, "all"), MEMORY_TYPES.map((mt) => {
						const count = state.memory.filter((m) => m.type === mt.id).length;
						return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: cn("rounded px-1.5 py-0.5 text-[0.6rem] font-medium transition-colors", state.selectedMemoryType === mt.id ? "bg-primary/10 text-primary" : "text-(--ui-text-tertiary) hover:text-foreground"),
							onClick: () => selectMemoryType(mt.id),
							type: "button",
							children: [
								mt.label,
								" (",
								count,
								")"
							]
						}, mt.id);
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => setShowForm(!showForm),
					size: "sm",
					variant: "textStrong",
					children: "+ Add"
				})]
			}),
			showForm && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
					className: cn("min-h-[60px] w-full resize-none rounded-md border border-(--ui-stroke-tertiary) bg-transparent px-2 py-1.5 text-xs", CREDENTIAL_CONTROL_CLASS),
					onChange: (e) => setContent(e.target.value),
					placeholder: "Memory content...",
					value: content
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("select", {
						className: CREDENTIAL_CONTROL_CLASS,
						onChange: (e) => setMemType(e.target.value),
						value: memType,
						children: MEMORY_TYPES.map((mt) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
							value: mt.id,
							children: mt.label
						}, mt.id))
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => setShowForm(false),
							size: "xs",
							variant: "ghost",
							children: "Cancel"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: handleAdd,
							size: "xs",
							variant: "textStrong",
							children: "Save"
						})]
					})]
				})]
			}),
			filtered.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col items-center justify-center py-24 text-center",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconBrain, { className: "mb-3 size-8 text-(--ui-text-tertiary)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm font-medium",
					children: "No memory entries"
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-2",
				children: filtered.map((entry) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(MemoryCard, { entry }, entry.id))
			})
		]
	});
}
function MemoryCard({ entry }) {
	const Icon = MEMORY_ICONS[entry.type];
	const color = MEMORY_COLORS[entry.type];
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5 transition-colors hover:bg-(--chrome-action-hover)",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-start gap-3",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "inline-flex size-7 items-center justify-center rounded-md",
					style: { backgroundColor: `color-mix(in srgb, ${color} 16%, transparent)` },
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, {
						className: "size-3.5",
						style: { color }
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "min-w-0 flex-1",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								className: "text-sm font-medium capitalize",
								children: [entry.type, " Memory"]
							}), entry.pinned && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								className: "px-1 py-0 text-[0.5rem]",
								variant: "default",
								children: "Pinned"
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-0.5 text-xs text-(--ui-text-secondary)",
							children: entry.content
						}),
						entry.summary && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-0.5 text-[0.6rem] italic text-(--ui-text-tertiary)",
							children: entry.summary
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-1 flex items-center gap-2 text-[0.55rem] text-(--ui-text-tertiary)",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
									"Score: ",
									(entry.relevanceScore * 100).toFixed(0),
									"%"
								] }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: ["Access: ", entry.accessCount] }),
								entry.source && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: ["Source: ", entry.source] })
							]
						})
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-1",
					children: [entry.pinned ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => unpinMemory(entry.id),
						size: "xs",
						variant: "ghost",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconSparkles, { className: "size-3 fill-amber-500 text-amber-500" })
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => pinMemory(entry.id),
						size: "xs",
						variant: "ghost",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconSparkles, { className: "size-3" })
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => {
							removeMemory(entry.id);
						},
						size: "xs",
						variant: "ghost",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTrash, { className: "size-3" })
					})]
				})
			]
		})
	});
}
function CollectionsPanel() {
	const state = useStore($knowledge);
	const [showForm, setShowForm] = (0, import_react.useState)(false);
	const [name, setName] = (0, import_react.useState)("");
	const [desc, setDesc] = (0, import_react.useState)("");
	const [color, setColor] = (0, import_react.useState)("#3B82F6");
	const handleAdd = () => {
		if (!name.trim()) return;
		addCollection({
			name: name.trim(),
			description: desc.trim(),
			color,
			icon: "folder"
		});
		setName("");
		setDesc("");
		setShowForm(false);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-4xl space-y-4",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
					className: "text-sm text-(--ui-text-tertiary)",
					children: [state.collections.length, " collections"]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => setShowForm(!showForm),
					size: "sm",
					variant: "textStrong",
					children: "+ New Collection"
				})]
			}),
			showForm && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-wrap items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) p-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						className: "h-7 w-48 text-xs",
						onChange: (e) => setName(e.target.value),
						placeholder: "Name...",
						value: name
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						className: "h-7 flex-1 text-xs",
						onChange: (e) => setDesc(e.target.value),
						placeholder: "Description...",
						value: desc
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						className: "h-7 w-8 cursor-pointer rounded border border-(--ui-stroke-tertiary)",
						onChange: (e) => setColor(e.target.value),
						type: "color",
						value: color
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: handleAdd,
						size: "xs",
						variant: "textStrong",
						children: "Create"
					})
				]
			}),
			state.collections.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col items-center justify-center py-24 text-center",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconFolderOpen, { className: "mb-3 size-8 text-(--ui-text-tertiary)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm font-medium",
					children: "No collections"
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3",
				children: state.collections.map((coll) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "rounded-lg border border-(--ui-stroke-tertiary) p-3 transition-colors hover:bg-(--chrome-action-hover)",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "inline-grid size-8 place-items-center rounded-md text-sm",
								style: { backgroundColor: `color-mix(in srgb, ${coll.color} 16%, transparent)` },
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconFolderOpen, {
									className: "size-4",
									style: { color: coll.color }
								})
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "min-w-0 flex-1",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-sm font-medium",
										children: coll.name
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-xs text-(--ui-text-tertiary)",
										children: coll.description
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
										className: "text-[0.55rem] text-(--ui-text-tertiary)",
										children: [coll.documentCount, " documents"]
									})
								]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => {
									removeCollection(coll.id);
								},
								size: "xs",
								variant: "ghost",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTrash, { className: "size-3" })
							})
						]
					})
				}, coll.id))
			})
		]
	});
}
function TagsPanel() {
	const state = useStore($knowledge);
	const [showForm, setShowForm] = (0, import_react.useState)(false);
	const [name, setName] = (0, import_react.useState)("");
	const [color, setColor] = (0, import_react.useState)("#3B82F6");
	const handleAdd = () => {
		if (!name.trim()) return;
		addTag({
			name: name.trim(),
			color
		});
		setName("");
		setShowForm(false);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-3xl space-y-4",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
					className: "text-sm text-(--ui-text-tertiary)",
					children: [state.tags.length, " tags"]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => setShowForm(!showForm),
					size: "sm",
					variant: "textStrong",
					children: "+ New Tag"
				})]
			}),
			showForm && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) p-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						className: "h-7 w-40 text-xs",
						onChange: (e) => setName(e.target.value),
						placeholder: "Tag name...",
						value: name
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						className: "h-7 w-8 cursor-pointer rounded border border-(--ui-stroke-tertiary)",
						onChange: (e) => setColor(e.target.value),
						type: "color",
						value: color
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: handleAdd,
						size: "xs",
						variant: "textStrong",
						children: "Add"
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex flex-wrap gap-2",
				children: state.tags.map((tag) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs transition-colors hover:opacity-80",
					style: {
						backgroundColor: `color-mix(in srgb, ${tag.color} 16%, transparent)`,
						color: tag.color
					},
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconHash, { className: "size-3" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: tag.name }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "opacity-60",
							children: [
								"(",
								tag.documentCount,
								")"
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "ml-0.5 opacity-50 hover:opacity-100",
							onClick: () => {
								removeTag(tag.id);
							},
							type: "button",
							children: "×"
						})
					]
				}, tag.id))
			})
		]
	});
}
function FavoritesPanel() {
	const favs = getFavoriteDocuments();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-5xl space-y-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
			className: "text-sm text-(--ui-text-tertiary)",
			children: [favs.length, " favorites"]
		}), favs.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex flex-col items-center justify-center py-24 text-center",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconSparkles, { className: "mb-3 size-8 text-(--ui-text-tertiary)" }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm font-medium",
					children: "No favorites yet"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-1 text-xs text-(--ui-text-tertiary)",
					children: "Star documents to add them to favorites"
				})
			]
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3",
			children: favs.map((doc) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DocumentCard, { doc }, doc.id))
		})]
	});
}
function RecentPanel() {
	const recent = getRecentDocuments();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-5xl space-y-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
			className: "text-sm text-(--ui-text-tertiary)",
			children: [recent.length, " recently viewed"]
		}), recent.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex flex-col items-center justify-center py-24 text-center",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconActivity, { className: "mb-3 size-8 text-(--ui-text-tertiary)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm font-medium",
				children: "No recent documents"
			})]
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3",
			children: recent.map((doc) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DocumentCard, { doc }, doc.id))
		})]
	});
}
function SharedPanel() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col items-center justify-center py-24 text-center",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconSend, { className: "mb-3 size-8 text-(--ui-text-tertiary)" }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm font-medium",
				children: "No shared documents"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-xs text-(--ui-text-tertiary)",
				children: "Share documents with other agents and workspaces"
			})
		]
	});
}
function ArchivedPanel() {
	const archived = getArchivedDocuments();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-5xl space-y-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
			className: "text-sm text-(--ui-text-tertiary)",
			children: [archived.length, " archived"]
		}), archived.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex flex-col items-center justify-center py-24 text-center",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconArchive, { className: "mb-3 size-8 text-(--ui-text-tertiary)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm font-medium",
				children: "No archived documents"
			})]
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3",
			children: archived.map((doc) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "rounded-lg border border-(--ui-stroke-tertiary) p-3 opacity-60 transition-colors hover:bg-(--chrome-action-hover)",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "inline-grid size-8 place-items-center rounded-md text-xs font-bold text-(--ui-text-tertiary) bg-(--ui-row-active-background)",
							children: doc.fileType.toUpperCase()
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0 flex-1",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-sm font-medium",
								children: doc.name
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex gap-2 text-[0.55rem] text-(--ui-text-tertiary)",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: formatBytes(doc.size) }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [doc.chunkCount, " chunks"] })]
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => restoreDocument(doc.id),
							size: "xs",
							variant: "ghost",
							children: "Restore"
						})
					]
				})
			}, doc.id))
		})]
	});
}
function GraphPanel() {
	const state = useStore($knowledge);
	const hasData = state.graphNodes.length > 0 || state.documents.length > 0;
	const handleGenerate = () => {
		for (const doc of state.documents.slice(0, 10)) addGraphNode({
			type: "document",
			label: doc.name,
			color: FILE_TYPE_COLORS[doc.fileType] ?? "#6B7280",
			connections: []
		});
		for (const agent of [
			"Research Agent",
			"Knowledge Agent",
			"Code Agent"
		]) addGraphNode({
			type: "agent",
			label: agent,
			color: "#8B5CF6",
			connections: []
		});
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-5xl space-y-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center justify-between",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
				className: "text-sm text-(--ui-text-tertiary)",
				children: [state.graphNodes.length, " nodes"]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
				onClick: handleGenerate,
				size: "sm",
				variant: "textStrong",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLayersIntersect2, { className: "size-3.5" }), " Generate Graph"]
			})]
		}), !hasData ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex flex-col items-center justify-center py-24 text-center",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLayersIntersect2, { className: "mb-3 size-8 text-(--ui-text-tertiary)" }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm font-medium",
					children: "No knowledge graph"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-1 text-xs text-(--ui-text-tertiary)",
					children: "Generate a graph to visualize relationships between documents, agents, and projects"
				})
			]
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3",
			children: state.graphNodes.map((node) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 transition-colors hover:bg-(--chrome-action-hover)",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "inline-grid size-7 shrink-0 place-items-center rounded text-[0.55rem] font-bold",
						style: {
							backgroundColor: `color-mix(in srgb, ${node.color} 16%, transparent)`,
							color: node.color
						},
						children: node.type[0].toUpperCase()
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "min-w-0 flex-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-sm font-medium capitalize",
							children: node.label
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-[0.55rem] text-(--ui-text-tertiary)",
							children: node.type
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "shrink-0 text-[0.55rem] text-(--ui-text-tertiary)",
						children: [node.connections.length, " edges"]
					})
				]
			}, node.id))
		})]
	});
}
function AnalyticsPanel() {
	const analytics = useStore($knowledge).analytics;
	const [showSearches, setShowSearches] = (0, import_react.useState)(false);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-5xl space-y-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4",
			children: [
				{
					key: "totalDocuments",
					label: "Documents",
					icon: IconFileText
				},
				{
					key: "totalChunks",
					label: "Chunks",
					icon: IconLayersIntersect2
				},
				{
					key: "totalBases",
					label: "Bases",
					icon: IconPackage
				},
				{
					key: "totalStorage",
					label: "Storage",
					icon: IconArchive,
					format: (v) => formatBytes(v)
				},
				{
					key: "totalEmbeddings",
					label: "Embeddings",
					icon: IconBolt
				},
				{
					key: "searchCount",
					label: "Searches",
					icon: IconSearch
				},
				{
					key: "memoryUsage",
					label: "Memory",
					icon: IconBrain
				},
				{
					key: "activeAgents",
					label: "Agents",
					icon: IconUsers
				}
			].map((c) => {
				const val = analytics[c.key];
				return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded-lg border border-(--ui-stroke-tertiary) px-3 py-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex items-center justify-between",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(c.icon, { className: "size-4 text-(--ui-text-tertiary)" })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 text-xl font-semibold tracking-tight",
							children: c.format ? c.format(val) : typeof val === "number" ? val : 0
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: c.label
						})
					]
				}, c.key);
			})
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid grid-cols-1 gap-4 sm:grid-cols-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "rounded-lg border border-(--ui-stroke-tertiary) p-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mb-2 text-xs font-semibold",
						children: "Documents by Type"
					}),
					analytics.documentsByType.map((d) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2 py-1",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "w-12 text-[0.6rem] text-(--ui-text-tertiary)",
								children: d.type.toUpperCase()
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "h-1.5 flex-1 rounded-full bg-(--ui-row-active-background)",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "h-1.5 rounded-full bg-primary",
									style: { width: `${d.count / Math.max(...analytics.documentsByType.map((x) => x.count), 1) * 100}%` }
								})
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "w-6 text-right text-[0.55rem] text-(--ui-text-tertiary)",
								children: d.count
							})
						]
					}, d.type)),
					analytics.documentsByType.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "py-2 text-center text-xs text-(--ui-text-tertiary)",
						children: "No data"
					})
				]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "rounded-lg border border-(--ui-stroke-tertiary) p-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "mb-2 flex items-center justify-between text-xs font-semibold",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "Recent Searches" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "text-(--ui-text-tertiary)",
							onClick: () => setShowSearches(!showSearches),
							type: "button",
							children: showSearches ? "Hide" : `Show (${analytics.recentSearches.length})`
						})]
					}),
					showSearches && analytics.recentSearches.map((s, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between py-0.5 text-[0.6rem]",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "truncate text-(--ui-text-secondary)",
							children: s.query
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "text-(--ui-text-tertiary)",
							children: [s.results, " results"]
						})]
					}, i)),
					analytics.recentSearches.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "py-2 text-center text-xs text-(--ui-text-tertiary)",
						children: "No searches yet"
					})
				]
			})]
		})]
	});
}
function SyncPanel() {
	const state = useStore($knowledge);
	const jobs = state.syncJobs;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-4xl space-y-4",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
				className: "text-sm text-(--ui-text-tertiary)",
				children: [jobs.length, " sync jobs"]
			}),
			jobs.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col items-center justify-center py-24 text-center",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconRefresh, { className: "mb-3 size-8 text-(--ui-text-tertiary)" }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm font-medium",
						children: "No sync jobs"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 text-xs text-(--ui-text-tertiary)",
						children: "Sync jobs appear when you trigger a knowledge base sync"
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-1",
				children: jobs.map((job) => {
					const base = state.bases.find((b) => b.id === job.baseId);
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone: job.status === "success" ? "good" : job.status === "error" ? "bad" : job.status === "syncing" ? "warn" : "muted" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "min-w-0 flex-1",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-sm font-medium",
										children: base?.name ?? "Unknown Base"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
										className: "text-xs capitalize text-(--ui-text-tertiary)",
										children: [job.status, job.progress > 0 && ` (${job.progress}%)`]
									}),
									job.error && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-xs text-destructive",
										children: job.error
									})
								]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-xs text-(--ui-text-tertiary)",
								children: job.lastRun ? formatTime(job.lastRun) : "Never"
							}),
							job.status === "idle" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => triggerSync(job.baseId),
								size: "xs",
								variant: "outline",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconRefresh, { className: "size-3" })
							})
						]
					}, job.id);
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "pt-4 text-xs font-semibold text-(--ui-text-tertiary)",
				children: "Available for sync:"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-1",
				children: state.bases.filter((b) => !jobs.some((j) => j.baseId === b.id)).map((base) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone: "muted" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "min-w-0 flex-1",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-sm font-medium",
								children: base.name
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => triggerSync(base.id),
							size: "xs",
							variant: "textStrong",
							children: "Sync Now"
						})
					]
				}, base.id))
			})
		]
	});
}
function SettingsPanel() {
	const state = useStore($knowledge);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-2xl space-y-8",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
				className: "mb-3 flex items-center gap-2 text-sm font-semibold",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLock, { className: "size-4" }), " Security"]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-1",
				children: [
					"workspaceIsolation",
					"encryption",
					"permissionManagement",
					"auditLogs"
				].map((key) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: state.security[key],
						onCheckedChange: (c) => updateSecurity({ [key]: c }),
						size: "xs"
					}),
					description: securityDesc(key),
					title: securityLabel(key)
				}, key))
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
				className: "mb-3 flex items-center gap-2 text-sm font-semibold",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconBolt, { className: "size-4" }), " Processing"]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-1",
				children: [
					"ocr",
					"vision",
					"speechToText",
					"metadataExtraction",
					"languageDetection",
					"deduplication",
					"chunking",
					"embedding",
					"indexing"
				].map((key) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: state.processing[key],
						onCheckedChange: (c) => updateProcessing({ [key]: c }),
						size: "xs"
					}),
					description: processingDesc(key),
					title: processingLabel(key)
				}, key))
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
					className: "mb-3 flex items-center gap-2 text-sm font-semibold",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconNotebook, { className: "size-4" }), " RAG Configuration"]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "space-y-1",
					children: [
						"contextInjection",
						"citation",
						"sourceTracking",
						"confidenceScore",
						"multiDocumentRetrieval"
					].map((key) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.rag[key],
							onCheckedChange: (c) => updateRAG({ [key]: c }),
							size: "xs"
						}),
						description: ragDesc(key),
						title: ragLabel(key)
					}, key))
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-3 grid grid-cols-2 gap-4 px-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-(--ui-text-secondary)",
						children: "Max Context Chunks"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("select", {
						className: cn("mt-1 w-full", CREDENTIAL_CONTROL_CLASS),
						onChange: (e) => updateRAG({ maxContextChunks: Number(e.target.value) }),
						value: state.rag.maxContextChunks,
						children: [
							5,
							10,
							15,
							20,
							30,
							50
						].map((n) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
							value: n,
							children: n
						}, n))
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-(--ui-text-secondary)",
						children: "Similarity Threshold"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("select", {
						className: cn("mt-1 w-full", CREDENTIAL_CONTROL_CLASS),
						onChange: (e) => updateRAG({ similarityThreshold: Number(e.target.value) }),
						value: state.rag.similarityThreshold,
						children: [
							.5,
							.6,
							.7,
							.75,
							.8,
							.85,
							.9
						].map((n) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
							value: n,
							children: n
						}, n))
					})] })]
				})
			] })
		]
	});
}
function securityLabel(key) {
	return {
		workspaceIsolation: "Workspace Isolation",
		encryption: "Encryption",
		permissionManagement: "Permission Management",
		auditLogs: "Audit Logs"
	}[key];
}
function securityDesc(key) {
	return {
		workspaceIsolation: "Isolate knowledge between workspaces",
		encryption: "Encrypt all knowledge at rest",
		permissionManagement: "Granular access control per document",
		auditLogs: "Log all access and modifications"
	}[key];
}
function processingLabel(key) {
	return {
		ocr: "OCR",
		vision: "Vision",
		speechToText: "Speech to Text",
		metadataExtraction: "Metadata Extraction",
		languageDetection: "Language Detection",
		deduplication: "Deduplication",
		chunking: "Chunking",
		embedding: "Embedding",
		indexing: "Indexing"
	}[key];
}
function processingDesc(key) {
	return {
		ocr: "Extract text from images and scanned PDFs",
		vision: "Analyze images with computer vision",
		speechToText: "Transcribe audio content",
		metadataExtraction: "Extract metadata from documents",
		languageDetection: "Auto-detect document language",
		deduplication: "Remove duplicate content",
		chunking: "Split documents into processable chunks",
		embedding: "Generate vector embeddings",
		indexing: "Build search indexes"
	}[key];
}
function ragLabel(key) {
	return {
		contextInjection: "Context Injection",
		citation: "Citation",
		sourceTracking: "Source Tracking",
		confidenceScore: "Confidence Score",
		multiDocumentRetrieval: "Multi-Document Retrieval",
		maxContextChunks: "Max Context Chunks",
		similarityThreshold: "Similarity Threshold"
	}[key] ?? key;
}
function ragDesc(key) {
	return {
		contextInjection: "Inject relevant context into prompts",
		citation: "Include source citations in responses",
		sourceTracking: "Track document sources for responses",
		confidenceScore: "Show confidence scores with results",
		multiDocumentRetrieval: "Retrieve from multiple documents simultaneously",
		maxContextChunks: "",
		similarityThreshold: ""
	}[key] ?? "";
}
//#endregion
export { KnowledgeView };

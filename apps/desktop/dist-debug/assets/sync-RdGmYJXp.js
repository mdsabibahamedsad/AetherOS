import { Qa as atom, Xa as init_nanostores } from "./index-B_yd1pEX.js";
//#region src/store/sync.ts
init_nanostores();
var DEFAULT_SCOPES = [
	{
		id: "messages",
		name: "Messages",
		description: "Synchronize conversation messages across devices",
		enabled: true
	},
	{
		id: "sessions",
		name: "Sessions",
		description: "Sync active sessions and their state",
		enabled: true
	},
	{
		id: "memory",
		name: "Memory",
		description: "Distribute agent memory across instances",
		enabled: true
	},
	{
		id: "knowledge",
		name: "Knowledge",
		description: "Sync knowledge base entries and embeddings",
		enabled: true
	},
	{
		id: "files",
		name: "Files",
		description: "Synchronize workspace files and attachments",
		enabled: true
	},
	{
		id: "config",
		name: "Configuration",
		description: "Sync settings and preferences",
		enabled: true
	},
	{
		id: "plugins",
		name: "Plugins",
		description: "Distribute plugin installations and state",
		enabled: true
	},
	{
		id: "skills",
		name: "Skills",
		description: "Sync skill definitions and usage data",
		enabled: true
	},
	{
		id: "cron",
		name: "Scheduled Jobs",
		description: "Distribute cron job definitions",
		enabled: false
	},
	{
		id: "contacts",
		name: "Contacts",
		description: "Sync contact and address book",
		enabled: true
	},
	{
		id: "bookmarks",
		name: "Bookmarks",
		description: "Sync bookmarks and saved items",
		enabled: true
	},
	{
		id: "templates",
		name: "Templates",
		description: "Sync message and response templates",
		enabled: false
	},
	{
		id: "agent-state",
		name: "Agent State",
		description: "Sync agent behavior and persona settings",
		enabled: true
	},
	{
		id: "toolsets",
		name: "Toolsets",
		description: "Sync enabled toolsets configuration",
		enabled: true
	},
	{
		id: "gateway",
		name: "Gateway",
		description: "Sync gateway platform configurations",
		enabled: false
	},
	{
		id: "ui-state",
		name: "UI State",
		description: "Sync desktop layout and UI preferences",
		enabled: false
	}
];
var $syncStatus = /* @__PURE__ */ atom("idle");
var $syncEnabled = /* @__PURE__ */ atom(true);
var $syncScopes = /* @__PURE__ */ atom(DEFAULT_SCOPES);
var $syncHistory = /* @__PURE__ */ atom([]);
var $syncConflicts = /* @__PURE__ */ atom([]);
var $syncLastSync = /* @__PURE__ */ atom(null);
var $syncProgress = /* @__PURE__ */ atom(0);
var $syncOnline = /* @__PURE__ */ atom(true);
var $syncError = /* @__PURE__ */ atom(null);
function setSyncScope(scopeId, enabled) {
	const scopes = $syncScopes.get();
	$syncScopes.set(scopes.map((s) => s.id === scopeId ? {
		...s,
		enabled
	} : s));
}
function completeSync(errorMessage) {
	$syncStatus.set(errorMessage ? "error" : "idle");
	$syncLastSync.set((/* @__PURE__ */ new Date()).toISOString());
	$syncProgress.set(100);
	if (errorMessage) $syncError.set(errorMessage);
}
function addSyncEvent(event) {
	const history = $syncHistory.get();
	$syncHistory.set([event, ...history].slice(0, 500));
}
function resolveConflict(conflictId, resolution) {
	const conflicts = $syncConflicts.get();
	$syncConflicts.set(conflicts.map((c) => c.id === conflictId ? {
		...c,
		status: "resolved",
		resolution,
		resolvedAt: (/* @__PURE__ */ new Date()).toISOString()
	} : c));
}
function clearSyncHistory() {
	$syncHistory.set([]);
}
function clearSyncError() {
	$syncError.set(null);
}
//#endregion
export { $syncLastSync as a, $syncStatus as c, clearSyncHistory as d, completeSync as f, $syncHistory as i, addSyncEvent as l, setSyncScope as m, $syncEnabled as n, $syncOnline as o, resolveConflict as p, $syncError as r, $syncScopes as s, $syncConflicts as t, clearSyncError as u };

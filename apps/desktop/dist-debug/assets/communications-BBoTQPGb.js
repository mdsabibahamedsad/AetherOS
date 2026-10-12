import { Qa as atom, Xa as init_nanostores } from "./index-B_yd1pEX.js";
//#region src/store/communications.ts
init_nanostores();
var DEFAULT_AI_CONFIG = {
	autoReply: false,
	smartSuggestions: false,
	rewriteEnabled: false,
	translateEnabled: false,
	summarizeEnabled: false,
	sentimentAnalysis: false,
	priorityDetection: false,
	spamDetection: false,
	meetingDetection: false,
	taskExtraction: false
};
var DEFAULT_VOICE_CONFIG = {
	enabled: false,
	provider: "whisper",
	pushToTalk: true,
	voiceCommands: false,
	voiceReply: false
};
var DEFAULT_MEDIA_CONFIG = {
	ocrEnabled: false,
	visionEnabled: false,
	captionEnabled: false,
	summarizeMedia: false,
	autoDownload: true,
	maxFileSize: 25e6
};
var DEFAULT_NOTIFICATION_CONFIG = {
	desktopNotifications: true,
	soundEnabled: true,
	silentMode: false,
	silentModeStart: "22:00",
	silentModeEnd: "07:00",
	priorityMode: false,
	doNotDisturb: false
};
var DEFAULT_SECURITY = {
	encryptedTokens: true,
	localStorage: true,
	credentialVault: false,
	permissionManager: false,
	auditLog: false
};
var PLATFORM_META = [
	{
		id: "telegram",
		name: "Telegram",
		icon: "send",
		color: "#26A5E4"
	},
	{
		id: "whatsapp",
		name: "WhatsApp",
		icon: "message-circle",
		color: "#25D366"
	},
	{
		id: "discord",
		name: "Discord",
		icon: "message-circle",
		color: "#5865F2"
	},
	{
		id: "slack",
		name: "Slack",
		icon: "message-square-text",
		color: "#4A154B"
	},
	{
		id: "gmail",
		name: "Gmail",
		icon: "mail",
		color: "#EA4335"
	},
	{
		id: "outlook",
		name: "Outlook",
		icon: "mail",
		color: "#0078D4"
	},
	{
		id: "teams",
		name: "Microsoft Teams",
		icon: "people",
		color: "#6264A7"
	},
	{
		id: "signal",
		name: "Signal",
		icon: "lock",
		color: "#3A76F0"
	},
	{
		id: "sms",
		name: "SMS Gateway",
		icon: "message-square-text",
		color: "#F43F5E"
	},
	{
		id: "webhook",
		name: "Webhook",
		icon: "link",
		color: "#71717A"
	},
	{
		id: "custom-rest",
		name: "Custom REST API",
		icon: "terminal",
		color: "#64748B"
	}
];
var generateId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
var $communications = /* @__PURE__ */ atom({
	activeTab: "dashboard",
	selectedPlatform: null,
	platformConnections: PLATFORM_META.map((p) => ({
		...p,
		connected: false,
		online: false,
		messagesToday: 0,
		aiReplies: 0,
		queued: 0,
		failed: 0,
		lastActivity: null
	})),
	conversations: [],
	messages: [],
	aiConfig: DEFAULT_AI_CONFIG,
	voiceConfig: DEFAULT_VOICE_CONFIG,
	mediaConfig: DEFAULT_MEDIA_CONFIG,
	notificationConfig: DEFAULT_NOTIFICATION_CONFIG,
	security: DEFAULT_SECURITY,
	automationRules: [],
	activityFeed: [],
	mediaItems: [],
	templates: [],
	inboxFilter: "all",
	inboxSearch: "",
	selectedConversation: null,
	selectedPlatformFilter: "all",
	searchQuery: "",
	loading: false
});
var patch = (update) => $communications.set({
	...$communications.get(),
	...update
});
function setCommsTab(tab) {
	patch({ activeTab: tab });
}
function setInboxFilter(filter) {
	patch({ inboxFilter: filter });
}
function setInboxSearch(search) {
	patch({ inboxSearch: search });
}
function setPlatformFilter(filter) {
	patch({ selectedPlatformFilter: filter });
}
function selectConversation(id) {
	patch({ selectedConversation: id });
}
function setPlatformConnection(id, update) {
	patch({ platformConnections: $communications.get().platformConnections.map((p) => p.id === id ? {
		...p,
		...update
	} : p) });
}
function setPlatformStatus(id, connected, online) {
	setPlatformConnection(id, {
		connected,
		online
	});
	addActivity({
		type: connected ? "connection" : "error",
		platform: id,
		description: `${PLATFORM_META.find((p) => p.id === id)?.name ?? id} ${connected ? "connected" : "disconnected"}`,
		platformName: PLATFORM_META.find((p) => p.id === id)?.name ?? id
	});
}
function addActivity(entry) {
	const newEntry = {
		...entry,
		id: generateId(),
		timestamp: (/* @__PURE__ */ new Date()).toISOString()
	};
	const feed = $communications.get().activityFeed;
	patch({ activityFeed: [newEntry, ...feed].slice(0, 100) });
}
function clearActivity() {
	patch({ activityFeed: [] });
}
function markMessageRead(id) {
	patch({ messages: $communications.get().messages.map((m) => m.id === id ? {
		...m,
		read: true
	} : m) });
}
function togglePinMessage(id) {
	patch({ messages: $communications.get().messages.map((m) => m.id === id ? {
		...m,
		pinned: !m.pinned
	} : m) });
}
function toggleImportantMessage(id) {
	patch({ messages: $communications.get().messages.map((m) => m.id === id ? {
		...m,
		important: !m.important
	} : m) });
}
function archiveMessage(id) {
	patch({ messages: $communications.get().messages.map((m) => m.id === id ? {
		...m,
		archived: true
	} : m) });
}
function updateAIConfig(update) {
	patch({ aiConfig: {
		...$communications.get().aiConfig,
		...update
	} });
}
function updateVoiceConfig(update) {
	patch({ voiceConfig: {
		...$communications.get().voiceConfig,
		...update
	} });
}
function updateMediaConfig(update) {
	patch({ mediaConfig: {
		...$communications.get().mediaConfig,
		...update
	} });
}
function updateNotificationConfig(update) {
	patch({ notificationConfig: {
		...$communications.get().notificationConfig,
		...update
	} });
}
function updateSecurity(update) {
	patch({ security: {
		...$communications.get().security,
		...update
	} });
}
function addAutomationRule(rule) {
	const newRule = {
		...rule,
		id: generateId()
	};
	patch({ automationRules: [...$communications.get().automationRules, newRule] });
}
function updateAutomationRule(id, update) {
	patch({ automationRules: $communications.get().automationRules.map((r) => r.id === id ? {
		...r,
		...update
	} : r) });
}
function removeAutomationRule(id) {
	patch({ automationRules: $communications.get().automationRules.filter((r) => r.id !== id) });
}
function getFilteredMessages() {
	const state = $communications.get();
	let msgs = state.messages;
	const filter = state.inboxFilter;
	const platformFilter = state.selectedPlatformFilter;
	const search = state.inboxSearch.toLowerCase().trim();
	if (platformFilter !== "all") msgs = msgs.filter((m) => m.platform === platformFilter);
	switch (filter) {
		case "unread":
			msgs = msgs.filter((m) => !m.read);
			break;
		case "important":
			msgs = msgs.filter((m) => m.important);
			break;
		case "pinned":
			msgs = msgs.filter((m) => m.pinned);
			break;
		case "ai-only":
			msgs = msgs.filter((m) => m.aiReplied);
			break;
		case "archived":
			msgs = msgs.filter((m) => m.archived);
			break;
		default:
			msgs = msgs.filter((m) => !m.archived);
			break;
	}
	if (search) msgs = msgs.filter((m) => m.content.toLowerCase().includes(search) || m.senderName.toLowerCase().includes(search));
	return msgs.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}
function getCommsStats() {
	const state = $communications.get();
	return {
		connectedAccounts: state.platformConnections.filter((p) => p.connected).length,
		onlineStatus: state.platformConnections.filter((p) => p.online).length,
		messagesToday: state.platformConnections.reduce((s, p) => s + p.messagesToday, 0),
		aiReplies: state.platformConnections.reduce((s, p) => s + p.aiReplies, 0),
		queuedMessages: state.platformConnections.reduce((s, p) => s + p.queued, 0),
		failedMessages: state.platformConnections.reduce((s, p) => s + p.failed, 0),
		automations: state.automationRules.filter((r) => r.enabled).length
	};
}
function getPlatformMeta(id) {
	return PLATFORM_META.find((p) => p.id === id);
}
function getAllPlatformMeta() {
	return PLATFORM_META;
}
//#endregion
export { updateMediaConfig as C, updateVoiceConfig as E, updateAutomationRule as S, updateSecurity as T, setPlatformFilter as _, clearActivity as a, togglePinMessage as b, getFilteredMessages as c, removeAutomationRule as d, selectConversation as f, setPlatformConnection as g, setInboxSearch as h, archiveMessage as i, getPlatformMeta as l, setInboxFilter as m, addActivity as n, getAllPlatformMeta as o, setCommsTab as p, addAutomationRule as r, getCommsStats as s, $communications as t, markMessageRead as u, setPlatformStatus as v, updateNotificationConfig as w, updateAIConfig as x, toggleImportantMessage as y };

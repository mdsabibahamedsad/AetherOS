//#region ../shared/dist/json-rpc-gateway.js
var ANY = "*";
var DEFAULT_REQUEST_TIMEOUT_MS = 12e4;
var DEFAULT_CONNECT_TIMEOUT_MS = 15e3;
var JsonRpcGatewayClient = class {
	nextId = 0;
	pending = /* @__PURE__ */ new Map();
	socket = null;
	state = "idle";
	eventHandlers = /* @__PURE__ */ new Map();
	stateHandlers = /* @__PURE__ */ new Set();
	options;
	constructor(options = {}) {
		this.options = {
			closedErrorMessage: options.closedErrorMessage ?? "WebSocket closed",
			connectErrorMessage: options.connectErrorMessage ?? "WebSocket connection failed",
			connectTimeoutMs: options.connectTimeoutMs ?? DEFAULT_CONNECT_TIMEOUT_MS,
			createRequestId: options.createRequestId ?? ((nextId) => `${options.requestIdPrefix ?? "r"}${nextId}`),
			notConnectedErrorMessage: options.notConnectedErrorMessage ?? "gateway not connected",
			requestIdPrefix: options.requestIdPrefix ?? "r",
			requestTimeoutMs: options.requestTimeoutMs ?? DEFAULT_REQUEST_TIMEOUT_MS,
			socketFactory: options.socketFactory
		};
	}
	get connectionState() {
		return this.state;
	}
	async connect(wsUrl) {
		if (this.socket?.readyState === WebSocket.OPEN || this.state === "connecting") return;
		this.setState("connecting");
		const socket = this.options.socketFactory?.(wsUrl) ?? new WebSocket(wsUrl);
		this.socket = socket;
		socket.addEventListener("message", (message) => {
			if (this.socket !== socket) return;
			this.handleMessage(message.data);
		});
		socket.addEventListener("close", () => {
			if (this.socket !== socket) return;
			this.socket = null;
			this.setState("closed");
			this.rejectAllPending(new Error(this.options.closedErrorMessage));
		});
		await new Promise((resolve, reject) => {
			let settled = false;
			let timer;
			const cleanup = () => {
				if (timer !== void 0) clearTimeout(timer);
				socket.removeEventListener("open", onOpen);
				socket.removeEventListener("error", onError);
			};
			const onOpen = () => {
				if (settled || this.socket !== socket) return;
				settled = true;
				cleanup();
				this.setState("open");
				resolve();
			};
			const onError = () => {
				if (settled || this.socket !== socket) return;
				settled = true;
				cleanup();
				this.setState("error");
				reject(new Error(this.options.connectErrorMessage));
			};
			socket.addEventListener("open", onOpen, { once: true });
			socket.addEventListener("error", onError, { once: true });
			if (this.options.connectTimeoutMs > 0) timer = setTimeout(() => {
				if (settled) return;
				settled = true;
				cleanup();
				if (this.socket === socket) {
					try {
						socket.close();
					} catch {}
					this.socket = null;
				}
				this.setState("error");
				reject(new Error(this.options.connectErrorMessage));
			}, this.options.connectTimeoutMs);
		});
	}
	close() {
		this.socket?.close();
		this.socket = null;
	}
	on(type, handler) {
		let handlers = this.eventHandlers.get(type);
		if (!handlers) {
			handlers = /* @__PURE__ */ new Set();
			this.eventHandlers.set(type, handlers);
		}
		handlers.add(handler);
		return () => handlers?.delete(handler);
	}
	onAny(handler) {
		return this.on(ANY, handler);
	}
	onEvent(handler) {
		return this.onAny(handler);
	}
	onState(handler) {
		this.stateHandlers.add(handler);
		handler(this.state);
		return () => this.stateHandlers.delete(handler);
	}
	request(method, params = {}, timeoutMs = this.options.requestTimeoutMs) {
		const socket = this.socket;
		if (!socket || socket.readyState !== WebSocket.OPEN) return Promise.reject(new Error(this.options.notConnectedErrorMessage));
		const id = this.options.createRequestId(++this.nextId);
		return new Promise((resolve, reject) => {
			const pending = {
				reject,
				resolve: (value) => resolve(value)
			};
			if (timeoutMs > 0) pending.timer = setTimeout(() => {
				if (this.pending.delete(id)) reject(/* @__PURE__ */ new Error(`request timed out: ${method}`));
			}, timeoutMs);
			this.pending.set(id, pending);
			try {
				socket.send(JSON.stringify({
					jsonrpc: "2.0",
					id,
					method,
					params
				}));
			} catch (error) {
				this.clearPending(id);
				reject(error instanceof Error ? error : new Error(String(error)));
			}
		});
	}
	handleMessage(raw) {
		const text = typeof raw === "string" ? raw : String(raw);
		let frame;
		try {
			frame = JSON.parse(text);
		} catch {
			return;
		}
		if (frame.id !== void 0 && frame.id !== null) {
			const call = this.pending.get(frame.id);
			if (!call) return;
			this.clearPending(frame.id);
			if (frame.error) call.reject(new Error(frame.error.message || "Aetheros RPC failed"));
			else call.resolve(frame.result);
			return;
		}
		if (frame.method === "event" && frame.params?.type) this.dispatchEvent(frame.params);
	}
	clearPending(id) {
		const call = this.pending.get(id);
		if (call?.timer) clearTimeout(call.timer);
		this.pending.delete(id);
	}
	dispatchEvent(event) {
		for (const handler of this.eventHandlers.get(event.type) ?? []) handler(event);
		for (const handler of this.eventHandlers.get(ANY) ?? []) handler(event);
	}
	rejectAllPending(error) {
		for (const [id, call] of this.pending) {
			if (call.timer) clearTimeout(call.timer);
			call.reject(error);
			this.pending.delete(id);
		}
	}
	setState(state) {
		if (this.state === state) return;
		this.state = state;
		for (const handler of this.stateHandlers) handler(state);
	}
};
//#endregion
//#region ../shared/dist/platform-capabilities.js
var native = () => ({
	browser: "native",
	terminal: "native",
	filesystem: "native",
	computerUse: "native",
	notifications: "native",
	tray: "native",
	agentControl: "native",
	taskSubmission: "native",
	planPreview: "native",
	confirmations: "native"
});
/** iOS is a control plane: privileged execution is always server-side. */
var iosCapabilities = () => ({
	browser: "backend-mediated",
	terminal: "backend-mediated",
	filesystem: "unsupported",
	computerUse: "backend-mediated",
	notifications: "native",
	tray: "unsupported",
	agentControl: "native",
	taskSubmission: "native",
	planPreview: "native",
	confirmations: "native"
});
/**
* Linux Wayland: capture/input/window-management stay UNSUPPORTED until a
* portal-based path is validated on real compositors (see linux-session.cjs).
*/
var waylandCapabilities = () => {
	const caps = native();
	caps.computerUse = "unsupported";
	return caps;
};
native(), native(), native(), waylandCapabilities(), iosCapabilities();
//#endregion
//#region src/hermes.ts
var DEFAULT_GATEWAY_REQUEST_TIMEOUT_MS = 3e4;
var SESSION_LIST_REQUEST_TIMEOUT_MS = 6e4;
var AetherosGateway = class extends JsonRpcGatewayClient {
	constructor() {
		super({
			closedErrorMessage: "Aetheros gateway connection closed",
			connectErrorMessage: "Could not connect to Aetheros gateway",
			createRequestId: (nextId) => nextId,
			notConnectedErrorMessage: "Aetheros gateway is not connected",
			requestTimeoutMs: DEFAULT_GATEWAY_REQUEST_TIMEOUT_MS
		});
	}
};
var _apiProfile = null;
function setApiRequestProfile(profile) {
	_apiProfile = profile || null;
}
function profileScoped() {
	return _apiProfile ? { profile: _apiProfile } : {};
}
async function listAllProfileSessions(limit = 40, minMessages = 0, archived = "exclude", order = "recent", profile = "all", filter = {}) {
	const sourceParam = filter.source ? `&source=${encodeURIComponent(filter.source)}` : "";
	const excludeParam = filter.excludeSources?.length ? `&exclude_sources=${encodeURIComponent(filter.excludeSources.join(","))}` : "";
	const result = await window.aetherosDesktop.api({
		path: `/api/profiles/sessions?limit=${limit}&offset=0&min_messages=${Math.max(0, minMessages)}&archived=${archived}&order=${order}&profile=${encodeURIComponent(profile)}${sourceParam}${excludeParam}`,
		timeoutMs: SESSION_LIST_REQUEST_TIMEOUT_MS
	});
	return {
		...result,
		sessions: result.sessions.slice(0, limit),
		offset: 0
	};
}
function setSessionArchived(id, archived, profile) {
	return window.aetherosDesktop.api({
		...profile ? { profile } : {},
		path: `/api/sessions/${encodeURIComponent(id)}`,
		method: "PATCH",
		body: { archived }
	});
}
function searchSessions(query) {
	return window.aetherosDesktop.api({ path: `/api/sessions/search?q=${encodeURIComponent(query)}` });
}
function getSessionMessages(id, profile) {
	const suffix = profile ? `?profile=${encodeURIComponent(profile)}` : "";
	return window.aetherosDesktop.api({
		...profile ? { profile } : {},
		path: `/api/sessions/${encodeURIComponent(id)}/messages${suffix}`
	});
}
function deleteSession(id, profile) {
	return window.aetherosDesktop.api({
		...profile ? { profile } : {},
		path: `/api/sessions/${encodeURIComponent(id)}`,
		method: "DELETE"
	});
}
function renameSession(id, title, profile) {
	return window.aetherosDesktop.api({
		...profile ? { profile } : {},
		path: `/api/sessions/${encodeURIComponent(id)}`,
		method: "PATCH",
		body: {
			title,
			...profile ? { profile } : {}
		}
	});
}
function getGlobalModelInfo() {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/model/info"
	});
}
function getStatus() {
	return window.aetherosDesktop.api({ path: "/api/status" });
}
function getLogs(params) {
	const query = new URLSearchParams();
	if (params.file) query.set("file", params.file);
	if (typeof params.lines === "number") query.set("lines", String(params.lines));
	if (params.level && params.level !== "ALL") query.set("level", params.level);
	if (params.component && params.component !== "all") query.set("component", params.component);
	const suffix = query.toString();
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: suffix ? `/api/logs?${suffix}` : "/api/logs"
	});
}
function getAetherosConfig() {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/config"
	});
}
function getAetherosConfigRecord() {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/config"
	});
}
function getAetherosConfigDefaults() {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/config/defaults"
	});
}
function getAetherosConfigSchema() {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/config/schema"
	});
}
function saveAetherosConfig(config) {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/config",
		method: "PUT",
		body: { config }
	});
}
function getEnvVars() {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/env"
	});
}
function setEnvVar(key, value) {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/env",
		method: "PUT",
		body: {
			key,
			value
		}
	});
}
function validateProviderCredential(key, value, apiKey) {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/providers/validate",
		method: "POST",
		body: {
			key,
			value,
			api_key: apiKey ?? ""
		}
	});
}
function deleteEnvVar(key) {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/env",
		method: "DELETE",
		body: { key }
	});
}
function revealEnvVar(key) {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/env/reveal",
		method: "POST",
		body: { key }
	});
}
function listOAuthProviders() {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/providers/oauth"
	});
}
function getSkills() {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/skills"
	});
}
function toggleSkill(name, enabled) {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/skills/toggle",
		method: "PUT",
		body: {
			name,
			enabled
		}
	});
}
function getToolsets() {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/tools/toolsets"
	});
}
function toggleToolset(name, enabled) {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: `/api/tools/toolsets/${encodeURIComponent(name)}`,
		method: "PUT",
		body: { enabled }
	});
}
function getToolsetConfig(name) {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: `/api/tools/toolsets/${encodeURIComponent(name)}/config`
	});
}
function selectToolsetProvider(name, provider) {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: `/api/tools/toolsets/${encodeURIComponent(name)}/provider`,
		method: "PUT",
		body: { provider }
	});
}
function runToolsetPostSetup(name, key) {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: `/api/tools/toolsets/${encodeURIComponent(name)}/post-setup`,
		method: "POST",
		body: { key }
	});
}
function getMessagingPlatforms() {
	return window.aetherosDesktop.api({ path: "/api/messaging/platforms" });
}
function updateMessagingPlatform(platformId, body) {
	return window.aetherosDesktop.api({
		path: `/api/messaging/platforms/${encodeURIComponent(platformId)}`,
		method: "PUT",
		body
	});
}
function testMessagingPlatform(platformId) {
	return window.aetherosDesktop.api({
		path: `/api/messaging/platforms/${encodeURIComponent(platformId)}/test`,
		method: "POST"
	});
}
function getCronJobs() {
	return window.aetherosDesktop.api({ path: "/api/cron/jobs" });
}
async function getCronJobRuns(jobId, limit = 20) {
	const { runs } = await window.aetherosDesktop.api({ path: `/api/cron/jobs/${encodeURIComponent(jobId)}/runs?limit=${limit}` });
	return runs ?? [];
}
function createCronJob(body) {
	return window.aetherosDesktop.api({
		path: "/api/cron/jobs",
		method: "POST",
		body
	});
}
function updateCronJob(jobId, updates) {
	return window.aetherosDesktop.api({
		path: `/api/cron/jobs/${encodeURIComponent(jobId)}`,
		method: "PUT",
		body: { updates }
	});
}
function pauseCronJob(jobId) {
	return window.aetherosDesktop.api({
		path: `/api/cron/jobs/${encodeURIComponent(jobId)}/pause`,
		method: "POST"
	});
}
function resumeCronJob(jobId) {
	return window.aetherosDesktop.api({
		path: `/api/cron/jobs/${encodeURIComponent(jobId)}/resume`,
		method: "POST"
	});
}
function triggerCronJob(jobId) {
	return window.aetherosDesktop.api({
		path: `/api/cron/jobs/${encodeURIComponent(jobId)}/trigger`,
		method: "POST"
	});
}
function deleteCronJob(jobId) {
	return window.aetherosDesktop.api({
		path: `/api/cron/jobs/${encodeURIComponent(jobId)}`,
		method: "DELETE"
	});
}
function getProfiles() {
	return window.aetherosDesktop.api({ path: "/api/profiles" });
}
function createProfile(body) {
	return window.aetherosDesktop.api({
		path: "/api/profiles",
		method: "POST",
		body
	});
}
function renameProfile(name, newName) {
	return window.aetherosDesktop.api({
		path: `/api/profiles/${encodeURIComponent(name)}`,
		method: "PATCH",
		body: { new_name: newName }
	});
}
function deleteProfile(name) {
	return window.aetherosDesktop.api({
		path: `/api/profiles/${encodeURIComponent(name)}`,
		method: "DELETE"
	});
}
function getProfileSoul(name) {
	return window.aetherosDesktop.api({ path: `/api/profiles/${encodeURIComponent(name)}/soul` });
}
function updateProfileSoul(name, content) {
	return window.aetherosDesktop.api({
		path: `/api/profiles/${encodeURIComponent(name)}/soul`,
		method: "PUT",
		body: { content }
	});
}
function getProfileSetupCommand(name) {
	return window.aetherosDesktop.api({ path: `/api/profiles/${encodeURIComponent(name)}/setup-command` });
}
function getUsageAnalytics(days = 30) {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: `/api/analytics/usage?days=${Math.max(1, Math.floor(days))}`
	});
}
function getGlobalModelOptions() {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/model/options"
	});
}
function getRecommendedDefaultModel(provider) {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: `/api/model/recommended-default?provider=${encodeURIComponent(provider)}`
	});
}
function setGlobalModel(provider, model) {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/model/set",
		method: "POST",
		body: {
			scope: "main",
			provider,
			model
		}
	});
}
function getAuxiliaryModels() {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/model/auxiliary"
	});
}
function setModelAssignment(body) {
	return window.aetherosDesktop.api({
		...profileScoped(),
		path: "/api/model/set",
		method: "POST",
		body
	});
}
function restartGateway() {
	return window.aetherosDesktop.api({
		path: "/api/gateway/restart",
		method: "POST"
	});
}
function updateAetheros() {
	return window.aetherosDesktop.api({
		path: "/api/aetheros/update",
		method: "POST"
	});
}
/** Spawn a real `aetheros backup` run. Track it with getActionStatus('backup'). */
function runBackup(output) {
	return window.aetherosDesktop.api({
		path: "/api/ops/backup",
		method: "POST",
		body: output ? { output } : {}
	});
}
/**
* Restore from a backup archive (`aetheros import`). Destructive: the caller
* must confirm explicitly (the backend aborts without force when a config
* already exists). Track with getActionStatus('import').
*/
function runImport(archive, force = false) {
	return window.aetherosDesktop.api({
		path: "/api/ops/import",
		method: "POST",
		body: {
			archive,
			force
		}
	});
}
/** Query the connected backend's own update state. In remote mode this is the
*  authoritative source for the backend's behind-count + "what's changed",
*  distinct from the Electron client clone's git state. */
function checkAetherosUpdate(force = false) {
	return window.aetherosDesktop.api({ path: `/api/aetheros/update/check${force ? "?force=true" : ""}` });
}
function getActionStatus(name, lines = 200) {
	return window.aetherosDesktop.api({ path: `/api/actions/${encodeURIComponent(name)}/status?lines=${Math.max(1, lines)}` });
}
function transcribeAudio(dataUrl, mimeType) {
	return window.aetherosDesktop.api({
		path: "/api/audio/transcribe",
		method: "POST",
		body: {
			data_url: dataUrl,
			mime_type: mimeType
		}
	});
}
function speakText(text) {
	return window.aetherosDesktop.api({
		path: "/api/audio/speak",
		method: "POST",
		body: { text }
	});
}
function getElevenLabsVoices() {
	return window.aetherosDesktop.api({ path: "/api/audio/elevenlabs/voices" });
}
//#endregion
export { testMessagingPlatform as $, getToolsetConfig as A, revealEnvVar as B, getProfileSetupCommand as C, getSessionMessages as D, getRecommendedDefaultModel as E, pauseCronJob as F, searchSessions as G, runImport as H, renameProfile as I, setEnvVar as J, selectToolsetProvider as K, renameSession as L, getUsageAnalytics as M, listAllProfileSessions as N, getSkills as O, listOAuthProviders as P, speakText as Q, restartGateway as R, getMessagingPlatforms as S, getProfiles as T, runToolsetPostSetup as U, runBackup as V, saveAetherosConfig as W, setModelAssignment as X, setGlobalModel as Y, setSessionArchived as Z, getElevenLabsVoices as _, deleteCronJob as a, updateCronJob as at, getGlobalModelOptions as b, deleteSession as c, validateProviderCredential as ct, getAetherosConfigDefaults as d, toggleSkill as et, getAetherosConfigRecord as f, getCronJobs as g, getCronJobRuns as h, createProfile as i, updateAetheros as it, getToolsets as j, getStatus as k, getActionStatus as l, getAuxiliaryModels as m, checkAetherosUpdate as n, transcribeAudio as nt, deleteEnvVar as o, updateMessagingPlatform as ot, getAetherosConfigSchema as p, setApiRequestProfile as q, createCronJob as r, triggerCronJob as rt, deleteProfile as s, updateProfileSoul as st, AetherosGateway as t, toggleToolset as tt, getAetherosConfig as u, getEnvVars as v, getProfileSoul as w, getLogs as x, getGlobalModelInfo as y, resumeCronJob as z };

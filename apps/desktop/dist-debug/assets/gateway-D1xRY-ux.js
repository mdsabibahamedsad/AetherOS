import { r as __exportAll } from "./chunk-DKxDMwdo.js";
import { t as AetherosGateway } from "./aetheros-DF_uJq_t.js";
import { Qa as atom, Ti as setGatewayState, Xa as init_nanostores } from "./index-B_yd1pEX.js";
//#region src/lib/gateway-ws-url.ts
init_nanostores();
var GatewayReauthRequiredError = class extends Error {
	needsOauthLogin = true;
	constructor(message, options) {
		super(message, options);
		this.name = "GatewayReauthRequiredError";
	}
};
function isGatewayReauthRequired(error) {
	return error instanceof GatewayReauthRequiredError || typeof error === "object" && error !== null && error.needsOauthLogin === true;
}
async function resolveGatewayWsUrl(desktop, conn) {
	const mint = desktop.getGatewayWsUrl;
	const profile = conn.profile ?? null;
	if (conn.authMode === "oauth") {
		if (!mint) throw new GatewayReauthRequiredError("Your remote gateway session needs to be refreshed. Open Settings → Gateway and click \"Sign in\" again.");
		try {
			return await mint(profile);
		} catch (error) {
			throw new GatewayReauthRequiredError("Your remote gateway session has expired. Open Settings → Gateway and click \"Sign in\" again.", { cause: error });
		}
	}
	if (mint) {
		const fresh = await mint(profile).catch(() => null);
		if (fresh) return fresh;
	}
	return conn.wsUrl;
}
//#endregion
//#region src/store/gateway.ts
var gateway_exports = /* @__PURE__ */ __exportAll({
	$gateway: () => $gateway,
	activeGateway: () => activeGateway,
	closeSecondaryGateways: () => closeSecondaryGateways,
	configureGatewayRegistry: () => configureGatewayRegistry,
	ensureActiveGatewayOpen: () => ensureActiveGatewayOpen,
	ensureGatewayForProfile: () => ensureGatewayForProfile,
	isActivePrimary: () => isActivePrimary,
	pruneSecondaryGateways: () => pruneSecondaryGateways,
	reconnectSecondaryGateways: () => reconnectSecondaryGateways,
	reportPrimaryGatewayState: () => reportPrimaryGatewayState,
	setPrimaryGateway: () => setPrimaryGateway,
	touchSecondaryGateways: () => touchSecondaryGateways
});
var normKey = (profile) => (profile ?? "").trim() || "default";
var isOpen = (gateway) => gateway?.connectionState === "open";
var $gateway = /* @__PURE__ */ atom(null);
var config = null;
function configureGatewayRegistry(cfg) {
	config = cfg;
}
var primaryGateway = null;
var primaryProfile = "default";
function setPrimaryGateway(gateway, profile = "default") {
	primaryGateway = gateway;
	primaryProfile = normKey(profile);
}
var secondaries = /* @__PURE__ */ new Map();
var activeKey = "default";
function isActivePrimary() {
	return activeKey === primaryProfile;
}
function activeGateway() {
	if (activeKey === primaryProfile) return primaryGateway;
	return secondaries.get(activeKey)?.gateway ?? primaryGateway;
}
function reportGatewayState(profile, state) {
	if (normKey(profile) === activeKey) setGatewayState(state);
}
function reportPrimaryGatewayState(state) {
	reportGatewayState(primaryProfile, state);
}
function setActive(profile) {
	activeKey = normKey(profile);
	const gateway = activeGateway();
	$gateway.set(gateway);
	setGatewayState(gateway?.connectionState ?? "closed");
}
function clearTimer(entry) {
	if (entry.reconnectTimer !== null) {
		clearTimeout(entry.reconnectTimer);
		entry.reconnectTimer = null;
	}
}
async function openSecondary(entry) {
	const desktop = window.aetherosDesktop;
	if (!desktop) return;
	const wsUrl = await resolveGatewayWsUrl(desktop, await desktop.getConnection(entry.profile));
	await entry.gateway.connect(wsUrl);
	desktop.touchBackend?.(entry.profile).catch(() => void 0);
}
function scheduleReconnect(entry) {
	if (entry.reconnecting || entry.reconnectTimer !== null || !entry.wantOpen) return;
	const delay = Math.min(15e3, 1e3 * 2 ** Math.min(entry.reconnectAttempt, 4));
	entry.reconnectAttempt += 1;
	entry.reconnectTimer = setTimeout(() => {
		entry.reconnectTimer = null;
		reconnectSecondary(entry);
	}, delay);
}
async function reconnectSecondary(entry) {
	if (entry.reconnecting || !entry.wantOpen || isOpen(entry.gateway)) return;
	entry.reconnecting = true;
	try {
		await openSecondary(entry);
		entry.reconnectAttempt = 0;
	} catch {} finally {
		entry.reconnecting = false;
		if (entry.wantOpen && !isOpen(entry.gateway)) scheduleReconnect(entry);
	}
}
function createSecondary(profile) {
	const gateway = new AetherosGateway();
	const entry = {
		profile,
		gateway,
		offEvent: () => {},
		offState: () => {},
		reconnectTimer: null,
		reconnectAttempt: 0,
		reconnecting: false,
		wantOpen: true
	};
	entry.offEvent = gateway.onEvent((event) => config?.onEvent(event));
	entry.offState = gateway.onState((state) => {
		reportGatewayState(profile, state);
		if (state === "open") {
			entry.reconnectAttempt = 0;
			clearTimer(entry);
		} else if ((state === "closed" || state === "error") && entry.wantOpen) scheduleReconnect(entry);
	});
	secondaries.set(profile, entry);
	return entry;
}
async function ensureGatewayForProfile(profile) {
	const key = normKey(profile);
	if (key === primaryProfile) {
		setActive(key);
		return;
	}
	let entry = secondaries.get(key);
	if (!entry) entry = createSecondary(key);
	entry.wantOpen = true;
	if (!isOpen(entry.gateway)) {
		clearTimer(entry);
		entry.reconnectAttempt = 0;
		try {
			await openSecondary(entry);
		} catch {
			scheduleReconnect(entry);
		}
	}
	setActive(key);
}
async function ensureActiveGatewayOpen() {
	if (activeKey === primaryProfile) return primaryGateway;
	const entry = secondaries.get(activeKey);
	if (!entry) return null;
	if (!isOpen(entry.gateway)) await reconnectSecondary(entry);
	return isOpen(entry.gateway) ? entry.gateway : null;
}
function reconnectSecondaryGateways() {
	for (const entry of secondaries.values()) {
		if (!entry.wantOpen || isOpen(entry.gateway)) continue;
		entry.reconnectAttempt = 0;
		clearTimer(entry);
		reconnectSecondary(entry);
	}
}
function touchSecondaryGateways() {
	const desktop = window.aetherosDesktop;
	for (const entry of secondaries.values()) if (entry.wantOpen) desktop?.touchBackend?.(entry.profile).catch(() => void 0);
}
function pruneSecondaryGateways(keep) {
	for (const [key, entry] of [...secondaries]) {
		if (key === activeKey || keep.has(key)) continue;
		entry.wantOpen = false;
		clearTimer(entry);
		entry.offEvent();
		entry.offState();
		entry.gateway.close();
		secondaries.delete(key);
	}
}
function closeSecondaryGateways() {
	for (const entry of secondaries.values()) {
		entry.wantOpen = false;
		clearTimer(entry);
		entry.offEvent();
		entry.offState();
		entry.gateway.close();
	}
	secondaries.clear();
}
//#endregion
export { ensureActiveGatewayOpen as a, isActivePrimary as c, reportPrimaryGatewayState as d, setPrimaryGateway as f, resolveGatewayWsUrl as h, configureGatewayRegistry as i, pruneSecondaryGateways as l, isGatewayReauthRequired as m, activeGateway as n, ensureGatewayForProfile as o, touchSecondaryGateways as p, closeSecondaryGateways as r, gateway_exports as s, $gateway as t, reconnectSecondaryGateways as u };

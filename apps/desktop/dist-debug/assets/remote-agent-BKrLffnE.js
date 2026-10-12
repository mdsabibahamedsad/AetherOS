import { Qa as atom, Xa as init_nanostores } from "./index-B_yd1pEX.js";
//#region src/store/remote-agent.ts
init_nanostores();
var INITIAL_AGENT_STATUS = {
	status: "stopped",
	cpu: 0,
	memory: 0,
	uptime: 0,
	startedAt: null,
	errorMessage: null
};
var $remoteInstances = /* @__PURE__ */ atom([]);
var $activeInstanceId = /* @__PURE__ */ atom(null);
var $remoteAgentStatus = /* @__PURE__ */ atom(INITIAL_AGENT_STATUS);
var $remoteLogs = /* @__PURE__ */ atom([]);
var $remoteTasks = /* @__PURE__ */ atom([]);
var $remoteConnected = /* @__PURE__ */ atom(false);
var $remoteLoading = /* @__PURE__ */ atom(false);
var $remoteLogLevelFilter = /* @__PURE__ */ atom("all");
function getActiveInstance() {
	const id = $activeInstanceId.get();
	if (!id) return null;
	return $remoteInstances.get().find((i) => i.id === id) ?? null;
}
function addRemoteInstance(instance) {
	const instances = $remoteInstances.get();
	if (instances.some((i) => i.id === instance.id)) return;
	$remoteInstances.set([...instances, instance]);
}
function removeRemoteInstance(id) {
	if ($activeInstanceId.get() === id) {
		$activeInstanceId.set(null);
		$remoteConnected.set(false);
	}
	$remoteInstances.set($remoteInstances.get().filter((i) => i.id !== id));
}
function updateInstanceStatus(id, status, errorMessage) {
	$remoteInstances.set($remoteInstances.get().map((i) => i.id === id ? {
		...i,
		status,
		errorMessage: errorMessage ?? null
	} : i));
}
function updateInstanceLatency(id, latency) {
	$remoteInstances.set($remoteInstances.get().map((i) => i.id === id ? {
		...i,
		latency
	} : i));
}
function updateInstanceHealth(id, health) {
	$remoteInstances.set($remoteInstances.get().map((i) => i.id === id ? {
		...i,
		healthCheck: health
	} : i));
}
function setActiveInstance(id) {
	$activeInstanceId.set(id);
}
async function connect(id) {
	setActiveInstance(id);
	updateInstanceStatus(id, "connecting");
	$remoteConnected.set(true);
	updateInstanceStatus(id, "online");
}
async function disconnect() {
	const id = $activeInstanceId.get();
	if (id) updateInstanceStatus(id, "offline");
	$remoteConnected.set(false);
	$activeInstanceId.set(null);
	$remoteAgentStatus.set(INITIAL_AGENT_STATUS);
	$remoteLogs.set([]);
	$remoteTasks.set([]);
}
async function reconnect(id) {
	await disconnect();
	await connect(id);
}
function startAgent() {
	const current = $remoteAgentStatus.get();
	$remoteAgentStatus.set({
		...current,
		status: "starting"
	});
	$remoteAgentStatus.set({
		...current,
		status: "running",
		startedAt: (/* @__PURE__ */ new Date()).toISOString(),
		errorMessage: null
	});
}
function stopAgent() {
	const current = $remoteAgentStatus.get();
	$remoteAgentStatus.set({
		...current,
		status: "stopping"
	});
	$remoteAgentStatus.set({
		...current,
		status: "stopped",
		startedAt: null,
		uptime: 0
	});
}
function pauseAgent() {
	const current = $remoteAgentStatus.get();
	if (current.status === "running") $remoteAgentStatus.set({
		...current,
		status: "paused"
	});
}
function resumeAgent() {
	const current = $remoteAgentStatus.get();
	if (current.status === "paused") $remoteAgentStatus.set({
		...current,
		status: "running"
	});
}
function restartAgent() {
	stopAgent();
	setTimeout(() => startAgent(), 500);
}
function refreshLogs() {
	$remoteLoading.set(true);
	$remoteLoading.set(false);
}
function setLogLevelFilter(level) {
	$remoteLogLevelFilter.set(level);
}
function getFilteredLogs() {
	const level = $remoteLogLevelFilter.get();
	if (level === "all") return $remoteLogs.get();
	return $remoteLogs.get().filter((l) => l.level === level);
}
function refreshTasks() {
	$remoteLoading.set(true);
	$remoteLoading.set(false);
}
//#endregion
export { stopAgent as C, startAgent as S, updateInstanceLatency as T, refreshTasks as _, $remoteLoading as a, resumeAgent as b, $remoteTasks as c, disconnect as d, getActiveInstance as f, refreshLogs as g, reconnect as h, $remoteInstances as i, addRemoteInstance as l, pauseAgent as m, $remoteAgentStatus as n, $remoteLogLevelFilter as o, getFilteredLogs as p, $remoteConnected as r, $remoteLogs as s, $activeInstanceId as t, connect as u, removeRemoteInstance as v, updateInstanceHealth as w, setLogLevelFilter as x, restartAgent as y };

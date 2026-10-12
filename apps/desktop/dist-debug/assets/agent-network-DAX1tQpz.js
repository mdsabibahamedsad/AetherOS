import { Qa as atom, Xa as init_nanostores } from "./index-B_yd1pEX.js";
//#region src/store/agent-network.ts
init_nanostores();
var $networkAgents = /* @__PURE__ */ atom([]);
var $networkTasks = /* @__PURE__ */ atom([]);
var $networkLoading = /* @__PURE__ */ atom(false);
var $networkError = /* @__PURE__ */ atom(null);
var $networkSection = /* @__PURE__ */ atom("network");
var $emergencyStopped = /* @__PURE__ */ atom(false);
function setNetworkAgents(agents) {
	$networkAgents.set(agents);
}
function setNetworkTasks(tasks) {
	$networkTasks.set(tasks);
}
function setNetworkLoading(loading) {
	$networkLoading.set(loading);
}
function setNetworkError(error) {
	$networkError.set(error);
}
function setNetworkSection(section) {
	$networkSection.set(section);
}
function setEmergencyStopped(stopped) {
	$emergencyStopped.set(stopped);
	if (stopped) $networkError.set("STOP ALL REMOTE AGENTS active — new delegation held in UI.");
	else $networkError.set(null);
}
//#endregion
export { $emergencyStopped, $networkAgents, $networkError, $networkLoading, $networkSection, $networkTasks, setEmergencyStopped, setNetworkAgents, setNetworkError, setNetworkLoading, setNetworkSection, setNetworkTasks };

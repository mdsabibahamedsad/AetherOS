//#region src/lib/agent-network-client.ts
async function networkList(requestGateway) {
	return (await requestGateway("agent.network.list", {})).agents ?? [];
}
async function networkDiscover(requestGateway, url) {
	return requestGateway("agent.network.discover", { url });
}
async function networkInfo(requestGateway, id) {
	return requestGateway("agent.network.info", { id });
}
async function networkVerify(requestGateway, id) {
	return requestGateway("agent.network.verify", { id });
}
async function networkTrust(requestGateway, id, level) {
	return requestGateway("agent.network.trust", {
		id,
		level
	});
}
async function networkBlock(requestGateway, id) {
	await requestGateway("agent.network.block", { id });
}
async function networkRevoke(requestGateway, id) {
	await requestGateway("agent.network.revoke", { id });
}
async function networkConnect(requestGateway, id) {
	return requestGateway("agent.network.connect", { id });
}
async function networkDelegate(requestGateway, id, task, permissions = ["agent.task.submit"], data_scope = "internal") {
	return requestGateway("agent.network.delegate", {
		id,
		task,
		permissions,
		data_scope
	});
}
async function networkTasks(requestGateway) {
	return requestGateway("agent.network.tasks", {});
}
async function networkCancel(requestGateway, task) {
	await requestGateway("agent.network.cancel", { task });
}
async function networkActivity(requestGateway, limit = 100) {
	return (await requestGateway("agent.network.activity", { limit })).events ?? [];
}
async function networkSecurity(requestGateway) {
	return requestGateway("agent.network.security", {});
}
//#endregion
export { networkActivity, networkBlock, networkCancel, networkConnect, networkDelegate, networkDiscover, networkInfo, networkList, networkRevoke, networkSecurity, networkTasks, networkTrust, networkVerify };

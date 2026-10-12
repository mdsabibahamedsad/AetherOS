//#region src/lib/agent-marketplace-client.ts
async function marketSearch(requestGateway, query, opts = {}) {
	return requestGateway("marketplace.search", {
		query,
		...opts
	});
}
async function marketAgent(requestGateway, id) {
	return requestGateway("marketplace.agent.get", { id });
}
async function marketService(requestGateway, id) {
	return requestGateway("marketplace.service.get", { id });
}
async function marketCompare(requestGateway, agent_ids, query = "") {
	return requestGateway("marketplace.compare", {
		agent_ids,
		query
	});
}
async function marketQuote(requestGateway, quote) {
	return requestGateway("marketplace.quote", { quote });
}
async function marketContractCreate(requestGateway, contract) {
	return requestGateway("marketplace.contract.create", { contract });
}
async function marketContractApprove(requestGateway, id) {
	return requestGateway("marketplace.contract.approve", { id });
}
async function marketDelegate(requestGateway, task, selection, approved_by = "", auto = false) {
	return requestGateway("marketplace.delegate", {
		task,
		selection,
		approved_by,
		auto
	});
}
async function marketTaskStatus(requestGateway, id) {
	return requestGateway("marketplace.task.status", { id });
}
async function marketTransactions(requestGateway, contract_id = "") {
	return requestGateway("marketplace.transaction.get", { contract_id });
}
async function marketReputation(requestGateway, id) {
	return requestGateway("marketplace.reputation.get", { id });
}
async function marketTrust(requestGateway, id) {
	return requestGateway("marketplace.trust.get", { id });
}
async function marketBudget(requestGateway, scope = "user", scope_id = "") {
	return requestGateway("marketplace.budget.get", {
		scope,
		scope_id
	});
}
async function marketPolicy(requestGateway) {
	return requestGateway("marketplace.policy.get", {});
}
async function marketPolicyUpdate(requestGateway, preferences) {
	return requestGateway("marketplace.policy.update", { preferences });
}
async function marketDispute(requestGateway, dispute) {
	return requestGateway("marketplace.dispute.create", { dispute });
}
//#endregion
export { marketAgent, marketBudget, marketCompare, marketContractApprove, marketContractCreate, marketDelegate, marketDispute, marketPolicy, marketPolicyUpdate, marketQuote, marketReputation, marketSearch, marketService, marketTaskStatus, marketTransactions, marketTrust };

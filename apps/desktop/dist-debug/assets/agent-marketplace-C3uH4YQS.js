import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { t as __vitePreload } from "./preload-helper-CaB_JTFv.js";
import { Di as notify, La as Button, O as Badge, Oi as notifyError, Qa as atom, Xa as init_nanostores, Ya as useStore, ao as require_jsx_runtime, ni as Input, oo as require_react } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/store/agent-marketplace.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
init_nanostores();
var $marketHits = /* @__PURE__ */ atom([]);
var $marketQuery = /* @__PURE__ */ atom("");
var $marketDelegations = /* @__PURE__ */ atom([]);
var $marketLedger = /* @__PURE__ */ atom(null);
var $marketBudget = /* @__PURE__ */ atom(null);
var $marketPolicy = /* @__PURE__ */ atom(null);
var $marketLoading = /* @__PURE__ */ atom(false);
var $marketError = /* @__PURE__ */ atom(null);
var $marketSection = /* @__PURE__ */ atom("discover");
var $marketStopped = /* @__PURE__ */ atom(false);
function setMarketHits(hits) {
	$marketHits.set(hits);
}
function setMarketQuery(query) {
	$marketQuery.set(query);
}
function addMarketDelegation(result) {
	$marketDelegations.set([result, ...$marketDelegations.get()].slice(0, 200));
}
function setMarketLedger(ledger) {
	$marketLedger.set(ledger);
}
function setMarketBudget(budget) {
	$marketBudget.set(budget);
}
function setMarketPolicy(policy) {
	$marketPolicy.set(policy);
}
function setMarketLoading(loading) {
	$marketLoading.set(loading);
}
function setMarketError(error) {
	$marketError.set(error);
}
function setMarketSection(section) {
	$marketSection.set(section);
}
function setMarketStopped(stopped) {
	$marketStopped.set(stopped);
	if (stopped) $marketError.set("STOP ALL MARKETPLACE ACTIVITY active — new delegations and payments held.");
	else $marketError.set(null);
}
//#endregion
//#region src/app/agent-marketplace/index.tsx
var import_jsx_runtime = require_jsx_runtime();
var SECTIONS = [
	{
		id: "discover",
		label: "Discover"
	},
	{
		id: "recommended",
		label: "Recommended"
	},
	{
		id: "agents",
		label: "Agents"
	},
	{
		id: "services",
		label: "Services"
	},
	{
		id: "reputation",
		label: "Reputation"
	},
	{
		id: "contracts",
		label: "Contracts"
	},
	{
		id: "transactions",
		label: "Transactions"
	},
	{
		id: "budgets",
		label: "Budgets"
	},
	{
		id: "disputes",
		label: "Disputes"
	},
	{
		id: "security",
		label: "Security"
	},
	{
		id: "trust",
		label: "Trust"
	}
];
function fmtMoney(minor, currency = "USD") {
	if (minor == null) return "quote required";
	return `${(minor / 100).toFixed(2)} ${currency}`;
}
function AgentMarketplaceView({ requestGateway }) {
	const hits = useStore($marketHits);
	const query = useStore($marketQuery);
	const delegations = useStore($marketDelegations);
	const ledger = useStore($marketLedger);
	const budget = useStore($marketBudget);
	const policy = useStore($marketPolicy);
	const loading = useStore($marketLoading);
	const error = useStore($marketError);
	const section = useStore($marketSection);
	const stopped = useStore($marketStopped);
	const [detail, setDetail] = (0, import_react.useState)(null);
	const [detailKind, setDetailKind] = (0, import_react.useState)(null);
	const runSearch = async () => {
		if (!query.trim()) return;
		const c = await __vitePreload(() => import("./agent-marketplace-client-fhjxDetP.js"), [], import.meta.url);
		setMarketLoading(true);
		try {
			const res = await c.marketSearch(requestGateway, query.trim());
			setMarketHits(res.hits);
			setMarketError(null);
			if (res.hits.length === 0) notify({
				title: "Marketplace",
				message: "No matching services — constraints eliminated all candidates"
			});
		} catch (e) {
			setMarketError(e instanceof Error ? e.message : String(e));
		} finally {
			setMarketLoading(false);
		}
	};
	const openDetail = async (kind, id) => {
		try {
			const c = await __vitePreload(() => import("./agent-marketplace-client-fhjxDetP.js"), [], import.meta.url);
			setDetail(kind === "agent" ? await c.marketAgent(requestGateway, id) : await c.marketService(requestGateway, id));
			setDetailKind(kind);
		} catch (e) {
			notifyError(e instanceof Error ? e.message : String(e), "Marketplace");
		}
	};
	const refreshOps = async () => {
		try {
			const c = await __vitePreload(() => import("./agent-marketplace-client-fhjxDetP.js"), [], import.meta.url);
			setMarketLedger(await c.marketTransactions(requestGateway));
			setMarketBudget(await c.marketBudget(requestGateway));
			setMarketPolicy(await c.marketPolicy(requestGateway));
			setMarketError(null);
		} catch (e) {
			setMarketError(e instanceof Error ? e.message : String(e));
		}
	};
	const delegateTo = async (hit) => {
		try {
			const res = await (await __vitePreload(() => import("./agent-marketplace-client-fhjxDetP.js"), [], import.meta.url)).marketDelegate(requestGateway, {
				summary: query || `Marketplace task via ${hit.service_id}`,
				data_class: "INTERNAL",
				verification_requirements: ["schema"],
				payment_provider: "none"
			}, {
				service_id: hit.service_id,
				agent_id: hit.agent_id
			});
			addMarketDelegation(res);
			if (res.status === "awaiting_approval") notify({
				title: "Marketplace",
				message: `Approval required (${res.tier}, ${fmtMoney(res.amount_minor, res.currency)})`
			});
			else notify({
				title: "Marketplace",
				message: `Delegated: ${res.delegation_id}`
			});
		} catch (e) {
			notifyError(e instanceof Error ? e.message : String(e), "Marketplace");
		}
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageShell, { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Agent Marketplace" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Discover, evaluate, delegate to, verify, and settle with external agents. Listings are UNVERIFIED until reconciled. Money never moves without policy, budget, and explicit authorization. Empty states are real — never simulated." })] }),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex flex-wrap gap-2",
			children: [
				SECTIONS.map((s) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => void setMarketSection(s.id),
					size: "sm",
					variant: section === s.id ? "default" : "outline",
					children: s.label
				}, s.id)),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => void refreshOps(),
					size: "sm",
					variant: "outline",
					children: "Operations"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => void setMarketStopped(!stopped),
					size: "sm",
					variant: stopped ? "default" : "destructive",
					children: stopped ? "Resume marketplace" : "Stop all marketplace activity"
				})
			]
		}),
		error && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-destructive",
			children: error
		}),
		(section === "discover" || section === "recommended") && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
				onChange: (e) => setMarketQuery(e.target.value),
				onKeyDown: (e) => {
					if (e.key === "Enter") runSearch();
				},
				placeholder: "What do I need? e.g. analyze financial spreadsheets",
				value: query
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				disabled: loading,
				onClick: () => void runSearch(),
				children: loading ? "Searching…" : "Search"
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-2",
			children: [hits.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-muted-foreground",
				children: "No results yet. Search states what you need; only real registry services match."
			}), hits.map((h) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "rounded border p-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "font-mono text-sm",
								children: h.service_id
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								variant: h.exact ? "default" : "secondary",
								children: h.exact ? "EXACT" : `KW ${h.keyword_score.toFixed(2)}`
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								variant: "outline",
								children: h.source.toUpperCase()
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "mt-1 text-sm text-muted-foreground",
						children: ["agent: ", h.agent_id]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
						className: "mt-1 list-disc pl-5 text-xs text-muted-foreground",
						children: h.reasons.slice(0, 4).map((r, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: r }, i))
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mt-2 flex flex-wrap gap-2",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => void openDetail("service", h.service_id),
								size: "sm",
								variant: "outline",
								children: "Inspect"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => void openDetail("agent", h.agent_id),
								size: "sm",
								variant: "outline",
								children: "Agent"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								disabled: stopped,
								onClick: () => void delegateTo(h),
								size: "sm",
								children: "Delegate"
							})
						]
					})
				]
			}, `${h.source}:${h.service_id}`))]
		})] }),
		detail && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "rounded border p-3",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "text-sm font-semibold",
					children: detailKind === "agent" ? "Agent detail" : "Service detail"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => setDetail(null),
					size: "sm",
					variant: "outline",
					children: "Close"
				})]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
				className: "mt-2 max-h-96 overflow-auto text-xs",
				children: JSON.stringify(detail, null, 2)
			})]
		}),
		(section === "transactions" || section === "budgets" || section === "contracts") && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-2",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded border p-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm font-semibold",
						children: "Ledger + accounting (append-only, hash-chained)"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
						className: "mt-1 max-h-64 overflow-auto text-xs",
						children: ledger ? JSON.stringify(ledger, null, 2) : "Press Operations to load real ledger state."
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded border p-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm font-semibold",
						children: "Budget usage"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
						className: "mt-1 max-h-64 overflow-auto text-xs",
						children: budget ? JSON.stringify(budget, null, 2) : "Press Operations to load real budget state."
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded border p-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm font-semibold",
						children: "Policy + flags"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
						className: "mt-1 max-h-64 overflow-auto text-xs",
						children: policy ? JSON.stringify(policy, null, 2) : "Press Operations to load effective policy."
					})]
				})
			]
		}),
		section === "disputes" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-muted-foreground",
			children: "Open disputes from the CLI (`aetheros agent-marketplace disputes --open-file …`) or the dispute IPC channel. Evidence is immutable and referenced by id."
		}),
		(section === "security" || section === "trust" || section === "reputation") && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-muted-foreground",
			children: "Select Inspect on a service or Agent on a hit to see listing verification, scan level (scanned / partially scanned / not scanned), trust dimensions with provenance, and reputation metrics with sample counts. Metrics without samples read “insufficient evidence” — never a percentage."
		}),
		delegations.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm font-semibold",
				children: "This session's delegations"
			}), delegations.map((d) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "rounded border p-3",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "font-mono text-sm",
							children: d.delegation_id ?? d.contract_id
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							variant: "outline",
							children: (d.status ?? "unknown").toUpperCase()
						}),
						d.amount_minor != null && d.amount_minor > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-xs",
							children: fmtMoney(d.amount_minor, d.currency)
						})
					]
				})
			}, d.delegation_id ?? d.contract_id))]
		})
	] });
}
//#endregion
export { AgentMarketplaceView };

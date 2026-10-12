import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { t as $gateway } from "./gateway-D1xRY-ux.js";
import { O as Badge, S as ScrollArea, Ya as useStore, ao as require_jsx_runtime, oo as require_react } from "./index-B_yd1pEX.js";
import { t as Card } from "./card-CXjwIosc.js";
import { t as EmptyState } from "./empty-state-DbK8L0dQ.js";
//#region src/lib/swarm-client.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
async function swarmStart(requestGateway, goal, opts = {}) {
	return requestGateway("swarm.start", {
		goal,
		...opts
	});
}
async function swarmStatus(requestGateway, runId) {
	return requestGateway("swarm.status", { run_id: runId });
}
async function swarmStop(requestGateway, runId) {
	await requestGateway("swarm.stop", { run_id: runId });
}
async function swarmEvents(requestGateway, runId, afterSeq = 0) {
	return (await requestGateway("swarm.events", {
		run_id: runId,
		after_seq: afterSeq
	})).events ?? [];
}
async function swarmTrace(requestGateway, runId) {
	return (await requestGateway("swarm.trace", { run_id: runId })).trace ?? {};
}
async function swarmApprove(requestGateway, requestId, approved) {
	await requestGateway("swarm.approve", {
		request_id: requestId,
		approved
	});
}
//#endregion
//#region src/app/swarm-center/index.tsx
var import_jsx_runtime = require_jsx_runtime();
function useGateway() {
	const client = useStore($gateway);
	return client?.request?.bind(client) ?? null;
}
function SwarmCenter() {
	const requestGateway = useGateway();
	const [tab, setTab] = (0, import_react.useState)("run");
	const [goal, setGoal] = (0, import_react.useState)("");
	const [forceSingle, setForceSingle] = (0, import_react.useState)(false);
	const [run, setRun] = (0, import_react.useState)(null);
	const [events, setEvents] = (0, import_react.useState)([]);
	const [trace, setTrace] = (0, import_react.useState)(null);
	const [selectedTask, setSelectedTask] = (0, import_react.useState)("");
	const [selectedAgent, setSelectedAgent] = (0, import_react.useState)("");
	const [approvalId, setApprovalId] = (0, import_react.useState)("");
	const [status, setStatus] = (0, import_react.useState)("idle");
	const [error, setError] = (0, import_react.useState)("");
	if (requestGateway === null) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
		className: "h-full",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mx-auto max-w-4xl p-6",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
				description: "Connect the gateway to plan and inspect live swarm runs.",
				icon: "hub",
				title: "Swarm backend unavailable"
			})
		})
	});
	async function start() {
		if (!requestGateway || !goal.trim()) return;
		setStatus("loading");
		try {
			setRun(await swarmStart(requestGateway, goal.trim(), { force_single: forceSingle }));
			setStatus("idle");
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setStatus("error");
		}
	}
	async function refresh() {
		if (!requestGateway || !run) return;
		try {
			setRun(await swarmStatus(requestGateway, run.run_id));
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setStatus("error");
		}
	}
	async function loadEvents() {
		if (!requestGateway || !run) return;
		try {
			setEvents(await swarmEvents(requestGateway, run.run_id));
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setStatus("error");
		}
	}
	async function loadTrace() {
		if (!requestGateway || !run) return;
		try {
			setTrace(await swarmTrace(requestGateway, run.run_id));
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setStatus("error");
		}
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
		className: "h-full",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mx-auto max-w-7xl space-y-6 p-6",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "p-6",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "text-2xl font-semibold tracking-tight",
							children: "Swarm Center"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-(--ui-text-tertiary) mb-4",
							children: "Live multi-agent runs. Every value comes from the backend."
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mb-3 flex gap-2",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									className: "flex-1 border px-2 py-1 text-xs",
									onChange: (e) => setGoal(e.target.value),
									placeholder: "Goal, e.g. Research three static-site generators then compare them",
									value: goal
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
									className: "flex items-center gap-1 text-xs",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
										checked: forceSingle,
										onChange: (e) => setForceSingle(e.target.checked),
										type: "checkbox"
									}), "single-agent"]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "text-xs underline",
									onClick: () => void start(),
									children: status === "loading" ? "Planning…" : "Plan run"
								}),
								run && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "text-xs underline",
									onClick: () => void refresh(),
									children: "Refresh"
								}),
								run && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "text-xs text-red-400 underline",
									onClick: () => requestGateway && void swarmStop(requestGateway, run.run_id).then(() => void refresh()),
									children: "Stop"
								})
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex gap-2 text-xs",
							children: [
								"run",
								"tasks",
								"agents",
								"events",
								"trace"
							].map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: tab === t ? "font-semibold underline" : "text-(--ui-text-tertiary)",
								onClick: () => {
									setTab(t);
									if (t === "events") loadEvents();
									if (t === "trace") loadTrace();
								},
								children: t
							}, t))
						})
					]
				}),
				status === "error" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "p-4 text-xs text-red-400",
					children: ["Swarm request failed: ", error]
				}),
				!run ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
					description: "Enter a goal above to get a live orchestration plan.",
					icon: "hub",
					title: "No run planned"
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
					tab === "run" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
						className: "p-4 text-xs",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mb-2 flex items-center gap-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: "text-[8px]",
										variant: "outline",
										children: run.mode
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: "text-[8px]",
										variant: "outline",
										children: run.topology
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: "text-[8px]",
										variant: "outline",
										children: run.status
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "text-(--ui-text-tertiary)",
										children: ["roles: ", run.roles.join(", ")]
									})
								]
							}),
							run.final ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
								className: "whitespace-pre-wrap text-[11px]",
								children: JSON.stringify(run.final, null, 2)
							}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "text-(--ui-text-tertiary)",
								children: [
									"Planned with ",
									run.tasks.length,
									" tasks and ",
									run.agents.length,
									" agents. Execution state refreshes via Refresh."
								]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-3 flex gap-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
										className: "border px-2 py-1 text-xs",
										onChange: (e) => setApprovalId(e.target.value),
										placeholder: "Approval request id",
										value: approvalId
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
										className: "text-xs underline",
										onClick: () => requestGateway && approvalId && void swarmApprove(requestGateway, approvalId, true),
										children: "Approve"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
										className: "text-xs text-red-400 underline",
										onClick: () => requestGateway && approvalId && void swarmApprove(requestGateway, approvalId, false),
										children: "Reject"
									})
								]
							})
						]
					}),
					tab === "tasks" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Card, {
						className: "p-4",
						children: run.tasks.map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "border-b border-(--ui-border) px-2 py-1.5 text-xs last:border-0",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: "flex w-full items-center gap-2 text-left",
								onClick: () => setSelectedTask(selectedTask === t.id ? "" : t.id),
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "flex-1 truncate font-medium",
										children: t.goal
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: "text-[8px]",
										variant: "outline",
										children: t.role
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: "text-[8px]",
										variant: "outline",
										children: t.state
									})
								]
							}), selectedTask === t.id && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
								className: "mt-1 whitespace-pre-wrap text-[11px] text-(--ui-text-tertiary)",
								children: JSON.stringify(t, null, 2)
							})]
						}, t.id))
					}),
					tab === "agents" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Card, {
						className: "p-4",
						children: run.agents.map((a) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "border-b border-(--ui-border) px-2 py-1.5 text-xs last:border-0",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: "flex w-full items-center gap-2 text-left",
								onClick: () => setSelectedAgent(selectedAgent === a.id ? "" : a.id),
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "flex-1 truncate font-medium",
										children: a.role
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: "text-[8px]",
										variant: "outline",
										children: a.status
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "text-[10px] text-(--ui-text-tertiary)",
										children: [
											a.tokens,
											" tok / $",
											a.cost.toFixed(4)
										]
									})
								]
							}), selectedAgent === a.id && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
								className: "mt-1 whitespace-pre-wrap text-[11px] text-(--ui-text-tertiary)",
								children: JSON.stringify(a, null, 2)
							})]
						}, a.id))
					}),
					tab === "events" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Card, {
						className: "p-4",
						children: events.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
							description: "Events stream here with sequence numbers.",
							icon: "activity",
							title: "No events yet"
						}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "space-y-1 text-xs",
							children: events.map((e) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "border-b border-(--ui-border) py-1 last:border-0",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "text-(--ui-text-tertiary)",
										children: ["#", e.seq]
									}),
									" ",
									e.kind,
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "ml-2 text-[10px] text-(--ui-text-tertiary)",
										children: (/* @__PURE__ */ new Date(e.at * 1e3)).toLocaleTimeString()
									})
								]
							}, e.seq))
						})
					}),
					tab === "trace" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Card, {
						className: "p-4",
						children: !trace ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
							description: "Open this tab to load the live trace tree.",
							icon: "info",
							title: "No trace loaded"
						}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
							className: "whitespace-pre-wrap text-[11px]",
							children: JSON.stringify(trace, null, 2)
						})
					})
				] })
			]
		})
	});
}
//#endregion
export { SwarmCenter };

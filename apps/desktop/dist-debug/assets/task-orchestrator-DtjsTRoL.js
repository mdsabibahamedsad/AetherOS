import { a as __toESM, i as __toCommonJS, n as __esmMin, r as __exportAll } from "./chunk-DKxDMwdo.js";
import { La as Button, O as Badge$1, Qa as atom, Ra as cn, Xa as init_nanostores, Ya as useStore, Za as computed, ao as require_jsx_runtime, k as Label, ni as Input, oo as require_react } from "./index-B_yd1pEX.js";
//#region src/store/task-orchestrator.ts
var task_orchestrator_exports = /* @__PURE__ */ __exportAll({
	$currentExecutionState: () => $currentExecutionState,
	$currentPlan: () => $currentPlan,
	$orchestrator: () => $orchestrator,
	$pendingApprovals: () => $pendingApprovals,
	$runningAgentActivities: () => $runningAgentActivities,
	addAgentActivity: () => addAgentActivity,
	addApprovalRequest: () => addApprovalRequest,
	addCheckpoint: () => addCheckpoint,
	createPlan: () => createPlan,
	removePlan: () => removePlan,
	respondApproval: () => respondApproval,
	setCurrentPlan: () => setCurrentPlan,
	setLimits: () => setLimits,
	setOfflineMode: () => setOfflineMode,
	updateAgentActivity: () => updateAgentActivity,
	updateExecutionState: () => updateExecutionState,
	updateTask: () => updateTask
});
function createPlan(goal) {
	const planId = generateId();
	const segments = goal.split(/[.?!\n]/).map((s) => s.trim()).filter((s) => s.length > 0).slice(0, 10);
	const plan = {
		id: planId,
		goal,
		description: goal,
		subtasks: segments.map((seg, i) => ({
			id: generateId(),
			name: seg.slice(0, 80),
			description: seg,
			agentRole: inferRole(seg),
			model: "",
			provider: "",
			tools: inferTools(seg),
			dependencies: i > 0 ? [planId + "-task-" + (i - 1)] : [],
			executionMode: "sequential",
			status: "pending",
			progress: 0,
			result: null,
			error: "",
			retryCount: 0,
			maxRetries: 3,
			requiresApproval: checkApproval(seg),
			estimatedDuration: estimateDuration(seg),
			actualDuration: 0,
			cost: 0,
			createdAt: Date.now(),
			startedAt: 0,
			completedAt: 0
		})),
		dependencies: {},
		requiredTools: [],
		requiredAgents: [],
		requiredPermissions: [],
		estimatedCost: segments.length * .01,
		estimatedTime: segments.reduce((sum, seg) => sum + estimateDuration(seg), 0),
		riskLevel: assessRisk(goal),
		createdAt: Date.now(),
		executionGraph: {
			nodes: [],
			edges: [],
			levels: []
		}
	};
	plan.subtasks.forEach((t, i) => {
		plan.executionGraph.nodes.push({
			id: t.id,
			name: t.name,
			status: t.status,
			role: t.agentRole
		});
		if (i > 0) plan.executionGraph.edges.push({
			from: plan.subtasks[i - 1].id,
			to: t.id
		});
	});
	plan.executionGraph.levels = buildLevels(plan.subtasks);
	const state = $orchestrator.get();
	$orchestrator.set({
		...state,
		plans: [...state.plans, plan],
		currentPlanId: planId
	});
	return plan;
}
function setCurrentPlan(planId) {
	const state = $orchestrator.get();
	$orchestrator.set({
		...state,
		currentPlanId: planId
	});
}
function updateTask(planId, taskId, updates) {
	const state = $orchestrator.get();
	const plans = state.plans.map((p) => {
		if (p.id !== planId) return p;
		return {
			...p,
			subtasks: p.subtasks.map((t) => t.id === taskId ? {
				...t,
				...updates
			} : t)
		};
	});
	$orchestrator.set({
		...state,
		plans
	});
}
function updateExecutionState(planId, updates) {
	const state = $orchestrator.get();
	$orchestrator.set({
		...state,
		executionStates: {
			...state.executionStates,
			[planId]: {
				...state.executionStates[planId] ?? createExecutionState(planId),
				...updates
			}
		}
	});
}
function addAgentActivity(activity) {
	const state = $orchestrator.get();
	$orchestrator.set({
		...state,
		agentActivities: [...state.agentActivities.slice(-200), activity],
		activeAgents: state.agentActivities.filter((a) => a.status === "running" || a.status === "thinking").length + 1
	});
}
function updateAgentActivity(agentId, updates) {
	const state = $orchestrator.get();
	$orchestrator.set({
		...state,
		agentActivities: state.agentActivities.map((a) => a.agentId === agentId ? {
			...a,
			...updates,
			updatedAt: Date.now()
		} : a)
	});
}
function addCheckpoint(checkpoint) {
	const state = $orchestrator.get();
	$orchestrator.set({
		...state,
		checkpoints: [...state.checkpoints, checkpoint]
	});
}
function addApprovalRequest(request) {
	const state = $orchestrator.get();
	$orchestrator.set({
		...state,
		approvalRequests: [...state.approvalRequests, request]
	});
}
function respondApproval(requestId, response) {
	const state = $orchestrator.get();
	$orchestrator.set({
		...state,
		approvalRequests: state.approvalRequests.map((r) => r.id === requestId ? {
			...r,
			status: response
		} : r)
	});
}
function setOfflineMode(offline) {
	const state = $orchestrator.get();
	$orchestrator.set({
		...state,
		offlineMode: offline
	});
}
function setLimits(limits) {
	const state = $orchestrator.get();
	$orchestrator.set({
		...state,
		limits: {
			...state.limits,
			...limits
		}
	});
}
function removePlan(planId) {
	const state = $orchestrator.get();
	$orchestrator.set({
		...state,
		plans: state.plans.filter((p) => p.id !== planId),
		currentPlanId: state.currentPlanId === planId ? null : state.currentPlanId,
		executionStates: Object.fromEntries(Object.entries(state.executionStates).filter(([k]) => k !== planId))
	});
}
function createExecutionState(planId) {
	return {
		planId,
		currentTaskId: "",
		completedTasks: [],
		pendingTasks: [],
		failedTasks: [],
		runningTasks: [],
		paused: false,
		cancelled: false,
		startedAt: Date.now(),
		updatedAt: Date.now()
	};
}
function inferRole(text) {
	const lower = text.toLowerCase();
	if (/research|search|investigate|find|gather/i.test(lower)) return "research";
	if (/code|develop|program|implement|build/i.test(lower)) return "developer";
	if (/write|draft|compose|author|document/i.test(lower)) return "writer";
	if (/browse|navigate|scrape|web/i.test(lower)) return "browser";
	if (/test|verify|validate|qa/i.test(lower)) return "qa";
	if (/deploy|release|publish/i.test(lower)) return "deployment";
	if (/security|audit|threat/i.test(lower)) return "security";
	if (/creative|design|art|generate|imagine/i.test(lower)) return "creative";
	if (/data|analyze|statistic|dashboard|report/i.test(lower)) return "data";
	if (/email|message|communicate|notify|send/i.test(lower)) return "communication";
	if (/review|check|proofread|examine|inspect/i.test(lower)) return "review";
	if (/file|save|open|read/i.test(lower)) return "file";
	if (/plan|organize|coordinate/i.test(lower)) return "planner";
	return "coordinator";
}
function inferTools(text) {
	const tools = [];
	const lower = text.toLowerCase();
	if (/search|research|web|find/i.test(lower)) tools.push("web_search");
	if (/browse|navigate|web page/i.test(lower)) tools.push("browser_navigate");
	if (/file|save|read|write/i.test(lower)) tools.push("file_operations");
	if (/terminal|command|run|shell/i.test(lower)) tools.push("terminal");
	if (/code|develop|program/i.test(lower)) tools.push("code_execution");
	if (/email|send/i.test(lower)) tools.push("send_message");
	if (/image|picture|vision/i.test(lower)) tools.push("vision");
	if (/data|analyze|chart/i.test(lower)) tools.push("data_analysis");
	return tools;
}
function checkApproval(text) {
	const lower = text.toLowerCase();
	return /delete|remove|destroy|payment|spend|buy|install|modify system|access sensitive/i.test(lower);
}
function estimateDuration(text) {
	const lower = text.toLowerCase();
	if (/research|investigate/i.test(lower)) return 120;
	if (/code|develop|implement|build/i.test(lower)) return 300;
	if (/browse|scrape/i.test(lower)) return 60;
	if (/analyze|data|report/i.test(lower)) return 180;
	if (/write|draft|compose/i.test(lower)) return 120;
	return 60;
}
function assessRisk(text) {
	const lower = text.toLowerCase();
	const count = [
		/delete/,
		/destroy/,
		/payment/,
		/install/,
		/permission/
	].filter((r) => r.test(lower)).length;
	if (count >= 2) return "high";
	if (count >= 1) return "medium";
	return "low";
}
function buildLevels(tasks) {
	const levels = [];
	const remaining = new Set(tasks.map((t) => t.id));
	const completed = /* @__PURE__ */ new Set();
	while (remaining.size > 0) {
		const level = [];
		for (const tid of remaining) {
			const task = tasks.find((t) => t.id === tid);
			if (task && task.dependencies.every((d) => completed.has(d))) level.push(tid);
		}
		if (level.length === 0) level.push(...remaining);
		levels.push(level);
		for (const tid of level) {
			remaining.delete(tid);
			completed.add(tid);
		}
	}
	return levels;
}
function generateId() {
	return "task_" + Math.random().toString(36).slice(2, 10);
}
var $orchestrator, $currentPlan, $currentExecutionState, $runningAgentActivities, $pendingApprovals;
var init_task_orchestrator = __esmMin((() => {
	init_nanostores();
	$orchestrator = /* @__PURE__ */ atom({
		plans: [],
		currentPlanId: null,
		executionStates: {},
		agentActivities: [],
		checkpoints: [],
		approvalRequests: [],
		activeAgents: 0,
		offlineMode: false,
		limits: {
			maxSteps: 100,
			maxTime: 3600,
			maxCost: 10,
			maxTokens: 1e6,
			maxSubAgents: 10,
			maxParallelTasks: 5,
			maxToolCalls: 500
		}
	});
	$currentPlan = /* @__PURE__ */ computed($orchestrator, (state) => {
		if (!state.currentPlanId) return null;
		return state.plans.find((p) => p.id === state.currentPlanId) ?? null;
	});
	$currentExecutionState = /* @__PURE__ */ computed($orchestrator, (state) => {
		if (!state.currentPlanId) return null;
		return state.executionStates[state.currentPlanId] ?? null;
	});
	$runningAgentActivities = /* @__PURE__ */ computed($orchestrator, (state) => state.agentActivities.filter((a) => a.status === "running" || a.status === "thinking"));
	$pendingApprovals = /* @__PURE__ */ computed($orchestrator, (state) => state.approvalRequests.filter((a) => a.status === "pending"));
}));
//#endregion
//#region src/app/task-orchestrator/agent-activity.tsx
init_task_orchestrator();
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var STATUS_CONFIG = {
	idle: {
		label: "Idle",
		color: "text-gray-500",
		icon: "○"
	},
	running: {
		label: "Running",
		color: "text-blue-500",
		icon: "▶"
	},
	thinking: {
		label: "Thinking",
		color: "text-purple-500",
		icon: "◉"
	},
	tool_called: {
		label: "Tool Called",
		color: "text-orange-500",
		icon: "⚙"
	},
	waiting: {
		label: "Waiting",
		color: "text-yellow-500",
		icon: "◷"
	},
	completed: {
		label: "Completed",
		color: "text-green-500",
		icon: "✓"
	},
	failed: {
		label: "Failed",
		color: "text-red-500",
		icon: "✗"
	},
	retrying: {
		label: "Retrying",
		color: "text-orange-500",
		icon: "↻"
	}
};
var ROLE_EMOJIS = {
	planner: "📋",
	developer: "💻",
	browser: "🌐",
	research: "🔍",
	writer: "✍️",
	creative: "🎨",
	data: "📊",
	coordinator: "🎯",
	security: "🛡️",
	qa: "✅",
	deployment: "🚀",
	memory: "🧠",
	communication: "📧",
	review: "👁",
	coding: "⚡",
	file: "📁"
};
function AgentActivityFeed({ activities }) {
	const displayed = (0, import_react.useMemo)(() => activities.slice(-100).reverse(), [activities]);
	const stats = (0, import_react.useMemo)(() => {
		return {
			running: activities.filter((a) => a.status === "running" || a.status === "thinking").length,
			completed: activities.filter((a) => a.status === "completed").length,
			failed: activities.filter((a) => a.status === "failed").length
		};
	}, [activities]);
	const activeByRole = (0, import_react.useMemo)(() => {
		const counts = {};
		for (const a of activities) if (a.status === "running" || a.status === "thinking") counts[a.role] = (counts[a.role] || 0) + 1;
		return counts;
	}, [activities]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-4xl",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mb-4 flex gap-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(MiniStat, {
						color: "text-blue-500",
						label: "Active",
						value: stats.running
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(MiniStat, {
						color: "text-green-500",
						label: "Completed",
						value: stats.completed
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(MiniStat, {
						color: "text-red-500",
						label: "Failed",
						value: stats.failed
					})
				]
			}),
			Object.keys(activeByRole).length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mb-4 rounded-lg border bg-muted/30 p-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "text-xs text-muted-foreground mb-2",
					children: "Active Agents by Role"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex flex-wrap gap-2",
					children: Object.entries(activeByRole).map(([role, count]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Badge$1, {
						className: "gap-1",
						variant: "outline",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "animate-pulse",
								children: ROLE_EMOJIS[role] ?? "🤖"
							}),
							role,
							" x",
							count
						]
					}, role))
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-0.5",
				children: displayed.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "py-12 text-center text-sm text-muted-foreground",
					children: "No agent activity yet"
				}) : displayed.map((activity, i) => {
					const cfg = STATUS_CONFIG[activity.status] ?? STATUS_CONFIG.idle;
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: cn("flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors", activity.status === "running" && "bg-blue-500/5", activity.status === "failed" && "bg-red-500/5", activity.status === "thinking" && "bg-purple-500/5"),
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: cn("w-4 text-center", cfg.color),
								children: cfg.icon
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-base shrink-0",
								children: ROLE_EMOJIS[activity.role] ?? "🤖"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex-1 min-w-0",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-2",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "font-medium truncate",
										children: activity.name
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: cn("text-xs", cfg.color),
										children: cfg.label
									})]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "text-xs text-muted-foreground",
									children: activity.message || `${activity.role} agent processing task ${activity.taskId.slice(0, 8)}`
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "text-right shrink-0",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "text-xs text-muted-foreground font-mono",
									children: activity.model
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "text-[10px] text-muted-foreground",
									children: activity.provider
								})]
							})
						]
					}, `${activity.agentId}-${activity.startedAt}-${i}`);
				})
			})
		]
	});
}
function MiniStat({ label, value, color }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "rounded-lg border px-3 py-2 text-center",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: cn("text-lg font-bold", color),
			children: value
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "text-[10px] text-muted-foreground",
			children: label
		})]
	});
}
//#endregion
//#region src/app/task-orchestrator/approval-panel.tsx
var ACTION_LABELS = {
	dangerous_action: "Dangerous Action",
	destructive_action: "Destructive Action",
	sensitive_data: "Sensitive Data",
	external_communication: "External Communication",
	payment: "Payment",
	account_change: "Account Change",
	permission_escalation: "Permission Escalation",
	uncertain_decision: "Uncertain Decision",
	file_write: "File Write",
	file_delete: "File Delete",
	network_access: "Network Access",
	code_execution: "Code Execution"
};
var ACTION_EMOJIS = {
	dangerous_action: "⚠️",
	destructive_action: "💥",
	sensitive_data: "🔒",
	external_communication: "📤",
	payment: "💰",
	account_change: "🔄",
	permission_escalation: "⬆️",
	uncertain_decision: "❓",
	file_write: "✏️",
	file_delete: "🗑️",
	network_access: "🌐",
	code_execution: "⚡"
};
function ApprovalPanel({ requests, onRespond }) {
	const pending = requests.filter((r) => r.status === "pending");
	const history = requests.filter((r) => r.status !== "pending");
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-4xl space-y-6",
		children: [pending.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex h-48 items-center justify-center rounded-lg border border-dashed",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "text-center",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm text-muted-foreground",
					children: "No pending approval requests"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-1 text-xs text-muted-foreground",
					children: "Approvals are requested when tasks require user permission"
				})]
			})
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "space-y-4",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
				className: "text-sm font-semibold text-muted-foreground uppercase tracking-wider",
				children: [
					"Pending Approvals (",
					pending.length,
					")"
				]
			}), pending.map((req) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "rounded-lg border border-yellow-500/30 bg-yellow-500/5 p-4",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-start gap-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-xl",
						children: "🔔"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex-1",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "font-semibold text-sm",
									children: "Approval Required"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge$1, {
									className: "text-yellow-600 border-yellow-500/30",
									variant: "outline",
									children: "Pending"
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-1 text-sm",
								children: req.description
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "mt-3 flex flex-wrap gap-2",
								children: req.actions.map((action) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Badge$1, {
									className: "gap-1 text-xs",
									variant: "outline",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: ACTION_EMOJIS[action] ?? "🔴" }), ACTION_LABELS[action] ?? action]
								}, action))
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-3 grid grid-cols-2 gap-4 text-xs text-muted-foreground",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-medium text-foreground",
											children: "Agent:"
										}),
										" ",
										req.agentName,
										" (",
										req.agentRole,
										")"
									] }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-medium text-foreground",
											children: "Task:"
										}),
										" ",
										req.taskName.slice(0, 60)
									] }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-medium text-foreground",
											children: "Requested:"
										}),
										" ",
										new Date(req.createdAt).toLocaleString()
									] })
								]
							}),
							Object.keys(req.details).length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-2 rounded-lg bg-muted/50 p-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "text-xs font-medium text-muted-foreground mb-1",
									children: "Details"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
									className: "text-xs text-muted-foreground overflow-auto max-h-24",
									children: JSON.stringify(req.details, null, 2)
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-4 flex items-center gap-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
										className: "bg-green-600 hover:bg-green-700 text-white",
										onClick: () => onRespond(req.id, "approved"),
										size: "sm",
										children: "✓ Approve Once"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
										className: "border-green-500/30 text-green-600",
										onClick: () => onRespond(req.id, "approved"),
										size: "sm",
										variant: "outline",
										children: "Approve Session"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
										className: "border-purple-500/30 text-purple-600",
										onClick: () => onRespond(req.id, "approved"),
										size: "sm",
										variant: "outline",
										children: "Always Allow"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
										className: "border-red-500/30 text-red-600",
										onClick: () => onRespond(req.id, "denied"),
										size: "sm",
										variant: "outline",
										children: "✗ Deny"
									})
								]
							})
						]
					})]
				})
			}, req.id))]
		}), history.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h4", {
			className: "mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wider",
			children: [
				"Approval History (",
				history.length,
				")"
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "space-y-1",
			children: history.slice(-20).reverse().map((req) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-3 rounded-lg border p-2 text-sm",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: cn("text-base", req.status === "approved" ? "" : ""),
						children: req.status === "approved" ? "✓" : "✗"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: cn("text-xs font-medium", req.status === "approved" ? "text-green-600" : "text-red-600"),
						children: req.status
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "flex-1 text-xs text-muted-foreground truncate",
						children: req.description.slice(0, 80)
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-[10px] text-muted-foreground",
						children: new Date(req.createdAt).toLocaleString()
					})
				]
			}, req.id))
		})] })]
	});
}
//#endregion
//#region src/app/task-orchestrator/checkpoint-view.tsx
function CheckpointView({ checkpoints, planId }) {
	const planCheckpoints = checkpoints.filter((c) => c.planId === planId);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-4xl",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mb-4 flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
					className: "text-sm font-semibold text-muted-foreground uppercase tracking-wider",
					children: ["Checkpoints ", planId ? `for plan ${planId.slice(0, 8)}` : ""]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: !planId,
						size: "sm",
						variant: "outline",
						children: "Save Checkpoint"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: planCheckpoints.length === 0,
						size: "sm",
						variant: "outline",
						children: "Restore Latest"
					})]
				})]
			}),
			planCheckpoints.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex h-48 items-center justify-center rounded-lg border border-dashed",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "text-center",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm text-muted-foreground",
						children: "No checkpoints saved yet"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 text-xs text-muted-foreground",
						children: "Checkpoints are created automatically during task execution"
					})]
				})
			}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-2",
				children: planCheckpoints.slice().reverse().map((cp) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between rounded-lg border p-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "h-2 w-2 rounded-full bg-green-500" }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "text-sm font-medium",
									children: ["Checkpoint ", cp.id.slice(0, 8)]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "text-xs text-muted-foreground font-mono",
									children: ["task: ", cp.taskId.slice(0, 8)]
								})
							]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-1 text-xs text-muted-foreground",
							children: [(/* @__PURE__ */ new Date(cp.timestamp * 1e3)).toLocaleString(), !!cp.state?.completedTasks && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
								" · ",
								Array.isArray(cp.state.completedTasks) ? cp.state.completedTasks.length : 0,
								" tasks completed"
							] })]
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							size: "sm",
							variant: "ghost",
							children: "Restore"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							className: "text-destructive",
							size: "sm",
							variant: "ghost",
							children: "Delete"
						})]
					})]
				}, cp.id))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-8",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
					className: "mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wider",
					children: "Checkpoint Actions"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid grid-cols-2 gap-3",
					children: [
						{
							label: "Pause & Save",
							desc: "Pause execution and save current state",
							disabled: false
						},
						{
							label: "Resume from Checkpoint",
							desc: "Restore execution from a saved checkpoint",
							disabled: planCheckpoints.length === 0
						},
						{
							label: "Cancel Execution",
							desc: "Stop all running tasks and save final state",
							disabled: false
						},
						{
							label: "Restart from Beginning",
							desc: "Clear all progress and start over",
							disabled: false
						}
					].map((action) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: cn("rounded-lg border p-3 text-left transition-colors hover:bg-muted/50", action.disabled && "opacity-40 cursor-not-allowed"),
						disabled: action.disabled,
						type: "button",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: action.label
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-muted-foreground mt-0.5",
							children: action.desc
						})]
					}, action.label))
				})]
			})
		]
	});
}
//#endregion
//#region src/app/task-orchestrator/execution-graph.tsx
function ExecutionGraphView({ plan, executionState }) {
	const taskMap = (0, import_react.useMemo)(() => {
		return new Map((plan?.subtasks ?? []).map((t) => [t.id, t]));
	}, [plan?.subtasks]);
	if (!plan) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex h-48 items-center justify-center",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-muted-foreground",
			children: "Select a plan to view its execution graph"
		})
	});
	const { levels, edges } = plan.executionGraph;
	const completedSet = new Set(executionState?.completedTasks ?? []);
	const failedSet = new Set(executionState?.failedTasks ?? []);
	const runningSet = new Set(executionState?.runningTasks ?? []);
	const pendingSet = new Set(executionState?.pendingTasks ?? []);
	const getTaskStatus = (taskId) => {
		if (completedSet.has(taskId)) return "completed";
		if (failedSet.has(taskId)) return "failed";
		if (runningSet.has(taskId)) return "running";
		if (pendingSet.has(taskId)) return "pending";
		return "pending";
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-4xl",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "mb-4 text-sm font-semibold text-muted-foreground uppercase tracking-wider",
				children: "Execution Graph"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-6",
				children: levels.map((level, levelIdx) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mb-2 text-xs text-muted-foreground font-mono",
						children: ["Level ", levelIdx + 1]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: cn("flex gap-3", level.length > 1 ? "flex-wrap" : ""),
						children: level.map((taskId) => {
							const task = taskMap.get(taskId);
							if (!task) return null;
							const status = getTaskStatus(taskId);
							return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: cn("relative flex flex-col rounded-lg border p-3 min-w-[180px] max-w-[220px] transition-all", status === "completed" && "border-green-500/30 bg-green-500/5", status === "running" && "border-blue-500/50 bg-blue-500/10 ring-1 ring-blue-500/30", status === "failed" && "border-red-500/30 bg-red-500/5", status === "pending" && "border-muted bg-muted/30"),
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("h-2 w-2 shrink-0 rounded-full", status === "completed" && "bg-green-500", status === "running" && "bg-blue-500 animate-pulse", status === "failed" && "bg-red-500", status === "pending" && "bg-gray-400") }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-xs font-medium truncate",
											children: task.name
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "mt-1.5 flex items-center gap-2 text-[10px] text-muted-foreground",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, { role: task.agentRole }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ModeBadge, { mode: task.executionMode })]
									}),
									status === "running" && task.progress > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
											className: "h-full rounded-full bg-blue-500 transition-all",
											style: { width: `${task.progress}%` }
										})
									})
								]
							}, taskId);
						})
					}),
					levelIdx < levels.length - 1 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex justify-center py-2",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
							className: "h-5 w-5 text-muted-foreground",
							fill: "none",
							stroke: "currentColor",
							strokeWidth: 2,
							viewBox: "0 0 24 24",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M12 5v14M5 12l7 7 7-7" })
						})
					})
				] }, levelIdx))
			}),
			edges.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-8",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
					className: "mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider",
					children: "Dependencies"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "space-y-1",
					children: edges.map((edge, i) => {
						const fromTask = taskMap.get(edge.from);
						const toTask = taskMap.get(edge.to);
						return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2 text-xs text-muted-foreground",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "font-medium text-foreground",
									children: fromTask?.name ?? edge.from
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
									className: "h-3 w-3",
									fill: "none",
									stroke: "currentColor",
									strokeWidth: 2,
									viewBox: "0 0 24 24",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M5 12h14M12 5l7 7-7 7" })
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "font-medium text-foreground",
									children: toTask?.name ?? edge.to
								})
							]
						}, i);
					})
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-8",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
					className: "mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider",
					children: "Legend"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex flex-wrap gap-4",
					children: [
						{
							color: "bg-green-500",
							label: "Completed"
						},
						{
							color: "bg-blue-500",
							label: "Running"
						},
						{
							color: "bg-red-500",
							label: "Failed"
						},
						{
							color: "bg-gray-400",
							label: "Pending"
						}
					].map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-1.5 text-xs text-muted-foreground",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("h-2 w-2 rounded-full", item.color) }), item.label]
					}, item.label))
				})]
			})
		]
	});
}
function Badge({ role }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		className: cn("rounded px-1 py-0.5 font-mono text-[10px]", {
			planner: "bg-purple-500/10 text-purple-600",
			developer: "bg-blue-500/10 text-blue-600",
			research: "bg-teal-500/10 text-teal-600",
			writer: "bg-green-500/10 text-green-600",
			creative: "bg-pink-500/10 text-pink-600",
			data: "bg-orange-500/10 text-orange-600",
			coordinator: "bg-primary/10 text-primary",
			security: "bg-red-500/10 text-red-600",
			browser: "bg-cyan-500/10 text-cyan-600"
		}[role] ?? "bg-muted text-muted-foreground"),
		children: role
	});
}
function ModeBadge({ mode }) {
	if (mode === "sequential") return null;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		className: "rounded bg-yellow-500/10 px-1 py-0.5 font-mono text-[10px] text-yellow-600",
		children: mode
	});
}
//#endregion
//#region src/app/task-orchestrator/plan-view.tsx
var ROLE_COLORS = {
	planner: "bg-purple-500/10 text-purple-600 border-purple-500/30",
	developer: "bg-blue-500/10 text-blue-600 border-blue-500/30",
	research: "bg-teal-500/10 text-teal-600 border-teal-500/30",
	writer: "bg-green-500/10 text-green-600 border-green-500/30",
	browser: "bg-cyan-500/10 text-cyan-600 border-cyan-500/30",
	qa: "bg-orange-500/10 text-orange-600 border-orange-500/30",
	deployment: "bg-red-500/10 text-red-600 border-red-500/30",
	security: "bg-rose-500/10 text-rose-600 border-rose-500/30",
	creative: "bg-pink-500/10 text-pink-600 border-pink-500/30",
	data: "bg-amber-500/10 text-amber-600 border-amber-500/30",
	communication: "bg-indigo-500/10 text-indigo-600 border-indigo-500/30",
	review: "bg-violet-500/10 text-violet-600 border-violet-500/30",
	coordinator: "bg-primary/10 text-primary border-primary/30"
};
function PlanView({ plan, executionState }) {
	const completedSet = (0, import_react.useMemo)(() => new Set(executionState?.completedTasks ?? []), [executionState]);
	const failedSet = (0, import_react.useMemo)(() => new Set(executionState?.failedTasks ?? []), [executionState]);
	const runningSet = (0, import_react.useMemo)(() => new Set(executionState?.runningTasks ?? []), [executionState]);
	if (!plan) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex h-48 items-center justify-center",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-muted-foreground",
			children: "Select or create a plan to view details"
		})
	});
	const completedCount = completedSet.size;
	const failedCount = failedSet.size;
	const runningCount = runningSet.size;
	const totalCount = plan.subtasks.length;
	const progress = totalCount > 0 ? Math.round((completedCount + failedCount) / totalCount * 100) : 0;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-4xl space-y-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "rounded-lg border p-4",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-start justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "font-semibold",
							children: plan.goal.slice(0, 120)
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 text-xs text-muted-foreground",
							children: plan.description.slice(0, 200)
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RiskBadge$1, { level: plan.riskLevel })]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-4 grid grid-cols-4 gap-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Metric, {
							label: "Tasks",
							value: String(totalCount)
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Metric, {
							label: "Est. Time",
							value: `${Math.round(plan.estimatedTime)}s`
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Metric, {
							label: "Est. Cost",
							value: `$${plan.estimatedCost.toFixed(2)}`
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Metric, {
							label: "Progress",
							value: `${progress}%`
						})
					]
				}),
				totalCount > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "mt-3 h-2 w-full overflow-hidden rounded-full bg-muted",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "h-full rounded-full bg-green-500 transition-all",
						style: { width: `${completedCount / totalCount * 100}%` }
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-3 flex gap-4 text-xs text-muted-foreground",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [completedCount, " completed"] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "text-blue-500",
							children: [runningCount, " running"]
						}),
						failedCount > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "text-red-500",
							children: [failedCount, " failed"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [totalCount - completedCount - runningCount - failedCount, " pending"] })
					]
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "space-y-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
				className: "text-sm font-semibold text-muted-foreground uppercase tracking-wider",
				children: "Tasks"
			}), plan.subtasks.map((task, idx) => {
				const isCompleted = completedSet.has(task.id);
				const isFailed = failedSet.has(task.id);
				const isRunning = runningSet.has(task.id);
				const status = isCompleted ? "completed" : isFailed ? "failed" : isRunning ? "running" : "pending";
				return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: cn("rounded-lg border p-3 transition-all", isCompleted && "border-green-500/30 bg-green-500/5", isRunning && "border-blue-500/30 bg-blue-500/5", isFailed && "border-red-500/30 bg-red-500/5"),
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-start gap-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground",
								children: idx + 1
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex-1 min-w-0",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-2",
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot$1, { status }),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: cn("font-medium text-sm", isCompleted && "line-through text-muted-foreground"),
												children: task.name
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge$1, {
												className: cn("text-[10px] h-5", ROLE_COLORS[task.agentRole] ?? ""),
												variant: "outline",
												children: task.agentRole
											}),
											task.requiresApproval && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge$1, {
												className: "text-[10px] h-5 text-yellow-600 border-yellow-500/30 bg-yellow-500/10",
												variant: "outline",
												children: "approval"
											})
										]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "mt-0.5 text-xs text-muted-foreground",
										children: task.description.slice(0, 120)
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "mt-1.5 flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground",
										children: [
											task.tools.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: ["Tools: ", task.tools.join(", ")] }),
											/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
												"Est: ",
												task.estimatedDuration,
												"s"
											] }),
											task.retryCount > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
												className: "text-orange-500",
												children: [
													"Retries: ",
													task.retryCount,
													"/",
													task.maxRetries
												]
											})
										]
									}),
									isRunning && task.progress > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "mt-2 h-1 w-32 overflow-hidden rounded-full bg-muted",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
											className: "h-full rounded-full bg-blue-500 transition-all",
											style: { width: `${task.progress}%` }
										})
									}),
									isFailed && task.error && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "mt-1 text-xs text-red-500",
										children: task.error.slice(0, 200)
									})
								]
							}),
							task.dependencies.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "shrink-0 text-[10px] text-muted-foreground",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "font-mono",
									children: ["after: ", task.dependencies.length]
								})
							})
						]
					})
				}, task.id);
			})]
		})]
	});
}
function Metric({ label, value }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "rounded-lg border bg-muted/30 px-3 py-2 text-center",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "text-lg font-bold",
			children: value
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "text-[10px] text-muted-foreground",
			children: label
		})]
	});
}
function StatusDot$1({ status }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("h-2 w-2 shrink-0 rounded-full", {
		pending: "bg-gray-400",
		running: "bg-blue-500 animate-pulse",
		completed: "bg-green-500",
		failed: "bg-red-500",
		cancelled: "bg-gray-400",
		paused: "bg-yellow-500"
	}[status] ?? "bg-gray-400") });
}
function RiskBadge$1({ level }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge$1, {
		className: cn({
			low: "bg-green-500/10 text-green-600 border-green-500/30",
			medium: "bg-yellow-500/10 text-yellow-600 border-yellow-500/30",
			high: "bg-orange-500/10 text-orange-600 border-orange-500/30",
			critical: "bg-red-500/10 text-red-600 border-red-500/30"
		}[level] ?? ""),
		variant: "outline",
		children: level
	});
}
//#endregion
//#region src/app/task-orchestrator/index.tsx
var TABS = [
	{
		id: "overview",
		label: "Overview"
	},
	{
		id: "plan",
		label: "Plan"
	},
	{
		id: "graph",
		label: "Graph"
	},
	{
		id: "activity",
		label: "Activity"
	},
	{
		id: "checkpoints",
		label: "Checkpoints"
	},
	{
		id: "approvals",
		label: "Approvals",
		badge: (s) => s.approvalRequests.filter((r) => r.status === "pending").length
	}
];
function TaskOrchestrator() {
	const state = useStore($orchestrator);
	const currentPlan = useStore($currentPlan);
	const executionState = useStore($currentExecutionState);
	const runningAgents = useStore($runningAgentActivities);
	const pendingApprovals = useStore($pendingApprovals);
	const [activeTab, setActiveTab] = (0, import_react.useState)("overview");
	const [newGoal, setNewGoal] = (0, import_react.useState)("");
	const [showNewPlan, setShowNewPlan] = (0, import_react.useState)(false);
	const stats = (0, import_react.useMemo)(() => {
		const all = state.plans;
		const active = all.filter((p) => {
			const es = state.executionStates[p.id];
			return es && !es.cancelled && es.completedTasks.length > 0;
		});
		return {
			total: all.length,
			active: active.length,
			running: runningAgents.length,
			pendingApprovals: pendingApprovals.length,
			totalCost: all.reduce((sum, p) => sum + p.estimatedCost, 0)
		};
	}, [
		state.plans,
		state.executionStates,
		runningAgents.length,
		pendingApprovals.length
	]);
	const handleCreatePlan = () => {
		if (newGoal.trim()) {
			createPlan(newGoal.trim());
			setNewGoal("");
			setShowNewPlan(false);
			setActiveTab("plan");
		}
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between border-b px-6 py-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-lg font-semibold",
					children: "Task Orchestrator"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-xs text-muted-foreground",
					children: "Autonomous agent orchestration and task management"
				})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [state.offlineMode && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge$1, {
						className: "text-yellow-600 border-yellow-300",
						variant: "outline",
						children: "Offline"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => setShowNewPlan(true),
						size: "sm",
						children: "New Plan"
					})]
				})]
			}),
			showNewPlan && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "border-b p-4",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mx-auto max-w-lg space-y-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Describe your objective" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							onChange: (e) => setNewGoal(e.target.value),
							onKeyDown: (e) => e.key === "Enter" && handleCreatePlan(),
							placeholder: "e.g., Research AI providers, compare pricing, create a report, and save it as PDF",
							value: newGoal
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex justify-end gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => setShowNewPlan(false),
								size: "sm",
								variant: "outline",
								children: "Cancel"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: handleCreatePlan,
								size: "sm",
								children: "Create & Analyze"
							})]
						})
					]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid grid-cols-4 gap-3 border-b px-6 py-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
						label: "Total Plans",
						value: stats.total
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
						color: "text-blue-600",
						label: "Active Agents",
						value: stats.running
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
						color: "text-yellow-600",
						label: "Pending Approvals",
						value: stats.pendingApprovals
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
						color: "text-green-600",
						label: "Est. Total Cost",
						value: `$${stats.totalCost.toFixed(2)}`
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex gap-1 border-b px-6",
				children: TABS.map((tab) => {
					const badge = tab.badge?.(state);
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: cn("relative px-4 py-2 text-sm font-medium transition-colors", activeTab === tab.id ? "text-foreground border-b-2 border-primary" : "text-muted-foreground hover:text-foreground"),
						onClick: () => setActiveTab(tab.id),
						type: "button",
						children: [tab.label, badge !== void 0 && badge > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "ml-1.5 rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary",
							children: badge
						})]
					}, tab.id);
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex-1 overflow-y-auto p-6",
				children: [
					activeTab === "overview" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverviewView, {
						activities: state.agentActivities,
						currentPlanId: state.currentPlanId,
						executionStates: state.executionStates,
						onRemovePlan: removePlan,
						onSelectPlan: (id) => {
							setCurrentPlan(id);
							setActiveTab("plan");
						},
						plans: state.plans
					}),
					activeTab === "plan" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PlanView, {
						executionState,
						plan: currentPlan
					}),
					activeTab === "graph" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ExecutionGraphView, {
						executionState,
						plan: currentPlan
					}),
					activeTab === "activity" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AgentActivityFeed, { activities: state.agentActivities }),
					activeTab === "checkpoints" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CheckpointView, {
						checkpoints: state.checkpoints,
						planId: state.currentPlanId
					}),
					activeTab === "approvals" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ApprovalPanel, {
						onRespond: (id, resp) => {
							const { respondApproval } = (init_task_orchestrator(), __toCommonJS(task_orchestrator_exports));
							respondApproval(id, resp);
						},
						requests: state.approvalRequests
					})
				]
			})
		]
	});
}
function StatCard({ label, value, color }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "rounded-lg border p-3 text-center",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: cn("text-xl font-bold", color ?? "text-foreground"),
			children: value
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "text-xs text-muted-foreground",
			children: label
		})]
	});
}
function OverviewView({ plans, executionStates, activities, currentPlanId, onSelectPlan, onRemovePlan }) {
	const recentActivities = activities.slice(-20).reverse();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-4xl space-y-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
			className: "mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wider",
			children: "Recent Plans"
		}), plans.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "py-8 text-center text-sm text-muted-foreground",
			children: "No plans yet. Create one to get started."
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "space-y-2",
			children: plans.slice(-10).reverse().map((plan) => {
				const es = executionStates[plan.id];
				const isActive = plan.id === currentPlanId;
				const status = es?.cancelled ? "cancelled" : es?.completedTasks.length === plan.subtasks.length ? "completed" : es ? "running" : "pending";
				return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: cn("flex items-center justify-between rounded-lg border p-3 transition-colors", isActive && "border-primary/50 bg-primary/5"),
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: "flex-1 text-left",
						onClick: () => onSelectPlan(plan.id),
						type: "button",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { status }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "font-medium text-sm truncate",
									children: plan.goal.slice(0, 80)
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(RiskBadge, { level: plan.riskLevel })
							]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "text-xs text-muted-foreground mt-1",
							children: [
								plan.subtasks.length,
								" tasks · ",
								plan.estimatedTime,
								"s est. · $",
								plan.estimatedCost.toFixed(2)
							]
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						className: "text-destructive",
						onClick: () => onRemovePlan(plan.id),
						size: "sm",
						variant: "ghost",
						children: "Remove"
					})]
				}, plan.id);
			})
		})] }), recentActivities.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
			className: "mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wider",
			children: "Recent Activity"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "space-y-1",
			children: recentActivities.slice(0, 10).map((a) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2 text-sm",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ActivityStatusDot, { status: a.status }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "font-medium",
						children: a.name
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-muted-foreground",
						children: a.message || a.status
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-xs text-muted-foreground",
						children: a.model
					})
				]
			}, a.agentId + a.startedAt))
		})] })]
	});
}
function StatusDot({ status }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("h-2 w-2 shrink-0 rounded-full", {
		pending: "bg-gray-400",
		running: "bg-blue-500 animate-pulse",
		completed: "bg-green-500",
		failed: "bg-red-500",
		cancelled: "bg-gray-400",
		paused: "bg-yellow-500"
	}[status] ?? "bg-gray-400") });
}
function ActivityStatusDot({ status }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("h-1.5 w-1.5 shrink-0 rounded-full", {
		idle: "bg-gray-400",
		running: "bg-blue-500 animate-pulse",
		thinking: "bg-purple-500 animate-pulse",
		tool_called: "bg-orange-500",
		waiting: "bg-yellow-500",
		completed: "bg-green-500",
		failed: "bg-red-500",
		retrying: "bg-orange-500 animate-pulse"
	}[status] ?? "bg-gray-400") });
}
function RiskBadge({ level }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge$1, {
		className: cn("text-[10px] h-5 px-1.5", {
			low: "bg-green-500/10 text-green-600 border-green-500/30",
			medium: "bg-yellow-500/10 text-yellow-600 border-yellow-500/30",
			high: "bg-orange-500/10 text-orange-600 border-orange-500/30",
			critical: "bg-red-500/10 text-red-600 border-red-500/30"
		}[level] ?? ""),
		variant: "outline",
		children: level
	});
}
//#endregion
export { TaskOrchestrator };

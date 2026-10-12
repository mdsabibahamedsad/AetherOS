import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { t as $gateway } from "./gateway-D1xRY-ux.js";
import { A as $subagentsBySession, Dt as sessionRoute, It as useEnterAnimation, Ki as IconSparkles, La as Button, Lt as FadeText, Oi as notifyError, Ra as cn, Sa as IconCircleCheck, Ya as useStore, an as ActivityTimerText, ao as require_jsx_runtime, di as $activeSessionId, eo as useNavigate, gi as $gatewayState, j as buildSubagentTree, ja as IconAlertCircle, ki as useI18n, ln as BrailleSpinner, on as useElapsedSeconds, oo as require_react, un as sessionTitle, vi as $sessions } from "./index-B_yd1pEX.js";
import { t as Card } from "./card-CXjwIosc.js";
import { t as OverlayView } from "./overlay-view-DLw12qQQ.js";
//#region src/components/agent/agent-card.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var TERMINAL = new Set([
	"completed",
	"failed",
	"interrupted"
]);
/**
* Roll a subagent tree up into an honest activity summary. Counts come
* straight from node state — done = terminal nodes, total = all nodes.
* No estimates, no fabricated progress.
*/
function summarizeAgentNodes(nodes) {
	const flat = [];
	const walk = (list) => {
		for (const node of list) {
			flat.push(node);
			walk(node.children);
		}
	};
	walk(nodes);
	const completed = flat.filter((n) => TERMINAL.has(n.status)).length;
	const running = flat.find((n) => n.status === "running" || n.status === "queued");
	const models = [...new Set(flat.map((n) => n.model).filter((m) => Boolean(m)))];
	const tokens = flat.reduce((sum, n) => sum + (n.inputTokens ?? 0) + (n.outputTokens ?? 0), 0);
	const filesChanged = flat.reduce((sum, n) => sum + n.filesRead.length + n.filesWritten.length, 0);
	return {
		completed,
		currentTool: running?.currentTool ?? null,
		filesChanged,
		models,
		tokens,
		total: flat.length
	};
}
var STATUS_META = {
	completed: {
		dot: "bg-emerald-500",
		label: "Completed"
	},
	failed: {
		dot: "bg-red-500",
		label: "Failed"
	},
	idle: {
		dot: "bg-muted-foreground/40",
		label: "Idle"
	},
	interrupted: {
		dot: "bg-amber-500",
		label: "Stopped"
	},
	queued: {
		dot: "bg-amber-500",
		label: "Queued"
	},
	running: {
		dot: "bg-blue-500",
		label: "Working"
	}
};
/**
* AGI-style agent card: identity, goal, concise status summary, progress,
* tools/model/tokens/files, and Inspect/Stop actions. Shows observable
* actions and summaries only — never raw chain-of-thought. Every number
* derives from the provided nodes via summarizeAgentNodes.
*/
function AgentCard({ className, currentActivity, goal, model, nodes, onInspect, onStop, status, stopDisabled, title }) {
	const summary = (0, import_react.useMemo)(() => summarizeAgentNodes(nodes), [nodes]);
	const meta = STATUS_META[status];
	const live = status === "running" || status === "queued";
	const progress = summary.total > 0 ? Math.round(summary.completed / summary.total * 100) : 0;
	const facts = [
		summary.currentTool ? `Using ${summary.currentTool}` : "",
		model ? `Model ${model}` : "",
		summary.tokens > 0 ? `${summary.tokens.toLocaleString()} tokens` : "",
		summary.filesChanged > 0 ? `${summary.filesChanged} files touched` : ""
	].filter(Boolean);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Card, {
		className: cn("p-4", className),
		"data-testid": "agent-card",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-start gap-3",
			children: [
				live ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(BrailleSpinner, {
					ariaLabel: meta.label,
					className: "mt-0.5 size-4 shrink-0 text-muted-foreground/80",
					spinner: "breathe"
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					"aria-hidden": true,
					className: cn("mt-1.5 size-2.5 shrink-0 rounded-full", meta.dot)
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "min-w-0 flex-1",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex flex-wrap items-center gap-x-2 gap-y-0.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "truncate text-sm font-semibold tracking-tight",
								children: title
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								"aria-label": `${meta.label}, ${summary.completed} of ${summary.total} steps`,
								className: "text-xs text-muted-foreground",
								role: "status",
								children: [meta.label, summary.total > 0 ? ` · ${summary.completed}/${summary.total} steps` : ""]
							})]
						}),
						goal ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-0.5 truncate text-xs text-muted-foreground",
							children: goal
						}) : null,
						currentActivity ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 truncate font-mono text-[0.7rem] text-foreground/80",
							children: currentActivity
						}) : null,
						summary.total > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							"aria-label": `Progress ${progress} percent`,
							"aria-valuemax": 100,
							"aria-valuemin": 0,
							"aria-valuenow": progress,
							className: "mt-2 h-1 overflow-hidden rounded-full bg-(--ui-bg-tertiary)",
							role: "progressbar",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: cn("h-full rounded-full transition-all", live ? "bg-blue-500" : "bg-emerald-500"),
								style: { width: `${progress}%` }
							})
						}) : null,
						facts.length > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1.5 truncate text-[0.68rem] text-muted-foreground/75",
							children: facts.join(" · ")
						}) : null
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex shrink-0 items-center gap-1.5",
					children: [onInspect ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: onInspect,
						size: "sm",
						variant: "outline",
						children: "Inspect"
					}) : null, onStop && live ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: stopDisabled,
						onClick: onStop,
						size: "sm",
						title: stopDisabled ? "Unavailable while offline" : "Interrupt this agent",
						variant: "outline",
						children: "Stop"
					}) : null]
				})
			]
		})
	});
}
//#endregion
//#region src/lib/agi-states.ts
var AGENT_LIFECYCLE_LABEL = {
	created: "Created",
	initializing: "Initializing",
	ready: "Ready",
	planning: "Planning",
	running: "Running",
	waiting: "Waiting",
	needs_approval: "Needs approval",
	completing: "Completing",
	completed: "Completed",
	blocked: "Blocked",
	failed: "Failed",
	cancelled: "Cancelled",
	paused: "Paused",
	unknown: "Unknown"
};
/** Subagent runtime states → canonical agent lifecycle (one-to-one). */
function agentLifecycleFromSubagent(status) {
	switch (status) {
		case "running": return "running";
		case "queued": return "waiting";
		case "completed": return "completed";
		case "failed": return "failed";
		case "interrupted": return "cancelled";
	}
}
//#endregion
//#region src/components/agi/execution-timeline.tsx
/**
* Derive an operational execution timeline from subagent node lifecycles:
* one "started" event per node (goal as label) plus one terminal event
* (completed/failed/cancelled with summary when present). Stream chatter
* is excluded — this is history, not a transcript.
*/
function nodeTimelineEvents(nodes) {
	const flat = [];
	const walk = (list) => {
		for (const node of list) {
			flat.push(node);
			walk(node.children);
		}
	};
	walk(nodes);
	const events = [];
	for (const node of flat) {
		if (typeof node.startedAt === "number" && node.startedAt > 0) events.push({
			at: node.startedAt,
			id: `${node.id}:started`,
			label: `Started — ${node.goal || node.id}`,
			tone: "info"
		});
		const lifecycle = agentLifecycleFromSubagent(node.status);
		if ((lifecycle === "completed" || lifecycle === "failed" || lifecycle === "cancelled") && node.updatedAt > 0) events.push({
			at: node.updatedAt,
			id: `${node.id}:terminal`,
			label: `${AGENT_LIFECYCLE_LABEL[lifecycle]}${node.summary ? ` — ${node.summary}` : ""}`,
			tone: lifecycle === "completed" ? "good" : lifecycle === "failed" ? "bad" : "warn"
		});
	}
	return events.sort((a, b) => a.at - b.at);
}
var TONE_DOT = {
	good: "bg-emerald-500",
	bad: "bg-red-500",
	warn: "bg-amber-500",
	muted: "bg-muted-foreground/40",
	info: "bg-blue-500"
};
function formatTime(at) {
	return new Date(at).toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit",
		second: "2-digit"
	});
}
function ExecutionTimeline({ className, nodes }) {
	const events = (0, import_react.useMemo)(() => nodeTimelineEvents(nodes), [nodes]);
	if (events.length === 0) return null;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		"aria-label": "Execution timeline",
		className: cn("min-w-0", className),
		"data-testid": "execution-timeline",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-[0.66rem] font-semibold uppercase tracking-wider text-muted-foreground/70",
			children: "Execution timeline"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ol", {
			className: "mt-2 grid gap-0",
			children: events.map((event, index) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
				className: "flex min-w-0 gap-2.5",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
					"aria-hidden": true,
					className: "flex flex-col items-center",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("mt-1.5 size-2 shrink-0 rounded-full", TONE_DOT[event.tone]) }), index < events.length - 1 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "w-px flex-1 bg-border" }) : null]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "min-w-0 flex-1 pb-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "truncate text-[0.76rem] text-foreground/90",
						children: event.label
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "font-mono text-[0.64rem] text-muted-foreground/70",
						children: formatTime(event.at)
					})]
				})]
			}, event.id))
		})]
	});
}
//#endregion
//#region src/app/agents/index.tsx
function statusGlyph(status, a) {
	if (status === "running" || status === "queued") return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(BrailleSpinner, {
		ariaLabel: a.running,
		className: "size-3.5 shrink-0 text-[0.95rem] text-muted-foreground/80",
		spinner: "breathe"
	});
	if (status === "failed" || status === "interrupted") return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconAlertCircle, {
		"aria-label": a.failed,
		className: "size-3.5 shrink-0 text-destructive"
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconCircleCheck, {
		"aria-label": a.done,
		className: "size-3.5 shrink-0 text-emerald-600/85 dark:text-emerald-400/85"
	});
}
var STREAM_TONE = {
	progress: "text-muted-foreground/75",
	summary: "text-foreground/85",
	thinking: "text-muted-foreground/80",
	tool: "text-foreground/85"
};
function streamGlyph(entry) {
	if (entry.isError) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconAlertCircle, {
		"aria-hidden": true,
		className: "mt-0.5 size-3 shrink-0 text-destructive"
	});
	if (entry.kind === "tool") return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		"aria-hidden": true,
		className: "mt-0.5 size-1.5 shrink-0 rounded-full bg-foreground/55"
	});
	if (entry.kind === "summary") return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconCircleCheck, {
		"aria-hidden": true,
		className: "mt-0.5 size-3 shrink-0 text-emerald-600/85 dark:text-emerald-400/85"
	});
	if (entry.kind === "thinking") return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		"aria-hidden": true,
		className: "font-mono text-[0.7rem] leading-none text-muted-foreground/70",
		children: "…"
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		"aria-hidden": true,
		className: "mt-0.5 size-1 shrink-0 rounded-full bg-muted-foreground/55"
	});
}
function AgentsView({ onClose }) {
	const { t } = useI18n();
	const navigate = useNavigate();
	const activeSessionId = useStore($activeSessionId);
	const subagentsBySession = useStore($subagentsBySession);
	const sessions = useStore($sessions);
	const gateway = useStore($gateway);
	const gatewayState = useStore($gatewayState);
	const activeSubagents = (0, import_react.useMemo)(() => activeSessionId ? subagentsBySession[activeSessionId] ?? [] : [], [activeSessionId, subagentsBySession]);
	const tree = (0, import_react.useMemo)(() => buildSubagentTree(activeSubagents), [activeSubagents]);
	const offline = gatewayState !== "open" && gatewayState !== "connected";
	const session = activeSessionId ? sessions.find((s) => s.id === activeSessionId) ?? null : null;
	const cardStatus = (0, import_react.useMemo)(() => {
		const flat = tree.flatMap(function walk(n) {
			return [n, ...n.children.flatMap(walk)];
		});
		if (flat.some((n) => n.status === "running" || n.status === "queued")) return "running";
		if (flat.some((n) => n.status === "failed" || n.status === "interrupted")) return "failed";
		return flat.length > 0 ? "completed" : "idle";
	}, [tree]);
	const currentActivity = (0, import_react.useMemo)(() => {
		const flat = tree.flatMap(function walk(n) {
			return [n, ...n.children.flatMap(walk)];
		});
		const live = flat.find((n) => n.status === "running" || n.status === "queued");
		const entries = live ? live.stream : flat[0]?.stream;
		const last = entries?.[entries.length - 1];
		return last ? last.text : null;
	}, [tree]);
	const stopSession = (0, import_react.useCallback)(async () => {
		if (!gateway || !activeSessionId) {
			notifyError(/* @__PURE__ */ new Error("Gateway is not connected"), "Stop unavailable while offline");
			return;
		}
		try {
			await gateway.request("session.interrupt", { session_id: activeSessionId });
		} catch (e) {
			notifyError(e, "Failed to stop the active session");
		}
	}, [activeSessionId, gateway]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(OverlayView, {
		closeLabel: t.agents.close,
		contentClassName: "px-5 pt-5 pb-4 sm:px-6",
		onClose,
		rootClassName: "mx-auto max-w-3xl",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
				className: "mb-3 shrink-0",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-sm font-semibold text-foreground",
					children: t.agents.title
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-xs text-muted-foreground/80",
					children: t.agents.subtitle
				})]
			}),
			activeSessionId ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mb-4 grid shrink-0 gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(AgentCard, {
					currentActivity,
					goal: tree[0]?.goal ?? null,
					model: session?.model ?? tree[0]?.model ?? null,
					nodes: tree,
					onInspect: () => {
						navigate(sessionRoute(activeSessionId));
						onClose();
					},
					onStop: stopSession,
					status: cardStatus,
					stopDisabled: offline || !gateway,
					title: session ? sessionTitle(session) : t.agents.title
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ExecutionTimeline, { nodes: tree })]
			}) : null,
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SubagentTree, { tree })
		]
	});
}
var fmtDuration = (seconds, a) => {
	if (!seconds || seconds <= 0) return "";
	if (seconds < 60) return a.durationSeconds(seconds.toFixed(1));
	const m = Math.floor(seconds / 60);
	const s = Math.round(seconds % 60);
	return a.durationMinutes(m, s);
};
var fmtTokens = (value, a) => {
	if (!value) return "";
	return value >= 1e3 ? a.tokensK((value / 1e3).toFixed(1)) : a.tokens(value);
};
var fmtAge = (updatedAt, nowMs, a) => {
	const s = Math.max(0, Math.round((nowMs - updatedAt) / 1e3));
	if (s < 2) return a.ageNow;
	if (s < 60) return a.ageSeconds(s);
	const m = Math.floor(s / 60);
	if (m < 60) return a.ageMinutes(m);
	return a.ageHours(Math.floor(m / 60));
};
var flatten = (nodes) => nodes.flatMap((node) => [node, ...flatten(node.children)]);
function groupDelegations(roots) {
	const groups = [];
	let n = 0;
	for (const node of roots) {
		const prev = groups.at(-1);
		const prevTail = prev?.nodes.at(-1);
		const closeInTime = prevTail ? Math.abs(node.startedAt - prevTail.startedAt) <= 5e3 : false;
		const sameShape = prev && node.taskCount > 1 && prev.taskCount === node.taskCount;
		const uniqueStep = prev ? !prev.nodes.some((item) => item.taskIndex === node.taskIndex) : false;
		if (prev && sameShape && closeInTime && uniqueStep) {
			prev.nodes.push(node);
			continue;
		}
		if (node.taskCount > 1) {
			n += 1;
			groups.push({
				id: `delegation-${n}`,
				delegationIndex: n,
				nodes: [node],
				taskCount: node.taskCount
			});
			continue;
		}
		groups.push({
			id: node.id,
			delegationIndex: 0,
			nodes: [node],
			taskCount: node.taskCount
		});
	}
	return groups;
}
function SubagentTree({ tree }) {
	const { t } = useI18n();
	const flat = (0, import_react.useMemo)(() => flatten(tree), [tree]);
	const groups = (0, import_react.useMemo)(() => groupDelegations(tree), [tree]);
	const [nowMs, setNowMs] = (0, import_react.useState)(() => Date.now());
	const active = flat.filter((n) => n.status === "running" || n.status === "queued").length;
	const failed = flat.filter((n) => n.status === "failed" || n.status === "interrupted").length;
	const tools = flat.reduce((sum, n) => sum + (n.toolCount ?? 0), 0);
	const files = flat.reduce((sum, n) => sum + n.filesRead.length + n.filesWritten.length, 0);
	const tokens = flat.reduce((sum, n) => sum + (n.inputTokens ?? 0) + (n.outputTokens ?? 0), 0);
	const cost = flat.reduce((sum, n) => sum + (n.costUsd ?? 0), 0);
	(0, import_react.useEffect)(() => {
		if (active <= 0 || typeof window === "undefined") return;
		const id = window.setInterval(() => setNowMs(Date.now()), 500);
		return () => window.clearInterval(id);
	}, [active]);
	if (tree.length === 0) return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "grid place-items-center gap-3 py-12 text-center",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconSparkles, { className: "size-6 text-muted-foreground/60" }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm font-medium text-foreground/90",
				children: t.agents.emptyTitle
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "max-w-md text-xs leading-relaxed text-muted-foreground/75",
				children: t.agents.emptyDesc
			})
		]
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-hidden",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "shrink-0 text-[0.7rem] text-muted-foreground/70",
			children: [
				t.agents.agentsCount(flat.length),
				active > 0 ? t.agents.activeCount(active) : "",
				failed > 0 ? t.agents.failedCount(failed) : "",
				tools > 0 ? t.agents.toolsCount(tools) : "",
				files > 0 ? t.agents.filesCount(files) : "",
				tokens > 0 ? fmtTokens(tokens, t.agents) : "",
				cost > 0 ? `$${cost.toFixed(2)}` : ""
			].filter(Boolean).join(" · ")
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "min-h-0 min-w-0 flex-1 overflow-x-hidden overflow-y-auto overscroll-contain pr-1",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex min-w-0 flex-col gap-6",
				children: groups.map((group) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DelegationGroup, {
					group,
					nowMs
				}, group.id))
			})
		})]
	});
}
function DelegationGroup({ group, nowMs }) {
	const { t } = useI18n();
	if (group.nodes.length === 1 && group.taskCount <= 1) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SubagentRow, {
		node: group.nodes[0],
		nowMs
	});
	const activeWorkers = group.nodes.filter((n) => n.status === "running" || n.status === "queued").length;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		className: "grid min-w-0 gap-3",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
			className: "text-[0.66rem] font-medium uppercase tracking-wider text-muted-foreground/70",
			children: [
				group.delegationIndex > 0 ? t.agents.delegation(group.delegationIndex) : "",
				" ",
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "text-muted-foreground/50",
					children: "·"
				}),
				" ",
				t.agents.workers(group.nodes.length),
				activeWorkers > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
					className: "text-primary/85",
					children: [" · ", t.agents.workersActive(activeWorkers)]
				}) : null
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid min-w-0 gap-4",
			children: group.nodes.map((node) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SubagentRow, {
				node,
				nowMs
			}, node.id))
		})]
	});
}
function StreamLine({ active, entry, parentRunning, rowKey }) {
	const { t } = useI18n();
	const enterRef = useEnterAnimation(parentRunning, `subagent-stream:${rowKey}`);
	const isMono = entry.kind === "tool";
	const tone = entry.isError ? "text-destructive" : STREAM_TONE[entry.kind];
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex min-w-0 items-baseline gap-2 text-[0.72rem] leading-relaxed",
		ref: enterRef,
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: "flex h-[0.95rem] shrink-0 items-center",
			children: streamGlyph(entry)
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
			className: cn("min-w-0 flex-1 wrap-anywhere", tone, isMono && "font-mono text-[0.69rem]"),
			children: [entry.text, active ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(BrailleSpinner, {
				ariaLabel: t.agents.streaming,
				className: "ml-1 inline-block size-2.5 align-middle text-muted-foreground/70",
				spinner: "breathe"
			}) : null]
		})]
	});
}
function SubagentRow({ node, depth = 0, nowMs }) {
	const { t } = useI18n();
	const running = node.status === "running" || node.status === "queued";
	const elapsed = useElapsedSeconds(running, `subagent:${node.id}`);
	const durationSeconds = typeof node.durationSeconds === "number" ? Math.max(0, Math.round(node.durationSeconds)) : elapsed;
	const [open, setOpen] = (0, import_react.useState)(() => running || depth < 2);
	const enterRef = useEnterAnimation(true, `subagent-row:${node.id}`);
	(0, import_react.useEffect)(() => {
		if (running) setOpen(true);
	}, [running]);
	const visibleRows = open ? node.stream.slice(-10) : node.stream.slice(-2);
	const fileLines = [...node.filesWritten.map((p) => `+ ${p}`), ...node.filesRead.map((p) => `· ${p}`)];
	const subtitle = [
		node.model,
		fmtDuration(durationSeconds, t.agents),
		node.toolCount ? t.agents.toolsCount(node.toolCount) : "",
		fmtTokens((node.inputTokens ?? 0) + (node.outputTokens ?? 0), t.agents),
		t.agents.updatedAgo(fmtAge(node.updatedAt, nowMs, t.agents))
	].filter(Boolean);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: cn("grid min-w-0 max-w-full gap-2", depth > 0 && "pl-4"),
		"data-slot": "tool-block",
		ref: enterRef,
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
				"aria-expanded": open,
				className: "group flex w-full min-w-0 items-start gap-2.5 text-left",
				onClick: () => setOpen((v) => !v),
				type: "button",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "mt-0.5 flex h-[1.1rem] shrink-0 items-center",
						children: statusGlyph(node.status, t.agents)
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "flex min-w-0 flex-1 flex-col gap-0.5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: cn("wrap-anywhere text-[0.82rem] font-medium leading-[1.1rem] text-foreground/90 transition-colors group-hover:text-foreground", running && "shimmer text-foreground/65"),
							children: node.goal
						}), subtitle.length > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(FadeText, {
							className: "text-[0.66rem] leading-[1.05rem] text-muted-foreground/65",
							children: subtitle.join(" · ")
						}) : null]
					}),
					running ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ActivityTimerText, {
						className: "mt-1 shrink-0 text-[0.6rem]",
						seconds: durationSeconds
					}) : null
				]
			}),
			visibleRows.length > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid min-w-0 gap-1 pl-6",
				children: visibleRows.map((entry, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(StreamLine, {
					active: running && i === visibleRows.length - 1,
					entry,
					parentRunning: running,
					rowKey: `${node.id}:${entry.kind}:${entry.at}`
				}, `${entry.kind}:${entry.at}:${i}`))
			}) : null,
			open && fileLines.length > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid min-w-0 gap-0.5 pl-6",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-[0.58rem] font-medium tracking-wider text-muted-foreground/60 uppercase",
						children: t.agents.files
					}),
					fileLines.slice(0, 8).map((line) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "wrap-break-word font-mono text-[0.67rem] leading-relaxed text-muted-foreground/80",
						children: line
					}, line)),
					fileLines.length > 8 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "font-mono text-[0.67rem] leading-relaxed text-muted-foreground/65",
						children: t.agents.moreFiles(fileLines.length - 8)
					}) : null
				]
			}) : null,
			node.children.length > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid min-w-0 gap-3 pl-6",
				children: node.children.map((child) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SubagentRow, {
					depth: depth + 1,
					node: child,
					nowMs
				}, child.id))
			}) : null
		]
	});
}
//#endregion
export { AgentsView };

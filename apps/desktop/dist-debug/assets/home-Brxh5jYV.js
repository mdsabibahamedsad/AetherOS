import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { t as $gateway } from "./gateway-D1xRY-ux.js";
import { Ct as ARTIFACTS_ROUTE, Di as notify, Dt as sessionRoute, Et as SKILLS_ROUTE, Gn as $healthStatus, Jn as $systemStats, La as Button, Mt as $allApprovalRequests, Oi as notifyError, Ra as cn, S as ScrollArea, St as AGENTS_ROUTE, Tn as $cronJobs, Tt as KNOWLEDGE_ROUTE, Vn as $activeProfile, Ya as useStore, Yn as $tokenUsage, Z as openCommandPalette, ai as BRAND_TAGLINE, ao as require_jsx_runtime, di as $activeSessionId, eo as useNavigate, gi as $gatewayState, mi as $currentModel, ni as Input, oi as BRAND_WORDMARK, oo as require_react, ri as BrandMark, sn as stashSessionDraft, un as sessionTitle, ut as Skeleton, vi as $sessions, wt as AUTOMATION_CENTER_ROUTE, yi as $workingSessionIds } from "./index-B_yd1pEX.js";
import { t as Card } from "./card-CXjwIosc.js";
//#region src/lib/emergency-stop.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
async function tryCall(request, method, params) {
	try {
		return {
			detail: "ok",
			ok: true,
			value: await request(method, params)
		};
	} catch (e) {
		return {
			detail: e instanceof Error ? e.message : String(e),
			ok: false
		};
	}
}
async function emergencyStopAll(request) {
	const legs = [];
	let stoppedSessions = 0;
	const sessions = await tryCall(request, "session.active_list", {});
	if (sessions.ok) {
		const ids = (sessions.value?.sessions ?? []).map((s) => s.id).filter((id) => typeof id === "string" && id.length > 0);
		for (const id of ids) {
			const r = await tryCall(request, "session.interrupt", { session_id: id });
			if (r.ok) stoppedSessions += 1;
			else legs.push({
				detail: `${id.slice(0, 8)}: ${r.detail}`,
				leg: "sessions",
				ok: false
			});
		}
		legs.push({
			detail: `${stoppedSessions}/${ids.length} sessions interrupted`,
			leg: "sessions",
			ok: stoppedSessions === ids.length
		});
	} else legs.push({
		detail: `session list failed: ${sessions.detail}`,
		leg: "sessions",
		ok: false
	});
	const procs = await tryCall(request, "process.stop", {});
	legs.push({
		detail: procs.ok ? `${procs.value?.killed ?? 0} background processes killed` : `process.stop failed: ${procs.detail}`,
		leg: "processes",
		ok: procs.ok
	});
	const autos = await tryCall(request, "automation.stop_all", {});
	legs.push({
		detail: autos.ok ? "automations halted" : `automation.stop_all failed: ${autos.detail}`,
		leg: "automations",
		ok: autos.ok
	});
	const swarm = await tryCall(request, "swarm.stop", {});
	legs.push({
		detail: swarm.ok ? "swarm stopped" : `swarm.stop failed: ${swarm.detail}`,
		leg: "swarm",
		ok: swarm.ok
	});
	return {
		legs,
		stoppedSessions
	};
}
//#endregion
//#region src/components/system-status/global-status.tsx
var import_jsx_runtime = require_jsx_runtime();
/**
* Subtle global status indicator (Master 63 §109) + emergency stop (§56, §180).
*
* Freshness-first: status derives from live stores — gateway connection state
* and the health atom — never from static markup. "Operational" requires an
* open gateway AND a healthy report; anything else degrades honestly.
* STOP ALL AGENTS drives `emergencyStopAll` (real session.interrupt /
* process.stop / automation.stop_all / swarm.stop legs) and reports per-leg
* results. It never merely hides UI.
*/
function useGlobalStatus() {
	const gatewayState = useStore($gatewayState);
	const health = useStore($healthStatus);
	if (gatewayState !== "open" && gatewayState !== "connected") return {
		level: "offline",
		label: "Offline",
		degradedSystems: 0
	};
	if (!health) return {
		level: "degraded",
		label: "Connecting",
		degradedSystems: 0
	};
	if (health.overall === "healthy") return {
		level: "operational",
		label: "Operational",
		degradedSystems: 0
	};
	const bad = health.services.filter((s) => s.status !== "running").length;
	return {
		level: "degraded",
		label: `${bad} system${bad === 1 ? "" : "s"} degraded`,
		degradedSystems: bad
	};
}
var DOT = {
	operational: "bg-emerald-500",
	degraded: "bg-amber-500",
	offline: "bg-red-500"
};
function GlobalStatusIndicator({ className }) {
	const status = useGlobalStatus();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
		"aria-label": `System status: ${status.label}`,
		className: cn("inline-flex items-center gap-1.5 text-xs text-muted-foreground", className),
		"data-testid": "global-status",
		role: "status",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			"aria-hidden": true,
			className: cn("size-2 rounded-full", DOT[status.level])
		}), status.level === "operational" ? "● Operational" : `● ${status.label}`]
	});
}
function StopAllAgentsButton({ className }) {
	const gateway = useStore($gateway);
	const [stopping, setStopping] = (0, import_react.useState)(false);
	const [confirming, setConfirming] = (0, import_react.useState)(false);
	const run = (0, import_react.useCallback)(async () => {
		if (!gateway) {
			notifyError(/* @__PURE__ */ new Error("Gateway is not connected"), "STOP ALL unavailable while offline");
			return;
		}
		setStopping(true);
		try {
			const report = await emergencyStopAll((method, params) => gateway.request(method, params ?? {}));
			const failed = report.legs.filter((l) => !l.ok);
			if (failed.length === 0) notify({
				kind: "success",
				title: "All agents stopped",
				message: `${report.stoppedSessions} session(s) interrupted; processes, automations, swarm halted.`
			});
			else notifyError(new Error(failed.map((l) => `${l.leg}: ${l.detail}`).join("; ")), "STOP ALL partially completed — inspect each leg");
		} catch (e) {
			notifyError(e, "STOP ALL failed");
		} finally {
			setStopping(false);
			setConfirming(false);
		}
	}, [gateway]);
	if (!confirming) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
		"aria-label": "Stop all agents",
		className: cn("rounded-md border border-red-500/40 px-2.5 py-1 text-xs font-semibold text-red-500 transition-colors hover:bg-red-500/10 focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-40", className),
		"data-testid": "stop-all-agents",
		disabled: stopping || !gateway,
		onClick: () => setConfirming(true),
		title: gateway ? "Interrupt all live sessions, processes, automations, and swarms" : "Unavailable while gateway is offline",
		type: "button",
		children: "STOP ALL"
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
		"aria-label": "Confirm stop all agents",
		className: cn("inline-flex items-center gap-2", className),
		role: "alertdialog",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-xs text-muted-foreground",
				children: "Stop everything?"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
				className: "rounded-md px-2 py-1 text-xs font-semibold text-muted-foreground hover:bg-accent",
				disabled: stopping,
				onClick: () => setConfirming(false),
				type: "button",
				children: "Cancel"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
				className: "rounded-md bg-red-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-red-500 disabled:opacity-40",
				"data-testid": "stop-all-confirm",
				disabled: stopping,
				onClick: run,
				type: "button",
				children: stopping ? "Stopping…" : "Stop all agents"
			})
		]
	});
}
//#endregion
//#region src/lib/context-model.ts
function buildContextChain(input) {
	const chain = [{
		kind: "global",
		label: "AetherOS"
	}];
	if (input.profile && input.profile !== "default") chain.push({
		kind: "workspace",
		label: input.profile,
		route: "/profiles"
	});
	if (input.appLabel) chain.push({
		kind: "app",
		label: input.appLabel,
		route: input.appRoute ?? null
	});
	if (input.sessionTitle) chain.push({
		kind: "task",
		label: input.sessionTitle,
		route: input.sessionRoute ?? null
	});
	if (typeof input.activeAgentCount === "number" && input.activeAgentCount > 0) chain.push({
		kind: "agent",
		label: input.activeAgentCount === 1 ? "1 agent" : `${input.activeAgentCount} agents`,
		route: "/agents"
	});
	if (input.currentTool) chain.push({
		kind: "action",
		label: input.currentTool
	});
	return chain;
}
/**
* What "this" means for an intent issued at this chain position — the
* scope an agent should assume, stated so the UI can show it
* ("Using context from: …") instead of silently injecting memory.
*/
function scopeDescription(chain) {
	const task = [...chain].reverse().find((layer) => layer.kind === "task" || layer.kind === "app");
	const workspace = chain.find((layer) => layer.kind === "workspace");
	if (!task) return workspace ? `Workspace ${workspace.label}` : null;
	return workspace ? `${task.label} (${workspace.label})` : task.label;
}
//#endregion
//#region src/app/home/index.tsx
/**
* Home — "What is happening?" (Master 63 §10–§11).
*
* Every state originates from live atoms fed by the gateway/IPC layer:
* sessions, working-session ids, parked approvals, cron jobs, health, and
* system stats. When the gateway is offline, panels say so explicitly instead
* of rendering decorative zeros. Every major state carries a real action
* (Inspect / Stop / Review) wired to runtime methods — never a dead button.
*/
function HomeView() {
	const navigate = useNavigate();
	const gatewayState = useStore($gatewayState);
	const sessions = useStore($sessions);
	const workingIds = useStore($workingSessionIds);
	const activeSessionId = useStore($activeSessionId);
	const approvals = useStore($allApprovalRequests);
	const cronJobs = useStore($cronJobs);
	const stats = useStore($systemStats);
	const health = useStore($healthStatus);
	const tokens = useStore($tokenUsage);
	const model = useStore($currentModel);
	const offline = gatewayState !== "open" && gatewayState !== "connected";
	const pendingApprovalSessions = (0, import_react.useMemo)(() => Object.keys(approvals), [approvals]);
	const runningSessions = (0, import_react.useMemo)(() => sessions.filter((s) => workingIds.includes(s.id)), [sessions, workingIds]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
		className: "h-full",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mx-auto max-w-7xl space-y-6 p-6",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
					className: "flex flex-wrap items-center justify-between gap-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
							className: "text-2xl font-semibold tracking-tight",
							children: "Home"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 text-sm text-(--ui-text-tertiary)",
							children: "Live operational state — agents, tasks, approvals, automations, system health."
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-2",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(GlobalStatusIndicator, {})
						})
					] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StopAllAgentsButton, {}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => navigate("/"),
							size: "sm",
							children: "New Chat"
						})]
					})]
				}),
				offline && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "border-amber-500/40 p-4",
					role: "alert",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "text-sm font-semibold text-amber-500",
						children: "Gateway offline"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 text-sm text-(--ui-text-tertiary)",
						children: "Live state is unavailable while the gateway is disconnected. Cached sessions may be shown below where available; actions are disabled until reconnect."
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IntentSection, { offline }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(QuickActionsSection, { offline }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(RecentWorkSection, { offline }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
					children: "Live operations"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(AttentionSection, {
					offline,
					pendingApprovalSessions,
					runningCount: runningSessions.length
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ActiveWorkSection, {
					activeSessionId,
					offline,
					runningSessions
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "grid gap-4 sm:grid-cols-2 lg:grid-cols-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
							className: "p-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "mb-3 text-xs font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
								children: "System Health"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SystemHealthBody, {
								health,
								offline,
								stats
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
							className: "p-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "mb-3 text-xs font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
								children: "Model"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ModelBody, {
								model,
								offline,
								tokens
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
							className: "p-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "mb-3 text-xs font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
								children: "Automations"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AutomationsBody, {
								cronJobs,
								offline
							})]
						})
					]
				})
			]
		})
	});
}
function daypart() {
	const h = (/* @__PURE__ */ new Date()).getHours();
	if (h < 5) return "Good night";
	if (h < 12) return "Good morning";
	if (h < 18) return "Good afternoon";
	return "Good evening";
}
/**
* Intent-first workspace header: contextual greeting, universal intent
* input, and suggested actions derived from REAL state. Submitting hands
* the text to the chat composer as a new-session draft (the agent loop
* itself runs there) — Home never pretends to execute anything.
*/
function IntentSection({ offline }) {
	const navigate = useNavigate();
	const [text, setText] = (0, import_react.useState)("");
	const approvals = useStore($allApprovalRequests);
	const cronJobs = useStore($cronJobs);
	const sessions = useStore($sessions);
	const workingIds = useStore($workingSessionIds);
	const profile = useStore($activeProfile);
	const pendingCount = Object.keys(approvals).length;
	const runningCount = sessions.filter((s) => workingIds.includes(s.id)).length;
	const scope = scopeDescription(buildContextChain({ profile }));
	const submit = (0, import_react.useCallback)(() => {
		const value = text.trim();
		if (!value || offline) return;
		stashSessionDraft(null, value, []);
		setText("");
		navigate("/");
	}, [
		navigate,
		offline,
		text
	]);
	const suggestions = (0, import_react.useMemo)(() => {
		const items = [];
		if (pendingCount > 0) items.push({
			description: `${pendingCount} waiting for a decision`,
			icon: "shield",
			id: "review-approvals",
			label: "Review approvals",
			run: () => navigate("/security")
		});
		if (runningCount > 0) items.push({
			description: `${runningCount} active right now`,
			icon: "pulse",
			id: "inspect-agents",
			label: "Inspect running agents",
			run: () => navigate("/agents")
		});
		const recent = sessions[0];
		if (recent) items.push({
			description: sessionTitle(recent),
			icon: "history",
			id: "resume-work",
			label: "Resume recent work",
			run: () => navigate(sessionRoute(recent.id))
		});
		if (cronJobs.length === 0) items.push({
			description: "Let AetherOS do recurring work",
			icon: "zap",
			id: "create-automation",
			label: "Create an automation",
			run: () => navigate("/automation-center")
		});
		items.push({
			description: "Files, apps, agents, commands",
			icon: "search",
			id: "command-palette",
			label: "Search everything",
			run: () => openCommandPalette()
		});
		return items.slice(0, 4);
	}, [
		cronJobs.length,
		navigate,
		pendingCount,
		runningCount,
		sessions
	]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
		className: "overflow-hidden p-5 sm:p-8",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(BrandMark, { className: "size-14 shrink-0 rounded-[14px]" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "min-w-0",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "text-xs font-semibold uppercase tracking-[0.2em] text-(--ui-text-tertiary)",
							children: [
								BRAND_WORDMARK,
								" · ",
								BRAND_TAGLINE
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h2", {
							className: "mt-1 truncate text-xl font-semibold tracking-tight sm:text-2xl",
							children: [daypart(), ", operator"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-0.5 truncate text-sm text-(--ui-text-tertiary)",
							children: "Your AI workspace for getting things done."
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 truncate text-sm text-(--ui-text-tertiary)",
							role: "status",
							children: offline ? "Gateway offline — cached state only." : runningCount > 0 ? `${runningCount} agent${runningCount === 1 ? "" : "s"} working · ${pendingCount} approval${pendingCount === 1 ? "" : "s"} waiting` : pendingCount > 0 ? `${pendingCount} approval${pendingCount === 1 ? "" : "s"} waiting for you` : "All quiet. What should AetherOS do?"
						}),
						scope ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "mt-0.5 truncate text-xs text-(--ui-text-tertiary)",
							children: ["Using context from: ", scope]
						}) : null
					]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("form", {
				className: "mt-5",
				onSubmit: (e) => {
					e.preventDefault();
					submit();
				},
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
					className: "mb-2 block text-sm font-medium",
					htmlFor: "home-intent-input",
					children: "What can I help you accomplish?"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2 rounded-2xl border-2 border-(--ui-stroke-tertiary) bg-(--ui-bg-tertiary)/40 px-4 shadow-sm transition-all focus-within:border-(--dt-ring) focus-within:shadow-md focus-within:ring-2 focus-within:ring-(--dt-ring)/20",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							"aria-hidden": true,
							className: "codicon codicon-sparkle text-(--ui-text-tertiary)"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							"aria-label": "Ask AetherOS",
							className: "h-12 flex-1 border-none bg-transparent text-[0.9375rem] shadow-none focus-visible:ring-0",
							disabled: offline,
							id: "home-intent-input",
							onChange: (e) => setText(e.target.value),
							placeholder: offline ? "Ask AetherOS… (unavailable offline)" : "Ask AetherOS… \"Organize my downloads\", \"Prepare a release summary\"",
							value: text
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("kbd", {
							"aria-hidden": true,
							className: "hidden shrink-0 rounded border border-(--ui-stroke-tertiary) px-1.5 py-0.5 font-mono text-[0.625rem] text-(--ui-text-tertiary) sm:inline-block",
							children: "⏎"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							disabled: offline || !text.trim(),
							size: "sm",
							type: "submit",
							children: "Run"
						})
					]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				"aria-label": "Suggested actions",
				className: "mt-3 flex flex-wrap gap-2",
				role: "list",
				children: suggestions.map((s) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: "group flex items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) px-2.5 py-1.5 text-left text-xs transition-colors hover:border-(--dt-ring) hover:shadow-sm focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-(--dt-ring)",
					onClick: s.run,
					role: "listitem",
					type: "button",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						"aria-hidden": true,
						className: `codicon codicon-${s.icon} text-(--ui-text-tertiary) group-hover:text-foreground`
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "block font-medium",
						children: s.label
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "block text-(--ui-text-tertiary)",
						children: s.description
					})] })]
				}, s.id))
			})
		]
	});
}
var QUICK_ACTIONS = [
	{
		id: "qa-session",
		title: "Start a session",
		description: "Chat with AetherOS to get work done",
		icon: "comment-discussion",
		route: "/"
	},
	{
		id: "qa-agents",
		title: "Browse agents",
		description: "Find a specialist for the task",
		icon: "robot",
		route: AGENTS_ROUTE
	},
	{
		id: "qa-skills",
		title: "Use a skill",
		description: "Reusable capabilities and tools",
		icon: "tools",
		route: SKILLS_ROUTE
	},
	{
		id: "qa-research",
		title: "Research something",
		description: "Evidence-backed answers",
		icon: "book",
		route: KNOWLEDGE_ROUTE
	},
	{
		id: "qa-artifact",
		title: "Create an artifact",
		description: "Documents, code, and outputs",
		icon: "package",
		route: ARTIFACTS_ROUTE
	},
	{
		id: "qa-automate",
		title: "Automate a task",
		description: "Schedules and recurring work",
		icon: "zap",
		route: AUTOMATION_CENTER_ROUTE
	}
];
function QuickActionsSection({ offline }) {
	const navigate = useNavigate();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		"aria-label": "Quick actions",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
			className: "mb-2 text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
			children: "Quick actions"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid gap-2 sm:grid-cols-2 lg:grid-cols-3",
			children: QUICK_ACTIONS.map((action) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
				className: "group flex items-start gap-3 rounded-xl border border-(--ui-stroke-tertiary) bg-(--ui-bg-secondary)/40 p-3 text-left transition-all hover:-translate-y-px hover:border-(--dt-ring) hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--dt-ring) disabled:cursor-not-allowed disabled:opacity-60",
				disabled: offline,
				onClick: () => navigate(action.route),
				title: offline ? "Unavailable while offline" : action.description,
				type: "button",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					"aria-hidden": true,
					className: "flex size-9 shrink-0 items-center justify-center rounded-lg bg-(--ui-bg-tertiary)/60 transition-colors group-hover:bg-(--ui-control-hover-background)",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `codicon codicon-${action.icon} text-(--ui-text-tertiary) group-hover:text-foreground` })
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
					className: "min-w-0",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "block truncate text-sm font-medium",
						children: action.title
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "block truncate text-xs text-(--ui-text-tertiary)",
						children: action.description
					})]
				})]
			}, action.id))
		})]
	});
}
function RecentWorkSection({ offline }) {
	const navigate = useNavigate();
	const sessions = useStore($sessions);
	const recent = (0, import_react.useMemo)(() => sessions.slice(0, 4), [sessions]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		"aria-label": "Recent work",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mb-2 flex items-center justify-between",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
				children: "Recent work"
			}), recent.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				onClick: () => navigate("/history"),
				size: "sm",
				variant: "ghost",
				children: "View all"
			})]
		}), recent.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
			className: "p-6 text-center",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm font-medium",
					children: "No recent sessions"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-1 text-sm text-(--ui-text-tertiary)",
					children: offline ? "Session history will appear here once the gateway reconnects." : "Start your first session to put AetherOS to work."
				}),
				!offline && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					className: "mt-3",
					onClick: () => navigate("/"),
					size: "sm",
					children: "Start your first session"
				})
			]
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
			className: "grid gap-2 sm:grid-cols-2",
			children: recent.map((session) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
				className: "flex w-full items-center gap-3 rounded-xl border border-(--ui-stroke-tertiary) p-3 text-left transition-colors hover:border-(--dt-ring) hover:shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--dt-ring)",
				onClick: () => navigate(sessionRoute(session.id)),
				type: "button",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						"aria-hidden": true,
						className: "codicon codicon-history shrink-0 text-(--ui-text-tertiary)"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "min-w-0 flex-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "block truncate text-sm font-medium",
							children: sessionTitle(session)
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "block truncate font-mono text-xs text-(--ui-text-tertiary)",
							children: session.id
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "shrink-0 text-xs text-(--ui-text-tertiary)",
						children: "Resume →"
					})
				]
			}) }, session.id))
		})]
	});
}
function AttentionSection({ offline, pendingApprovalSessions, runningCount }) {
	const navigate = useNavigate();
	if (offline) return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
		className: "p-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
			className: "mb-1 text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
			children: "Needs Attention"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-(--ui-text-tertiary)",
			children: "Unavailable — gateway offline."
		})]
	});
	if (pendingApprovalSessions.length === 0 && runningCount === 0) return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
		className: "p-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
			className: "mb-1 text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
			children: "Needs Attention"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-(--ui-text-tertiary)",
			children: "Nothing waiting for you. Agents are idle and no approvals are pending."
		})]
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
		className: "p-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
			className: "mb-3 text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
			children: "Needs Attention"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("ul", {
			className: "space-y-2",
			children: [pendingApprovalSessions.map((sessionId) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
				className: "flex flex-wrap items-center gap-2 rounded-xl border border-amber-500/40 bg-amber-500/5 p-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-shield text-amber-500" }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "min-w-0 flex-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Approval required"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "truncate font-mono text-xs text-(--ui-text-tertiary)",
							children: sessionId
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => navigate("/security"),
						size: "sm",
						variant: "outline",
						children: "Review"
					})
				]
			}, sessionId)), runningCount > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
				className: "flex flex-wrap items-center gap-2 rounded-xl border border-(--ui-stroke-tertiary) p-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-pulse text-(--ui-text-tertiary)" }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "min-w-0 flex-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "text-sm font-medium",
							children: [
								runningCount,
								" agent",
								runningCount === 1 ? "" : "s",
								" running"
							]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Inspect below to pause or stop."
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => navigate("/tasks"),
						size: "sm",
						variant: "outline",
						children: "Open Tasks"
					})
				]
			})]
		})]
	});
}
function ActiveWorkSection({ activeSessionId, offline, runningSessions }) {
	const navigate = useNavigate();
	const gateway = useStore($gateway);
	const stopSession = (0, import_react.useCallback)(async (sessionId) => {
		if (!gateway) {
			notifyError(/* @__PURE__ */ new Error("Gateway is not connected"), "Stop unavailable while offline");
			return;
		}
		try {
			await gateway.request("session.interrupt", { session_id: sessionId });
		} catch (e) {
			notifyError(e, `Failed to stop session ${sessionId.slice(0, 8)}`);
		}
	}, [gateway]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
		className: "p-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mb-3 flex items-center justify-between",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
				children: "Active Work"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-xs text-(--ui-text-tertiary)",
				role: "status",
				children: offline ? "Paused — offline" : `Live · ${runningSessions.length} running`
			})]
		}), runningSessions.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "py-4 text-center",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-(--ui-text-tertiary)",
				children: offline ? "Live agent state is unavailable while offline." : "No agents running. Start a chat or create a task to put agents to work."
			}), !offline && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-3 flex justify-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => navigate("/"),
					size: "sm",
					variant: "outline",
					children: "New Chat"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => navigate("/tasks"),
					size: "sm",
					variant: "outline",
					children: "Create Task"
				})]
			})]
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
			className: "space-y-2",
			children: runningSessions.map((session) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
				className: cn("flex flex-wrap items-center gap-2 rounded-xl border p-3", session.id === activeSessionId ? "border-(--dt-ring)" : "border-(--ui-stroke-tertiary)"),
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						"aria-hidden": true,
						className: "size-2 shrink-0 rounded-full bg-blue-500"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "min-w-0 flex-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "truncate text-sm font-medium",
							children: sessionTitle(session)
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "truncate font-mono text-xs text-(--ui-text-tertiary)",
							children: [session.id, session.id === activeSessionId ? " · this session" : ""]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => navigate(sessionRoute(session.id)),
						size: "sm",
						variant: "outline",
						children: "Inspect"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: offline,
						onClick: () => stopSession(session.id),
						size: "sm",
						title: offline ? "Unavailable while offline" : "Interrupt this session",
						variant: "outline",
						children: "Stop"
					})
				]
			}, session.id))
		})]
	});
}
function SystemHealthBody({ health, offline, stats }) {
	if (offline) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
		className: "text-sm text-(--ui-text-tertiary)",
		children: "Unavailable — gateway offline."
	});
	if (!stats && !health) return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		"aria-label": "Loading system health",
		className: "space-y-2",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-4 w-24" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-4 w-32" })]
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("dl", {
		className: "space-y-3",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "rounded-xl border border-(--ui-stroke-tertiary) p-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dt", {
						className: "text-xs font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
						children: "CPU"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
						className: "mt-1 text-lg font-semibold tracking-tight",
						children: stats ? `${stats.cpu}%` : "Not reported"
					}),
					stats && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
						className: "text-xs text-(--ui-text-tertiary)",
						children: stats.platform
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "rounded-xl border border-(--ui-stroke-tertiary) p-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dt", {
					className: "text-xs font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
					children: "Memory"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
					className: "mt-1 text-lg font-semibold tracking-tight",
					children: stats ? `${Math.round(stats.memory.used / 1024)}GB / ${Math.round(stats.memory.total / 1024)}GB` : "Not reported"
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "rounded-xl border border-(--ui-stroke-tertiary) p-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dt", {
						className: "text-xs font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
						children: "Status"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
						className: "mt-1 text-lg font-semibold tracking-tight",
						children: health ? health.overall === "healthy" ? "All Systems Go" : health.overall : "Not reported"
					}),
					health && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("dd", {
						className: "text-xs text-(--ui-text-tertiary)",
						children: [
							health.services.length,
							" service",
							health.services.length === 1 ? "" : "s",
							" reporting"
						]
					})
				]
			})
		]
	});
}
function ModelBody({ model, offline, tokens }) {
	const navigate = useNavigate();
	if (offline) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
		className: "text-sm text-(--ui-text-tertiary)",
		children: "Unavailable — gateway offline."
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-3",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "rounded-xl border border-(--ui-stroke-tertiary) p-3",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "text-xs font-medium uppercase tracking-wider text-(--ui-text-tertiary)",
					children: "Current Model"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "mt-1 text-lg font-semibold tracking-tight",
					children: model || "Not configured"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "mt-0.5 text-xs text-(--ui-text-tertiary)",
					children: tokens.total > 0 ? `${tokens.total.toLocaleString()} tokens this session (${tokens.input} in / ${tokens.output} out)` : "No usage recorded this session"
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
			onClick: () => navigate("/models"),
			size: "sm",
			variant: "outline",
			children: model ? "Switch Model" : "Choose Model"
		})]
	});
}
function AutomationsBody({ cronJobs, offline }) {
	const navigate = useNavigate();
	if (offline) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
		className: "text-sm text-(--ui-text-tertiary)",
		children: "Unavailable — gateway offline."
	});
	if (cronJobs.length === 0) return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "py-2 text-center",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-(--ui-text-tertiary)",
				children: "No scheduled automations."
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-xs text-(--ui-text-tertiary)",
				children: "Create an automation to let AetherOS perform recurring work for you."
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				className: "mt-3",
				onClick: () => navigate("/automation-center"),
				size: "sm",
				variant: "outline",
				children: "Create Automation"
			})
		]
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-2",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
				className: "text-sm",
				role: "status",
				children: [
					cronJobs.length,
					" scheduled automation",
					cronJobs.length === 1 ? "" : "s",
					" · ",
					cronJobs.filter((j) => j.enabled).length,
					" active"
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
				className: "space-y-1.5",
				children: cronJobs.slice(0, 4).map((job) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
					className: "truncate rounded-lg border border-(--ui-stroke-tertiary) px-2.5 py-1.5 text-sm",
					children: [job.name || job.id, !job.enabled ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "ml-2 text-xs text-(--ui-text-tertiary)",
						children: "disabled"
					}) : null]
				}, job.id))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				onClick: () => navigate("/automation-center"),
				size: "sm",
				variant: "outline",
				children: "Open Automations"
			})
		]
	});
}
//#endregion
export { HomeView };

import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Bt as Tooltip, Ht as TooltipTrigger, La as Button, M as StatusDot, O as Badge, Ra as cn, S as ScrollArea, Vt as TooltipContent, Ya as useStore, _i as $messages, ao as require_jsx_runtime, fi as $busy, gi as $gatewayState, hi as $currentProvider, mi as $currentModel, oo as require_react } from "./index-B_yd1pEX.js";
import { t as Card } from "./card-CXjwIosc.js";
//#region src/app/computer-usage/ComputerUseView.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
function ComputerUseView() {
	const gatewayState = useStore($gatewayState);
	const busy = useStore($busy);
	const messages = useStore($messages);
	useStore($currentModel);
	useStore($currentProvider);
	const [isPreviewing, setIsPreviewing] = (0, import_react.useState)(false);
	const [isPaused, setIsPaused] = (0, import_react.useState)(false);
	const [targetWindow, setTargetWindow] = (0, import_react.useState)("any");
	const [actionTimeline, setActionTimeline] = (0, import_react.useState)([]);
	const [securityState, setSecurityState] = (0, import_react.useState)("protected");
	const securityIndicators = [
		{
			name: "Sandbox",
			status: "active",
			critical: false
		},
		{
			name: "Approval",
			status: "none",
			critical: false
		},
		{
			name: "Clipboard",
			status: "active",
			critical: false
		},
		{
			name: "File System",
			status: "active",
			critical: false
		},
		{
			name: "Terminal",
			status: "active",
			critical: false
		}
	];
	computeRecentActions(messages);
	function computeRecentActions(msgList) {
		const actions = [];
		msgList.filter((m) => m.role === "tool").forEach((m, i) => {
			const name = m.name || "unknown";
			m.result || m.content;
			let safeSummary;
			let technical;
			if (name.includes("mouse") || name.includes("click")) {
				safeSummary = "Clicking interface element";
				technical = m.details || void 0;
			} else if (name.includes("keyboard") || name.types) {
				safeSummary = "Sending keystrokes";
				technical = m.details || void 0;
			} else if (name.includes("browser") || name.includes("page")) {
				safeSummary = `Viewing ${m.target || "web page"}`;
				technical = m.url || void 0;
			} else if (name.includes("terminal") || name.exec) {
				safeSummary = "Executing command";
				technical = m.command || void 0;
			} else if (name.includes("file") || name.read || name.write) {
				safeSummary = `Operating on ${m.target || "file"}`;
				technical = m.path || void 0;
			} else {
				safeSummary = `Running ${name}`;
				technical = void 0;
			}
			actions.push({
				id: i,
				action: name,
				timestamp: m.timestamp || Date.now(),
				safeSummary,
				technical
			});
		});
		return actions.sort((a, b) => b.timestamp - a.timestamp).slice(0, 10);
	}
	const togglePause = () => {
		setIsPaused((prev) => !prev);
		if (gatewayState === "open") {}
	};
	const stopExecution = () => {
		setIsPreviewing(false);
		setIsPaused(false);
		setSecurityState("blocked");
	};
	(0, import_react.useEffect)(() => {
		if (gatewayState === "open" && busy) {
			const timer = setInterval(() => {}, 1e3);
			return () => clearInterval(timer);
		}
	}, [gatewayState, busy]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
		className: "h-full",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mx-auto max-w-7xl space-y-6 p-6",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
					className: "flex items-center justify-between border-b border-(--ui-stroke-tertiary) pb-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
						className: "text-2xl font-semibold tracking-tight",
						children: busy ? "Computer Use" : "AetherOS"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 text-sm text-(--ui-text-tertiary)",
						children: busy ? "Control your desktop" : ""
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, {
									size: "sm",
									status: busy ? "running" : "idle"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-xs font-medium text-(--ui-text-tertiary)",
									children: busy ? "Active" : "Idle"
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Tooltip, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TooltipTrigger, {
								asChild: true,
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									"aria-label": "Pause",
									className: "p-2 rounded hover:bg-(--ui-surface-secondary)",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-pause" })
								})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TooltipContent, { children: "Pause agent execution" })] }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Tooltip, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TooltipTrigger, {
								asChild: true,
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									"aria-label": "Stop",
									className: "p-2 rounded hover:bg-(--ui-surface-secondary)",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-stop" })
								})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TooltipContent, { children: "Stop current operation" })] })
						]
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "p-4 sm:p-6",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary) mb-3",
							children: "Live Screen"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "relative h-64 w-full rounded-lg overflow-hidden bg-(--ui-surface) mb-4",
							children: isPreviewing ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "absolute inset-0 bg-(--ui-surface-secondary) flex items-center justify-center text-(--ui-text-tertiary)",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "codicon codicon-video",
									style: { fontSize: "2rem" }
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "Previewing screen..." })]
							}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "h-full w-full bg-(--ui-surface-secondary) rounded-lg",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "h-full w-full flex items-center justify-center text-(--ui-text-tertiary)",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "codicon codicon-display",
										style: { fontSize: "2rem" }
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "Screen preview" })]
								})
							})
						}),
						isPreviewing && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "absolute inset-0 pointer-events-none",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "w-2 h-2 rounded-full bg-(--ui-accent) transform origin-top-left" })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-3 pt-3 border-t border-(--ui-border) flex flex-col gap-1 text-xs text-(--ui-text-tertiary)",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: ["Target: ", targetWindow || "Any window"] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: ["Mode: ", isPaused ? "Paused" : "Active"] })]
						})
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "p-4 sm:p-6",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary) mb-3",
						children: "Action Timeline"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "h-48 overflow-auto text-xs",
						children: actionTimeline.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "py-4 text-(--ui-text-tertiary)",
							children: "No actions recorded yet. Agent activity will appear here as operations complete."
						}) : actionTimeline.map((action, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: cn("flex items-center gap-2 px-2 py-1.5 border-b border-(--ui-border) last:border-0", i % 2 === 0 ? "bg-(--ui-surface)" : ""),
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, {
									size: "xs",
									status: "success"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "truncate flex-1 max-w-xs",
									children: action.safeSummary
								}),
								action.technical && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Tooltip, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TooltipContent, { children: action.technical }) })
							]
						}, action.id))
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "p-4 sm:p-6",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary) mb-3",
							children: "Security State"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "grid grid-cols-2 gap-2 text-xs mb-4",
							children: securityIndicators.map((ind, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: cn("flex items-center gap-1 px-2 py-1 rounded", ind.critical ? "bg-red-500/10 text-red-400" : "bg-(--ui-surface-secondary) text-(--ui-text-tertiary)"),
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-dot" }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: ind.name }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `text-(--ui-accent) ${ind.status === "pending" ? "animate-pulse" : ""}` })
								]
							}, i))
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "font-medium",
							children: "Current State:"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							variant: securityState === "blocked" ? "destructive" : securityState === "approval-required" ? "warn" : "default",
							children: securityState
						})] })
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "p-4 sm:p-6 border-t border-(--ui-stroke-tertiary)",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary) mb-3",
						children: "Control"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							className: cn("flex-1", isPaused ? "bg-(--ui-accent)" : "bg-(--ui-surface) text-(--ui-text)"),
							disabled: !isPreviewing,
							onClick: togglePause,
							children: isPaused ? "Resume" : "Pause"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							className: cn("flex-1", "bg-red-500/20 text-red-400"),
							onClick: stopExecution,
							children: "Stop"
						})]
					})]
				})
			]
		})
	});
}
//#endregion
export { ComputerUseView };

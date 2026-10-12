import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { M as getUsageAnalytics, R as restartGateway, it as updateAetheros, k as getStatus, l as getActionStatus, x as getLogs } from "./aetheros-DF_uJq_t.js";
import { Cn as unpinSession, Ea as IconChartBar, Hi as IconTrash, La as Button, Ma as IconActivity, Na as createReactComponent, Ra as cn, Si as sessionPinId, Sn as pinSession, Ya as useStore, ao as require_jsx_runtime, bt as PageLoader, ja as IconAlertCircle, ki as useI18n, oo as require_react, un as sessionTitle, va as IconDownload, vi as $sessions, vt as SearchField, x as upsertDesktopActionTask, xn as $pinnedSessionIds, xt as exportSession } from "./index-B_yd1pEX.js";
import { t as OverlayView } from "./overlay-view-DLw12qQQ.js";
import { t as useRefreshHotkey } from "./use-refresh-hotkey-CjSQqOti.js";
import { t as useRouteEnumParam } from "./use-route-enum-param-BgGOGZCn.js";
import { t as SegmentedControl } from "./segmented-control-BKG2J5LJ.js";
import { a as OverlaySplitLayout, i as OverlaySidebar, n as OverlayNavItem, t as OverlayMain } from "./overlay-split-layout-DUaHa8tB.js";
var IconBookmark = createReactComponent("outline", "bookmark", "Bookmark", [["path", {
	"d": "M18 7v14l-6 -4l-6 4v-14a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4",
	"key": "svg-0"
}]]);
var IconPin = createReactComponent("outline", "pin", "Pin", [
	["path", {
		"d": "M15 4.5l-4 4l-4 1.5l-1.5 1.5l7 7l1.5 -1.5l1.5 -4l4 -4",
		"key": "svg-0"
	}],
	["path", {
		"d": "M9 15l-4.5 4.5",
		"key": "svg-1"
	}],
	["path", {
		"d": "M14.5 4l5.5 5.5",
		"key": "svg-2"
	}]
]);
var IconBookmarkFilled = createReactComponent("filled", "bookmark-filled", "BookmarkFilled", [["path", {
	"d": "M14 2a5 5 0 0 1 5 5v14a1 1 0 0 1 -1.555 .832l-5.445 -3.63l-5.444 3.63a1 1 0 0 1 -1.55 -.72l-.006 -.112v-14a5 5 0 0 1 5 -5h4z",
	"key": "svg-0"
}]]);
//#endregion
//#region src/app/command-center/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var SECTIONS = [
	"sessions",
	"system",
	"usage"
];
var USAGE_PERIODS = [
	7,
	30,
	90
];
function formatTimestamp(value) {
	if (!value) return "";
	const date = /* @__PURE__ */ new Date(value * 1e3);
	if (Number.isNaN(date.getTime())) return "";
	return new Intl.DateTimeFormat(void 0, {
		dateStyle: "medium",
		timeStyle: "short"
	}).format(date);
}
function useDebouncedValue(value, delayMs) {
	const [debounced, setDebounced] = (0, import_react.useState)(value);
	(0, import_react.useEffect)(() => {
		const id = window.setTimeout(() => setDebounced(value), delayMs);
		return () => window.clearTimeout(id);
	}, [delayMs, value]);
	return debounced;
}
function RowIconButton({ children, className, onClick, title }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
		"aria-label": title,
		className: cn("text-(--ui-text-tertiary) hover:bg-(--chrome-action-hover) hover:text-foreground", className),
		onClick,
		size: "icon-xs",
		title,
		type: "button",
		variant: "ghost",
		children
	});
}
function EmptyPanel({ action, description, title }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "grid min-h-48 place-items-center px-6 text-center",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
			title && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "text-[length:var(--conversation-text-font-size)] font-medium text-foreground",
				children: title
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-1 text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) text-(--ui-text-tertiary)",
				children: description
			}),
			action && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-3 flex justify-center",
				children: action
			})
		] })
	});
}
function CommandCenterView({ initialSection, onClose, onDeleteSession, onOpenSession }) {
	const { t } = useI18n();
	const cc = t.commandCenter;
	const sessions = useStore($sessions);
	const pinnedSessionIds = useStore($pinnedSessionIds);
	const [section, setSection] = useRouteEnumParam("section", SECTIONS, initialSection ?? "sessions");
	const [query, setQuery] = (0, import_react.useState)("");
	const [status, setStatus] = (0, import_react.useState)(null);
	const [logs, setLogs] = (0, import_react.useState)([]);
	const [systemLoading, setSystemLoading] = (0, import_react.useState)(false);
	const [systemError, setSystemError] = (0, import_react.useState)("");
	const [systemAction, setSystemAction] = (0, import_react.useState)(null);
	const [usagePeriod, setUsagePeriod] = (0, import_react.useState)(30);
	const [usage, setUsage] = (0, import_react.useState)(null);
	const [usageLoading, setUsageLoading] = (0, import_react.useState)(false);
	const [usageError, setUsageError] = (0, import_react.useState)("");
	const usageRequestRef = (0, import_react.useRef)(0);
	const debouncedQuery = useDebouncedValue(query.trim(), 180);
	const filteredSessions = (0, import_react.useMemo)(() => {
		const sorted = [...sessions].sort((a, b) => {
			const left = a.last_active || a.started_at || 0;
			return (b.last_active || b.started_at || 0) - left;
		});
		const needle = debouncedQuery.toLowerCase();
		if (!needle) return sorted;
		return sorted.filter((session) => {
			return `${sessionTitle(session)} ${session.id}`.toLowerCase().includes(needle);
		});
	}, [debouncedQuery, sessions]);
	const refreshSystem = (0, import_react.useCallback)(async () => {
		setSystemLoading(true);
		setSystemError("");
		try {
			const [nextStatus, nextLogs] = await Promise.all([getStatus(), getLogs({
				file: "agent",
				lines: 120
			})]);
			setStatus(nextStatus);
			setLogs(nextLogs.lines);
		} catch (error) {
			setSystemError(error instanceof Error ? error.message : String(error));
		} finally {
			setSystemLoading(false);
		}
	}, []);
	const refreshUsage = (0, import_react.useCallback)(async (days) => {
		const requestId = usageRequestRef.current + 1;
		usageRequestRef.current = requestId;
		setUsageLoading(true);
		setUsageError("");
		try {
			const response = await getUsageAnalytics(days);
			if (usageRequestRef.current === requestId) setUsage(response);
		} catch (error) {
			if (usageRequestRef.current === requestId) setUsageError(error instanceof Error ? error.message : String(error));
		} finally {
			if (usageRequestRef.current === requestId) setUsageLoading(false);
		}
	}, []);
	(0, import_react.useEffect)(() => {
		if (section === "system" && !status && !systemLoading) refreshSystem();
	}, [
		refreshSystem,
		section,
		status,
		systemLoading
	]);
	(0, import_react.useEffect)(() => {
		if (section === "usage") refreshUsage(usagePeriod);
	}, [
		refreshUsage,
		section,
		usagePeriod
	]);
	useRefreshHotkey(() => {
		if (section === "system") refreshSystem();
		else if (section === "usage") refreshUsage(usagePeriod);
	});
	const sessionListHasResults = filteredSessions.length > 0;
	const runSystemAction = (0, import_react.useCallback)(async (kind) => {
		setSystemError("");
		try {
			const started = kind === "restart" ? await restartGateway() : await updateAetheros();
			let nextStatus = null;
			for (let attempt = 0; attempt < 18; attempt += 1) {
				await new Promise((resolve) => window.setTimeout(resolve, 1200));
				const polled = await getActionStatus(started.name, 180);
				nextStatus = polled;
				setSystemAction(polled);
				upsertDesktopActionTask(polled);
				if (!polled.running) break;
			}
			if (!nextStatus) {
				const pendingStatus = {
					exit_code: null,
					lines: [cc.actionStartedWaiting],
					name: started.name,
					pid: started.pid,
					running: true
				};
				setSystemAction(pendingStatus);
				upsertDesktopActionTask(pendingStatus);
			}
		} catch (error) {
			setSystemError(error instanceof Error ? error.message : String(error));
		} finally {
			refreshSystem();
		}
	}, [cc, refreshSystem]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayView, {
		closeLabel: cc.close,
		onClose,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(OverlaySplitLayout, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlaySidebar, { children: SECTIONS.map((value) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayNavItem, {
			active: section === value,
			icon: value === "sessions" ? IconPin : value === "system" ? IconActivity : IconChartBar,
			label: cc.sections[value],
			onClick: () => setSection(value)
		}, value)) }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(OverlayMain, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
			className: "mb-4 flex items-center justify-between gap-3",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-[length:var(--conversation-text-font-size)] font-semibold text-foreground",
					children: cc.sections[section]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-0.5 text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) text-(--ui-text-tertiary)",
					children: cc.sectionDescriptions[section]
				})]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex shrink-0 items-center gap-2",
				children: [section === "sessions" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SearchField, {
					containerClassName: "max-w-[40vw]",
					onChange: (next) => setQuery(next),
					placeholder: cc.searchPlaceholder,
					value: query
				}), section === "usage" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SegmentedControl, {
					onChange: (id) => setUsagePeriod(Number(id)),
					options: USAGE_PERIODS.map((value) => ({
						id: String(value),
						label: cc.days(value)
					})),
					value: String(usagePeriod)
				})]
			})]
		}), section === "sessions" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "min-h-0 flex-1 overflow-y-auto",
			children: !sessionListHasResults ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyPanel, { description: debouncedQuery ? cc.noResults : cc.noSessions }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", { children: filteredSessions.map((session) => {
				const pinId = sessionPinId(session);
				const pinned = pinnedSessionIds.includes(pinId);
				return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
					className: "group flex items-center gap-2 py-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: "min-w-0 flex-1 text-left",
						onClick: () => onOpenSession(session.id),
						type: "button",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "truncate text-[length:var(--conversation-text-font-size)] font-medium text-foreground",
							children: sessionTitle(session)
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "truncate text-[length:var(--conversation-caption-font-size)] text-(--ui-text-tertiary)",
							children: formatTimestamp(session.last_active || session.started_at)
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(RowIconButton, {
								onClick: () => pinned ? unpinSession(pinId) : pinSession(pinId),
								title: pinned ? cc.unpinSession : cc.pinSession,
								children: pinned ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconBookmarkFilled, { className: "size-3.5" }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconBookmark, { className: "size-3.5" })
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(RowIconButton, {
								onClick: () => void exportSession(session.id, {
									session,
									title: sessionTitle(session)
								}),
								title: cc.exportSession,
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconDownload, { className: "size-3.5" })
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(RowIconButton, {
								className: "hover:text-destructive",
								onClick: () => void onDeleteSession(session.id),
								title: cc.deleteSession,
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTrash, { className: "size-3.5" })
							})
						]
					})]
				}, session.id);
			}) })
		}) : section === "usage" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(UsagePanel, {
			error: usageError,
			loading: usageLoading,
			onRefresh: () => void refreshUsage(usagePeriod),
			period: usagePeriod,
			usage
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid min-h-0 flex-1 grid-rows-[auto_minmax(0,1fr)] gap-4",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "border-b border-(--ui-stroke-tertiary) pb-4",
				children: status ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "grid gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-start justify-between gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("size-2 rounded-full", status.gateway_running ? "bg-emerald-500" : "bg-amber-500") }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-[length:var(--conversation-text-font-size)] font-medium text-foreground",
									children: status.gateway_running ? cc.gatewayRunning : cc.gatewayStopped
								})]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "mt-1 text-[length:var(--conversation-caption-font-size)] text-(--ui-text-tertiary)",
								children: cc.aetherosActiveSessions(status.version, status.active_sessions)
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex shrink-0 items-center gap-1.5 whitespace-nowrap",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => void runSystemAction("restart"),
								size: "xs",
								variant: "text",
								children: cc.restartMessaging
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => void runSystemAction("update"),
								size: "xs",
								variant: "textStrong",
								children: cc.updateAetheros
							})]
						})]
					}), systemAction && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "text-[length:var(--conversation-caption-font-size)] text-(--ui-text-tertiary)",
						children: [
							systemAction.name,
							" ·",
							" ",
							systemAction.running ? cc.actionRunning : systemAction.exit_code === 0 ? cc.actionDone : cc.actionFailed
						]
					})]
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageLoader, {
					className: "min-h-32",
					label: cc.loadingStatus
				})
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex min-h-0 flex-col",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mb-2 flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-[0.625rem] font-medium uppercase tracking-[0.08em] text-(--ui-text-tertiary)",
						children: cc.recentLogs
					}), systemError && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "inline-flex items-center gap-1 text-[length:var(--conversation-caption-font-size)] text-destructive",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconAlertCircle, { className: "size-3.5" }), systemError]
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
					className: "min-h-0 flex-1 overflow-auto whitespace-pre-wrap wrap-break-word rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) p-3 font-mono text-[0.65rem] leading-relaxed text-(--ui-text-tertiary)",
					children: logs.length ? logs.join("\n") : cc.noLogs
				})]
			})]
		})] })] })
	});
}
function formatTokens(value) {
	const num = Number(value || 0);
	if (num >= 1e6) return `${(num / 1e6).toFixed(1)}M`;
	if (num >= 1e3) return `${(num / 1e3).toFixed(1)}K`;
	return num.toLocaleString();
}
function formatCost(value) {
	const num = Number(value || 0);
	if (num === 0) return "$0.00";
	if (num < .01) return "<$0.01";
	return `$${num.toFixed(2)}`;
}
function formatInteger(value) {
	return Number(value ?? 0).toLocaleString();
}
function UsagePanel({ error, loading, onRefresh, period, usage }) {
	const { t } = useI18n();
	const cc = t.commandCenter;
	const daily = (0, import_react.useMemo)(() => usage?.daily ?? [], [usage]);
	const totals = usage?.totals;
	const byModel = usage?.by_model ?? [];
	const topSkills = usage?.skills?.top_skills ?? [];
	const maxTokens = (0, import_react.useMemo)(() => {
		if (!daily.length) return 1;
		return daily.reduce((acc, entry) => Math.max(acc, (entry.input_tokens || 0) + (entry.output_tokens || 0)), 1);
	}, [daily]);
	if (!totals) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "min-h-0 flex-1",
		children: loading ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageLoader, {
			className: "min-h-48",
			label: cc.loadingUsage
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyPanel, {
			action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				onClick: onRefresh,
				size: "xs",
				variant: "text",
				children: cc.retry
			}),
			description: cc.noUsage(period)
		})
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto pb-2",
		children: [
			error && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
				className: "inline-flex items-center gap-1 text-[length:var(--conversation-caption-font-size)] text-destructive",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconAlertCircle, { className: "size-3.5" }), error]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid grid-cols-2 gap-x-4 gap-y-4 border-b border-(--ui-stroke-tertiary) pb-5 sm:grid-cols-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(UsageStat, {
						label: cc.statSessions,
						value: formatInteger(totals.total_sessions)
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(UsageStat, {
						label: cc.statApiCalls,
						value: formatInteger(totals.total_api_calls)
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(UsageStat, {
						label: cc.statTokens,
						value: `${formatTokens(totals.total_input)} / ${formatTokens(totals.total_output)}`
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(UsageStat, {
						hint: totals.total_actual_cost > 0 ? cc.actualCost(formatCost(totals.total_actual_cost)) : void 0,
						label: cc.statCost,
						value: formatCost(totals.total_estimated_cost)
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mb-2 flex items-baseline justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "text-[0.625rem] font-medium uppercase tracking-[0.08em] text-(--ui-text-tertiary)",
					children: cc.dailyTokens
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
					className: "flex items-center gap-3 text-[0.65rem] text-(--ui-text-tertiary)",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "inline-flex items-center gap-1",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "size-2 rounded-[1px] bg-[color:var(--dt-primary)]/60" }),
							" ",
							cc.input
						]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "inline-flex items-center gap-1",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "size-2 rounded-[1px] bg-emerald-500/70" }),
							" ",
							cc.output
						]
					})]
				})]
			}), daily.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid h-24 place-items-center text-[length:var(--conversation-caption-font-size)] text-(--ui-text-tertiary)",
				children: cc.noDailyActivity
			}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex h-24 items-end gap-px",
				children: daily.map((entry) => {
					const inputH = Math.round((entry.input_tokens || 0) / maxTokens * 96);
					const outputH = Math.round((entry.output_tokens || 0) / maxTokens * 96);
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "group relative flex h-24 min-w-0 flex-1 flex-col justify-end",
						title: `${entry.day} · in ${formatTokens(entry.input_tokens)} · out ${formatTokens(entry.output_tokens)}`,
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "w-full rounded-t-[1px] bg-[color:var(--dt-primary)]/50",
							style: { height: Math.max(inputH, entry.input_tokens > 0 ? 1 : 0) }
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "w-full bg-emerald-500/60",
							style: { height: Math.max(outputH, entry.output_tokens > 0 ? 1 : 0) }
						})]
					}, entry.day);
				})
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-1 flex justify-between text-[0.6rem] text-(--ui-text-tertiary)",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: daily[0]?.day }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: daily[daily.length - 1]?.day })]
			})] })] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid min-h-0 gap-x-8 gap-y-5 border-t border-(--ui-stroke-tertiary) pt-5 sm:grid-cols-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(UsageList, {
					emptyLabel: cc.noModelUsage,
					rows: byModel.slice(0, 6).map((entry) => ({
						key: entry.model,
						label: entry.model,
						value: `${formatTokens((entry.input_tokens || 0) + (entry.output_tokens || 0))} · ${formatCost(entry.estimated_cost)}`
					})),
					title: cc.topModels
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(UsageList, {
					emptyLabel: cc.noSkillActivity,
					rows: topSkills.slice(0, 6).map((entry) => ({
						key: entry.skill,
						label: entry.skill,
						value: cc.actions(entry.total_count.toLocaleString())
					})),
					title: cc.topSkills
				})]
			})
		]
	});
}
function UsageList({ emptyLabel, rows, title }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		className: "min-w-0",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mb-1.5 text-[0.625rem] font-medium uppercase tracking-[0.08em] text-(--ui-text-tertiary)",
			children: title
		}), rows.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "text-[length:var(--conversation-caption-font-size)] text-(--ui-text-tertiary)",
			children: emptyLabel
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", { children: rows.map((row) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
			className: "flex items-center justify-between gap-2 py-1.5",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "min-w-0 truncate font-mono text-[0.7rem] text-foreground",
				children: row.label
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "shrink-0 text-[0.65rem] text-(--ui-text-tertiary)",
				children: row.value
			})]
		}, row.key)) })]
	});
}
function UsageStat({ hint, label, value }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "min-w-0",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "text-[0.625rem] font-medium uppercase tracking-[0.12em] text-(--ui-text-tertiary)",
				children: label
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-1 truncate text-base font-semibold tracking-tight text-foreground",
				children: value
			}),
			hint && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-0.5 truncate text-[0.62rem] text-(--ui-text-tertiary)",
				children: hint
			})
		]
	});
}
//#endregion
export { CommandCenterView };

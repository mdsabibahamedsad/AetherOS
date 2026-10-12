import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { F as pauseCronJob, a as deleteCronJob, at as updateCronJob, g as getCronJobs, h as getCronJobRuns, r as createCronJob, rt as triggerCronJob, z as resumeCronJob } from "./aetheros-DF_uJq_t.js";
import { Aa as IconAlertTriangle, An as Dialog, C as Select, D as SelectValue, Di as notify, Dn as setCronJobs, E as SelectTrigger, En as setCronFocusJobId, Fn as DialogTitle, Ia as Codicon, La as Button, Mn as DialogDescription, Nn as DialogFooter, Oi as notifyError, On as updateCronJobs, Pn as DialogHeader, Ra as cn, T as SelectItem, Tn as $cronJobs, Ya as useStore, ao as require_jsx_runtime, bt as PageLoader, ct as jobTitle, jn as DialogContent, jt as Textarea, ki as useI18n, ni as Input, oo as require_react, ot as STATE_DOT, st as jobState, vt as SearchField, w as SelectContent, wn as $cronFocusJobId, xa as IconClock } from "./index-B_yd1pEX.js";
import { t as OverlayView } from "./overlay-view-DLw12qQQ.js";
import { t as useRefreshHotkey } from "./use-refresh-hotkey-CjSQqOti.js";
import { a as OverlaySplitLayout, i as OverlaySidebar, r as OverlayNewButton, t as OverlayMain } from "./overlay-split-layout-DUaHa8tB.js";
//#region src/app/cron/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var DEFAULT_DELIVER = "local";
var DELIVERY_VALUES = [
	"local",
	"telegram",
	"discord",
	"slack",
	"email"
];
var SCHEDULE_OPTIONS = [
	{
		expr: "0 9 * * *",
		value: "daily"
	},
	{
		expr: "0 9 * * 1-5",
		value: "weekdays"
	},
	{
		expr: "0 9 * * 1",
		value: "weekly"
	},
	{
		expr: "0 9 1 * *",
		value: "monthly"
	},
	{
		expr: "0 * * * *",
		value: "hourly"
	},
	{
		expr: "*/15 * * * *",
		value: "every-15-minutes"
	},
	{ value: "custom" }
];
var STATE_TONE = {
	enabled: "good",
	scheduled: "good",
	running: "good",
	paused: "warn",
	disabled: "muted",
	error: "bad",
	completed: "muted"
};
var PILL_TONE = {
	good: "bg-primary/10 text-primary",
	muted: "bg-muted text-muted-foreground",
	warn: "bg-amber-500/10 text-amber-600 dark:text-amber-300",
	bad: "bg-destructive/10 text-destructive"
};
var asText = (value) => typeof value === "string" ? value : "";
var truncate = (value, max = 80) => value.length > max ? `${value.slice(0, max)}…` : value;
function jobName(job) {
	return asText(job.name).trim();
}
function jobPrompt(job) {
	return asText(job.prompt);
}
function jobScheduleDisplay(job) {
	return asText(job.schedule_display) || asText(job.schedule?.display) || asText(job.schedule?.expr) || "—";
}
function jobScheduleExpr(job) {
	return asText(job.schedule?.expr) || asText(job.schedule_display) || "";
}
function jobDeliver(job) {
	return asText(job.deliver) || DEFAULT_DELIVER;
}
function cronParts(expr) {
	const parts = expr.trim().replace(/\s+/g, " ").split(" ");
	return parts.length === 5 ? parts : null;
}
function dayName(value, c) {
	return c.days[value] ?? c.dayFallback(value);
}
function formatCronTime(minute, hour) {
	const numericHour = Number(hour);
	const numericMinute = Number(minute);
	if (!Number.isInteger(numericHour) || !Number.isInteger(numericMinute)) return `${hour}:${minute}`;
	return new Date(2e3, 0, 1, numericHour, numericMinute).toLocaleTimeString(void 0, {
		hour: "numeric",
		minute: "2-digit"
	});
}
function isIntegerToken(value) {
	return /^\d+$/.test(value);
}
function scheduleOptionForExpr(expr) {
	const normalized = expr.trim().replace(/\s+/g, " ");
	const exactMatch = SCHEDULE_OPTIONS.find((option) => option.expr === normalized);
	if (exactMatch) return exactMatch;
	const parts = cronParts(normalized);
	if (!parts) return SCHEDULE_OPTIONS[SCHEDULE_OPTIONS.length - 1];
	const [minute, hour, dayOfMonth, month, dayOfWeek] = parts;
	if (dayOfMonth === "*" && month === "*" && dayOfWeek === "*" && isIntegerToken(minute) && isIntegerToken(hour)) return SCHEDULE_OPTIONS.find((option) => option.value === "daily") ?? SCHEDULE_OPTIONS[0];
	if (dayOfMonth === "*" && month === "*" && dayOfWeek === "1-5" && isIntegerToken(minute) && isIntegerToken(hour)) return SCHEDULE_OPTIONS.find((option) => option.value === "weekdays") ?? SCHEDULE_OPTIONS[0];
	if (dayOfMonth === "*" && month === "*" && isIntegerToken(dayOfWeek) && isIntegerToken(minute) && isIntegerToken(hour)) return SCHEDULE_OPTIONS.find((option) => option.value === "weekly") ?? SCHEDULE_OPTIONS[0];
	if (month === "*" && dayOfWeek === "*" && isIntegerToken(dayOfMonth) && isIntegerToken(minute) && isIntegerToken(hour)) return SCHEDULE_OPTIONS.find((option) => option.value === "monthly") ?? SCHEDULE_OPTIONS[0];
	if (hour === "*" && dayOfMonth === "*" && month === "*" && dayOfWeek === "*" && isIntegerToken(minute)) return SCHEDULE_OPTIONS.find((option) => option.value === "hourly") ?? SCHEDULE_OPTIONS[0];
	if (normalized === "*/15 * * * *") return SCHEDULE_OPTIONS.find((option) => option.value === "every-15-minutes") ?? SCHEDULE_OPTIONS[0];
	return SCHEDULE_OPTIONS[SCHEDULE_OPTIONS.length - 1];
}
function scheduleSummary(option, expr, c) {
	const parts = cronParts(expr);
	if (!parts) return c.scheduleHints[option.value] ?? "";
	const [minute, hour, dayOfMonth, , dayOfWeek] = parts;
	if (option.value === "daily") return c.everyDayAt(formatCronTime(minute, hour));
	if (option.value === "weekdays") return c.weekdaysAt(formatCronTime(minute, hour));
	if (option.value === "weekly") return c.everyDayOfWeekAt(dayName(dayOfWeek, c), formatCronTime(minute, hour));
	if (option.value === "monthly") return c.monthlyOnDayAt(dayOfMonth, formatCronTime(minute, hour));
	if (option.value === "hourly") return minute === "0" ? c.topOfHour : c.everyHourAt(minute.padStart(2, "0"));
	return c.scheduleHints[option.value] ?? "";
}
function formatTime(iso) {
	if (!iso) return "—";
	const date = new Date(iso);
	if (Number.isNaN(date.valueOf())) return iso;
	return date.toLocaleString();
}
function matchesQuery(job, q) {
	if (!q) return true;
	const needle = q.toLowerCase();
	return [
		jobTitle(job),
		jobPrompt(job),
		jobScheduleDisplay(job),
		jobScheduleExpr(job),
		jobDeliver(job)
	].some((value) => value.toLowerCase().includes(needle));
}
function CronView({ onClose, onOpenSession, setStatusbarItemGroup: _setStatusbarItemGroup }) {
	const { t } = useI18n();
	const c = t.cron;
	const jobs = useStore($cronJobs);
	const [loading, setLoading] = (0, import_react.useState)(jobs.length === 0);
	const [query, setQuery] = (0, import_react.useState)("");
	const [busyJobId, setBusyJobId] = (0, import_react.useState)(null);
	const [selectedJobId, setSelectedJobId] = (0, import_react.useState)(null);
	const pendingScrollRef = (0, import_react.useRef)(null);
	const focusJobId = useStore($cronFocusJobId);
	const [editor, setEditor] = (0, import_react.useState)({ mode: "closed" });
	const [pendingDelete, setPendingDelete] = (0, import_react.useState)(null);
	const [deleting, setDeleting] = (0, import_react.useState)(false);
	const refresh = (0, import_react.useCallback)(async () => {
		try {
			setCronJobs(await getCronJobs());
		} catch (err) {
			notifyError(err, c.failedLoad);
		} finally {
			setLoading(false);
		}
	}, [c]);
	useRefreshHotkey(refresh);
	(0, import_react.useEffect)(() => {
		refresh();
	}, [refresh]);
	(0, import_react.useEffect)(() => {
		if (!focusJobId) return;
		const match = jobs.find((job) => job.id === focusJobId || jobName(job) === focusJobId);
		if (match) {
			setSelectedJobId(match.id);
			pendingScrollRef.current = match.id;
		}
		setCronFocusJobId(null);
	}, [focusJobId, jobs]);
	const visibleJobs = (0, import_react.useMemo)(() => jobs.filter((job) => matchesQuery(job, query.trim())).sort((a, b) => jobTitle(a).localeCompare(jobTitle(b))), [jobs, query]);
	const selectedJob = (0, import_react.useMemo)(() => visibleJobs.find((job) => job.id === selectedJobId) ?? visibleJobs[0] ?? null, [visibleJobs, selectedJobId]);
	(0, import_react.useEffect)(() => {
		const target = pendingScrollRef.current;
		if (!target || selectedJob?.id !== target) return;
		pendingScrollRef.current = null;
		requestAnimationFrame(() => {
			document.querySelector(`[data-cron-row="${CSS.escape(target)}"]`)?.scrollIntoView({ block: "nearest" });
		});
	}, [selectedJob]);
	const totalCount = jobs.length;
	async function handlePauseResume(job) {
		setBusyJobId(job.id);
		try {
			const isPaused = jobState(job) === "paused";
			const updated = isPaused ? await resumeCronJob(job.id) : await pauseCronJob(job.id);
			updateCronJobs((rows) => rows.map((row) => row.id === job.id ? updated : row));
			notify({
				kind: "success",
				title: isPaused ? c.resumed : c.paused,
				message: truncate(jobTitle(job), 60)
			});
		} catch (err) {
			notifyError(err, c.failedUpdate);
		} finally {
			setBusyJobId(null);
		}
	}
	async function handleTrigger(job) {
		setBusyJobId(job.id);
		try {
			const updated = await triggerCronJob(job.id);
			updateCronJobs((rows) => rows.map((row) => row.id === job.id ? updated : row));
			notify({
				kind: "success",
				title: c.triggered,
				message: truncate(jobTitle(job), 60)
			});
		} catch (err) {
			notifyError(err, c.failedTrigger);
		} finally {
			setBusyJobId(null);
		}
	}
	async function handleConfirmDelete() {
		if (!pendingDelete) return;
		setDeleting(true);
		try {
			await deleteCronJob(pendingDelete.id);
			updateCronJobs((rows) => rows.filter((row) => row.id !== pendingDelete.id));
			notify({
				kind: "success",
				title: c.deleted,
				message: truncate(jobTitle(pendingDelete), 60)
			});
			setPendingDelete(null);
		} catch (err) {
			notifyError(err, c.failedDelete);
		} finally {
			setDeleting(false);
		}
	}
	async function handleEditorSave(values) {
		if (editor.mode === "create") {
			const created = await createCronJob({
				prompt: values.prompt,
				schedule: values.schedule,
				name: values.name || void 0,
				deliver: values.deliver || DEFAULT_DELIVER
			});
			updateCronJobs((rows) => [...rows, created]);
			notify({
				kind: "success",
				title: c.created,
				message: truncate(jobTitle(created), 60)
			});
		} else if (editor.mode === "edit") {
			const updated = await updateCronJob(editor.job.id, {
				prompt: values.prompt,
				schedule: values.schedule,
				name: values.name,
				deliver: values.deliver
			});
			updateCronJobs((rows) => rows.map((row) => row.id === updated.id ? updated : row));
			notify({
				kind: "success",
				title: c.updated,
				message: truncate(jobTitle(updated), 60)
			});
		}
		setEditor({ mode: "closed" });
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(OverlayView, {
		closeLabel: c.close,
		onClose,
		children: [
			loading && jobs.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageLoader, { label: c.loading }) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(OverlaySplitLayout, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(OverlaySidebar, { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayNewButton, {
					label: c.newCron,
					onClick: () => setEditor({ mode: "create" })
				}),
				totalCount > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SearchField, {
					"aria-label": c.search,
					containerClassName: "mb-1 w-full px-2",
					onChange: setQuery,
					placeholder: c.search,
					value: query
				}),
				visibleJobs.map((job) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CronJobListRow, {
					active: selectedJob?.id === job.id,
					c,
					job,
					onSelect: () => setSelectedJobId(job.id)
				}, job.id)),
				visibleJobs.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "px-2 py-4 text-center text-xs text-muted-foreground",
					children: totalCount === 0 ? c.emptyTitleNew : c.emptyTitleSearch
				})
			] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayMain, {
				className: "px-0",
				children: selectedJob ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CronJobDetail, {
					busy: busyJobId === selectedJob.id,
					c,
					job: selectedJob,
					onDelete: () => setPendingDelete(selectedJob),
					onEdit: () => setEditor({
						mode: "edit",
						job: selectedJob
					}),
					onOpenSession,
					onPauseResume: () => void handlePauseResume(selectedJob),
					onTrigger: () => void handleTrigger(selectedJob)
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid h-full place-items-center px-6 py-12 text-center text-sm text-muted-foreground",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconClock, { className: "mx-auto size-6 text-muted-foreground/60" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-3",
						children: totalCount === 0 ? c.emptyDescNew : c.emptyDescSearch
					})] })
				})
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CronEditorDialog, {
				editor,
				onClose: () => setEditor({ mode: "closed" }),
				onSave: handleEditorSave
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dialog, {
				onOpenChange: (open) => !open && !deleting && setPendingDelete(null),
				open: pendingDelete !== null,
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, {
					className: "max-w-md",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, { children: c.deleteTitle }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogDescription, { children: pendingDelete ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
						c.deleteDescPrefix,
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "font-medium text-foreground",
							children: truncate(jobTitle(pendingDelete), 60)
						}),
						c.deleteDescSuffix
					] }) : null })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogFooter, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: deleting,
						onClick: () => setPendingDelete(null),
						variant: "outline",
						children: t.common.cancel
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: deleting,
						onClick: () => void handleConfirmDelete(),
						variant: "destructive",
						children: deleting ? c.deleting : t.common.delete
					})] })]
				})
			})
		]
	});
}
function CronJobListRow({ active, c, job, onSelect }) {
	const state = jobState(job);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		className: cn("flex w-full flex-col items-start gap-0.5 rounded-md px-2 py-1.5 text-left transition-colors", active ? "bg-accent text-foreground" : "text-foreground/85 hover:bg-accent/60"),
		"data-cron-row": job.id,
		onClick: onSelect,
		type: "button",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
			className: "flex w-full items-center gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				"aria-hidden": "true",
				className: cn("size-1.5 shrink-0 rounded-full", STATE_DOT[state] ?? "bg-muted-foreground")
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "min-w-0 flex-1 truncate text-sm font-medium",
				children: jobTitle(job)
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: "truncate pl-3.5 text-[0.66rem] text-muted-foreground",
			children: jobScheduleDisplay(job)
		})]
	});
}
function CronJobDetail({ busy, c, job, onDelete, onEdit, onOpenSession, onPauseResume, onTrigger }) {
	const state = jobState(job);
	const isPaused = state === "paused";
	const deliver = jobDeliver(job);
	const prompt = jobPrompt(job);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex h-full min-h-0 flex-col",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "min-h-0 flex-1 overflow-y-auto",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mx-auto max-w-2xl space-y-6 px-6 py-6",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
					className: "space-y-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex flex-wrap items-start justify-between gap-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "min-w-0 space-y-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex flex-wrap items-center gap-2",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
											className: "text-xl font-semibold tracking-tight",
											children: jobTitle(job)
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatePill, {
											tone: STATE_TONE[state] ?? "muted",
											children: c.states[state] ?? state
										}),
										deliver && deliver !== DEFAULT_DELIVER && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatePill, {
											tone: "muted",
											children: c.deliveryLabels[deliver] ?? deliver
										})
									]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex flex-wrap items-center gap-x-4 gap-y-1 text-[0.7rem] text-muted-foreground",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
											className: "inline-flex items-center gap-1",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconClock, { className: "size-3" }), jobScheduleDisplay(job)]
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
											c.last,
											" ",
											formatTime(job.last_run_at)
										] }),
										/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
											c.next,
											" ",
											formatTime(job.next_run_at)
										] })
									]
								})]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex shrink-0 items-center gap-1",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
										disabled: busy,
										onClick: onPauseResume,
										size: "sm",
										variant: "outline",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
											name: isPaused ? "play" : "debug-pause",
											size: "0.875rem"
										}), isPaused ? c.resumeTitle : c.pauseTitle]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
										disabled: busy,
										onClick: onTrigger,
										size: "sm",
										variant: "outline",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
											name: "zap",
											size: "0.875rem"
										}), c.triggerNow]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
										onClick: onEdit,
										size: "sm",
										variant: "outline",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
											name: "edit",
											size: "0.875rem"
										}), c.edit]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
										className: "text-muted-foreground hover:bg-destructive/10 hover:text-destructive",
										onClick: onDelete,
										size: "sm",
										variant: "ghost",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
											name: "trash",
											size: "0.875rem"
										})
									})
								]
							})]
						}),
						prompt && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "line-clamp-3 text-xs text-muted-foreground",
							children: prompt
						}),
						job.last_error && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "inline-flex items-start gap-1 text-[0.7rem] text-destructive",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconAlertTriangle, { className: "mt-px size-3 shrink-0" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "line-clamp-2",
								children: job.last_error
							})]
						})
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CronJobRuns, {
					c,
					jobId: job.id,
					onOpenSession
				})]
			})
		})
	});
}
function formatRunTime(seconds) {
	if (!seconds) return "—";
	const date = /* @__PURE__ */ new Date(seconds * 1e3);
	return Number.isNaN(date.valueOf()) ? "—" : date.toLocaleString();
}
var RUNS_POLL_INTERVAL_MS = 8e3;
function CronJobRuns({ c, jobId, onOpenSession }) {
	const [runs, setRuns] = (0, import_react.useState)(null);
	(0, import_react.useEffect)(() => {
		let cancelled = false;
		const load = () => getCronJobRuns(jobId).then((result) => {
			if (!cancelled) setRuns(result);
		}).catch(() => {
			if (!cancelled) setRuns((prev) => prev ?? []);
		});
		load();
		const intervalId = window.setInterval(() => {
			if (document.visibilityState === "visible") load();
		}, RUNS_POLL_INTERVAL_MS);
		const onVisible = () => {
			if (document.visibilityState === "visible") load();
		};
		document.addEventListener("visibilitychange", onVisible);
		return () => {
			cancelled = true;
			window.clearInterval(intervalId);
			document.removeEventListener("visibilitychange", onVisible);
		};
	}, [jobId]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mb-1.5 text-[0.62rem] font-medium uppercase tracking-wide text-muted-foreground",
		children: [c.runHistory, runs && runs.length > 0 ? ` · ${runs.length}` : ""]
	}), runs === null ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex items-center gap-1.5 py-1 text-xs text-muted-foreground",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
			name: "loading",
			size: "0.75rem",
			spinning: true
		})
	}) : runs.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "py-1 text-xs text-muted-foreground",
		children: c.noRuns
	}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex flex-col gap-px",
		children: runs.map((run) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
			className: "flex items-center justify-between gap-3 rounded-md px-2 py-1 text-left text-xs hover:bg-(--chrome-action-hover) focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40",
			onClick: () => onOpenSession?.(run.id),
			type: "button",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "truncate text-foreground",
				children: run.title?.trim() || run.preview?.trim() || run.id
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "shrink-0 text-[0.62rem] text-muted-foreground tabular-nums",
				children: formatRunTime(run.last_active || run.started_at)
			})]
		}, run.id))
	})] });
}
function StatePill({ children, tone }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		className: cn("inline-flex items-center rounded-full px-1.5 py-0.5 text-[0.64rem] capitalize", PILL_TONE[tone]),
		children
	});
}
function CronEditorDialog({ editor, onClose, onSave }) {
	const { t } = useI18n();
	const c = t.cron;
	const open = editor.mode !== "closed";
	const isEdit = editor.mode === "edit";
	const initial = isEdit ? editor.job : null;
	const [name, setName] = (0, import_react.useState)("");
	const [prompt, setPrompt] = (0, import_react.useState)("");
	const [schedule, setSchedule] = (0, import_react.useState)("");
	const [schedulePreset, setSchedulePreset] = (0, import_react.useState)("daily");
	const [deliver, setDeliver] = (0, import_react.useState)(DEFAULT_DELIVER);
	const [saving, setSaving] = (0, import_react.useState)(false);
	const [error, setError] = (0, import_react.useState)(null);
	(0, import_react.useEffect)(() => {
		if (!open) return;
		setName(initial ? jobName(initial) : "");
		setPrompt(initial ? jobPrompt(initial) : "");
		setSchedule(initial ? jobScheduleExpr(initial) : SCHEDULE_OPTIONS[0].expr ?? "");
		setSchedulePreset(initial ? scheduleOptionForExpr(jobScheduleExpr(initial)).value : "daily");
		setDeliver(initial ? jobDeliver(initial) : DEFAULT_DELIVER);
		setError(null);
		setSaving(false);
	}, [initial, open]);
	const selectedScheduleOption = SCHEDULE_OPTIONS.find((candidate) => candidate.value === schedulePreset) ?? SCHEDULE_OPTIONS[0];
	function handleSchedulePresetChange(nextPreset) {
		setSchedulePreset(nextPreset);
		setError(null);
		const option = SCHEDULE_OPTIONS.find((candidate) => candidate.value === nextPreset);
		if (option?.expr) setSchedule(option.expr);
		else if (scheduleOptionForExpr(schedule).value !== "custom") setSchedule("");
	}
	const scheduleHint = scheduleSummary(selectedScheduleOption, schedule, c);
	async function handleSubmit(event) {
		event.preventDefault();
		const trimmedPrompt = prompt.trim();
		const trimmedSchedule = schedule.trim();
		if (!trimmedPrompt || !trimmedSchedule) {
			setError(c.promptScheduleRequired);
			return;
		}
		setSaving(true);
		setError(null);
		try {
			await onSave({
				deliver,
				name: name.trim(),
				prompt: trimmedPrompt,
				schedule: trimmedSchedule
			});
		} catch (err) {
			setError(err instanceof Error ? err.message : c.failedSave);
		} finally {
			setSaving(false);
		}
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dialog, {
		onOpenChange: (value) => !value && !saving && onClose(),
		open,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, {
			className: "max-w-lg",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, { children: isEdit ? c.editTitle : c.createTitle }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogDescription, { children: isEdit ? c.editDesc : c.createDesc })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("form", {
				className: "grid gap-4",
				onSubmit: handleSubmit,
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
						htmlFor: "cron-name",
						label: c.nameLabel,
						optional: true,
						optionalLabel: c.optional,
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							autoFocus: true,
							id: "cron-name",
							onChange: (event) => setName(event.target.value),
							placeholder: c.namePlaceholder,
							value: name
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
						htmlFor: "cron-prompt",
						label: c.promptLabel,
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
							className: "min-h-24 font-mono",
							id: "cron-prompt",
							onChange: (event) => setPrompt(event.target.value),
							placeholder: c.promptPlaceholder,
							value: prompt
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid items-start gap-4 sm:grid-cols-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
							htmlFor: "cron-frequency",
							label: c.frequencyLabel,
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
								onValueChange: handleSchedulePresetChange,
								value: schedulePreset,
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
									className: "h-9 rounded-md",
									id: "cron-frequency",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: SCHEDULE_OPTIONS.map((option) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: option.value,
									children: c.scheduleLabels[option.value]
								}, option.value)) })]
							})
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
							htmlFor: "cron-deliver",
							label: c.deliverLabel,
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
								onValueChange: setDeliver,
								value: deliver,
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
									className: "h-9 rounded-md",
									id: "cron-deliver",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: DELIVERY_VALUES.map((value) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value,
									children: c.deliveryLabels[value]
								}, value)) })]
							})
						})]
					}),
					schedulePreset === "custom" ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Field, {
						htmlFor: "cron-schedule",
						label: c.customScheduleLabel,
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							className: "font-mono",
							id: "cron-schedule",
							onChange: (event) => setSchedule(event.target.value),
							placeholder: c.customPlaceholder,
							value: schedule
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(FieldHint, { children: c.customHint })]
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "rounded-md bg-(--ui-bg-quinary) px-3 py-2",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex flex-wrap items-center justify-between gap-2 text-xs",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "font-medium text-foreground",
								children: scheduleHint
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "font-mono text-muted-foreground",
								children: schedule
							})]
						})
					}),
					error && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-start gap-2 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconAlertTriangle, { className: "mt-0.5 size-3.5 shrink-0" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: error })]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogFooter, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: saving,
						onClick: onClose,
						type: "button",
						variant: "outline",
						children: t.common.cancel
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: saving,
						type: "submit",
						children: saving ? t.common.saving : isEdit ? c.saveChanges : c.createAction
					})] })
				]
			})]
		})
	});
}
function Field({ children, htmlFor, label, optional, optionalLabel }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "grid gap-1.5",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "flex items-baseline gap-2 text-xs font-medium text-foreground",
			htmlFor,
			children: [label, optional && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-[0.65rem] font-normal text-muted-foreground",
				children: optionalLabel
			})]
		}), children]
	});
}
function FieldHint({ children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
		className: "text-[0.66rem] leading-4 text-muted-foreground",
		children
	});
}
//#endregion
export { CronView };

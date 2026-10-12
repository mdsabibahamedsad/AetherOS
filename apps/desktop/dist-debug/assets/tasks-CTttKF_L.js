import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { La as Button, M as StatusDot, O as Badge, Ra as cn, S as ScrollArea, Tn as $cronJobs, Ya as useStore, ao as require_jsx_runtime, b as $desktopActionTasks, eo as useNavigate, oo as require_react } from "./index-B_yd1pEX.js";
import { t as Card } from "./card-CXjwIosc.js";
import { t as EmptyState } from "./empty-state-DbK8L0dQ.js";
import { t as formatTimestamp } from "./format-timestamp-DA7XesLP.js";
import { a as TableHeader, i as TableHead, n as TableBody, o as TableRow, r as TableCell, t as Table } from "./table-DCnw6rtb.js";
//#region src/app/tasks/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
function TasksView() {
	const navigate = useNavigate();
	const cronJobs = useStore($cronJobs);
	const actionTasks = useStore($desktopActionTasks);
	const allTasks = [...cronJobs.map((job) => ({
		id: `cron:${job.id}`,
		title: job.title || "Unnamed Cron Job",
		description: job.schedule || "Scheduled job",
		status: job.status || "pending",
		type: "cron",
		createdAt: job.createdAt || Date.now(),
		lastRun: job.nextRun || null,
		agent: job.agent || "System"
	})), ...Object.values(actionTasks).map((task) => ({
		id: `action:${task.status.name}`,
		title: task.status.name || "Action",
		description: task.status.description || "",
		status: task.status.running ? "running" : task.status.exit_code === 0 ? "success" : "error",
		type: "action",
		createdAt: task.updatedAt || Date.now(),
		lastRun: task.updatedAt ? new Date(task.updatedAt).toLocaleString() : null,
		agent: "Agent"
	}))];
	allTasks.sort((a, b) => b.createdAt - a.createdAt);
	const activeTasks = allTasks.filter((t) => t.status !== "completed" && t.status !== "cancelled");
	const completedTasks = allTasks.filter((t) => t.status === "completed" || t.status === "success");
	const failedTasks = allTasks.filter((t) => t.status === "error" || t.status === "failed");
	const [filter, setFilter] = (0, import_react.useState)("all");
	const visibleTasks = filter === "active" ? activeTasks : filter === "completed" ? completedTasks : filter === "failed" ? failedTasks : allTasks;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
		className: "h-full",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mx-auto max-w-7xl space-y-6 p-6",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
				className: "p-6",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "text-2xl font-semibold tracking-tight",
						children: "Tasks"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-(--ui-text-tertiary) mb-4",
						children: "Background and scheduled tasks"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-4 mb-6 sm:grid-cols-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TaskSummaryCard, {
								active: filter === "active",
								count: activeTasks.length,
								label: "Active",
								onSelect: () => setFilter(filter === "active" ? "all" : "active"),
								status: "running"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TaskSummaryCard, {
								active: filter === "completed",
								count: completedTasks.length,
								label: "Completed",
								onSelect: () => setFilter(filter === "completed" ? "all" : "completed"),
								status: "success"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TaskSummaryCard, {
								active: filter === "failed",
								count: failedTasks.length,
								label: "Failed",
								onSelect: () => setFilter(filter === "failed" ? "all" : "failed"),
								status: "error"
							})
						]
					}),
					allTasks.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: "Scheduled and background tasks will appear here",
						icon: "checklist",
						title: "No active tasks"
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "mb-2 text-xs text-(--ui-text-tertiary)",
						role: "status",
						children: [
							"Showing ",
							Math.min(visibleTasks.length, 20),
							" of ",
							visibleTasks.length,
							" task",
							visibleTasks.length === 1 ? "" : "s",
							filter !== "all" ? ` · filtered by ${filter} — select again to clear` : ""
						]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Table, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableHead, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TableRow, { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableHeader, { children: "Task" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableHeader, { children: "Status" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableHeader, { children: "Type" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableHeader, { children: "Created" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableHeader, { children: "Last Run" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableHeader, { children: "Actions" })
					] }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TableBody, { children: [visibleTasks.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableRow, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TableCell, {
						className: "py-6 text-center text-sm text-(--ui-text-tertiary)",
						colSpan: 6,
						children: [
							"No ",
							filter,
							" tasks — select the filter again to show all tasks."
						]
					}) }) : null, visibleTasks.slice(0, 20).map((task) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TableRow, { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TableCell, {
							className: "font-medium",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "truncate max-w-xs",
								children: task.title
							}), task.description && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "text-xs text-(--ui-text-tertiary) truncate",
								children: task.description
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableCell, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, {
							size: "sm",
							status: task.status
						}) }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableCell, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							variant: "outline",
							children: task.type
						}) }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableCell, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: formatTimestamp(task.createdAt)
						}) }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableCell, { children: task.lastRun ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: formatTimestamp(task.lastRun)
						}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "—"
						}) }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableCell, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							"aria-label": "View task details",
							className: "p-1.5 rounded hover:bg-(--ui-surface-hover)",
							onClick: () => navigate(task.type === "cron" ? "/automation-center" : "/task-orchestrator"),
							size: "icon",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-eye" })
						}) })
					] }, task.id))] })] })] })
				]
			})
		})
	});
}
function TaskSummaryCard({ active, label, count, onSelect, status }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Card, {
		className: cn("p-4 rounded-xl border", {
			running: "from-blue-500/20 to-blue-600/10 border-blue-500/20",
			success: "from-emerald-500/20 to-emerald-600/10 border-emerald-500/20",
			error: "from-red-500/20 to-red-600/10 border-red-500/20"
		}[status]),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
			"aria-pressed": Boolean(active),
			className: "flex w-full items-center justify-between text-left",
			onClick: onSelect,
			type: "button",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
				className: "text-sm font-medium",
				children: [label, active ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "ml-2 text-xs text-(--ui-text-tertiary)",
					children: "●"
				}) : null]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-2xl font-bold text-(--ui-text)",
				children: count
			})]
		})
	});
}
//#endregion
export { TasksView };

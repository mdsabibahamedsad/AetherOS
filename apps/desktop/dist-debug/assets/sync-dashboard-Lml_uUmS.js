import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { H as runImport, V as runBackup, l as getActionStatus } from "./aetheros-DF_uJq_t.js";
import { Di as notify, Ia as Codicon, La as Button, O as Badge, Oi as notifyError, P as Switch, Ra as cn, Ya as useStore, ao as require_jsx_runtime, ni as Input, oo as require_react } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
import { a as $syncLastSync, c as $syncStatus, f as completeSync, i as $syncHistory, l as addSyncEvent, m as setSyncScope, n as $syncEnabled, o as $syncOnline, r as $syncError, s as $syncScopes, t as $syncConflicts, u as clearSyncError } from "./sync-RdGmYJXp.js";
//#region src/lib/backup.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
/**
* Poll a spawned backend action (`backup`, `import`, …) until it stops
* running, then report the real exit code. Timeouts surface as thrown
* errors — never as fake success.
*/
async function pollActionDone(getStatus, name, opts = {}) {
	const intervalMs = opts.intervalMs ?? 1500;
	const timeoutMs = opts.timeoutMs ?? 12e4;
	const deadline = Date.now() + timeoutMs;
	for (;;) {
		const status = await getStatus(name, 20);
		if (!status.running) {
			const ok = status.exit_code === 0;
			return {
				lines: status.lines ?? [],
				ok
			};
		}
		if (Date.now() >= deadline) throw new Error(`${name} timed out after ${Math.round(timeoutMs / 1e3)}s`);
		await delay(intervalMs);
	}
}
//#endregion
//#region src/app/sync-dashboard/index.tsx
var import_jsx_runtime = require_jsx_runtime();
var SCOPE_ICONS = {
	messages: "comment-discussion",
	sessions: "window",
	memory: "database",
	knowledge: "book",
	files: "file-directory",
	config: "gear",
	plugins: "extensions",
	skills: "hubot",
	cron: "history",
	contacts: "organization",
	bookmarks: "bookmark",
	templates: "copy",
	"agent-state": "robot",
	toolsets: "tools",
	gateway: "server",
	"ui-state": "paintcan"
};
function SyncDashboardView() {
	const status = useStore($syncStatus);
	const enabled = useStore($syncEnabled);
	const scopes = useStore($syncScopes);
	const history = useStore($syncHistory);
	const conflicts = useStore($syncConflicts);
	const lastSync = useStore($syncLastSync);
	const online = useStore($syncOnline);
	const syncError = useStore($syncError);
	const [busy, setBusy] = (0, import_react.useState)(false);
	const [archive, setArchive] = (0, import_react.useState)("");
	const backupEvents = (0, import_react.useMemo)(() => history.filter((e) => e.scope === "backup"), [history]);
	const lastBackup = backupEvents.find((e) => e.status === "success") ?? null;
	const failedCount = (0, import_react.useMemo)(() => history.filter((e) => e.status === "failed").length, [history]);
	const statusIcon = (0, import_react.useMemo)(() => {
		if (!enabled) return "circle-slash";
		if (syncError) return "error";
		if (status === "syncing") return "sync";
		if (status === "paused") return "pause";
		return online ? "check" : "circle-slash";
	}, [
		status,
		enabled,
		online,
		syncError
	]);
	const statusColor = (0, import_react.useMemo)(() => {
		if (!enabled || !online) return "text-muted-foreground";
		if (syncError) return "text-destructive";
		if (status === "syncing") return "text-primary";
		if (status === "paused") return "text-amber-500";
		return "text-emerald-500";
	}, [
		status,
		enabled,
		online,
		syncError
	]);
	const statusLabel = (0, import_react.useMemo)(() => {
		if (!enabled) return "Disabled";
		if (syncError) return "Error";
		if (status === "syncing") return "Working";
		if (status === "paused") return "Paused";
		return online ? "Online" : "Offline";
	}, [
		status,
		enabled,
		online,
		syncError
	]);
	const handleRunBackup = (0, import_react.useCallback)(async () => {
		if (busy) return;
		setBusy(true);
		clearSyncError();
		const id = `backup-${Date.now()}`;
		try {
			await runBackup();
			const outcome = await pollActionDone(getActionStatus, "backup");
			completeSync(outcome.ok ? void 0 : "Backup failed");
			if (!outcome.ok) {
				const tail = outcome.lines.slice(-3).join("\n");
				throw new Error(tail || "Backup exited non-zero");
			}
			addSyncEvent({
				id,
				scope: "backup",
				type: "push",
				status: "success",
				timestamp: (/* @__PURE__ */ new Date()).toISOString(),
				itemsCount: 1
			});
			notify({
				kind: "success",
				title: "Backup complete",
				message: "AetherOS backup finished successfully"
			});
		} catch (error) {
			completeSync(error instanceof Error ? error.message : String(error));
			addSyncEvent({
				id,
				scope: "backup",
				type: "error",
				status: "failed",
				timestamp: (/* @__PURE__ */ new Date()).toISOString(),
				itemsCount: 0,
				errorMessage: error instanceof Error ? error.message : String(error)
			});
			notifyError(error, "Backup failed");
		} finally {
			setBusy(false);
		}
	}, [busy]);
	const handleRestore = (0, import_react.useCallback)(async () => {
		const path = archive.trim();
		if (!path || busy) return;
		if (!window.confirm(`Restore from this archive?\n\n${path}\n\nThis overwrites local configuration and state.`)) return;
		setBusy(true);
		const id = `restore-${Date.now()}`;
		try {
			await runImport(path, true);
			const outcome = await pollActionDone(getActionStatus, "import");
			if (!outcome.ok) {
				const tail = outcome.lines.slice(-3).join("\n");
				throw new Error(tail || "Restore exited non-zero");
			}
			addSyncEvent({
				id,
				scope: "backup",
				type: "pull",
				status: "success",
				timestamp: (/* @__PURE__ */ new Date()).toISOString(),
				itemsCount: 1
			});
			notify({
				kind: "success",
				title: "Restore complete",
				message: "Archive restored — restart AetherOS to apply"
			});
		} catch (error) {
			addSyncEvent({
				id,
				scope: "backup",
				type: "error",
				status: "failed",
				timestamp: (/* @__PURE__ */ new Date()).toISOString(),
				itemsCount: 0,
				errorMessage: error instanceof Error ? error.message : String(error)
			});
			notifyError(error, "Restore failed");
		} finally {
			setBusy(false);
		}
	}, [archive, busy]);
	const handleToggleScope = (0, import_react.useCallback)((scopeId, value) => {
		setSyncScope(scopeId, value);
		notify({
			kind: "info",
			title: `${$syncScopes.get().find((s) => s.id === scopeId)?.name ?? scopeId}`,
			message: value ? "Sync enabled" : "Sync disabled"
		});
	}, []);
	const enabledCount = (0, import_react.useMemo)(() => scopes.filter((s) => s.enabled).length, [scopes]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageHeader, {
			className: "w-full",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Sync & Backup" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Local sync preferences and real backend backups" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex items-center gap-2 text-xs text-muted-foreground",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: cn("flex items-center gap-1.5", statusColor),
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: statusIcon,
								size: "0.75rem"
							}), statusLabel]
						})
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						disabled: busy || !enabled,
						onClick: () => void handleRunBackup(),
						size: "sm",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: cn(busy && "animate-spin"),
							name: busy ? "sync" : "database",
							size: "0.85rem"
						}), busy ? "Working…" : "Run backup"]
					})]
				})]
			})
		}),
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mb-4 rounded-lg border border-amber-500/40 bg-amber-500/5 p-3 text-xs text-muted-foreground",
				role: "note",
				children: "Device sync has no connected backend in this build — scopes and history below are local state. Backups and restores run against the real backend (`aetheros backup` / `aetheros import`)."
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid grid-cols-4 gap-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2 text-xs text-muted-foreground",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "checklist",
								size: "0.85rem"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "Scopes" })]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "mt-1 text-lg font-semibold",
							children: [
								enabledCount,
								"/",
								scopes.length
							]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2 text-xs text-muted-foreground",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "warning",
								size: "0.85rem"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "Conflicts" })]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: cn("mt-1 text-lg font-semibold", conflicts.length > 0 && "text-amber-500"),
							children: conflicts.length
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2 text-xs text-muted-foreground",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "database",
								size: "0.85rem"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "Backups" })]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 text-lg font-semibold",
							children: backupEvents.filter((e) => e.status === "success").length
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2 text-xs text-muted-foreground",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "error",
								size: "0.85rem"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "Failed" })]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: cn("mt-1 text-lg font-semibold", failedCount > 0 && "text-destructive"),
							children: failedCount
						})]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-4 rounded-lg border border-(--ui-stroke-tertiary) p-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
						children: "Backup & Restore"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-muted-foreground",
						role: "status",
						children: lastBackup ? `Last backup: ${new Date(lastBackup.timestamp).toLocaleString()}` : lastSync ? `Last activity: ${new Date(lastSync).toLocaleString()}` : "No backups recorded yet"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mt-3 flex flex-wrap items-center gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							"aria-label": "Backup archive path for restore",
							className: "h-8 max-w-sm flex-1 text-xs",
							disabled: busy,
							onChange: (e) => setArchive(e.target.value),
							placeholder: "/path/to/aetheros-backup.tar.gz",
							value: archive
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							disabled: busy || !archive.trim(),
							onClick: () => void handleRestore(),
							size: "sm",
							variant: "outline",
							children: "Restore from archive"
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-2 text-[0.65rem] text-muted-foreground",
						children: "Restore overwrites local configuration and state, then asks you to restart. Confirmation is required."
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
					children: "Local Sync Scopes"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid grid-cols-2 gap-2",
					children: scopes.map((scope) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) px-3 py-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									name: SCOPE_ICONS[scope.id] ?? "symbol-misc",
									size: "0.85rem"
								})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-xs font-medium",
								children: scope.name
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-[0.6rem] text-muted-foreground",
								children: scope.description
							})] })]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: scope.enabled,
							onCheckedChange: (v) => handleToggleScope(scope.id, v)
						})]
					}, scope.id))
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
					children: "Recent Activity"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-1",
					children: [history.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "grid min-h-24 place-items-center text-center",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-muted-foreground/40",
							name: "history",
							size: "1.5rem"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 text-xs text-muted-foreground",
							children: "No sync activity yet"
						})] })
					}), history.slice(0, 10).map((event) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EventRow, { event }, event.id))]
				})]
			})
		]
	});
}
function EventRow({ event }) {
	const typeIcon = (0, import_react.useMemo)(() => {
		switch (event.type) {
			case "push": return "arrow-up";
			case "pull": return "arrow-down";
			case "conflict": return "warning";
			case "error": return "error";
		}
	}, [event.type]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center justify-between rounded-md px-2.5 py-1.5 text-xs transition-colors hover:bg-accent/30",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center gap-2.5",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
					className: (0, import_react.useMemo)(() => {
						switch (event.status) {
							case "success": return "text-emerald-500";
							case "failed": return "text-destructive";
							case "pending": return "text-amber-500";
						}
					}, [event.status]),
					name: typeIcon,
					size: "0.75rem"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
					className: "capitalize",
					children: [
						event.type,
						" - ",
						event.scope
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
					className: "text-[0.55rem]",
					variant: event.status === "failed" ? "destructive" : "muted",
					children: event.status
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
					className: "text-muted-foreground",
					children: [event.itemsCount, " items"]
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: "text-muted-foreground",
			children: new Date(event.timestamp).toLocaleTimeString()
		})]
	});
}
//#endregion
export { SyncDashboardView };

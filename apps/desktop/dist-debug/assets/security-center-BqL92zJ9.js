import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { t as $gateway } from "./gateway-D1xRY-ux.js";
import { An as Dialog, C as Select, D as SelectValue, Di as notify, E as SelectTrigger, Fn as DialogTitle, Ia as Codicon, La as Button, Mn as DialogDescription, Mt as $allApprovalRequests, Nn as DialogFooter, Nt as clearApprovalRequest, O as Badge, Oi as notifyError, P as Switch, Pn as DialogHeader, Qa as atom, Ra as cn, S as ScrollArea, T as SelectItem, Xa as init_nanostores, Ya as useStore, _t as Separator, ao as require_jsx_runtime, jn as DialogContent, ni as Input, oo as require_react, vt as SearchField, w as SelectContent } from "./index-B_yd1pEX.js";
import { t as EmptyState } from "./empty-state-DbK8L0dQ.js";
//#region src/store/security.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
init_nanostores();
var $securityState = /* @__PURE__ */ atom({
	initialized: true,
	zeroTrust: true,
	version: "0.24.0",
	permissions: [],
	grants: [],
	approvalRequests: [],
	sandboxes: [],
	auditEntries: [],
	alerts: [],
	secrets: [],
	sessions: [],
	activeAlertsCount: 0,
	blockedActionsCount: 0,
	recentApprovals: 0,
	privacyMode: null,
	offlineMode: false,
	telemetryEnabled: false,
	systemIntegrity: "passed"
});
var PERMISSION_DEFINITIONS = [
	{
		id: "fs-read",
		category: "filesystem",
		action: "read",
		label: "Read Files",
		description: "Read files from the filesystem",
		defaultPolicy: "allow",
		riskLevel: "low"
	},
	{
		id: "fs-write",
		category: "filesystem",
		action: "write",
		label: "Write Files",
		description: "Write and modify files",
		defaultPolicy: "ask-every-time",
		riskLevel: "medium"
	},
	{
		id: "fs-delete",
		category: "filesystem",
		action: "delete",
		label: "Delete Files",
		description: "Permanently delete files",
		defaultPolicy: "deny",
		riskLevel: "critical"
	},
	{
		id: "fs-move",
		category: "filesystem",
		action: "move",
		label: "Move Files",
		description: "Move or rename files",
		defaultPolicy: "ask-every-time",
		riskLevel: "medium"
	},
	{
		id: "fs-create-dir",
		category: "filesystem",
		action: "create-directory",
		label: "Create Directories",
		description: "Create new directories",
		defaultPolicy: "allow",
		riskLevel: "low"
	},
	{
		id: "net-internet",
		category: "network",
		action: "internet",
		label: "Internet Access",
		description: "Access the internet",
		defaultPolicy: "ask-every-time",
		riskLevel: "medium"
	},
	{
		id: "net-domains",
		category: "network",
		action: "specific-domains",
		label: "Specific Domains",
		description: "Access only specific domains",
		defaultPolicy: "allow",
		riskLevel: "low"
	},
	{
		id: "net-ports",
		category: "network",
		action: "specific-ports",
		label: "Specific Ports",
		description: "Access only specific ports",
		defaultPolicy: "allow",
		riskLevel: "low"
	},
	{
		id: "net-local",
		category: "network",
		action: "local-network",
		label: "Local Network",
		description: "Access local network resources",
		defaultPolicy: "deny",
		riskLevel: "medium"
	},
	{
		id: "browser-open",
		category: "browser",
		action: "open-pages",
		label: "Open Pages",
		description: "Open web pages in the browser",
		defaultPolicy: "ask-every-time",
		riskLevel: "medium"
	},
	{
		id: "browser-download",
		category: "browser",
		action: "download",
		label: "Download Files",
		description: "Download files via browser",
		defaultPolicy: "ask-every-time",
		riskLevel: "high"
	},
	{
		id: "browser-upload",
		category: "browser",
		action: "upload",
		label: "Upload Files",
		description: "Upload files via browser",
		defaultPolicy: "deny",
		riskLevel: "high"
	},
	{
		id: "browser-cookies",
		category: "browser",
		action: "cookies",
		label: "Cookies",
		description: "Access browser cookies",
		defaultPolicy: "deny",
		riskLevel: "critical"
	},
	{
		id: "clipboard-read",
		category: "clipboard",
		action: "read",
		label: "Read Clipboard",
		description: "Read clipboard contents",
		defaultPolicy: "deny",
		riskLevel: "high"
	},
	{
		id: "clipboard-write",
		category: "clipboard",
		action: "write",
		label: "Write Clipboard",
		description: "Write to clipboard",
		defaultPolicy: "ask-every-time",
		riskLevel: "medium"
	},
	{
		id: "term-execute",
		category: "terminal",
		action: "execute",
		label: "Command Execution",
		description: "Execute terminal commands",
		defaultPolicy: "ask-every-time",
		riskLevel: "high"
	},
	{
		id: "term-shell",
		category: "terminal",
		action: "shell",
		label: "Shell Access",
		description: "Access interactive shell",
		defaultPolicy: "deny",
		riskLevel: "high"
	},
	{
		id: "term-process",
		category: "terminal",
		action: "process-manage",
		label: "Process Management",
		description: "Manage running processes",
		defaultPolicy: "deny",
		riskLevel: "critical"
	},
	{
		id: "docker-create",
		category: "docker",
		action: "container-create",
		label: "Container Creation",
		description: "Create Docker containers",
		defaultPolicy: "deny",
		riskLevel: "critical"
	},
	{
		id: "docker-exec",
		category: "docker",
		action: "container-exec",
		label: "Container Execution",
		description: "Execute commands in containers",
		defaultPolicy: "deny",
		riskLevel: "high"
	},
	{
		id: "docker-net",
		category: "docker",
		action: "container-network",
		label: "Container Network",
		description: "Configure container networking",
		defaultPolicy: "deny",
		riskLevel: "critical"
	},
	{
		id: "py-exec",
		category: "python",
		action: "code-exec",
		label: "Code Execution",
		description: "Execute Python code",
		defaultPolicy: "deny",
		riskLevel: "high"
	},
	{
		id: "py-pkg",
		category: "python",
		action: "package-install",
		label: "Package Installation",
		description: "Install Python packages",
		defaultPolicy: "deny",
		riskLevel: "high"
	},
	{
		id: "db-read",
		category: "database",
		action: "read",
		label: "Database Read",
		description: "Read from databases",
		defaultPolicy: "ask-every-time",
		riskLevel: "medium"
	},
	{
		id: "db-write",
		category: "database",
		action: "write",
		label: "Database Write",
		description: "Write to databases",
		defaultPolicy: "deny",
		riskLevel: "high"
	},
	{
		id: "db-delete",
		category: "database",
		action: "delete",
		label: "Database Delete",
		description: "Delete from databases",
		defaultPolicy: "deny",
		riskLevel: "critical"
	},
	{
		id: "cloud-email",
		category: "cloud",
		action: "email",
		label: "Email",
		description: "Access email services",
		defaultPolicy: "deny",
		riskLevel: "high"
	},
	{
		id: "cloud-messaging",
		category: "cloud",
		action: "messaging",
		label: "Messaging",
		description: "Access messaging services",
		defaultPolicy: "deny",
		riskLevel: "high"
	},
	{
		id: "cloud-calendar",
		category: "cloud",
		action: "calendar",
		label: "Calendar",
		description: "Access calendar services",
		defaultPolicy: "deny",
		riskLevel: "medium"
	},
	{
		id: "cloud-github",
		category: "cloud",
		action: "github",
		label: "GitHub",
		description: "Access GitHub API and repos",
		defaultPolicy: "deny",
		riskLevel: "high"
	},
	{
		id: "cloud-storage",
		category: "cloud",
		action: "storage",
		label: "Storage",
		description: "Access cloud storage services",
		defaultPolicy: "deny",
		riskLevel: "high"
	},
	{
		id: "sys-settings",
		category: "system",
		action: "settings",
		label: "System Settings",
		description: "Modify system settings",
		defaultPolicy: "deny",
		riskLevel: "critical"
	},
	{
		id: "sys-extensions",
		category: "system",
		action: "extensions",
		label: "Extensions",
		description: "Install and manage extensions",
		defaultPolicy: "deny",
		riskLevel: "high"
	}
];
function updateSecurityState(partial) {
	$securityState.set({
		...$securityState.get(),
		...partial
	});
}
function removeGrant(grantId) {
	$securityState.set({
		...$securityState.get(),
		grants: $securityState.get().grants.filter((g) => g.id !== grantId)
	});
}
function addSandbox(sandbox) {
	$securityState.set({
		...$securityState.get(),
		sandboxes: [...$securityState.get().sandboxes, sandbox]
	});
}
function removeSandbox(id) {
	$securityState.set({
		...$securityState.get(),
		sandboxes: $securityState.get().sandboxes.filter((s) => s.id !== id)
	});
}
function addSecret(secret) {
	const secrets = $securityState.get().secrets;
	if (secrets.some((s) => s.id === secret.id)) return;
	$securityState.set({
		...$securityState.get(),
		secrets: [...secrets, secret]
	});
}
function removeSecret(id) {
	$securityState.set({
		...$securityState.get(),
		secrets: $securityState.get().secrets.filter((s) => s.id !== id)
	});
}
function setPrivacyMode(mode) {
	$securityState.set({
		...$securityState.get(),
		privacyMode: mode
	});
}
function setOfflineMode(enabled) {
	$securityState.set({
		...$securityState.get(),
		offlineMode: enabled
	});
}
function setTelemetryEnabled(enabled) {
	$securityState.set({
		...$securityState.get(),
		telemetryEnabled: enabled
	});
}
//#endregion
//#region src/app/security-center/alerts.tsx
var import_jsx_runtime = require_jsx_runtime();
var SEVERITY_COLORS = {
	info: "bg-blue-500/10 text-blue-600",
	warning: "bg-amber-500/10 text-amber-600",
	error: "bg-orange-500/10 text-orange-600",
	critical: "bg-red-500/10 text-red-600"
};
var SEVERITY_ICONS = {
	info: "info",
	warning: "warning",
	error: "error",
	critical: "error"
};
var CATEGORY_LABELS$2 = {
	"repeated-failures": "Repeated Failures",
	"suspicious-tool-usage": "Suspicious Tool Usage",
	"unexpected-network": "Unexpected Network Access",
	"permission-escalation": "Permission Escalation",
	"untrusted-plugin": "Untrusted Plugin",
	"invalid-signature": "Invalid Signature",
	"credential-failure": "Credential Failure",
	"brute-force": "Brute Force",
	"abnormal-activity": "Abnormal Activity"
};
function classifyLine(line) {
	const l = line.toLowerCase();
	if (/brute.?force|intrusion|breach/.test(l)) return {
		category: "brute-force",
		severity: "critical"
	};
	if (/signature.*(fail|invalid|mismatch)|invalid signature/.test(l)) return {
		category: "invalid-signature",
		severity: "error"
	};
	if (/credential|auth.*fail|token.*(expired|revoked|invalid)|login fail/.test(l)) return {
		category: "credential-failure",
		severity: "error"
	};
	if (/denied|blocked|violation|policy denied|forbidden/.test(l)) return {
		category: "permission-escalation",
		severity: "error"
	};
	if (/unexpected|allowlist|not in.*allow/.test(l)) return {
		category: "unexpected-network",
		severity: "warning"
	};
	if (/suspicious|anomal|untrusted/.test(l)) return {
		category: "suspicious-tool-usage",
		severity: "warning"
	};
	if (/fail|error|exception|traceback/.test(l)) return {
		category: "repeated-failures",
		severity: "warning"
	};
	return null;
}
function deriveAlerts(lines) {
	const byKey = /* @__PURE__ */ new Map();
	for (const raw of lines) {
		const line = raw.trim();
		if (!line) continue;
		const hit = classifyLine(line);
		if (!hit) continue;
		const key = `${hit.category}:${line.slice(0, 160)}`;
		const existing = byKey.get(key);
		if (existing) existing.count += 1;
		else byKey.set(key, {
			category: hit.category,
			count: 1,
			evidence: line.slice(0, 500),
			id: `log-${byKey.size}`,
			severity: hit.severity,
			source: "Backend log",
			title: hit.category === "invalid-signature" ? "Signature verification failure" : hit.category === "credential-failure" ? "Credential failure" : hit.category === "permission-escalation" ? "Blocked / denied action" : hit.category === "brute-force" ? "Possible intrusion signal" : "Suspicious backend event"
		});
	}
	return [...byKey.values()].slice(0, 50);
}
function SecurityAlertsView() {
	const gateway = useStore($gateway);
	const [lines, setLines] = (0, import_react.useState)([]);
	const [loading, setLoading] = (0, import_react.useState)(true);
	const [unavailable, setUnavailable] = (0, import_react.useState)(false);
	const [severityFilter, setSeverityFilter] = (0, import_react.useState)("all");
	const [categoryFilter, setCategoryFilter] = (0, import_react.useState)("all");
	const [dismissed, setDismissed] = (0, import_react.useState)(/* @__PURE__ */ new Set());
	(0, import_react.useEffect)(() => {
		let live = true;
		(async () => {
			try {
				const recent = await window.aetherosDesktop?.getRecentLogs?.();
				if (!live) return;
				if (recent?.lines) setLines(recent.lines);
				else setUnavailable(true);
			} catch {
				if (live) setUnavailable(true);
			} finally {
				if (live) setLoading(false);
			}
		})();
		return () => {
			live = false;
		};
	}, []);
	const alerts = (0, import_react.useMemo)(() => {
		const derived = deriveAlerts(lines);
		if (!gateway) derived.unshift({
			category: "abnormal-activity",
			count: 1,
			evidence: "Gateway client is not connected; live approval and event flow are unavailable.",
			id: "gateway-disconnected",
			severity: "warning",
			source: "Connection monitor",
			title: "Gateway disconnected"
		});
		return derived.filter((a) => !dismissed.has(a.id));
	}, [
		lines,
		gateway,
		dismissed
	]);
	const filtered = (0, import_react.useMemo)(() => alerts.filter((a) => {
		if (severityFilter !== "all" && a.severity !== severityFilter) return false;
		if (categoryFilter !== "all" && a.category !== categoryFilter) return false;
		return true;
	}), [
		alerts,
		severityFilter,
		categoryFilter
	]);
	const categories = [...new Set(alerts.map((a) => a.category))];
	function dismiss(id, label) {
		setDismissed((prev) => new Set(prev).add(id));
		notify({
			kind: "info",
			title: label,
			message: "Alert dismissed from this view (log lines unchanged)."
		});
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex shrink-0 items-center gap-2 border-b border-(--ui-stroke-tertiary) px-4 py-2",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
					onValueChange: (v) => setSeverityFilter(v),
					value: severityFilter,
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
						className: "h-7 w-32 text-xs",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
							value: "all",
							children: "All Severity"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
							value: "critical",
							children: "Critical"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
							value: "error",
							children: "Error"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
							value: "warning",
							children: "Warning"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
							value: "info",
							children: "Info"
						})
					] })]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
					onValueChange: (v) => setCategoryFilter(v),
					value: categoryFilter,
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
						className: "h-7 w-44 text-xs",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
						value: "all",
						children: "All Categories"
					}), categories.map((c) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
						value: c,
						children: CATEGORY_LABELS$2[c]
					}, c))] })]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "ml-auto text-xs text-muted-foreground",
					children: [filtered.length, " alerts"]
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
			className: "flex-1",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-1.5 p-4",
				children: [loading ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "py-8 text-center text-xs text-muted-foreground",
					children: "Scanning backend signals…"
				}) : unavailable && alerts.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "py-8 text-center",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: "Backend logs could not be read, so there is nothing to assess. Reconnect the backend instead of assuming safety.",
						icon: "shield",
						title: "Monitoring unavailable"
					})
				}) : filtered.map((alert) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: cn("flex items-start gap-3 rounded-lg border px-4 py-3 text-xs transition-colors", SEVERITY_COLORS[alert.severity]),
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: cn("mt-0.5 shrink-0", alert.severity === "critical" || alert.severity === "error" ? "text-red-500" : "text-amber-500"),
							name: SEVERITY_ICONS[alert.severity],
							size: "1rem"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0 flex-1",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-2",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-sm font-medium",
										children: alert.title
									}), alert.count > 1 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Badge, {
										className: "text-[0.5rem]",
										variant: "muted",
										children: [alert.count, "x"]
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "mt-0.5 font-mono text-[0.65rem] break-words text-muted-foreground",
									children: alert.evidence
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "mt-1 flex items-center gap-2 text-[0.6rem] text-muted-foreground/60",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "capitalize",
											children: CATEGORY_LABELS$2[alert.category]
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "·" }),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: alert.source })
									]
								})
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex shrink-0 items-center gap-1",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								className: "text-xs",
								onClick: () => dismiss(alert.id, "Alert dismissed"),
								size: "sm",
								variant: "ghost",
								children: "Dismiss"
							})
						})
					]
				}, alert.id)), !loading && !(unavailable && alerts.length === 0) && filtered.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "px-4 py-12 text-center text-xs text-muted-foreground",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "mx-auto mb-2 text-muted-foreground/40",
						name: "check",
						size: "2rem"
					}), alerts.length === 0 ? "No security signals in recent backend output" : "No alerts match your filters"]
				})]
			})
		})]
	});
}
//#endregion
//#region src/app/security-center/approvals.tsx
function shortSession(id) {
	if (!id) return "current session";
	return id.length > 12 ? `${id.slice(0, 8)}…` : id;
}
function ApprovalCenter() {
	const all = useStore($allApprovalRequests);
	const gateway = useStore($gateway);
	const [searchQuery, setSearchQuery] = (0, import_react.useState)("");
	const [selectedKey, setSelectedKey] = (0, import_react.useState)(null);
	const [submitting, setSubmitting] = (0, import_react.useState)(null);
	const [armAlways, setArmAlways] = (0, import_react.useState)(false);
	const rows = (0, import_react.useMemo)(() => Object.entries(all).map(([sessionKey, req]) => ({
		allowPermanent: req.allowPermanent !== false,
		command: req.command,
		description: req.description,
		sessionKey,
		sessionId: req.sessionId
	})), [all]);
	const filtered = (0, import_react.useMemo)(() => {
		const q = searchQuery.trim().toLowerCase();
		if (!q) return rows;
		return rows.filter((r) => r.command.toLowerCase().includes(q) || r.description.toLowerCase().includes(q) || r.sessionKey.toLowerCase().includes(q));
	}, [rows, searchQuery]);
	const selected = filtered.find((r) => r.sessionKey === selectedKey) ?? null;
	async function respond(row, choice) {
		if (submitting || !gateway) {
			if (!gateway) notifyError(/* @__PURE__ */ new Error("Gateway disconnected"), "Cannot send approval response");
			return;
		}
		setSubmitting(choice);
		try {
			await gateway.request("approval.respond", {
				choice,
				session_id: row.sessionId ?? void 0
			});
			clearApprovalRequest(row.sessionId);
			notify({
				kind: choice === "deny" ? "info" : "success",
				title: choice === "deny" ? "Request denied" : "Request approved",
				message: choice === "deny" ? "The action was blocked." : choice === "once" ? "Approved for this action only." : choice === "session" ? "Approved for this session." : "Permanently allow-listed."
			});
			setSelectedKey(null);
			setArmAlways(false);
		} catch (error) {
			notifyError(error, "Approval response failed");
		} finally {
			setSubmitting(null);
		}
	}
	if (!gateway) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "grid h-full place-items-center p-6",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
			description: "Connect the gateway to review live approval requests.",
			icon: "checklist",
			title: "Gateway disconnected"
		})
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "w-80 shrink-0 border-r border-(--ui-stroke-tertiary) p-4",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-sm font-medium",
							children: "Approval Requests"
						}), rows.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Badge, {
							className: "text-[0.55rem]",
							variant: "warn",
							children: [rows.length, " pending"]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SearchField, {
						containerClassName: "w-full",
						onChange: setSearchQuery,
						placeholder: "Search requests...",
						value: searchQuery
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						"aria-label": "Pending approval requests",
						className: "space-y-0.5",
						role: "list",
						children: [filtered.map((req) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: cn("flex w-full items-start gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors", selected?.sessionKey === req.sessionKey ? "bg-accent text-accent-foreground" : "hover:bg-accent/60"),
							onClick: () => {
								setSelectedKey(req.sessionKey);
								setArmAlways(false);
							},
							role: "listitem",
							type: "button",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								"aria-hidden": true,
								className: "mt-0.5 size-2 shrink-0 rounded-full bg-amber-500"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "min-w-0 flex-1",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-1.5",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "truncate text-sm font-medium",
											children: shortSession(req.sessionId)
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
											className: "bg-amber-500/10 text-[0.5rem] text-amber-600",
											variant: "muted",
											children: "pending"
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "truncate text-xs text-muted-foreground",
										children: req.description
									}),
									req.command.trim() && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "mt-0.5 truncate font-mono text-[0.6rem] text-muted-foreground/60",
										children: req.command
									})
								]
							})]
						}, req.sessionKey)), filtered.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "px-2 py-6 text-center",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "text-xs text-muted-foreground",
								children: "No pending approvals"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "mt-1 text-[0.65rem] text-muted-foreground/60",
								children: "Requests appear here when a running agent needs a decision."
							})]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "px-1 text-[0.6rem] leading-snug text-muted-foreground/60",
						children: "Terminal and code-execution gate. The backend keeps one in-flight request per session and no history."
					})
				]
			})
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "min-w-0 flex-1 overflow-y-auto p-4",
			children: selected ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "rounded-xl border-2 border-amber-500/30 bg-amber-500/10 p-4",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								className: "text-amber-500",
								name: "warning",
								size: "1.25rem"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "text-lg font-semibold",
								children: selected.description
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "text-xs text-muted-foreground",
								children: ["Session ", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("strong", {
									className: "font-mono",
									children: shortSession(selected.sessionId)
								})]
							})] })]
						})
					}),
					selected.command.trim() && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground",
							children: "Command"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
							className: "mt-1 overflow-x-auto rounded bg-muted/30 p-2 font-mono text-xs",
							children: selected.command
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground",
							children: "Scope"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-1 text-sm",
							children: "Terminal / code execution in this session only. Nothing else is granted."
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex flex-wrap items-center gap-2",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
								className: "text-xs",
								disabled: submitting !== null,
								onClick: () => void respond(selected, "once"),
								size: "sm",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "mr-1",
									name: "check",
									size: "0.75rem"
								}), submitting === "once" ? "Sending…" : "Allow Once"]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
								className: "text-xs",
								disabled: submitting !== null,
								onClick: () => void respond(selected, "session"),
								size: "sm",
								variant: "secondary",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "mr-1",
									name: "clock",
									size: "0.75rem"
								}), " Allow Session"]
							}),
							selected.allowPermanent && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
								className: "text-xs",
								disabled: submitting !== null,
								onClick: () => {
									if (armAlways) respond(selected, "always");
									else setArmAlways(true);
								},
								size: "sm",
								variant: "outline",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "mr-1",
									name: "lock",
									size: "0.75rem"
								}), armAlways ? "Click again to confirm permanent allow" : "Always Allow"]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
								className: "ml-auto text-xs",
								disabled: submitting !== null,
								onClick: () => void respond(selected, "deny"),
								size: "sm",
								variant: "destructive",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "mr-1",
									name: "x",
									size: "0.75rem"
								}), submitting === "deny" ? "Sending…" : "Deny"]
							})
						]
					}),
					armAlways && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-amber-600",
						children: "Permanent allow writes to configuration. Deny keeps the agent blocked on this action."
					})
				]
			}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid min-h-52 place-items-center text-center",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "text-muted-foreground/40",
						name: "checklist",
						size: "2rem"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mt-2 text-sm font-medium text-muted-foreground",
						children: "Select a request"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mt-1 text-xs text-muted-foreground/60",
						children: "Choose a pending approval to review details"
					})
				] })
			})
		})]
	});
}
//#endregion
//#region src/app/security-center/audit.tsx
function AuditLogView() {
	const [lines, setLines] = (0, import_react.useState)([]);
	const [sourcePath, setSourcePath] = (0, import_react.useState)("");
	const [loading, setLoading] = (0, import_react.useState)(true);
	const [failed, setFailed] = (0, import_react.useState)(false);
	const [searchQuery, setSearchQuery] = (0, import_react.useState)("");
	const [visibleCount, setVisibleCount] = (0, import_react.useState)(200);
	async function refresh() {
		setLoading(true);
		setFailed(false);
		try {
			const recent = await window.aetherosDesktop?.getRecentLogs?.();
			if (recent?.lines) {
				setLines(recent.lines);
				setSourcePath(recent.path ?? "");
			} else setFailed(true);
		} catch {
			setFailed(true);
		} finally {
			setLoading(false);
		}
	}
	(0, import_react.useEffect)(() => {
		refresh();
	}, []);
	const filtered = (0, import_react.useMemo)(() => {
		const q = searchQuery.trim().toLowerCase();
		if (!q) return lines;
		return lines.filter((l) => l.toLowerCase().includes(q));
	}, [lines, searchQuery]);
	const visible = filtered.slice(-visibleCount);
	function handleExport() {
		try {
			const blob = new Blob([filtered.join("\n")], { type: "text/plain" });
			const url = URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url;
			a.download = "aetheros-backend.log";
			a.click();
			URL.revokeObjectURL(url);
			notify({
				kind: "success",
				title: "Log Exported",
				message: `${filtered.length} lines exported`
			});
		} catch {
			notify({
				kind: "error",
				title: "Export Failed",
				message: "Could not export log lines"
			});
		}
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex shrink-0 items-center gap-2 border-b border-(--ui-stroke-tertiary) px-4 py-2",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SearchField, {
					containerClassName: "w-64",
					onChange: setSearchQuery,
					placeholder: "Filter log lines...",
					value: searchQuery
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "truncate text-[0.65rem] text-muted-foreground/60",
					title: sourcePath,
					children: sourcePath || "backend log stream"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "ml-auto flex items-center gap-1",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							className: "text-xs",
							onClick: () => window.aetherosDesktop?.revealLogs?.(),
							size: "sm",
							variant: "ghost",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								className: "mr-1",
								name: "folder-opened",
								size: "0.75rem"
							}), " Reveal"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							className: "text-xs",
							onClick: handleExport,
							size: "sm",
							variant: "ghost",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								className: "mr-1",
								name: "export",
								size: "0.75rem"
							}), " Export"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							className: "text-xs",
							onClick: () => void refresh(),
							size: "sm",
							variant: "ghost",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								className: "mr-1",
								name: "refresh",
								size: "0.75rem"
							}), " Refresh"]
						})
					]
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
			className: "flex-1",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "p-4 font-mono text-[0.65rem] leading-5",
				children: loading ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "py-8 text-center text-muted-foreground",
					children: "Loading backend logs…"
				}) : failed ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "py-8 text-center",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: "The backend log stream could not be read. Check that the backend is running.",
						icon: "history",
						title: "Logs unavailable"
					})
				}) : visible.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "py-8 text-center text-muted-foreground",
					children: lines.length === 0 ? "No log lines yet" : "No lines match the filter"
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [filtered.length > visible.length && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: "mb-2 text-muted-foreground underline",
					onClick: () => setVisibleCount((c) => c + 500),
					type: "button",
					children: [
						"Show more (",
						filtered.length - visible.length,
						" older lines hidden)"
					]
				}), visible.map((line, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "whitespace-pre-wrap break-words text-(--ui-text-tertiary)",
					children: line
				}, `${i}-${line.slice(0, 32)}`))] })
			})
		})]
	});
}
//#endregion
//#region src/app/security-center/overview.tsx
function OverviewDashboard() {
	const state = useStore($securityState);
	const pendingEntries = Object.entries(useStore($allApprovalRequests));
	const pendingApprovals = pendingEntries.length;
	const runningSandboxes = state.sandboxes.filter((s) => s.status === "running");
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-6 p-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid grid-cols-2 gap-4 lg:grid-cols-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
						color: "blue",
						icon: "lock",
						label: "Active Permissions",
						sub: `${PERMISSION_DEFS.length} categories`,
						value: state.grants.length
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
						color: "amber",
						icon: "checklist",
						label: "Pending Approvals",
						sub: "Live across sessions",
						value: pendingApprovals
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
						color: "purple",
						icon: "container",
						label: "Running Sandboxes",
						sub: `${state.sandboxes.length} total`,
						value: runningSandboxes.length
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
						color: "indigo",
						icon: "device-desktop",
						label: "Connected Devices",
						sub: "Active sessions",
						value: state.sessions.length
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
					className: "flex items-center gap-2 text-sm font-semibold",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						name: "checklist",
						size: "1rem"
					}), "Pending Approvals"]
				}), pendingApprovals === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "rounded-lg border border-dashed px-4 py-6 text-center text-xs text-muted-foreground",
					children: "No pending approval requests"
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "space-y-1.5",
					children: pendingEntries.slice(0, 5).map(([sessionKey, req]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-3 rounded-lg border px-3 py-2 text-xs",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								className: "shrink-0 text-amber-500",
								name: "question",
								size: "1rem"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "min-w-0 flex-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "font-medium",
									children: req.description
								}), req.command.trim() && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "ml-2 font-mono text-muted-foreground/60",
									children: req.command.slice(0, 80)
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								className: "shrink-0 text-[0.55rem]",
								variant: "warn",
								children: sessionKey.length > 12 ? `${sessionKey.slice(0, 8)}…` : sessionKey
							})
						]
					}, sessionKey))
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
					className: "flex items-center gap-2 text-sm font-semibold",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						name: "server",
						size: "1rem"
					}), "Running Sandboxes"]
				}), runningSandboxes.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "rounded-lg border border-dashed px-4 py-6 text-center text-xs text-muted-foreground",
					children: "No sandboxes are currently running"
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-3",
					children: runningSandboxes.map((sb) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-lg border px-3 py-2 text-xs",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2 font-medium",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("size-2 rounded-full", sb.status === "running" ? "bg-emerald-500" : "bg-amber-500") }), sb.name]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-1 flex items-center gap-2 text-muted-foreground",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									name: "symbol-misc",
									size: "0.75rem"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "capitalize",
									children: sb.mode
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-muted-foreground/40",
									children: "·"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "capitalize",
									children: sb.type
								})
							]
						})]
					}, sb.id))
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Separator, {}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "pb-4 text-center text-[0.6rem] text-muted-foreground",
				children: [
					"Security Center v",
					state.version,
					" · ",
					state.zeroTrust ? "Zero Trust enabled" : "Standard security",
					" · Last checked: ",
					(/* @__PURE__ */ new Date()).toLocaleTimeString()
				]
			})
		]
	}) });
}
var PERMISSION_DEFS = [
	{
		id: "filesystem",
		icon: "file-directory",
		label: "Filesystem"
	},
	{
		id: "network",
		icon: "globe",
		label: "Network"
	},
	{
		id: "browser",
		icon: "globe",
		label: "Browser"
	},
	{
		id: "clipboard",
		icon: "clippy",
		label: "Clipboard"
	},
	{
		id: "terminal",
		icon: "terminal",
		label: "Terminal"
	},
	{
		id: "docker",
		icon: "container",
		label: "Docker"
	},
	{
		id: "python",
		icon: "symbol-misc",
		label: "Python"
	},
	{
		id: "database",
		icon: "database",
		label: "Database"
	},
	{
		id: "cloud",
		icon: "cloud",
		label: "Cloud"
	}
];
function StatCard({ icon, label, value, sub, color }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center gap-2 text-[0.65rem] font-medium uppercase tracking-wider text-muted-foreground",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
				name: icon,
				size: "0.875rem"
			}), label]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mt-2 flex items-baseline gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-2xl font-bold tabular-nums",
				children: value
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-xs text-muted-foreground",
				children: sub
			})]
		})]
	});
}
//#endregion
//#region src/app/security-center/permissions.tsx
var CATEGORY_ICONS$1 = {
	filesystem: "file-directory",
	network: "globe",
	browser: "globe",
	clipboard: "clippy",
	terminal: "terminal",
	docker: "container",
	python: "symbol-misc",
	database: "database",
	cloud: "cloud",
	system: "settings-gear"
};
var CATEGORY_LABELS$1 = {
	filesystem: "Filesystem",
	network: "Network",
	browser: "Browser",
	clipboard: "Clipboard",
	terminal: "Terminal",
	docker: "Docker",
	python: "Python",
	database: "Database",
	cloud: "Cloud Services",
	system: "System"
};
var POLICY_LABELS = {
	allow: "Allow",
	deny: "Deny",
	"ask-every-time": "Ask Every Time",
	"ask-once": "Ask Once"
};
var POLICY_COLORS = {
	allow: "text-emerald-500",
	deny: "text-red-500",
	"ask-every-time": "text-amber-500",
	"ask-once": "text-blue-500"
};
var RISK_COLORS = {
	low: "text-emerald-500",
	medium: "text-amber-500",
	high: "text-orange-500",
	critical: "text-red-500"
};
var DURATION_LABELS = {
	"ask-every-time": "Ask Every Time",
	"ask-once": "Ask Once",
	"temporary": "Temporary",
	"session": "Session",
	"permanent": "Permanent"
};
var GRANTEE_TYPES = [
	"agent",
	"plugin",
	"mcp-server",
	"automation",
	"tool"
];
var SAMPLE_GRANTS = [
	{
		id: "g1",
		permissionId: "fs-read",
		granteeType: "agent",
		granteeId: "agent-default",
		granteeName: "Default Agent",
		policy: "allow",
		duration: "permanent",
		grantedAt: "2026-07-01T00:00:00Z",
		expiresAt: null,
		grantedBy: "user"
	},
	{
		id: "g2",
		permissionId: "fs-write",
		granteeType: "agent",
		granteeId: "agent-default",
		granteeName: "Default Agent",
		policy: "ask-every-time",
		duration: "permanent",
		grantedAt: "2026-07-01T00:00:00Z",
		expiresAt: null,
		grantedBy: "user"
	},
	{
		id: "g3",
		permissionId: "net-internet",
		granteeType: "agent",
		granteeId: "agent-default",
		granteeName: "Default Agent",
		policy: "ask-every-time",
		duration: "session",
		grantedAt: "2026-07-21T00:00:00Z",
		expiresAt: null,
		grantedBy: "user"
	},
	{
		id: "g4",
		permissionId: "term-execute",
		granteeType: "agent",
		granteeId: "agent-default",
		granteeName: "Default Agent",
		policy: "ask-every-time",
		duration: "permanent",
		grantedAt: "2026-07-01T00:00:00Z",
		expiresAt: null,
		grantedBy: "user"
	},
	{
		id: "g5",
		permissionId: "fs-read",
		granteeType: "plugin",
		granteeId: "plugin-filesystem",
		granteeName: "Filesystem Plugin",
		policy: "allow",
		duration: "permanent",
		grantedAt: "2026-07-01T00:00:00Z",
		expiresAt: null,
		grantedBy: "user"
	},
	{
		id: "g6",
		permissionId: "fs-write",
		granteeType: "plugin",
		granteeId: "plugin-filesystem",
		granteeName: "Filesystem Plugin",
		policy: "allow",
		duration: "permanent",
		grantedAt: "2026-07-01T00:00:00Z",
		expiresAt: null,
		grantedBy: "user"
	},
	{
		id: "g7",
		permissionId: "net-internet",
		granteeType: "mcp-server",
		granteeId: "mcp-github",
		granteeName: "GitHub MCP",
		policy: "allow",
		duration: "permanent",
		grantedAt: "2026-07-01T00:00:00Z",
		expiresAt: null,
		grantedBy: "user"
	},
	{
		id: "g8",
		permissionId: "fs-read",
		granteeType: "automation",
		granteeId: "auto-backup",
		granteeName: "Backup Workflow",
		policy: "allow",
		duration: "session",
		grantedAt: "2026-07-21T00:00:00Z",
		expiresAt: null,
		grantedBy: "user"
	},
	{
		id: "g9",
		permissionId: "fs-delete",
		granteeType: "agent",
		granteeId: "agent-default",
		granteeName: "Default Agent",
		policy: "deny",
		duration: "permanent",
		grantedAt: "2026-07-01T00:00:00Z",
		expiresAt: null,
		grantedBy: "system"
	},
	{
		id: "g10",
		permissionId: "browser-cookies",
		granteeType: "agent",
		granteeId: "agent-default",
		granteeName: "Default Agent",
		policy: "deny",
		duration: "permanent",
		grantedAt: "2026-07-01T00:00:00Z",
		expiresAt: null,
		grantedBy: "system"
	}
];
function PermissionManager() {
	const [searchQuery, setSearchQuery] = (0, import_react.useState)("");
	const [categoryFilter, setCategoryFilter] = (0, import_react.useState)("all");
	const [granteeFilter, setGranteeFilter] = (0, import_react.useState)("all");
	const [selectedGrantee, setSelectedGrantee] = (0, import_react.useState)(null);
	const [showAddDialog, setShowAddDialog] = (0, import_react.useState)(false);
	const [grants, setGrants] = (0, import_react.useState)(SAMPLE_GRANTS);
	const categories = [...new Set(PERMISSION_DEFINITIONS.map((p) => p.category))];
	const filteredGrants = (0, import_react.useMemo)(() => {
		const q = searchQuery.trim().toLowerCase();
		return grants.filter((g) => {
			const def = PERMISSION_DEFINITIONS.find((p) => p.id === g.permissionId);
			if (q && !g.granteeName.toLowerCase().includes(q) && !def?.label.toLowerCase().includes(q)) return false;
			if (categoryFilter !== "all" && def?.category !== categoryFilter) return false;
			if (granteeFilter !== "all" && g.granteeType !== granteeFilter) return false;
			return true;
		});
	}, [
		grants,
		searchQuery,
		categoryFilter,
		granteeFilter
	]);
	const grantsByGrantee = (0, import_react.useMemo)(() => {
		const map = /* @__PURE__ */ new Map();
		for (const g of filteredGrants) {
			const key = `${g.granteeType}:${g.granteeId}`;
			if (!map.has(key)) map.set(key, {
				name: g.granteeName,
				type: g.granteeType,
				grants: []
			});
			map.get(key).grants.push(g);
		}
		return Array.from(map.entries()).sort((a, b) => a[1].name.localeCompare(b[1].name));
	}, [filteredGrants]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "w-72 shrink-0 border-r border-(--ui-stroke-tertiary) p-4",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SearchField, {
						containerClassName: "w-full",
						onChange: setSearchQuery,
						placeholder: "Search permissions...",
						value: searchQuery
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
							onValueChange: (v) => setCategoryFilter(v),
							value: categoryFilter,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
								className: "h-7 flex-1 text-xs",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
								value: "all",
								children: "All Categories"
							}), categories.map((c) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
								value: c,
								children: CATEGORY_LABELS$1[c]
							}, c))] })]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
							onValueChange: (v) => setGranteeFilter(v),
							value: granteeFilter,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
								className: "h-7 flex-1 text-xs",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
								value: "all",
								children: "All Types"
							}), GRANTEE_TYPES.map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
								value: t,
								children: t.charAt(0).toUpperCase() + t.slice(1).replace("-", " ")
							}, t))] })]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-0.5",
						children: [grantsByGrantee.map(([key, group]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: cn("flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors", selectedGrantee && `${selectedGrantee.type}:${selectedGrantee.id}` === key ? "bg-accent text-accent-foreground" : "hover:bg-accent/60"),
							onClick: () => setSelectedGrantee({
								type: group.type,
								id: key.split(":")[1],
								name: group.name
							}),
							type: "button",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: CATEGORY_ICONS$1[group.type === "mcp-server" ? "cloud" : group.type] || "lock",
								size: "1rem"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "min-w-0 flex-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "truncate text-sm font-medium",
									children: group.name
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "text-[0.6rem] text-muted-foreground",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "capitalize",
											children: group.type
										}),
										" · ",
										group.grants.length,
										" permissions"
									]
								})]
							})]
						}, key)), grantsByGrantee.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "px-2 py-6 text-center text-xs text-muted-foreground",
							children: "No matching permissions"
						})]
					})
				]
			})
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "min-w-0 flex-1 overflow-y-auto p-4",
			children: selectedGrantee ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PermissionGranteeDetail, {
				granteeName: selectedGrantee.name,
				granteeType: selectedGrantee.type,
				grants: grants.filter((g) => g.granteeId === selectedGrantee.id && g.granteeType === selectedGrantee.type),
				onRemoveGrant: (grantId) => {
					setGrants((prev) => prev.filter((g) => g.id !== grantId));
					removeGrant(grantId);
					notify({
						kind: "success",
						title: "Permission Removed",
						message: "Grant has been revoked"
					});
				}
			}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid min-h-52 place-items-center text-center",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "text-muted-foreground/40",
						name: "lock",
						size: "2rem"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mt-2 text-sm font-medium text-muted-foreground",
						children: "Select a grantee"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mt-1 text-xs text-muted-foreground/60",
						children: "Choose an agent, plugin, or server to view permissions"
					})
				] })
			})
		})]
	});
}
function PermissionGranteeDetail({ grants, granteeName, granteeType, onRemoveGrant }) {
	const [editGrant, setEditGrant] = (0, import_react.useState)(null);
	const grantsByCategory = (0, import_react.useMemo)(() => {
		const map = /* @__PURE__ */ new Map();
		for (const g of grants) {
			const def = PERMISSION_DEFINITIONS.find((p) => p.id === g.permissionId);
			if (!def) continue;
			const cat = def.category;
			if (!map.has(cat)) map.set(cat, []);
			map.get(cat).push(g);
		}
		return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]));
	}, [grants]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center gap-3",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
				name: "lock",
				size: "1.25rem"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "text-lg font-semibold",
				children: granteeName
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "text-xs text-muted-foreground capitalize",
				children: [
					granteeType,
					" · ",
					grants.length,
					" permissions"
				]
			})] })]
		}), grantsByCategory.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "rounded-lg border border-dashed px-4 py-8 text-center text-xs text-muted-foreground",
			children: [
				"No permissions configured for ",
				granteeName,
				". Default policy: Deny all."
			]
		}) : grantsByCategory.map(([category, categoryGrants]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "rounded-xl border border-(--ui-stroke-tertiary)",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2 border-b border-(--ui-stroke-tertiary) px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
					name: CATEGORY_ICONS$1[category],
					size: "0.875rem"
				}), CATEGORY_LABELS$1[category]]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "divide-y divide-(--ui-stroke-tertiary)",
				children: categoryGrants.map((grant) => {
					const def = PERMISSION_DEFINITIONS.find((p) => p.id === grant.permissionId);
					if (!def) return null;
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between px-4 py-2.5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0 flex-1",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "flex items-center gap-2 text-sm font-medium",
								children: def.label
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "text-xs text-muted-foreground",
								children: def.description
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-3",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									className: cn("text-[0.55rem]", RISK_COLORS[def.riskLevel]),
									variant: "outline",
									children: def.riskLevel
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: cn("text-xs font-medium", POLICY_COLORS[grant.policy]),
									children: POLICY_LABELS[grant.policy]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-[0.6rem] text-muted-foreground",
									children: DURATION_LABELS[grant.duration]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "text-muted-foreground hover:text-destructive",
									onClick: () => onRemoveGrant(grant.id),
									type: "button",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: "trash",
										size: "0.875rem"
									})
								})
							]
						})]
					}, grant.id);
				})
			})]
		}, category))]
	});
}
//#endregion
//#region src/app/security-center/privacy.tsx
var PRIVACY_MODES = [
	{
		id: "offline",
		label: "Offline Mode",
		description: "Disable all network access for agents and plugins. No external connections allowed.",
		icon: "globe"
	},
	{
		id: "local-only",
		label: "Local-Only Mode",
		description: "Only allow connections to localhost and local network. Internet access blocked.",
		icon: "home"
	},
	{
		id: "no-telemetry",
		label: "No Telemetry Mode",
		description: "Disable all usage analytics, error reporting, and anonymous data collection.",
		icon: "eye-closed"
	},
	{
		id: "private",
		label: "Private Mode",
		description: "Maximum privacy. No data leaves your device. Local processing only.",
		icon: "shield"
	},
	{
		id: "strict-sandbox",
		label: "Strict Sandbox Mode",
		description: "All executions run in read-only sandboxes with no persistent storage.",
		icon: "lock"
	}
];
function PrivacySettings() {
	const [activeMode, setActiveMode] = (0, import_react.useState)(null);
	const [offlineEnabled, setOfflineEnabled] = (0, import_react.useState)(false);
	const [telemetryEnabled, setTelemetry] = (0, import_react.useState)(false);
	const handleModeToggle = (mode) => {
		const newMode = activeMode === mode ? null : mode;
		setActiveMode(newMode);
		setPrivacyMode(newMode);
		if (newMode) notify({
			kind: "success",
			title: `${PRIVACY_MODES.find((m) => m.id === newMode)?.label || newMode} Enabled`,
			message: "Privacy mode has been activated"
		});
		else notify({
			kind: "info",
			title: "Privacy Mode Disabled",
			message: "Standard privacy settings restored"
		});
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-2xl space-y-6 p-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-1",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-lg font-semibold",
					children: "Privacy Settings"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm text-muted-foreground",
					children: "Control how AetherOS handles your data, network access, and telemetry. Privacy modes are enforced across all agents, plugins, and services."
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3.5",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "plug",
							size: "1rem"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Offline Mode"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-muted-foreground",
							children: "Block all network connections. Agents run entirely offline."
						})] })]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: offlineEnabled,
						onCheckedChange: (checked) => {
							setOfflineEnabled(checked);
							setOfflineMode(checked);
							notify({
								kind: "info",
								title: checked ? "Offline Mode Enabled" : "Offline Mode Disabled",
								message: checked ? "All network access blocked" : "Network access restored"
							});
						}
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3.5",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "graph",
							size: "1rem"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Telemetry"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-muted-foreground",
							children: "Send anonymous usage data to help improve AetherOS."
						})] })]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: telemetryEnabled,
						onCheckedChange: (checked) => {
							setTelemetry(checked);
							setTelemetryEnabled(checked);
							notify({
								kind: "info",
								title: checked ? "Telemetry Enabled" : "Telemetry Disabled",
								message: checked ? "Anonymous usage data will be collected" : "Telemetry collection stopped"
							});
						}
					})]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Separator, {}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h4", {
				className: "mb-3 flex items-center gap-2 text-sm font-semibold",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
					name: "shield",
					size: "1rem"
				}), "Privacy Modes"]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-2",
				children: PRIVACY_MODES.map((mode) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: cn("flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-left transition-all", activeMode === mode.id ? "border-primary/50 bg-primary/5" : "border-(--ui-stroke-tertiary) hover:bg-accent/30"),
					onClick: () => handleModeToggle(mode.id),
					type: "button",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: cn("mt-0.5", activeMode === mode.id ? "text-primary" : "text-muted-foreground"),
							name: mode.icon,
							size: "1rem"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0 flex-1",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-sm font-medium",
									children: mode.label
								}), activeMode === mode.id && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									className: "text-[0.5rem]",
									variant: "default",
									children: "Active"
								})]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-0.5 text-xs text-muted-foreground",
								children: mode.description
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: cn("mt-0.5 size-4 shrink-0 rounded-full border-2 transition-colors", activeMode === mode.id ? "border-primary bg-primary" : "border-muted-foreground/30"),
							children: activeMode === mode.id && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								className: "block text-primary-foreground",
								name: "check",
								size: "0.75rem"
							})
						})
					]
				}, mode.id))
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Separator, {}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-start gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "mt-0.5 shrink-0 text-amber-500",
						name: "info",
						size: "1rem"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "text-xs text-amber-700",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("strong", { children: "Privacy Note:" }), " When privacy modes are active, some features may be limited. Cloud sync, remote agent access, and certain provider APIs require network connectivity. Strict modes may prevent plugin installation and updates."]
					})]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
					className: "mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
					children: "Data Handling Policy"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("ul", {
					className: "space-y-1 text-xs text-muted-foreground",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
							className: "flex items-start gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								className: "mt-0.5 shrink-0 text-emerald-500",
								name: "check",
								size: "0.75rem"
							}), "All secrets are encrypted at rest using AES-256-GCM"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
							className: "flex items-start gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								className: "mt-0.5 shrink-0 text-emerald-500",
								name: "check",
								size: "0.75rem"
							}), "Credentials are never written to logs or prompts"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
							className: "flex items-start gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								className: "mt-0.5 shrink-0 text-emerald-500",
								name: "check",
								size: "0.75rem"
							}), "No data is sent to external servers unless explicitly configured"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
							className: "flex items-start gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								className: "mt-0.5 shrink-0 text-emerald-500",
								name: "check",
								size: "0.75rem"
							}), "Audit logs are stored locally and never exfiltrated"]
						})
					]
				})]
			})
		]
	});
}
//#endregion
//#region src/app/security-center/sandbox.tsx
var MODE_COLORS = {
	"read-only": "bg-blue-500/10 text-blue-600",
	"restricted": "bg-amber-500/10 text-amber-600",
	"standard": "bg-emerald-500/10 text-emerald-600",
	"trusted": "bg-purple-500/10 text-purple-600",
	"custom": "bg-slate-500/10 text-slate-600"
};
var STATUS_DOT = {
	running: "bg-emerald-500",
	stopped: "bg-muted-foreground/40",
	error: "bg-red-500",
	creating: "bg-amber-500"
};
var TYPE_ICONS = {
	agent: "robot",
	plugin: "extensions",
	"mcp-server": "server",
	python: "symbol-misc",
	shell: "terminal",
	browser: "globe",
	automation: "run-all"
};
var SAMPLE_SANDBOXES = [
	{
		id: "sb-1",
		name: "Default Agent Sandbox",
		type: "agent",
		mode: "standard",
		status: "running",
		allowedFolders: ["/home/user/projects", "/tmp/aetheros"],
		blockedFolders: [
			"/etc",
			"/usr",
			"/bin",
			"/boot"
		],
		readOnlyFolders: ["/usr/share"],
		tempFolder: "/tmp/aetheros-sandbox",
		projectWorkspace: "/home/user/projects",
		domainAllowlist: [
			"*.npmjs.org",
			"*.github.com",
			"*.python.org"
		],
		domainBlocklist: ["*.malware.com", "*.phishing.net"],
		ipRestrictions: [],
		portRestrictions: [
			80,
			443,
			22,
			5432
		],
		offlineMode: false,
		memoryLimit: 2048,
		cpuLimit: 80,
		timeout: 300,
		startedAt: (/* @__PURE__ */ new Date(Date.now() - 36e5)).toISOString(),
		pid: 12345
	},
	{
		id: "sb-2",
		name: "Plugin Isolated Runtime",
		type: "plugin",
		mode: "restricted",
		status: "running",
		allowedFolders: ["/home/user/projects/plugin-data"],
		blockedFolders: [
			"/",
			"/home",
			"/etc",
			"/usr"
		],
		readOnlyFolders: [],
		tempFolder: "/tmp/plugin-sandbox",
		projectWorkspace: "",
		domainAllowlist: ["api.openai.com"],
		domainBlocklist: [],
		ipRestrictions: ["0.0.0.0/0"],
		portRestrictions: [443],
		offlineMode: false,
		memoryLimit: 512,
		cpuLimit: 50,
		timeout: 120,
		startedAt: (/* @__PURE__ */ new Date(Date.now() - 72e5)).toISOString(),
		pid: 12346
	},
	{
		id: "sb-3",
		name: "Python Execution Sandbox",
		type: "python",
		mode: "read-only",
		status: "stopped",
		allowedFolders: ["/tmp/sandbox-python"],
		blockedFolders: [
			"/home",
			"/etc",
			"/usr",
			"/var"
		],
		readOnlyFolders: ["/usr/lib/python3"],
		tempFolder: "/tmp/sandbox-python/tmp",
		projectWorkspace: "",
		domainAllowlist: [],
		domainBlocklist: ["*"],
		ipRestrictions: ["127.0.0.1"],
		portRestrictions: [],
		offlineMode: true,
		memoryLimit: 256,
		cpuLimit: 25,
		timeout: 60,
		startedAt: (/* @__PURE__ */ new Date(Date.now() - 864e5)).toISOString(),
		pid: null
	},
	{
		id: "sb-4",
		name: "Browser Isolation",
		type: "browser",
		mode: "standard",
		status: "creating",
		allowedFolders: ["/tmp/browser-data"],
		blockedFolders: [
			"/home",
			"/etc",
			"/usr"
		],
		readOnlyFolders: [],
		tempFolder: "/tmp/browser-sandbox",
		projectWorkspace: "",
		domainAllowlist: ["*"],
		domainBlocklist: [],
		ipRestrictions: [],
		portRestrictions: [80, 443],
		offlineMode: false,
		memoryLimit: 1024,
		cpuLimit: 60,
		timeout: 600,
		startedAt: (/* @__PURE__ */ new Date()).toISOString(),
		pid: null
	},
	{
		id: "sb-5",
		name: "Automation Workflow Runner",
		type: "automation",
		mode: "trusted",
		status: "running",
		allowedFolders: ["/home/user/projects", "/home/user/.aetheros"],
		blockedFolders: ["/etc", "/usr/bin"],
		readOnlyFolders: [],
		tempFolder: "/tmp/aetheros-automation",
		projectWorkspace: "/home/user/projects",
		domainAllowlist: ["*"],
		domainBlocklist: [],
		ipRestrictions: [],
		portRestrictions: [],
		offlineMode: false,
		memoryLimit: 4096,
		cpuLimit: 90,
		timeout: 900,
		startedAt: (/* @__PURE__ */ new Date(Date.now() - 18e5)).toISOString(),
		pid: 12347
	}
];
var SANDBOX_MODES = [
	"read-only",
	"restricted",
	"standard",
	"trusted",
	"custom"
];
var SANDBOX_TYPES = [
	"agent",
	"plugin",
	"mcp-server",
	"python",
	"shell",
	"browser",
	"automation"
];
function SandboxManager() {
	const [sandboxes, setSandboxes] = (0, import_react.useState)(SAMPLE_SANDBOXES);
	const [searchQuery, setSearchQuery] = (0, import_react.useState)("");
	const [typeFilter, setTypeFilter] = (0, import_react.useState)("all");
	const [statusFilter, setStatusFilter] = (0, import_react.useState)("all");
	const [selectedId, setSelectedId] = (0, import_react.useState)(null);
	const [showCreate, setShowCreate] = (0, import_react.useState)(false);
	const filteredSandboxes = (0, import_react.useMemo)(() => {
		const q = searchQuery.trim().toLowerCase();
		return sandboxes.filter((s) => {
			if (q && !s.name.toLowerCase().includes(q) && !s.type.includes(q)) return false;
			if (typeFilter !== "all" && s.type !== typeFilter) return false;
			if (statusFilter !== "all" && s.status !== statusFilter) return false;
			return true;
		});
	}, [
		sandboxes,
		searchQuery,
		typeFilter,
		statusFilter
	]);
	const selected = (0, import_react.useMemo)(() => sandboxes.find((s) => s.id === selectedId) ?? null, [sandboxes, selectedId]);
	const handleRemove = (id) => {
		setSandboxes((prev) => prev.filter((s) => s.id !== id));
		removeSandbox(id);
		if (selectedId === id) setSelectedId(null);
		notify({
			kind: "success",
			title: "Sandbox Removed",
			message: "Sandbox has been destroyed"
		});
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "w-72 shrink-0 border-r border-(--ui-stroke-tertiary) p-4",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center justify-between",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-sm font-medium",
								children: "Sandboxes"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
								className: "text-xs",
								onClick: () => setShowCreate(true),
								size: "sm",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "mr-1",
									name: "plus",
									size: "0.75rem"
								}), " Create"]
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SearchField, {
							containerClassName: "w-full",
							onChange: setSearchQuery,
							placeholder: "Search sandboxes...",
							value: searchQuery
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
								onValueChange: (v) => setTypeFilter(v),
								value: typeFilter,
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
									className: "h-7 flex-1 text-xs",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "all",
									children: "All Types"
								}), SANDBOX_TYPES.map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: t,
									children: t.charAt(0).toUpperCase() + t.slice(1)
								}, t))] })]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
								onValueChange: (v) => setStatusFilter(v),
								value: statusFilter,
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
									className: "h-7 flex-1 text-xs",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
										value: "all",
										children: "All Status"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
										value: "running",
										children: "Running"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
										value: "stopped",
										children: "Stopped"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
										value: "error",
										children: "Error"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
										value: "creating",
										children: "Creating"
									})
								] })]
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-0.5",
							children: [filteredSandboxes.map((sb) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: cn("flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors", selected?.id === sb.id ? "bg-accent text-accent-foreground" : "hover:bg-accent/60"),
								onClick: () => setSelectedId(sb.id),
								type: "button",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("size-2 shrink-0 rounded-full", STATUS_DOT[sb.status]) }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: "shrink-0 text-muted-foreground",
										name: TYPE_ICONS[sb.type] || "container",
										size: "0.875rem"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "min-w-0 flex-1",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
											className: "truncate text-sm font-medium",
											children: sb.name
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "flex items-center gap-1.5 text-[0.6rem] text-muted-foreground",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
												className: cn("text-[0.5rem]", MODE_COLORS[sb.mode]),
												variant: "muted",
												children: sb.mode
											}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "capitalize",
												children: sb.type
											})]
										})]
									})
								]
							}, sb.id)), filteredSandboxes.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "px-2 py-6 text-center text-xs text-muted-foreground",
								children: searchQuery ? "No sandboxes match your search" : "No sandboxes configured"
							})]
						})
					]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "min-w-0 flex-1 overflow-y-auto p-4",
				children: selected ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SandboxDetail, {
					onRemove: () => handleRemove(selected.id),
					sandbox: selected
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid min-h-52 place-items-center text-center",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-muted-foreground/40",
							name: "container",
							size: "2rem"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-2 text-sm font-medium text-muted-foreground",
							children: "No sandbox selected"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-1 text-xs text-muted-foreground/60",
							children: "Select a sandbox or create a new one"
						})
					] })
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CreateSandboxDialog, {
				onClose: () => setShowCreate(false),
				onCreate: (sb) => {
					setSandboxes((prev) => [...prev, sb]);
					addSandbox(sb);
					setShowCreate(false);
					notify({
						kind: "success",
						title: "Sandbox Created",
						message: `${sb.name} created in ${sb.mode} mode`
					});
				},
				open: showCreate
			})
		]
	});
}
function SandboxDetail({ sandbox, onRemove }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-4",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-start justify-between rounded-xl border border-(--ui-stroke-tertiary) p-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("mt-1 size-3 shrink-0 rounded-full", STATUS_DOT[sandbox.status]) }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-muted-foreground",
							name: TYPE_ICONS[sandbox.type] || "container",
							size: "1.25rem"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "text-lg font-semibold",
							children: sandbox.name
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex flex-wrap items-center gap-2 text-xs text-muted-foreground",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									className: cn("text-[0.55rem]", MODE_COLORS[sandbox.mode]),
									variant: "muted",
									children: sandbox.mode
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "capitalize",
									children: sandbox.type
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: sandbox.status }),
								sandbox.pid && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "font-mono",
									children: ["PID ", sandbox.pid]
								})
							]
						})] })
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					className: "text-xs text-muted-foreground hover:text-destructive",
					onClick: onRemove,
					size: "sm",
					variant: "ghost",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "mr-1",
						name: "trash",
						size: "0.75rem"
					}), " Destroy"]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid grid-cols-3 gap-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
						label: "Memory Limit",
						value: `${sandbox.memoryLimit} MB`
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
						label: "CPU Limit",
						value: `${sandbox.cpuLimit}%`
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
						label: "Timeout",
						value: `${sandbox.timeout}s`
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Filesystem",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
							label: "Allowed Folders",
							mono: true,
							value: sandbox.allowedFolders.length > 0 ? sandbox.allowedFolders.join(", ") : "None"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
							label: "Blocked Folders",
							mono: true,
							value: sandbox.blockedFolders.length > 0 ? sandbox.blockedFolders.join(", ") : "None"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
							label: "Read-Only Folders",
							mono: true,
							value: sandbox.readOnlyFolders.length > 0 ? sandbox.readOnlyFolders.join(", ") : "None"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
							label: "Temp Folder",
							mono: true,
							value: sandbox.tempFolder
						}),
						sandbox.projectWorkspace && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
							label: "Project Workspace",
							mono: true,
							value: sandbox.projectWorkspace
						})
					]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Network",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
							label: "Domain Allowlist",
							value: sandbox.domainAllowlist.length > 0 ? sandbox.domainAllowlist.join(", ") : "None"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
							label: "Domain Blocklist",
							value: sandbox.domainBlocklist.length > 0 ? sandbox.domainBlocklist.join(", ") : "None"
						}),
						sandbox.ipRestrictions.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
							label: "IP Restrictions",
							value: sandbox.ipRestrictions.join(", ")
						}),
						sandbox.portRestrictions.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
							label: "Port Restrictions",
							value: sandbox.portRestrictions.join(", ")
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2 text-xs",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "font-medium text-muted-foreground",
								children: "Offline Mode:"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: sandbox.offlineMode ? "Enabled" : "Disabled" })]
						})
					]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailField, {
				label: "Started At",
				value: new Date(sandbox.startedAt).toLocaleString()
			})
		]
	});
}
function Section({ title, children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
			className: "mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground",
			children: title
		}), children]
	});
}
function DetailField({ label, value, mono }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "text-xs",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
			className: "font-medium text-muted-foreground",
			children: [label, ": "]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: mono ? "font-mono" : "",
			children: value
		})]
	});
}
function CreateSandboxDialog({ onCreate, onClose, open }) {
	const [name, setName] = (0, import_react.useState)("");
	const [type, setType] = (0, import_react.useState)("agent");
	const [mode, setMode] = (0, import_react.useState)("standard");
	const [memoryLimit, setMemoryLimit] = (0, import_react.useState)("1024");
	const [timeout, setTimeout] = (0, import_react.useState)("300");
	const handleSubmit = (e) => {
		e.preventDefault();
		if (!name.trim()) return;
		onCreate({
			id: `sb-${Date.now()}`,
			name: name.trim(),
			type,
			mode,
			status: "creating",
			allowedFolders: [],
			blockedFolders: [],
			readOnlyFolders: [],
			tempFolder: `/tmp/sandbox-${name.toLowerCase().replace(/\s+/g, "-")}`,
			projectWorkspace: "",
			domainAllowlist: [],
			domainBlocklist: [],
			ipRestrictions: [],
			portRestrictions: [],
			offlineMode: mode === "read-only",
			memoryLimit: parseInt(memoryLimit) || 1024,
			cpuLimit: 50,
			timeout: parseInt(timeout) || 300,
			startedAt: (/* @__PURE__ */ new Date()).toISOString(),
			pid: null
		});
		setName("");
		setType("agent");
		setMode("standard");
		setMemoryLimit("1024");
		setTimeout("300");
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dialog, {
		onOpenChange: (v) => !v && onClose(),
		open,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, {
			className: "max-w-md",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, { children: "Create Sandbox" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogDescription, { children: "Configure an isolated execution environment" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("form", {
				className: "grid gap-4",
				onSubmit: handleSubmit,
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-1.5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
							className: "text-xs font-medium",
							htmlFor: "sb-name",
							children: "Name"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							autoFocus: true,
							id: "sb-name",
							onChange: (e) => setName(e.target.value),
							placeholder: "My Sandbox",
							value: name
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid grid-cols-2 gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "grid gap-1.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "text-xs font-medium",
								htmlFor: "sb-type",
								children: "Type"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
								onValueChange: setType,
								value: type,
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
									className: "h-9",
									id: "sb-type",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: SANDBOX_TYPES.map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: t,
									children: t.charAt(0).toUpperCase() + t.slice(1)
								}, t)) })]
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "grid gap-1.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "text-xs font-medium",
								htmlFor: "sb-mode",
								children: "Mode"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
								onValueChange: (v) => setMode(v),
								value: mode,
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
									className: "h-9",
									id: "sb-mode",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: SANDBOX_MODES.map((m) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: m,
									children: m.charAt(0).toUpperCase() + m.slice(1).replace("-", " ")
								}, m)) })]
							})]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid grid-cols-2 gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "grid gap-1.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "text-xs font-medium",
								htmlFor: "sb-memory",
								children: "Memory Limit (MB)"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
								id: "sb-memory",
								onChange: (e) => setMemoryLimit(e.target.value),
								type: "number",
								value: memoryLimit
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "grid gap-1.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "text-xs font-medium",
								htmlFor: "sb-timeout",
								children: "Timeout (s)"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
								id: "sb-timeout",
								onChange: (e) => setTimeout(e.target.value),
								type: "number",
								value: timeout
							})]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogFooter, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: onClose,
						type: "button",
						variant: "outline",
						children: "Cancel"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: !name.trim(),
						type: "submit",
						children: "Create Sandbox"
					})] })
				]
			})]
		})
	});
}
//#endregion
//#region src/app/security-center/secrets.tsx
var CATEGORY_ICONS = {
	"api-key": "key",
	"password": "lock",
	"token": "key",
	"certificate": "shield",
	"other": "symbol-misc"
};
var CATEGORY_LABELS = {
	"api-key": "API Key",
	"password": "Password",
	"token": "Token",
	"certificate": "Certificate",
	"other": "Other"
};
var SAMPLE_SECRETS = [
	{
		id: "secret-1",
		name: "OpenAI API Key",
		category: "api-key",
		provider: "OpenAI",
		createdAt: "2026-01-15T00:00:00Z",
		lastAccessed: "2026-07-21T10:30:00Z",
		expiresAt: null,
		maskedValue: "sk-••••••••••••••••"
	},
	{
		id: "secret-2",
		name: "GitHub Personal Access Token",
		category: "token",
		provider: "GitHub",
		createdAt: "2026-03-01T00:00:00Z",
		lastAccessed: "2026-07-21T09:15:00Z",
		expiresAt: null,
		maskedValue: "ghp_••••••••••••••••"
	},
	{
		id: "secret-3",
		name: "GitHub OAuth Token",
		category: "token",
		provider: "GitHub",
		createdAt: "2026-06-01T00:00:00Z",
		lastAccessed: "2026-07-20T18:00:00Z",
		expiresAt: null,
		maskedValue: "gho_••••••••••••••••"
	},
	{
		id: "secret-4",
		name: "Anthropic API Key",
		category: "api-key",
		provider: "Anthropic",
		createdAt: "2026-02-10T00:00:00Z",
		lastAccessed: "2026-07-21T08:00:00Z",
		expiresAt: null,
		maskedValue: "sk-ant-••••••••••••"
	},
	{
		id: "secret-5",
		name: "PostgreSQL Password",
		category: "password",
		provider: "Local Database",
		createdAt: "2026-04-01T00:00:00Z",
		lastAccessed: "2026-07-19T14:30:00Z",
		expiresAt: null,
		maskedValue: "••••••••••"
	},
	{
		id: "secret-6",
		name: "Docker Hub Token",
		category: "token",
		provider: "Docker",
		createdAt: "2026-05-15T00:00:00Z",
		lastAccessed: null,
		expiresAt: "2026-08-15T00:00:00Z",
		maskedValue: "dckr_••••••••••••"
	},
	{
		id: "secret-7",
		name: "Google Cloud Service Account",
		category: "certificate",
		provider: "Google Cloud",
		createdAt: "2026-01-01T00:00:00Z",
		lastAccessed: "2026-07-18T12:00:00Z",
		expiresAt: "2027-01-01T00:00:00Z",
		maskedValue: "••••••••••••••••"
	},
	{
		id: "secret-8",
		name: "Slack Bot Token",
		category: "token",
		provider: "Slack",
		createdAt: "2026-06-20T00:00:00Z",
		lastAccessed: "2026-07-21T11:00:00Z",
		expiresAt: null,
		maskedValue: "xoxb-••••••••••••••"
	}
];
function SecretsManager() {
	const [secrets, setSecrets] = (0, import_react.useState)(SAMPLE_SECRETS);
	const [searchQuery, setSearchQuery] = (0, import_react.useState)("");
	const [categoryFilter, setCategoryFilter] = (0, import_react.useState)("all");
	const [selectedSecret, setSelectedSecret] = (0, import_react.useState)(null);
	const [showAddDialog, setShowAddDialog] = (0, import_react.useState)(false);
	const filteredSecrets = (0, import_react.useMemo)(() => {
		const q = searchQuery.trim().toLowerCase();
		return secrets.filter((s) => {
			if (q && !s.name.toLowerCase().includes(q) && !s.provider.toLowerCase().includes(q)) return false;
			if (categoryFilter !== "all" && s.category !== categoryFilter) return false;
			return true;
		});
	}, [
		secrets,
		searchQuery,
		categoryFilter
	]);
	const handleRemove = (id) => {
		setSecrets((prev) => prev.filter((s) => s.id !== id));
		removeSecret(id);
		if (selectedSecret?.id === id) setSelectedSecret(null);
		notify({
			kind: "success",
			title: "Secret Removed",
			message: "Secret has been deleted from the vault"
		});
	};
	const handleReveal = (secret) => {
		notify({
			kind: "info",
			title: "Secret Accessed",
			message: `Audit log: ${secret.name} was accessed`
		});
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "w-72 shrink-0 border-r border-(--ui-stroke-tertiary) p-4",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center justify-between",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-sm font-medium",
								children: "Secrets Vault"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
								className: "text-xs",
								onClick: () => setShowAddDialog(true),
								size: "sm",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "mr-1",
									name: "plus",
									size: "0.75rem"
								}), " Add"]
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SearchField, {
							containerClassName: "w-full",
							onChange: setSearchQuery,
							placeholder: "Search secrets...",
							value: searchQuery
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
							onValueChange: (v) => setCategoryFilter(v),
							value: categoryFilter,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
								className: "h-7 w-full text-xs",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "all",
									children: "All Categories"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "api-key",
									children: "API Keys"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "password",
									children: "Passwords"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "token",
									children: "Tokens"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "certificate",
									children: "Certificates"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "other",
									children: "Other"
								})
							] })]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-0.5",
							children: [filteredSecrets.map((secret) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: cn("flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors", selectedSecret?.id === secret.id ? "bg-accent text-accent-foreground" : "hover:bg-accent/60"),
								onClick: () => setSelectedSecret(secret),
								type: "button",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "shrink-0 text-muted-foreground",
									name: CATEGORY_ICONS[secret.category],
									size: "0.875rem"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "min-w-0 flex-1",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "truncate text-sm font-medium",
										children: secret.name
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-1.5 text-[0.6rem] text-muted-foreground",
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: secret.provider }),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "·" }),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
												className: "text-[0.5rem]",
												variant: "outline",
												children: CATEGORY_LABELS[secret.category]
											})
										]
									})]
								})]
							}, secret.id)), filteredSecrets.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "px-2 py-6 text-center text-xs text-muted-foreground",
								children: searchQuery ? "No secrets match your search" : "No secrets stored"
							})]
						})
					]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "min-w-0 flex-1 overflow-y-auto p-4",
				children: selectedSecret ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-start justify-between rounded-xl border border-(--ui-stroke-tertiary) p-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-3",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "text-muted-foreground",
									name: CATEGORY_ICONS[selectedSecret.category],
									size: "1.25rem"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
									className: "text-lg font-semibold",
									children: selectedSecret.name
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-2 text-xs text-muted-foreground",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										variant: "outline",
										children: CATEGORY_LABELS[selectedSecret.category]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: selectedSecret.provider })]
								})] })]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-1.5",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
									className: "text-xs",
									onClick: () => handleReveal(selectedSecret),
									size: "sm",
									variant: "outline",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: "mr-1",
										name: "eye",
										size: "0.75rem"
									}), " Reveal"]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									className: "text-xs text-muted-foreground hover:text-destructive",
									onClick: () => handleRemove(selectedSecret.id),
									size: "sm",
									variant: "ghost",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: "trash",
										size: "0.875rem"
									})
								})]
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground",
								children: "Value"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "mt-1 font-mono text-sm tracking-widest",
								children: selectedSecret.maskedValue
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "grid grid-cols-2 gap-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground",
									children: "Created"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "mt-0.5 text-sm",
									children: new Date(selectedSecret.createdAt).toLocaleDateString()
								})]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground",
									children: "Last Accessed"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "mt-0.5 text-sm",
									children: selectedSecret.lastAccessed ? new Date(selectedSecret.lastAccessed).toLocaleString() : "Never"
								})]
							})]
						}),
						selectedSecret.expiresAt && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground",
								children: "Expires"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "mt-0.5 text-sm",
								children: new Date(selectedSecret.expiresAt).toLocaleDateString()
							})]
						})
					]
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid min-h-52 place-items-center text-center",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-muted-foreground/40",
							name: "key",
							size: "2rem"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-2 text-sm font-medium text-muted-foreground",
							children: "Select a secret"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-1 text-xs text-muted-foreground/60",
							children: "Choose a secret to view details"
						})
					] })
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(AddSecretDialog, {
				onAdd: (secret) => {
					setSecrets((prev) => [...prev, secret]);
					addSecret(secret);
					setShowAddDialog(false);
					notify({
						kind: "success",
						title: "Secret Added",
						message: `${secret.name} has been stored securely`
					});
				},
				onClose: () => setShowAddDialog(false),
				open: showAddDialog
			})
		]
	});
}
function AddSecretDialog({ onAdd, onClose, open }) {
	const [name, setName] = (0, import_react.useState)("");
	const [category, setCategory] = (0, import_react.useState)("api-key");
	const [provider, setProvider] = (0, import_react.useState)("");
	const [value, setValue] = (0, import_react.useState)("");
	const handleSubmit = (e) => {
		e.preventDefault();
		if (!name.trim() || !value.trim()) return;
		onAdd({
			id: `secret-${Date.now()}`,
			name: name.trim(),
			category,
			provider: provider.trim() || "Custom",
			createdAt: (/* @__PURE__ */ new Date()).toISOString(),
			lastAccessed: null,
			expiresAt: null,
			maskedValue: value.trim().slice(0, 4) + "••••••••••••"
		});
		setName("");
		setCategory("api-key");
		setProvider("");
		setValue("");
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dialog, {
		onOpenChange: (v) => !v && onClose(),
		open,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, {
			className: "max-w-md",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, { children: "Add Secret" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogDescription, { children: "Store a new credential securely in the vault" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("form", {
				className: "grid gap-4",
				onSubmit: handleSubmit,
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-1.5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
							className: "text-xs font-medium",
							htmlFor: "sec-name",
							children: "Secret Name"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							autoFocus: true,
							id: "sec-name",
							onChange: (e) => setName(e.target.value),
							placeholder: "My API Key",
							value: name
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid grid-cols-2 gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "grid gap-1.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "text-xs font-medium",
								htmlFor: "sec-category",
								children: "Category"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
								onValueChange: setCategory,
								value: category,
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
									className: "h-9",
									id: "sec-category",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
										value: "api-key",
										children: "API Key"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
										value: "password",
										children: "Password"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
										value: "token",
										children: "Token"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
										value: "certificate",
										children: "Certificate"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
										value: "other",
										children: "Other"
									})
								] })]
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "grid gap-1.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "text-xs font-medium",
								htmlFor: "sec-provider",
								children: "Provider"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
								id: "sec-provider",
								onChange: (e) => setProvider(e.target.value),
								placeholder: "OpenAI, GitHub...",
								value: provider
							})]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-1.5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
							className: "text-xs font-medium",
							htmlFor: "sec-value",
							children: "Secret Value"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							id: "sec-value",
							onChange: (e) => setValue(e.target.value),
							placeholder: "Enter secret value",
							type: "password",
							value
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogFooter, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: onClose,
						type: "button",
						variant: "outline",
						children: "Cancel"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: !name.trim() || !value.trim(),
						type: "submit",
						children: "Add Secret"
					})] })
				]
			})]
		})
	});
}
//#endregion
//#region src/app/security-center/index.tsx
var TABS = [
	{
		id: "overview",
		label: "Overview",
		icon: "dashboard"
	},
	{
		id: "permissions",
		label: "Permissions",
		icon: "lock"
	},
	{
		id: "approvals",
		label: "Approvals",
		icon: "checklist"
	},
	{
		id: "sandbox",
		label: "Sandbox",
		icon: "container"
	},
	{
		id: "audit",
		label: "Audit Log",
		icon: "history"
	},
	{
		id: "alerts",
		label: "Alerts",
		icon: "alert"
	},
	{
		id: "secrets",
		label: "Secrets",
		icon: "key"
	},
	{
		id: "privacy",
		label: "Privacy",
		icon: "shield"
	}
];
function SecurityCenterView() {
	const [activeTab, setActiveTab] = (0, import_react.useState)("overview");
	const [checking, setChecking] = (0, import_react.useState)(false);
	const state = useStore($securityState);
	const gateway = useStore($gateway);
	const pendingApprovals = Object.keys(useStore($allApprovalRequests)).length;
	async function runIntegrityCheck() {
		if (checking) return;
		setChecking(true);
		const findings = [];
		if (!gateway) findings.push("gateway disconnected");
		try {
			if (!(await window.aetherosDesktop?.getRecentLogs?.())?.lines) findings.push("backend logs unreadable");
		} catch {
			findings.push("backend logs unreadable");
		}
		const integrity = findings.length === 0 ? "passed" : findings.length === 1 ? "warning" : "failed";
		updateSecurityState({
			initialized: true,
			systemIntegrity: integrity
		});
		notify({
			kind: integrity === "passed" ? "success" : integrity === "warning" ? "info" : "error",
			title: integrity === "passed" ? "Integrity check passed" : "Integrity issues found",
			message: integrity === "passed" ? "Gateway reachable, backend logs readable." : findings.join("; ")
		});
		setChecking(false);
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col overflow-hidden bg-background",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
				className: "flex shrink-0 items-center justify-between border-b px-6 py-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex items-center gap-4",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
								className: "text-xl font-semibold",
								children: "Security Center"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								className: "text-[0.6rem]",
								variant: state.systemIntegrity === "passed" ? "default" : state.systemIntegrity === "warning" ? "warn" : "destructive",
								children: state.systemIntegrity === "passed" ? "Secure" : state.systemIntegrity === "warning" ? "Warning" : "Compromised"
							}),
							state.zeroTrust && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								className: "text-[0.6rem]",
								variant: "outline",
								children: "Zero Trust"
							})
						]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "text-sm text-muted-foreground",
						children: [
							state.alerts.length,
							" alerts · ",
							state.grants.length,
							" grants · ",
							pendingApprovals,
							" pending approvals · ",
							state.sandboxes.length,
							" sandboxes"
						]
					})] })
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					className: "text-xs",
					disabled: checking,
					onClick: () => void runIntegrityCheck(),
					size: "sm",
					variant: "outline",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "mr-1",
							name: "check",
							size: "0.75rem"
						}),
						" ",
						checking ? "Checking…" : "Verify Integrity"
					]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex shrink-0 items-center gap-1 border-b px-4",
				children: TABS.map((tab) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: cn("flex items-center gap-1.5 border-b-2 px-4 py-3 text-sm font-medium transition-colors", activeTab === tab.id ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"),
					onClick: () => setActiveTab(tab.id),
					type: "button",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-xs",
							name: tab.icon,
							size: "0.75rem"
						}),
						tab.label,
						tab.id === "approvals" && pendingApprovals > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							className: "ml-1 text-[0.5rem]",
							variant: "warn",
							children: pendingApprovals
						}),
						tab.id === "alerts" && state.activeAlertsCount > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							className: "ml-1 text-[0.5rem]",
							variant: "destructive",
							children: state.activeAlertsCount
						})
					]
				}, tab.id))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex-1 overflow-y-auto",
				children: [
					activeTab === "overview" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverviewDashboard, {}),
					activeTab === "permissions" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PermissionManager, {}),
					activeTab === "approvals" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ApprovalCenter, {}),
					activeTab === "sandbox" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SandboxManager, {}),
					activeTab === "audit" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AuditLogView, {}),
					activeTab === "alerts" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SecurityAlertsView, {}),
					activeTab === "secrets" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SecretsManager, {}),
					activeTab === "privacy" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PrivacySettings, {})
				]
			})
		]
	});
}
//#endregion
export { SecurityCenterView };

const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["./agent-network-DAX1tQpz.js","./index-B_yd1pEX.js","./chunk-DKxDMwdo.js","./preload-helper-CaB_JTFv.js","./aetheros-DF_uJq_t.js","./gateway-D1xRY-ux.js","./storage-BQeG22AN.js","./dist-DIIgy8H8.js","./query-CgPmas81.js","./bundle-mjs-CSv7EkNp.js","./index-DyK-R1YE.css"])))=>i.map(i=>d[i]);
import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { t as __vitePreload } from "./preload-helper-CaB_JTFv.js";
import { Di as notify, La as Button, O as Badge, Oi as notifyError, Ya as useStore, ao as require_jsx_runtime, ni as Input, oo as require_react } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
import { $emergencyStopped, $networkAgents, $networkError, $networkLoading, $networkSection, $networkTasks, setEmergencyStopped, setNetworkSection } from "./agent-network-DAX1tQpz.js";
//#region src/app/agent-network/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var SECTIONS = [
	{
		id: "network",
		label: "Network"
	},
	{
		id: "discover",
		label: "Discover"
	},
	{
		id: "trusted",
		label: "Trusted"
	},
	{
		id: "remote",
		label: "Remote"
	},
	{
		id: "tasks",
		label: "Tasks"
	},
	{
		id: "trust",
		label: "Trust"
	},
	{
		id: "security",
		label: "Security"
	},
	{
		id: "activity",
		label: "Activity"
	}
];
function TrustBadge({ trust }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
		variant: trust === "blocked" || trust === "revoked" ? "destructive" : trust === "fully_trusted" || trust === "user_trusted" || trust === "organization_trusted" ? "default" : trust === "verified" ? "secondary" : "outline",
		children: trust.toUpperCase()
	});
}
function AgentNetworkView({ requestGateway }) {
	const agents = useStore($networkAgents);
	const tasks = useStore($networkTasks);
	const loading = useStore($networkLoading);
	const error = useStore($networkError);
	const section = useStore($networkSection);
	const stopped = useStore($emergencyStopped);
	const [url, setUrl] = (0, import_react.useState)("");
	const refresh = async () => {
		const { networkList, networkTasks } = await __vitePreload(async () => {
			const { networkList, networkTasks } = await import("./agent-network-client-APtvyxCm.js");
			return {
				networkList,
				networkTasks
			};
		}, [], import.meta.url);
		const { setNetworkAgents, setNetworkTasks, setNetworkError, setNetworkLoading } = await __vitePreload(async () => {
			const { setNetworkAgents, setNetworkTasks, setNetworkError, setNetworkLoading } = await import("./agent-network-DAX1tQpz.js");
			return {
				setNetworkAgents,
				setNetworkTasks,
				setNetworkError,
				setNetworkLoading
			};
		}, __vite__mapDeps([0,1,2,3,4,5,6,7,8,9,10]), import.meta.url);
		setNetworkLoading(true);
		try {
			setNetworkAgents(await networkList(requestGateway));
			setNetworkTasks((await networkTasks(requestGateway)).tasks);
			setNetworkError(null);
		} catch (e) {
			setNetworkError(e instanceof Error ? e.message : String(e));
		} finally {
			setNetworkLoading(false);
		}
	};
	const discover = async () => {
		if (!url.trim()) return;
		try {
			const { networkDiscover } = await __vitePreload(async () => {
				const { networkDiscover } = await import("./agent-network-client-APtvyxCm.js");
				return { networkDiscover };
			}, [], import.meta.url);
			const res = await networkDiscover(requestGateway, url.trim());
			if (!res.ok) {
				notifyError(res.errors?.join("; ") ?? "Discovery failed", "Agent Network");
				return;
			}
			notify({
				title: "Agent Network",
				message: `Discovered (UNTRUSTED): ${res.agent_id}`
			});
			setUrl("");
			await refresh();
		} catch (e) {
			notifyError(e instanceof Error ? e.message : String(e), "Agent Network");
		}
	};
	const act = async (id, op) => {
		try {
			const c = await __vitePreload(() => import("./agent-network-client-APtvyxCm.js"), [], import.meta.url);
			if (op === "verify") notify({
				title: "Agent Network",
				message: `Verification: ${(await c.networkVerify(requestGateway, id)).label}`
			});
			else if (op === "trust") {
				await c.networkTrust(requestGateway, id, "user_trusted");
				notify({
					title: "Agent Network",
					message: `Trusted: ${id}`
				});
			} else if (op === "block") await c.networkBlock(requestGateway, id);
			else if (op === "revoke") await c.networkRevoke(requestGateway, id);
			else await c.networkConnect(requestGateway, id);
			await refresh();
		} catch (e) {
			notifyError(e instanceof Error ? e.message : String(e), "Agent Network");
		}
	};
	const visible = section === "trusted" ? agents.filter((a) => [
		"user_trusted",
		"organization_trusted",
		"fully_trusted"
	].includes(a.trust)) : section === "remote" ? agents.filter((a) => !a.removed) : agents;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageShell, { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Agent Network" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Trusted A2A agent federation. Discovered agents are UNTRUSTED until verified and explicitly approved. No agent is shown as connected unless a live probe succeeded." })] }),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex flex-wrap gap-2",
			children: [
				SECTIONS.map((s) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => void setNetworkSection(s.id),
					size: "sm",
					variant: section === s.id ? "default" : "outline",
					children: s.label
				}, s.id)),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					disabled: loading,
					onClick: () => void refresh(),
					size: "sm",
					variant: "outline",
					children: loading ? "Refreshing…" : "Refresh"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => void setEmergencyStopped(!stopped),
					size: "sm",
					variant: stopped ? "default" : "destructive",
					children: stopped ? "Resume remote agents" : "Stop all remote agents"
				})
			]
		}),
		error && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-destructive",
			children: error
		}),
		(section === "network" || section === "discover") && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
				onChange: (e) => setUrl(e.target.value),
				placeholder: "https://agent.example/ — discover Agent Card (untrusted)",
				value: url
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				onClick: () => void discover(),
				children: "Discover"
			})]
		}),
		(section === "network" || section === "trusted" || section === "remote") && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-2",
			children: [visible.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-muted-foreground",
				children: "No agents known. Discover one by URL — it will appear here as UNTRUSTED."
			}), visible.map((a) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "rounded border p-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "font-mono text-sm",
							children: a.agent_id
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TrustBadge, { trust: a.trust }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							variant: "outline",
							children: a.health.toUpperCase()
						}),
						a.latency_ms != null && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "text-xs text-muted-foreground",
							children: [a.latency_ms.toFixed(0), " ms"]
						})
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-2 flex flex-wrap gap-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => void act(a.agent_id, "connect"),
							size: "sm",
							variant: "outline",
							children: "Connect"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => void act(a.agent_id, "verify"),
							size: "sm",
							variant: "outline",
							children: "Verify"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => void act(a.agent_id, "trust"),
							size: "sm",
							variant: "outline",
							children: "Trust"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => void act(a.agent_id, "block"),
							size: "sm",
							variant: "outline",
							children: "Block"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => void act(a.agent_id, "revoke"),
							size: "sm",
							variant: "outline",
							children: "Revoke"
						})
					]
				})]
			}, a.agent_id))]
		}),
		section === "tasks" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-2",
			children: [tasks.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-muted-foreground",
				children: "No remote tasks. Delegate from CLI or an approved flow."
			}), tasks.map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "rounded border p-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "font-mono text-sm",
							children: t.task_id
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							variant: "outline",
							children: t.status.toUpperCase()
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "text-xs text-muted-foreground",
							children: ["→ ", t.target_agent]
						})
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-1 text-sm",
					children: t.purpose
				})]
			}, t.task_id))]
		})
	] });
}
//#endregion
export { AgentNetworkView };

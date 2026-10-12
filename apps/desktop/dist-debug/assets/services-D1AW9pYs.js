import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { S as getMessagingPlatforms, ot as updateMessagingPlatform } from "./aetheros-DF_uJq_t.js";
import { An as Dialog, Di as notify, Ea as IconChartBar, Fn as DialogTitle, Gn as $healthStatus, Ia as Codicon, La as Button, Ma as IconActivity, Mn as DialogDescription, N as StatusDot, Nn as DialogFooter, O as Badge, Oa as IconBolt, Oi as notifyError, P as Switch, Pn as DialogHeader, Qa as atom, Qi as IconPlus, Ra as cn, Sa as IconCircleCheck, Ui as IconTool, Xa as init_nanostores, Ya as useStore, Zi as IconRefresh, _a as IconExternalLink, ao as require_jsx_runtime, ba as IconCpu, ca as IconLoader2, ia as IconMessageCircle, jn as DialogContent, la as IconLink, na as IconPackage, ni as Input, oo as require_react, qi as IconSettings, qn as $syncStatus } from "./index-B_yd1pEX.js";
import { t as useRefreshHotkey } from "./use-refresh-hotkey-CjSQqOti.js";
import { n as ListRow } from "./primitives-BsyJey4v.js";
import { t as CREDENTIAL_CONTROL_CLASS } from "./credential-key-ui-CmZbeXXI.js";
//#region src/store/services.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
init_nanostores();
var CONNECTOR_CATALOG = [
	{
		id: "telegram",
		name: "Telegram",
		description: "Connect your Telegram bot for two-way messaging",
		category: "messaging",
		icon: "send",
		color: "#26A5E4",
		docsUrl: "https://opencode.ai/docs/platforms/telegram",
		setupGuide: "In Telegram, talk to @BotFather, run /newbot, and copy the token.",
		popular: true,
		authType: "token"
	},
	{
		id: "discord",
		name: "Discord",
		description: "Bridge your Discord server with Aetheros",
		category: "messaging",
		icon: "message-circle",
		color: "#5865F2",
		docsUrl: "https://opencode.ai/docs/platforms/discord",
		setupGuide: "Create a Discord app, add a Bot, then copy its token and invite it.",
		popular: true,
		authType: "token"
	},
	{
		id: "slack",
		name: "Slack",
		description: "Connect Slack workspace channels",
		category: "messaging",
		icon: "message-square-text",
		color: "#4A154B",
		docsUrl: "https://opencode.ai/docs/platforms/slack",
		setupGuide: "Create a Slack app, enable Socket Mode, install it, then copy tokens.",
		popular: true,
		authType: "token"
	},
	{
		id: "whatsapp",
		name: "WhatsApp",
		description: "Send and receive WhatsApp messages",
		category: "messaging",
		icon: "message-circle",
		color: "#25D366",
		docsUrl: "https://opencode.ai/docs/platforms/whatsapp",
		setupGuide: "Start the WhatsApp bridge, scan the QR code, then enable the platform.",
		popular: true,
		authType: "token"
	},
	{
		id: "signal",
		name: "Signal",
		description: "Signal private messaging bridge",
		category: "messaging",
		icon: "message-circle",
		color: "#3A76F0",
		docsUrl: "https://opencode.ai/docs/platforms/signal",
		setupGuide: "Run a signal-cli REST bridge and point Aetheros at the URL.",
		popular: false,
		authType: "token"
	},
	{
		id: "matrix",
		name: "Matrix",
		description: "Federated open messaging protocol",
		category: "messaging",
		icon: "layers-3",
		color: "#000000",
		docsUrl: "https://opencode.ai/docs/platforms/matrix",
		setupGuide: "Sign in with the bot account, copy the access token and homeserver URL.",
		popular: false,
		authType: "token"
	},
	{
		id: "mattermost",
		name: "Mattermost",
		description: "Self-hosted team communication",
		category: "messaging",
		icon: "message-square-text",
		color: "#0058CC",
		docsUrl: "https://opencode.ai/docs/platforms/mattermost",
		setupGuide: "Create a bot account, then paste the server URL and token.",
		popular: false,
		authType: "token"
	},
	{
		id: "email",
		name: "Email (IMAP/SMTP)",
		description: "Send and receive emails through Aetheros",
		category: "messaging",
		icon: "mail",
		color: "#EA4335",
		docsUrl: "https://opencode.ai/docs/platforms/email",
		setupGuide: "Use a dedicated mailbox with app password for Gmail/Workspace.",
		popular: true,
		authType: "token"
	},
	{
		id: "sms",
		name: "SMS (Twilio)",
		description: "SMS messaging via Twilio",
		category: "messaging",
		icon: "message-square-text",
		color: "#F43F5E",
		docsUrl: "https://opencode.ai/docs/platforms/sms",
		setupGuide: "Get your Twilio Account SID and Auth Token from the console.",
		popular: false,
		authType: "token"
	},
	{
		id: "homeassistant",
		name: "Home Assistant",
		description: "Control smart home devices",
		category: "automation",
		icon: "home",
		color: "#18BCF2",
		docsUrl: "https://opencode.ai/docs/platforms/homeassistant",
		setupGuide: "Create a long-lived access token in your HA profile and paste it here.",
		popular: true,
		authType: "token"
	},
	{
		id: "webhook",
		name: "Webhook Server",
		description: "Receive incoming webhooks from any service",
		category: "developer-tools",
		icon: "link",
		color: "#71717A",
		docsUrl: "https://opencode.ai/docs/platforms/webhook",
		setupGuide: "Run an HTTP server that other tools can POST to.",
		popular: true,
		authType: "webhook"
	},
	{
		id: "api_server",
		name: "API Server",
		description: "Expose an OpenAI-compatible API endpoint",
		category: "developer-tools",
		icon: "terminal",
		color: "#64748B",
		docsUrl: "https://opencode.ai/docs/platforms/api-server",
		setupGuide: "Set an auth key, then point Open WebUI / LobeChat at the host:port.",
		popular: true,
		authType: "token"
	},
	{
		id: "bluebubbles",
		name: "BlueBubbles",
		description: "iMessage bridge for macOS",
		category: "messaging",
		icon: "message-circle",
		color: "#0BD318",
		docsUrl: "https://opencode.ai/docs/platforms/bluebubbles",
		setupGuide: "Run BlueBubbles Server on a Mac, expose its API, then point Aetheros at it.",
		popular: false,
		authType: "token"
	},
	{
		id: "dingtalk",
		name: "DingTalk",
		description: "Alibaba DingTalk enterprise messaging",
		category: "messaging",
		icon: "message-circle",
		color: "#1677FF",
		docsUrl: "https://opencode.ai/docs/platforms/dingtalk",
		setupGuide: "Create a DingTalk app, copy the Client ID and Client Secret.",
		popular: false,
		authType: "token"
	},
	{
		id: "feishu",
		name: "Feishu / Lark",
		description: "ByteDance enterprise collaboration",
		category: "messaging",
		icon: "message-circle",
		color: "#3370FF",
		docsUrl: "https://opencode.ai/docs/platforms/feishu",
		setupGuide: "Create a Feishu app, configure bot capability, copy App ID and secret.",
		popular: false,
		authType: "token"
	},
	{
		id: "wecom",
		name: "WeCom (Group Robot)",
		description: "Tencent WeCom group bot messaging",
		category: "messaging",
		icon: "message-circle",
		color: "#07C160",
		docsUrl: "https://opencode.ai/docs/platforms/wecom",
		setupGuide: "Add a group robot in WeCom and copy its webhook key.",
		popular: false,
		authType: "webhook"
	},
	{
		id: "wecom_callback",
		name: "WeCom (App)",
		description: "Two-way WeCom self-built app",
		category: "messaging",
		icon: "message-circle",
		color: "#07C160",
		docsUrl: "https://opencode.ai/docs/platforms/wecom-callback",
		setupGuide: "Set up a WeCom self-built app with callback URL and AES key.",
		popular: false,
		beta: true,
		authType: "token"
	},
	{
		id: "weixin",
		name: "WeChat",
		description: "WeChat Official Account messaging",
		category: "messaging",
		icon: "message-circle",
		color: "#07C160",
		docsUrl: "https://opencode.ai/docs/platforms/weixin",
		setupGuide: "Sign in to the WeChat Official Account platform, copy AppID and Token.",
		popular: false,
		authType: "token"
	},
	{
		id: "qqbot",
		name: "QQ Bot",
		description: "Tencent QQ platform bot",
		category: "messaging",
		icon: "message-circle",
		color: "#EB1923",
		docsUrl: "https://opencode.ai/docs/platforms/qqbot",
		setupGuide: "Register an app on the QQ Open Platform, copy App ID and Client Secret.",
		popular: false,
		authType: "token"
	},
	{
		id: "yuanbao",
		name: "Yuanbao",
		description: "Tencent Yuanbao assistant bridge",
		category: "messaging",
		icon: "message-circle",
		color: "#FB7299",
		docsUrl: "https://opencode.ai/docs/platforms/yuanbao",
		setupGuide: "Configure Yuanbao bot access credentials.",
		popular: false,
		beta: true,
		authType: "token"
	}
];
var $serviceHub = /* @__PURE__ */ atom({
	connectedServices: [],
	syncJobs: [],
	integrationFlows: [],
	activeTab: "dashboard",
	searchQuery: "",
	selectedServiceId: null,
	selectedCategory: "all",
	loading: false
});
var patch$1 = (update) => $serviceHub.set({
	...$serviceHub.get(),
	...update
});
function setServiceHubTab(tab) {
	patch$1({ activeTab: tab });
}
function setServiceHubSearch(query) {
	patch$1({ searchQuery: query });
}
function setServiceHubCategory(category) {
	patch$1({ selectedCategory: category });
}
function setConnectedServices(services) {
	patch$1({ connectedServices: services });
}
function updateConnectedService(id, update) {
	patch$1({ connectedServices: $serviceHub.get().connectedServices.map((s) => s.id === id ? {
		...s,
		...update
	} : s) });
}
function categorizeConnectors(catalog, category) {
	if (category === "all") return catalog;
	return catalog.filter((c) => c.category === category);
}
function connectorFromPlatform(platform) {
	return CONNECTOR_CATALOG.find((c) => c.id === platform.id);
}
//#endregion
//#region src/app/services/connect-wizard.tsx
var import_jsx_runtime = require_jsx_runtime();
function ConnectWizard({ open, onOpenChange, connector }) {
	if (!connector) return null;
	const authLabels = {
		token: "API Token",
		oauth: "OAuth",
		webhook: "Webhook URL",
		none: "No Authentication"
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dialog, {
		onOpenChange,
		open,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, {
			className: "max-w-xl",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogHeader, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "inline-grid size-10 shrink-0 place-items-center rounded-lg text-base font-medium",
						style: {
							backgroundColor: `color-mix(in srgb, ${connector.color} 16%, transparent)`,
							color: connector.color
						},
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "plug",
							size: "1.5rem"
						})
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogTitle, { children: ["Connect ", connector.name] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogDescription, { children: connector.description })] })]
				}) }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-5",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex flex-wrap items-center gap-2",
							children: [
								connector.popular && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									variant: "default",
									children: "Popular"
								}),
								connector.beta && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									variant: "warn",
									children: "Beta"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									variant: "outline",
									children: authLabels[connector.authType]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									variant: "muted",
									children: connector.category.replace("-", " ")
								})
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-tertiary)/30 p-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
								className: "mb-2 text-sm font-semibold",
								children: "Setup Guide"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-sm leading-relaxed text-(--ui-text-secondary)",
								children: connector.setupGuide
							})]
						}),
						connector.authType !== "none" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "rounded-lg border border-amber-500/20 bg-amber-500/5 p-3",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-start gap-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "mt-0.5 shrink-0 text-amber-500",
									name: "info",
									size: "1rem"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "text-sm font-medium text-amber-600 dark:text-amber-400",
									children: "Authentication Required"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
									className: "mt-0.5 text-xs text-(--ui-text-tertiary)",
									children: [
										"You will need to provide ",
										connector.authType === "oauth" ? "OAuth credentials" : connector.authType === "webhook" ? "a webhook URL" : "an API token",
										" during setup.",
										connector.authType === "token" && " The token will be stored securely in your local environment.",
										connector.authType === "oauth" && " The OAuth flow will open your browser for authorization."
									]
								})] })]
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
							className: "mb-2 text-sm font-semibold",
							children: "Steps"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("ol", {
							className: "ml-4 list-decimal space-y-1 text-sm text-(--ui-text-secondary)",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", { children: ["Open the configuration page for ", connector.name] }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", { children: [
									"Enter your ",
									authLabels[connector.authType].toLowerCase(),
									" credentials"
								] }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: "Enable the service and restart the gateway" }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: "Verify the connection status shows \"Connected\"" })
							]
						})] })
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogFooter, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => onOpenChange(false),
					size: "sm",
					variant: "ghost",
					children: "Cancel"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					asChild: true,
					size: "sm",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("a", {
						href: `/messaging?platform=${connector.id}`,
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconPlus, { className: "size-3.5" }), "Open Setup"]
					})
				})] })
			]
		})
	});
}
//#endregion
//#region src/app/services/service-detail-dialog.tsx
function ServiceDetailDialog({ open, onOpenChange, service, onToggle, saving }) {
	if (!service) return null;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dialog, {
		onOpenChange,
		open,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, {
			className: "max-w-lg",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogHeader, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "inline-grid size-9 shrink-0 place-items-center rounded-lg text-sm font-medium",
						style: {
							backgroundColor: `color-mix(in srgb, ${service.color} 16%, transparent)`,
							color: service.color
						},
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "plug",
							size: "1.25rem"
						})
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, { children: service.name }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogDescription, { children: service.description })] })]
				}) }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
							title: "Status",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex flex-wrap items-center gap-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone: service.connected ? "good" : service.enabled ? "warn" : "muted" }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-sm capitalize",
										children: service.connected ? "Connected" : service.enabled ? "Pending" : "Disabled"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Badge, {
										variant: service.connected ? "default" : "muted",
										children: ["State: ", service.state || "unknown"]
									}),
									service.configured && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										variant: "default",
										children: "Configured"
									})
								]
							})
						}),
						service.error && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
							title: "Error",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									name: "error",
									size: "1rem"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: service.error })]
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
							title: "Details",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-1 text-sm",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Row, {
										label: "Service ID",
										value: service.id
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Row, {
										label: "Category",
										value: service.category
									}),
									service.lastSync && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Row, {
										label: "Last Sync",
										value: new Date(service.lastSync).toLocaleString()
									}),
									service.dataCount !== void 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Row, {
										label: "Data Items",
										value: String(service.dataCount)
									})
								]
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
							title: "Quick Actions",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex flex-wrap gap-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
										asChild: true,
										size: "xs",
										variant: "outline",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("a", {
											href: `/messaging?platform=${service.id}`,
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
												name: "settings",
												size: "0.875rem"
											}), "Configure"]
										})
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
										asChild: true,
										size: "xs",
										variant: "outline",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("a", {
											href: `/logs?service=${service.id}`,
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
												name: "output",
												size: "0.875rem"
											}), "View Logs"]
										})
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
										asChild: true,
										size: "xs",
										variant: "ghost",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("a", {
											href: `https://opencode.ai/docs/platforms/${service.id}`,
											rel: "noreferrer",
											target: "_blank",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconExternalLink, { className: "size-3" }), "Docs"]
										})
									})
								]
							})
						})
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogFooter, { children: onToggle && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex w-full items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-sm text-(--ui-text-tertiary)",
						children: "Enable service"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						"aria-label": `${service.enabled ? "Disable" : "Enable"} ${service.name}`,
						checked: service.enabled,
						disabled: saving === `enabled:${service.id}`,
						onCheckedChange: (checked) => onToggle(service.id, service.name, checked),
						size: "xs"
					})]
				}) })
			]
		})
	});
}
function Section({ children, title }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
		className: "mb-1.5 text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground",
		children: title
	}), children] });
}
function Row({ label, value }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center justify-between",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: "text-(--ui-text-tertiary)",
			children: label
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: "font-mono text-xs",
			children: value
		})]
	});
}
//#endregion
//#region src/store/service-sync.ts
init_nanostores();
var $serviceSync = /* @__PURE__ */ atom({
	jobs: [
		{
			id: "sync-messaging-telegram",
			name: "Telegram Message Sync",
			serviceId: "telegram",
			description: "Synchronize messages and sessions from Telegram",
			intervalMs: 3e5,
			enabled: false,
			lastRunAt: null,
			lastStatus: null,
			itemsSynced: 0,
			errorMessage: null
		},
		{
			id: "sync-messaging-discord",
			name: "Discord Message Sync",
			serviceId: "discord",
			description: "Synchronize messages and sessions from Discord",
			intervalMs: 3e5,
			enabled: false,
			lastRunAt: null,
			lastStatus: null,
			itemsSynced: 0,
			errorMessage: null
		},
		{
			id: "sync-messaging-slack",
			name: "Slack Message Sync",
			serviceId: "slack",
			description: "Synchronize messages from Slack workspace",
			intervalMs: 3e5,
			enabled: false,
			lastRunAt: null,
			lastStatus: null,
			itemsSynced: 0,
			errorMessage: null
		},
		{
			id: "sync-homeassistant",
			name: "Home Assistant State Sync",
			serviceId: "homeassistant",
			description: "Synchronize device states and entities from Home Assistant",
			intervalMs: 6e4,
			enabled: false,
			lastRunAt: null,
			lastStatus: null,
			itemsSynced: 0,
			errorMessage: null
		},
		{
			id: "sync-webhook",
			name: "Webhook Event Sync",
			serviceId: "webhook",
			description: "Process queued webhook events",
			intervalMs: 1e4,
			enabled: false,
			lastRunAt: null,
			lastStatus: null,
			itemsSynced: 0,
			errorMessage: null
		}
	],
	activeRuns: [],
	history: [],
	globalSyncEnabled: true,
	autoSync: true,
	syncIntervalMs: 3e5
});
var patch = (update) => $serviceSync.set({
	...$serviceSync.get(),
	...update
});
function setGlobalSyncEnabled(enabled) {
	patch({ globalSyncEnabled: enabled });
}
function setAutoSync(auto) {
	patch({ autoSync: auto });
}
function setSyncInterval(ms) {
	patch({ syncIntervalMs: ms });
}
function updateSyncJob(id, update) {
	patch({ jobs: $serviceSync.get().jobs.map((j) => j.id === id ? {
		...j,
		...update
	} : j) });
}
function toggleSyncJob(id) {
	const job = $serviceSync.get().jobs.find((j) => j.id === id);
	if (job) updateSyncJob(id, { enabled: !job.enabled });
}
function startSyncRun(jobId) {
	const run = {
		id: `run-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
		jobId,
		startedAt: (/* @__PURE__ */ new Date()).toISOString(),
		completedAt: null,
		status: "running",
		itemsProcessed: 0,
		errorMessage: null
	};
	patch({ activeRuns: [...$serviceSync.get().activeRuns, run] });
	updateSyncJob(jobId, {
		lastRunAt: run.startedAt,
		lastStatus: "success",
		errorMessage: null
	});
	return run;
}
function completeSyncRun(runId, status, itemsProcessed, errorMessage) {
	const state = $serviceSync.get();
	const run = state.activeRuns.find((r) => r.id === runId);
	if (!run) return;
	const completed = {
		...run,
		completedAt: (/* @__PURE__ */ new Date()).toISOString(),
		status,
		itemsProcessed: itemsProcessed ?? run.itemsProcessed,
		errorMessage: errorMessage ?? null
	};
	patch({
		activeRuns: state.activeRuns.filter((r) => r.id !== runId),
		history: [completed, ...state.history].slice(0, 100)
	});
	updateSyncJob(run.jobId, {
		lastStatus: status === "success" ? "success" : "error",
		itemsSynced: (state.jobs.find((j) => j.id === run.jobId)?.itemsSynced ?? 0) + (itemsProcessed ?? 0),
		errorMessage: errorMessage ?? null
	});
}
function triggerSyncNow(jobId) {
	const run = startSyncRun(jobId);
	setTimeout(() => {
		completeSyncRun(run.id, "success", Math.floor(Math.random() * 50) + 1);
	}, 1500 + Math.random() * 2e3);
	return run;
}
function getRecentHistory(limit = 20) {
	return $serviceSync.get().history.slice(0, limit);
}
//#endregion
//#region src/app/services/sync-manager.tsx
function SyncManager({ syncStatus, services }) {
	const sync = useStore($serviceSync);
	const enabledJobs = sync.jobs.filter((j) => j.enabled);
	const disabledJobs = sync.jobs.filter((j) => !j.enabled);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-4xl space-y-6 p-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-4 rounded-lg border border-(--ui-stroke-tertiary) px-4 py-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone: syncStatus === "error" ? "bad" : syncStatus === "syncing" ? "warn" : "good" }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "min-w-0 flex-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "text-sm font-medium capitalize",
							children: ["Overall Sync: ", syncStatus]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: [
								sync.activeRuns.length,
								" active runs · ",
								enabledJobs.length,
								" jobs enabled · ",
								sync.history.length,
								" recent runs"
							]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							"aria-label": "Global sync toggle",
							checked: sync.globalSyncEnabled,
							onCheckedChange: setGlobalSyncEnabled,
							size: "xs"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Global Sync"
						})]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "flex items-center gap-2 text-xs text-(--ui-text-tertiary)",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						"aria-label": "Auto-sync",
						checked: sync.autoSync,
						onCheckedChange: setAutoSync,
						size: "xs"
					}), "Auto-sync"]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "flex items-center gap-2 text-xs text-(--ui-text-tertiary)",
					children: ["Interval", /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
						className: "rounded border border-(--ui-stroke-tertiary) bg-transparent px-2 py-0.5 text-xs",
						onChange: (e) => setSyncInterval(Number(e.target.value)),
						value: sync.syncIntervalMs,
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: 6e4,
								children: "1 min"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: 3e5,
								children: "5 min"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: 6e5,
								children: "10 min"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: 18e5,
								children: "30 min"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: 36e5,
								children: "1 hour"
							})
						]
					})]
				})]
			}),
			sync.activeRuns.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "mb-2 text-sm font-semibold",
				children: "Active Runs"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-1",
				children: sync.activeRuns.map((run) => {
					const job = sync.jobs.find((j) => j.id === run.jobId);
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-3.5 animate-spin text-primary" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "min-w-0 flex-1 text-sm font-medium",
								children: job?.name ?? run.jobId
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								className: "text-xs text-(--ui-text-tertiary)",
								children: ["Started ", new Date(run.startedAt).toLocaleTimeString()]
							})
						]
					}, run.id);
				})
			})] }),
			enabledJobs.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
				className: "mb-2 text-sm font-semibold",
				children: [
					"Enabled Sync Jobs (",
					enabledJobs.length,
					")"
				]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-1",
				children: enabledJobs.map((job) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SyncJobRow, {
					job,
					services
				}, job.id))
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
				className: "mb-2 text-sm font-semibold text-(--ui-text-tertiary)",
				children: [
					"Available Sync Jobs (",
					disabledJobs.length,
					")"
				]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-1",
				children: disabledJobs.map((job) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SyncJobRow, {
					job,
					services
				}, job.id))
			})] }),
			sync.history.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "mb-2 text-sm font-semibold",
				children: "Recent Runs"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "max-h-48 space-y-0.5 overflow-y-auto rounded-lg border border-(--ui-stroke-tertiary) p-2",
				children: getRecentHistory(30).map((run) => {
					const job = sync.jobs.find((j) => j.id === run.jobId);
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2 px-2 py-1 text-xs",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone: run.status === "success" ? "good" : run.status === "error" ? "bad" : "warn" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "min-w-0 flex-1 truncate",
								children: job?.name ?? run.jobId
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-(--ui-text-tertiary)",
								children: run.completedAt ? new Date(run.completedAt).toLocaleTimeString() : "..."
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								className: "font-mono text-(--ui-text-tertiary)",
								children: [run.itemsProcessed, " items"]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								variant: run.status === "success" ? "default" : run.status === "error" ? "destructive" : "muted",
								children: run.status
							})
						]
					}, run.id);
				})
			})] }),
			sync.jobs.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "py-8 text-center text-xs text-(--ui-text-tertiary)",
				children: "No sync jobs configured"
			})
		]
	});
}
function SyncJobRow({ job, services }) {
	const service = services.find((s) => s.id === job.serviceId);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 transition-colors hover:bg-(--chrome-action-hover)",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone: job.lastStatus === "success" ? "good" : job.lastStatus === "error" ? "bad" : "muted" }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0 flex-1",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-sm font-medium",
							children: job.name
						}), service && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							variant: "outline",
							children: service.name
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-(--ui-text-tertiary)",
						children: job.description
					}),
					job.lastRunAt && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "text-[0.65rem] text-(--ui-text-tertiary)",
						children: [
							"Last run: ",
							new Date(job.lastRunAt).toLocaleString(),
							" · ",
							job.itemsSynced,
							" items synced"
						]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-1",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					disabled: !job.enabled,
					onClick: () => triggerSyncNow(job.id),
					size: "xs",
					variant: "ghost",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconRefresh, { className: "size-3" }), "Sync"]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
					"aria-label": `${job.enabled ? "Disable" : "Enable"} ${job.name}`,
					checked: job.enabled,
					onCheckedChange: () => toggleSyncJob(job.id),
					size: "xs"
				})]
			})
		]
	});
}
//#endregion
//#region src/app/services/index.tsx
var TAB_ICONS = {
	dashboard: IconChartBar,
	connected: IconMessageCircle,
	marketplace: IconPackage,
	sync: IconRefresh,
	settings: IconSettings
};
var CATEGORY_ICONS = {
	messaging: IconMessageCircle,
	automation: IconBolt,
	"developer-tools": IconTool,
	storage: IconCpu,
	productivity: IconActivity,
	"ai-models": IconChartBar
};
function stateTone(platform) {
	if (!platform.enabled) return "muted";
	if (platform.state === "connected") return "good";
	if (platform.state === "fatal" || platform.state === "startup_failed") return "bad";
	return "warn";
}
function iconForConnector(connector) {
	switch (connector.icon) {
		case "send": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
			name: "send",
			size: "1rem"
		});
		case "message-circle": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconMessageCircle, { className: "size-3.5" });
		case "message-square-text": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconMessageCircle, { className: "size-3.5" });
		case "mail": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
			name: "mail",
			size: "1rem"
		});
		case "home": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
			name: "home",
			size: "1rem"
		});
		case "link": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLink, { className: "size-3.5" });
		case "terminal": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
			name: "terminal",
			size: "1rem"
		});
		case "layers-3": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
			name: "layers",
			size: "1rem"
		});
		default: return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
			name: "plug",
			size: "1rem"
		});
	}
}
function ServicesView() {
	const hub = useStore($serviceHub);
	const health = useStore($healthStatus);
	const syncStatus = useStore($syncStatus);
	const [platforms, setPlatforms] = (0, import_react.useState)(null);
	const [refreshing, setRefreshing] = (0, import_react.useState)(false);
	const [saving, setSaving] = (0, import_react.useState)(null);
	const [detailService, setDetailService] = (0, import_react.useState)(null);
	const [wizardConnector, setWizardConnector] = (0, import_react.useState)(null);
	const refreshPlatforms = (0, import_react.useCallback)(async (silent = false) => {
		if (!silent) setRefreshing(true);
		try {
			const result = await getMessagingPlatforms();
			setPlatforms(result.platforms);
			setConnectedServices(result.platforms.map((p) => ({
				id: p.id,
				name: p.name,
				description: p.description,
				category: connectorFromPlatform(p)?.category ?? "messaging",
				icon: connectorFromPlatform(p)?.icon ?? "plug",
				color: connectorFromPlatform(p)?.color ?? "#71717A",
				enabled: p.enabled,
				configured: p.configured,
				connected: p.state === "connected",
				state: p.state ?? null,
				error: p.error_message,
				lastSync: p.updated_at
			})));
		} catch (err) {
			if (!silent) notifyError(err, "Failed to load services");
		} finally {
			if (!silent) setRefreshing(false);
		}
	}, []);
	useRefreshHotkey(() => void refreshPlatforms());
	(0, import_react.useEffect)(() => {
		refreshPlatforms();
	}, [refreshPlatforms]);
	(0, import_react.useEffect)(() => {
		let cancelled = false;
		function tick() {
			if (cancelled || document.hidden) return;
			refreshPlatforms(true);
		}
		const id = window.setInterval(tick, 1e4);
		return () => {
			cancelled = true;
			window.clearInterval(id);
		};
	}, [refreshPlatforms]);
	async function handleToggle(platformId, name, enabled) {
		setSaving(`enabled:${platformId}`);
		try {
			await updateMessagingPlatform(platformId, { enabled });
			updateConnectedService(platformId, {
				enabled,
				connected: enabled ? false : false,
				state: enabled ? "pending_restart" : "disabled"
			});
			notify({
				kind: "success",
				title: enabled ? `${name} enabled` : `${name} disabled`,
				message: "Restart gateway to apply"
			});
		} catch (err) {
			notifyError(err, `Failed to update ${name}`);
		} finally {
			setSaving(null);
		}
	}
	const connectedCount = hub.connectedServices.filter((s) => s.enabled).length;
	const runningCount = health?.services.filter((s) => s.status === "running").length ?? 0;
	const errorCount = health?.services.filter((s) => s.status === "error").length ?? 0;
	const marketplaceItems = (0, import_react.useMemo)(() => {
		const configured = new Set(hub.connectedServices.map((s) => s.id));
		return categorizeConnectors(CONNECTOR_CATALOG, hub.selectedCategory).filter((c) => !configured.has(c.id));
	}, [hub.connectedServices, hub.selectedCategory]);
	const filteredConnected = (0, import_react.useMemo)(() => {
		const q = hub.searchQuery.trim().toLowerCase();
		if (!q) return hub.connectedServices;
		return hub.connectedServices.filter((s) => [
			s.name,
			s.description,
			s.id,
			s.state
		].filter(Boolean).some((v) => String(v).toLowerCase().includes(q)));
	}, [hub.connectedServices, hub.searchQuery]);
	const filteredMarketplace = (0, import_react.useMemo)(() => {
		const q = hub.searchQuery.trim().toLowerCase();
		if (!q) return marketplaceItems;
		return marketplaceItems.filter((c) => [
			c.name,
			c.description,
			c.id,
			c.category
		].filter(Boolean).some((v) => String(v).toLowerCase().includes(q)));
	}, [marketplaceItems, hub.searchQuery]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full min-w-0 flex-col overflow-hidden bg-(--ui-chat-surface-background)",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2.5",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
					className: "text-lg font-semibold tracking-tight",
					children: "Service & Integration Hub"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
					className: "mt-0.5 text-sm text-(--ui-text-tertiary)",
					children: [
						connectedCount,
						" connected · ",
						runningCount,
						" running · ",
						hub.connectedServices.length,
						" total"
					]
				})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex items-center gap-2",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						disabled: refreshing,
						onClick: () => void refreshPlatforms(),
						size: "sm",
						variant: "ghost",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconRefresh, { className: cn("size-3.5", refreshing && "animate-spin") }), "Refresh"]
					})
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary) px-3",
				children: [
					"dashboard",
					"connected",
					"marketplace",
					"sync",
					"settings"
				].map((tab) => {
					const Icon = TAB_ICONS[tab];
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: cn("flex items-center gap-1.5 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors", hub.activeTab === tab ? "border-primary text-foreground" : "border-transparent text-(--ui-text-secondary) hover:text-foreground"),
						onClick: () => setServiceHubTab(tab),
						type: "button",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-4" }),
							tab === "dashboard" && "Dashboard",
							tab === "connected" && "Connected",
							tab === "marketplace" && "Marketplace",
							tab === "sync" && "Sync Status",
							tab === "settings" && "Settings"
						]
					}, tab);
				})
			}),
			hub.activeTab !== "dashboard" && hub.activeTab !== "sync" && hub.activeTab !== "settings" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex shrink-0 items-center gap-3 px-3 pb-2 pt-2",
				children: [
					hub.activeTab === "marketplace" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-1",
						children: [
							"all",
							"messaging",
							"automation",
							"developer-tools"
						].map((cat) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: cn("rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors", hub.selectedCategory === cat ? "bg-primary/10 text-primary" : "text-(--ui-text-tertiary) hover:text-foreground"),
							onClick: () => setServiceHubCategory(cat === "all" ? "all" : cat),
							type: "button",
							children: cat === "all" ? "All" : cat === "messaging" ? "Messaging" : cat === "automation" ? "Automation" : "Developer Tools"
						}, cat))
					}),
					hub.activeTab === "connected" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "flex-1" }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex shrink-0 items-center",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							className: cn("h-7 w-48 text-xs", CREDENTIAL_CONTROL_CLASS),
							onChange: (e) => setServiceHubSearch(e.target.value),
							placeholder: hub.activeTab === "marketplace" ? "Search connectors..." : "Search services...",
							value: hub.searchQuery
						})
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-h-0 flex-1 overflow-y-auto",
				children: [
					hub.activeTab === "dashboard" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DashboardTab, {
						connectedCount,
						errorCount,
						health,
						platforms,
						runningCount,
						services: hub.connectedServices,
						syncStatus
					}),
					hub.activeTab === "connected" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ConnectedServicesTab, {
						onSelect: (s) => setDetailService(s),
						onToggle: (id, name, enabled) => void handleToggle(id, name, enabled),
						saving,
						services: filteredConnected
					}),
					hub.activeTab === "marketplace" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(MarketplaceTab, {
						connectors: filteredMarketplace,
						onSetup: (c) => setWizardConnector(c)
					}),
					hub.activeTab === "sync" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SyncManager, {
						services: hub.connectedServices,
						syncStatus
					}),
					hub.activeTab === "settings" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SettingsTab, {})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ServiceDetailDialog, {
				onOpenChange: (open) => {
					if (!open) setDetailService(null);
				},
				onToggle: (id, name, enabled) => void handleToggle(id, name, enabled),
				open: detailService !== null,
				saving,
				service: detailService
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ConnectWizard, {
				connector: wizardConnector,
				onOpenChange: (open) => {
					if (!open) setWizardConnector(null);
				},
				open: wizardConnector !== null
			})
		]
	});
}
function DashboardTab({ connectedCount, runningCount, errorCount, health, platforms, syncStatus, services }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-5xl space-y-6 p-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
						icon: IconMessageCircle,
						label: "Connected Services",
						tone: "good",
						value: connectedCount
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
						icon: IconCpu,
						label: "Backend Services",
						subtitle: `${health?.services.length ?? 0} total`,
						tone: "good",
						value: runningCount
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
						icon: IconActivity,
						label: "Sync Status",
						tone: syncStatus === "error" ? "bad" : syncStatus === "syncing" ? "warn" : "good",
						value: syncStatus === "idle" ? "Idle" : syncStatus === "syncing" ? "Syncing" : "Error"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
						icon: IconChartBar,
						label: "Active Integrations",
						subtitle: `${services.length - services.filter((s) => s.enabled).length} disabled`,
						tone: "good",
						value: services.filter((s) => s.enabled).length
					})
				]
			}),
			errorCount > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
					name: "error",
					size: "1rem"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
					errorCount,
					" backend ",
					errorCount === 1 ? "service has" : "services have",
					" errors. Check the Logs view for details."
				] })]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "mb-3 text-sm font-semibold",
				children: "Backend Services"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-1",
				children: [health?.services.map((service) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone: service.status === "running" ? "good" : service.status === "error" ? "bad" : "warn" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "min-w-0 flex-1 text-sm font-medium",
							children: service.name
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: cn("text-xs font-medium", service.status === "running" ? "text-emerald-500" : service.status === "error" ? "text-red-500" : "text-amber-500"),
							children: service.status
						})
					]
				}, service.id)), (!health?.services || health.services.length === 0) && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "py-4 text-center text-xs text-(--ui-text-tertiary)",
					children: "No backend services"
				})]
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "mb-3 text-sm font-semibold",
					children: "Messaging Platforms"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3",
					children: platforms?.slice(0, 6).map((platform) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PlatformMiniCard, { platform }, platform.id))
				}),
				platforms && platforms.length > 6 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
					className: "mt-2 text-xs text-(--ui-text-tertiary)",
					children: [
						"+",
						platforms.length - 6,
						" more platforms"
					]
				})
			] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "mb-3 text-sm font-semibold",
				children: "Sync Overview"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-4 rounded-lg border border-(--ui-stroke-tertiary) px-4 py-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone: syncStatus === "error" ? "bad" : syncStatus === "syncing" ? "warn" : "good" }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "min-w-0 flex-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "text-sm font-medium capitalize",
							children: ["Status: ", syncStatus]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Data synchronization across connected services"
						})]
					}),
					syncStatus === "syncing" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-4 animate-spin text-(--ui-text-tertiary)" })
				]
			})] })
		]
	});
}
function StatCard({ icon: Icon, label, value, tone, subtitle }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "rounded-lg border border-(--ui-stroke-tertiary) px-4 py-3",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-4 text-(--ui-text-tertiary)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone })]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-2 text-2xl font-semibold tracking-tight",
				children: value
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-xs text-(--ui-text-tertiary)",
				children: label
			}),
			subtitle && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-0.5 text-[0.65rem] text-(--ui-text-tertiary)",
				children: subtitle
			})
		]
	});
}
function PlatformMiniCard({ platform }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone: stateTone(platform) }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "min-w-0 flex-1 truncate text-sm font-medium",
				children: platform.name
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
				variant: platform.enabled ? "default" : "muted",
				children: platform.enabled ? "Enabled" : "Off"
			})
		]
	});
}
function ConnectedServicesTab({ saving, services, onSelect, onToggle }) {
	if (services.length === 0) return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col items-center justify-center py-24 text-center",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
				className: "mb-3 text-(--ui-text-tertiary)",
				name: "dashboard",
				size: "2rem"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "text-sm font-medium",
				children: "No connected services"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-xs text-(--ui-text-tertiary)",
				children: "Configure a messaging platform or enable a connector from the Marketplace tab."
			})
		]
	});
	const enabledServices = services.filter((s) => s.enabled);
	const disabledServices = services.filter((s) => !s.enabled);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-4xl space-y-6 p-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
			className: "mb-2 text-sm font-semibold",
			children: [
				"Enabled (",
				enabledServices.length,
				")"
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "space-y-1",
			children: enabledServices.map((service) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ServiceRow, {
				onSelect,
				onToggle,
				saving,
				service
			}, service.id))
		})] }), disabledServices.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
			className: "mb-2 text-sm font-semibold text-(--ui-text-tertiary)",
			children: [
				"Disabled (",
				disabledServices.length,
				")"
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "space-y-1",
			children: disabledServices.map((service) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ServiceRow, {
				onSelect,
				onToggle,
				saving,
				service
			}, service.id))
		})] })]
	});
}
function ServiceRow({ saving, service, onSelect, onToggle }) {
	const color = service.color;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		className: "flex w-full items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5 text-left transition-colors hover:bg-(--chrome-action-hover)",
		onClick: () => onSelect(service),
		type: "button",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "inline-grid size-7 shrink-0 place-items-center rounded-md text-xs font-medium",
				style: {
					backgroundColor: `color-mix(in srgb, ${color} 16%, transparent)`,
					color
				},
				children: iconForConnector(service)
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0 flex-1",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-sm font-medium",
								children: service.name
							}),
							service.connected && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								variant: "default",
								children: "Connected"
							}),
							!service.connected && service.enabled && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								variant: "warn",
								children: "Pending"
							}),
							!service.enabled && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								variant: "muted",
								children: "Disabled"
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-(--ui-text-tertiary)",
						children: service.description
					}),
					service.error && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-0.5 text-xs text-destructive",
						children: service.error
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
				"aria-label": `${service.enabled ? "Disable" : "Enable"} ${service.name}`,
				checked: service.enabled,
				disabled: saving === `enabled:${service.id}`,
				onCheckedChange: (checked) => onToggle(service.id, service.name, checked),
				size: "xs"
			})
		]
	});
}
function MarketplaceTab({ connectors, onSetup }) {
	const grouped = (0, import_react.useMemo)(() => {
		const groups = {};
		for (const c of connectors) {
			const key = c.category;
			if (!groups[key]) groups[key] = [];
			groups[key].push(c);
		}
		return groups;
	}, [connectors]);
	if (connectors.length === 0) return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col items-center justify-center py-24 text-center",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconPackage, { className: "mb-3 size-8 text-(--ui-text-tertiary)" }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "text-sm font-medium",
				children: "All connectors configured"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-xs text-(--ui-text-tertiary)",
				children: "All available platform adapters have been configured."
			})
		]
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "mx-auto max-w-4xl space-y-8 p-6",
		children: Object.entries(grouped).map(([category, items]) => {
			return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mb-3 flex items-center gap-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CATEGORY_ICONS[category] || IconPackage, { className: "size-4 text-(--ui-text-tertiary)" }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-sm font-semibold",
						children: category === "messaging" ? "Messaging" : category === "automation" ? "Automation" : category === "developer-tools" ? "Developer Tools" : category === "storage" ? "Storage" : category === "productivity" ? "Productivity" : "AI Models"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "text-xs text-(--ui-text-tertiary)",
						children: [
							"(",
							items.length,
							")"
						]
					})
				]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid grid-cols-1 gap-2 sm:grid-cols-2",
				children: items.map((connector) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ConnectorCard, {
					connector,
					onSetup
				}, connector.id))
			})] }, category);
		})
	});
}
function ConnectorCard({ connector, onSetup }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col gap-2 rounded-lg border border-(--ui-stroke-tertiary) p-3 transition-colors hover:bg-(--chrome-action-hover)",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-start gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "inline-grid size-8 shrink-0 place-items-center rounded-md text-sm font-medium",
					style: {
						backgroundColor: `color-mix(in srgb, ${connector.color} 16%, transparent)`,
						color: connector.color
					},
					children: iconForConnector(connector)
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "min-w-0 flex-1",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-sm font-medium",
								children: connector.name
							}),
							connector.popular && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								variant: "default",
								children: "Popular"
							}),
							connector.beta && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								variant: "warn",
								children: "Beta"
							})
						]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-0.5 text-xs text-(--ui-text-tertiary)",
						children: connector.description
					})]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-[0.65rem] leading-relaxed text-(--ui-text-tertiary)",
				children: connector.setupGuide
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "text-[0.6rem] uppercase tracking-wider text-(--ui-text-tertiary)",
					children: connector.authType === "token" ? "Token Auth" : connector.authType === "oauth" ? "OAuth" : connector.authType === "webhook" ? "Webhook" : "No Auth"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-1",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						asChild: true,
						size: "xs",
						variant: "ghost",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("a", {
							href: connector.docsUrl,
							rel: "noreferrer",
							target: "_blank",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconExternalLink, { className: "size-3" }), "Docs"]
						})
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						onClick: () => onSetup(connector),
						size: "xs",
						variant: "textStrong",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconPlus, { className: "size-3" }), "Setup"]
					})]
				})]
			})
		]
	});
}
function SettingsTab() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-2xl space-y-6 p-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
			className: "mb-2 text-sm font-semibold",
			children: "Service Hub Preferences"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "space-y-1",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						defaultChecked: true,
						size: "xs"
					}),
					description: "Show sync status in the sidebar navigation",
					title: "Display sync status in sidebar"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						defaultChecked: true,
						size: "xs"
					}),
					description: "Automatically check for service updates",
					title: "Auto-check service health"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						defaultChecked: true,
						size: "xs"
					}),
					description: "Show desktop notifications for service errors",
					title: "Service error notifications"
				})
			]
		})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
			className: "mb-2 text-sm font-semibold",
			children: "Diagnostics"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "space-y-1",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
				action: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					size: "xs",
					variant: "outline",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconCircleCheck, { className: "size-3" }), "Run Check"]
				}),
				description: "Check connectivity and configuration for all services",
				title: "Run health check"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
				action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					size: "xs",
					variant: "textStrong",
					children: "View Logs"
				}),
				description: "Service-specific logs and error details",
				title: "Service logs"
			})]
		})] })]
	});
}
//#endregion
export { ServicesView };

import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { t as IconDeviceFloppy } from "./IconDeviceFloppy-DF2vDv8v.js";
import { S as getMessagingPlatforms, ot as updateMessagingPlatform } from "./aetheros-DF_uJq_t.js";
import { $i as IconPhoto, Aa as IconAlertTriangle, Bi as IconVolume2, Di as notify, Ea as IconChartBar, Hi as IconTrash, La as Button, Ma as IconActivity, N as StatusDot, O as Badge, Oa as IconBolt, Oi as notifyError, P as Switch, Ra as cn, Ya as useStore, Yt as DisclosureCaret, _a as IconExternalLink, aa as IconMessage2, ao as require_jsx_runtime, ia as IconMessageCircle, ni as Input, oo as require_react, qi as IconSettings, yt as PlatformAvatar, zi as IconWaveSine } from "./index-B_yd1pEX.js";
import { t as useRefreshHotkey } from "./use-refresh-hotkey-CjSQqOti.js";
import { t as PageSearchShell } from "./page-search-shell-CWZgYH3F.js";
import { C as updateMediaConfig, E as updateVoiceConfig, S as updateAutomationRule, T as updateSecurity, _ as setPlatformFilter, a as clearActivity, b as togglePinMessage, c as getFilteredMessages, d as removeAutomationRule, f as selectConversation, g as setPlatformConnection, h as setInboxSearch, i as archiveMessage, l as getPlatformMeta, m as setInboxFilter, o as getAllPlatformMeta, p as setCommsTab, r as addAutomationRule, s as getCommsStats, t as $communications, u as markMessageRead, v as setPlatformStatus, w as updateNotificationConfig, x as updateAIConfig, y as toggleImportantMessage } from "./communications-BBoTQPGb.js";
import { n as ListRow } from "./primitives-BsyJey4v.js";
import { t as CREDENTIAL_CONTROL_CLASS } from "./credential-key-ui-CmZbeXXI.js";
//#region src/app/messaging/comms-panels.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
function AIFeaturesPanel() {
	const aiConfig = useStore($communications).aiConfig;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-2xl space-y-6 p-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
			className: "text-sm font-semibold",
			children: "AI Features"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "mt-1 text-xs text-(--ui-text-tertiary)",
			children: "Configure AI-powered features for your communications"
		})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "space-y-1",
			children: [
				{
					key: "autoReply",
					label: "Auto Reply",
					description: "Automatically reply to incoming messages using AI"
				},
				{
					key: "smartSuggestions",
					label: "Smart Suggestions",
					description: "Suggest contextual replies as you type"
				},
				{
					key: "rewriteEnabled",
					label: "Rewrite",
					description: "Reword messages for clarity and tone"
				},
				{
					key: "translateEnabled",
					label: "Translate",
					description: "Translate messages between languages"
				},
				{
					key: "summarizeEnabled",
					label: "Summarize",
					description: "Summarize long conversations and emails"
				},
				{
					key: "sentimentAnalysis",
					label: "Sentiment Analysis",
					description: "Detect emotional tone of messages"
				},
				{
					key: "priorityDetection",
					label: "Priority Detection",
					description: "Flag urgent and high-priority messages"
				},
				{
					key: "spamDetection",
					label: "Spam Detection",
					description: "Identify and filter spam messages"
				},
				{
					key: "meetingDetection",
					label: "Meeting Detection",
					description: "Detect meeting requests and calendar events"
				},
				{
					key: "taskExtraction",
					label: "Task Extraction",
					description: "Extract action items and tasks from messages"
				}
			].map((f) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
				action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
					checked: aiConfig[f.key],
					onCheckedChange: (checked) => updateAIConfig({ [f.key]: checked }),
					size: "xs"
				}),
				description: f.description,
				title: f.label
			}, f.key))
		})]
	});
}
var VOICE_PROVIDERS = [
	{
		id: "whisper",
		label: "Whisper (Local)"
	},
	{
		id: "deepgram",
		label: "Deepgram"
	},
	{
		id: "openai-voice",
		label: "OpenAI Voice"
	},
	{
		id: "local-stt",
		label: "Local STT"
	}
];
function VoicePanel() {
	const voiceConfig = useStore($communications).voiceConfig;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-2xl space-y-6 p-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "text-sm font-semibold",
				children: "Voice Settings"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-xs text-(--ui-text-tertiary)",
				children: "Configure speech recognition and voice features"
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
				action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
					checked: voiceConfig.enabled,
					onCheckedChange: (c) => updateVoiceConfig({ enabled: c }),
					size: "xs"
				}),
				description: "Enable voice features across all platforms",
				title: "Voice Enabled"
			}),
			voiceConfig.enabled && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
				className: "mb-2 text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground",
				children: "Provider"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex flex-wrap gap-2",
				children: VOICE_PROVIDERS.map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					className: cn("rounded-lg border px-3 py-2 text-sm transition-colors", voiceConfig.provider === p.id ? "border-primary bg-primary/10 text-primary" : "border-(--ui-stroke-tertiary) text-(--ui-text-secondary) hover:text-foreground"),
					onClick: () => updateVoiceConfig({ provider: p.id }),
					type: "button",
					children: p.label
				}, p.id))
			})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-1",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: voiceConfig.pushToTalk,
							onCheckedChange: (c) => updateVoiceConfig({ pushToTalk: c }),
							size: "xs"
						}),
						description: "Hold a key to record voice input",
						title: "Push to Talk"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: voiceConfig.voiceCommands,
							onCheckedChange: (c) => updateVoiceConfig({ voiceCommands: c }),
							size: "xs"
						}),
						description: "Control the app with voice commands",
						title: "Voice Commands"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: voiceConfig.voiceReply,
							onCheckedChange: (c) => updateVoiceConfig({ voiceReply: c }),
							size: "xs"
						}),
						description: "Reply to messages using voice",
						title: "Voice Reply"
					})
				]
			})] })
		]
	});
}
function MediaPanel() {
	const mediaConfig = useStore($communications).mediaConfig;
	const mediaItems = useStore($communications).mediaItems;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto flex h-full min-h-0 max-w-4xl flex-col gap-6 p-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "text-sm font-semibold",
				children: "Media Settings"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-xs text-(--ui-text-tertiary)",
				children: "Configure media handling across all platforms"
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-1",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: mediaConfig.ocrEnabled,
							onCheckedChange: (c) => updateMediaConfig({ ocrEnabled: c }),
							size: "xs"
						}),
						description: "Extract text from images using OCR",
						title: "OCR"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: mediaConfig.visionEnabled,
							onCheckedChange: (c) => updateMediaConfig({ visionEnabled: c }),
							size: "xs"
						}),
						description: "Analyze images with computer vision",
						title: "Vision"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: mediaConfig.captionEnabled,
							onCheckedChange: (c) => updateMediaConfig({ captionEnabled: c }),
							size: "xs"
						}),
						description: "Auto-generate captions for images",
						title: "Caption"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: mediaConfig.summarizeMedia,
							onCheckedChange: (c) => updateMediaConfig({ summarizeMedia: c }),
							size: "xs"
						}),
						description: "Generate summaries of media content",
						title: "Summarize Media"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: mediaConfig.autoDownload,
							onCheckedChange: (c) => updateMediaConfig({ autoDownload: c }),
							size: "xs"
						}),
						description: "Automatically download media files",
						title: "Auto Download"
					})
				]
			}),
			mediaItems.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h4", {
				className: "mb-3 text-sm font-semibold",
				children: [
					"Recent Media (",
					mediaItems.length,
					")"
				]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4",
				children: mediaItems.slice(0, 12).map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded-lg border border-(--ui-stroke-tertiary) p-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex items-center justify-center rounded bg-(--ui-row-active-background) py-6 text-xs text-(--ui-text-tertiary)",
							children: item.type.toUpperCase()
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 truncate text-xs",
							children: item.name
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-[0.55rem] text-(--ui-text-tertiary)",
							children: formatSize(item.size)
						})
					]
				}, item.id))
			})] })
		]
	});
}
function NotificationsPanel() {
	const notifConfig = useStore($communications).notificationConfig;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-2xl space-y-6 p-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
			className: "text-sm font-semibold",
			children: "Notification Settings"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "mt-1 text-xs text-(--ui-text-tertiary)",
			children: "Configure how and when you get notified"
		})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "space-y-1",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: notifConfig.desktopNotifications,
						onCheckedChange: (c) => updateNotificationConfig({ desktopNotifications: c }),
						size: "xs"
					}),
					description: "Show desktop notifications for new messages",
					title: "Desktop Notifications"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: notifConfig.soundEnabled,
						onCheckedChange: (c) => updateNotificationConfig({ soundEnabled: c }),
						size: "xs"
					}),
					description: "Play notification sounds",
					title: "Sound"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: notifConfig.silentMode,
						onCheckedChange: (c) => updateNotificationConfig({ silentMode: c }),
						size: "xs"
					}),
					description: "Mute notifications during specified hours",
					title: "Silent Mode"
				}),
				notifConfig.silentMode && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-3 px-4 py-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-xs text-(--ui-text-secondary)",
							children: "From"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							className: cn("h-7 w-20 text-xs", CREDENTIAL_CONTROL_CLASS),
							onChange: (e) => updateNotificationConfig({ silentModeStart: e.target.value }),
							type: "time",
							value: notifConfig.silentModeStart
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-xs text-(--ui-text-secondary)",
							children: "To"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							className: cn("h-7 w-20 text-xs", CREDENTIAL_CONTROL_CLASS),
							onChange: (e) => updateNotificationConfig({ silentModeEnd: e.target.value }),
							type: "time",
							value: notifConfig.silentModeEnd
						})
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: notifConfig.priorityMode,
						onCheckedChange: (c) => updateNotificationConfig({ priorityMode: c }),
						size: "xs"
					}),
					description: "Only show notifications from priority contacts",
					title: "Priority Mode"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: notifConfig.doNotDisturb,
						onCheckedChange: (c) => updateNotificationConfig({ doNotDisturb: c }),
						size: "xs"
					}),
					description: "Mute all notifications",
					title: "Do Not Disturb"
				})
			]
		})]
	});
}
function SettingsSecurityPanel() {
	const security = useStore($communications).security;
	const [showTokens, setShowTokens] = (0, import_react.useState)(false);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-2xl space-y-8 p-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "mb-3 text-sm font-semibold",
				children: "Security"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-1",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: security.encryptedTokens,
							onCheckedChange: (c) => updateSecurity({ encryptedTokens: c }),
							size: "xs"
						}),
						description: "Encrypt all tokens and credentials at rest",
						title: "Encrypted Tokens"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: security.localStorage,
							onCheckedChange: (c) => updateSecurity({ localStorage: c }),
							size: "xs"
						}),
						description: "Store credentials in local secure storage",
						title: "Local Storage"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: security.credentialVault,
							onCheckedChange: (c) => updateSecurity({ credentialVault: c }),
							size: "xs"
						}),
						description: "Use system credential vault for secrets",
						title: "Credential Vault"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: security.permissionManager,
							onCheckedChange: (c) => updateSecurity({ permissionManager: c }),
							size: "xs"
						}),
						description: "Granular permission controls per platform",
						title: "Permission Manager"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: security.auditLog,
							onCheckedChange: (c) => updateSecurity({ auditLog: c }),
							size: "xs"
						}),
						description: "Log all access and configuration changes",
						title: "Audit Log"
					})
				]
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "mb-3 text-sm font-semibold",
				children: "Data Management"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-1",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							size: "xs",
							variant: "textStrong",
							children: "Export"
						}),
						description: "Export all communications configuration",
						title: "Export Configuration"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							size: "xs",
							variant: "textStrong",
							children: "Import"
						}),
						description: "Import communications configuration from file",
						title: "Import Configuration"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							size: "xs",
							variant: "destructive",
							children: "Clear All"
						}),
						description: "Remove all platform connections and data",
						title: "Delete All Connections"
					})
				]
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "mb-3 text-sm font-semibold",
				children: "Connection Management"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-1",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							size: "xs",
							variant: "outline",
							children: "Reconnect"
						}),
						description: "Attempt to reconnect all disconnected platforms",
						title: "Reconnect All"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							size: "xs",
							variant: "outline",
							children: "Backup"
						}),
						description: "Create a backup of all connection configurations",
						title: "Backup"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							size: "xs",
							variant: "ghost",
							children: "View Logs"
						}),
						description: "View connection and communication logs",
						title: "Communication Logs"
					})
				]
			})] })
		]
	});
}
function AutomationCommsPanel() {
	const rules = useStore($communications).automationRules;
	const [showNewForm, setShowNewForm] = (0, import_react.useState)(false);
	const [newRule, setNewRule] = (0, import_react.useState)({
		name: "",
		platform: "all",
		trigger: "message_received",
		condition: "",
		action: "run_agent",
		requireApproval: false,
		enabled: true
	});
	const handleAdd = () => {
		if (!newRule.name.trim()) return;
		addAutomationRule({
			...newRule,
			name: newRule.name.trim()
		});
		setNewRule({
			name: "",
			platform: "all",
			trigger: "message_received",
			condition: "",
			action: "run_agent",
			requireApproval: false,
			enabled: true
		});
		setShowNewForm(false);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-2xl space-y-6 p-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-sm font-semibold",
					children: "Communication Automations"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-1 text-xs text-(--ui-text-tertiary)",
					children: "Automate responses and actions across platforms"
				})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => setShowNewForm(!showNewForm),
					size: "sm",
					variant: "textStrong",
					children: "+ New Rule"
				})]
			}),
			showNewForm && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3 rounded-lg border border-(--ui-stroke-tertiary) p-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						className: "h-7 text-xs",
						onChange: (e) => setNewRule((r) => ({
							...r,
							name: e.target.value
						})),
						placeholder: "Rule name...",
						value: newRule.name
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex flex-wrap gap-2",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
								className: CREDENTIAL_CONTROL_CLASS,
								onChange: (e) => setNewRule((r) => ({
									...r,
									platform: e.target.value
								})),
								value: newRule.platform,
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "all",
										children: "All Platforms"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "telegram",
										children: "Telegram"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "whatsapp",
										children: "WhatsApp"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "discord",
										children: "Discord"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "slack",
										children: "Slack"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "gmail",
										children: "Gmail"
									})
								]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
								className: CREDENTIAL_CONTROL_CLASS,
								onChange: (e) => setNewRule((r) => ({
									...r,
									trigger: e.target.value
								})),
								value: newRule.trigger,
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "message_received",
										children: "Message Received"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "keyword_detected",
										children: "Keyword Detected"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "sender_match",
										children: "Sender Match"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "schedule",
										children: "Schedule"
									})
								]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
								className: CREDENTIAL_CONTROL_CLASS,
								onChange: (e) => setNewRule((r) => ({
									...r,
									action: e.target.value
								})),
								value: newRule.action,
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "run_agent",
										children: "Run Agent"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "search_memory",
										children: "Search Memory"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "search_knowledge",
										children: "Search Knowledge"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "generate_response",
										children: "Generate Response"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "send_reply",
										children: "Send Reply"
									})
								]
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						className: "h-7 text-xs",
						onChange: (e) => setNewRule((r) => ({
							...r,
							condition: e.target.value
						})),
						placeholder: "Condition (e.g. contains 'urgent', from: user123)...",
						value: newRule.condition
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
							className: "flex items-center gap-2 text-xs",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
								checked: newRule.requireApproval,
								onCheckedChange: (c) => setNewRule((r) => ({
									...r,
									requireApproval: c
								})),
								size: "xs"
							}), "Require approval before sending"]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => setShowNewForm(false),
								size: "xs",
								variant: "ghost",
								children: "Cancel"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: handleAdd,
								size: "xs",
								variant: "textStrong",
								children: "Add Rule"
							})]
						})]
					})
				]
			}),
			rules.length === 0 && !showNewForm && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col items-center justify-center py-16 text-center",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-xs text-(--ui-text-tertiary)",
					children: "No automation rules configured"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-1 text-[0.65rem] text-(--ui-text-tertiary)",
					children: "Create rules to automate responses across platforms"
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-1",
				children: rules.map((rule) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: rule.enabled,
							onCheckedChange: (c) => updateAutomationRule(rule.id, { enabled: c }),
							size: "xs"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0 flex-1",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-sm font-medium",
										children: rule.name
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: "px-1 py-0 text-[0.55rem]",
										variant: "muted",
										children: rule.trigger.replace(/_/g, " ")
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										className: "px-1 py-0 text-[0.55rem]",
										variant: "muted",
										children: rule.action.replace(/_/g, " ")
									})
								]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "text-xs text-(--ui-text-tertiary)",
								children: [
									rule.platform === "all" ? "All platforms" : rule.platform,
									" · ",
									rule.condition || "No condition"
								]
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => removeAutomationRule(rule.id),
							size: "xs",
							variant: "ghost",
							children: "×"
						})
					]
				}, rule.id))
			})
		]
	});
}
function formatSize(bytes) {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
	return `${(bytes / 1048576).toFixed(1)} MB`;
}
//#endregion
//#region src/app/messaging/dashboard-view.tsx
var STAT_CARDS = [
	{
		key: "connectedAccounts",
		icon: IconMessageCircle,
		label: "Connected Accounts"
	},
	{
		key: "onlineStatus",
		icon: IconBolt,
		label: "Online"
	},
	{
		key: "messagesToday",
		icon: IconMessage2,
		label: "Messages Today"
	},
	{
		key: "aiReplies",
		icon: IconChartBar,
		label: "AI Replies"
	},
	{
		key: "queuedMessages",
		icon: IconActivity,
		label: "Queued"
	},
	{
		key: "failedMessages",
		icon: IconAlertTriangle,
		label: "Failed"
	}
];
function statTone(key, value) {
	if (key === "failedMessages") return value > 0 ? "bad" : "good";
	if (key === "queuedMessages") return value > 0 ? "warn" : "good";
	if (key === "aiReplies") return "good";
	return value > 0 ? "good" : "muted";
}
function DashboardView() {
	const state = useStore($communications);
	const stats = (0, import_react.useMemo)(() => getCommsStats(), [state]);
	const platforms = (0, import_react.useMemo)(() => getAllPlatformMeta(), []);
	const connections = (0, import_react.useMemo)(() => state.platformConnections, [state.platformConnections]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto flex h-full min-w-0 max-w-5xl flex-col gap-6 overflow-y-auto p-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6",
				children: STAT_CARDS.map((card) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatCard, {
					icon: card.icon,
					label: card.label,
					tone: statTone(card.key, stats[card.key]),
					value: stats[card.key]
				}, card.key))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "mb-3 text-sm font-semibold",
				children: "Platforms"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
				children: platforms.map((meta) => {
					return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PlatformCard, {
						connection: connections.find((c) => c.id === meta.id),
						meta
					}, meta.id);
				})
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "mb-3 text-sm font-semibold",
				children: "Recent Activity"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-1",
				children: [state.activityFeed.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "py-8 text-center text-xs text-(--ui-text-tertiary)",
					children: "No recent activity"
				}), state.activityFeed.slice(0, 20).map((entry) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ActivityRow, { entry }, entry.id))]
			})] })
		]
	});
}
function StatCard({ icon: Icon, label, value, tone }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "rounded-lg border border-(--ui-stroke-tertiary) px-3 py-3",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-4 text-(--ui-text-tertiary)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone })]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-xl font-semibold tracking-tight",
				children: value
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-xs text-(--ui-text-tertiary)",
				children: label
			})
		]
	});
}
function PlatformCard({ connection, meta }) {
	const connected = connection?.connected ?? false;
	const online = connection?.online ?? false;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		className: cn("flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5 text-left transition-colors", connected ? "hover:bg-(--chrome-action-hover)" : "opacity-60"),
		onClick: () => {
			if (!connected) setPlatformStatus(meta.id, true, true);
		},
		type: "button",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: "inline-grid size-8 shrink-0 place-items-center rounded-md text-sm font-medium",
			style: {
				backgroundColor: `color-mix(in srgb, ${meta.color} 16%, transparent)`,
				color: meta.color
			},
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-xs font-bold",
				children: meta.name[0]
			})
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "min-w-0 flex-1",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "text-sm font-medium",
					children: meta.name
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone: online ? "good" : connected ? "warn" : "muted" })]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-xs text-(--ui-text-tertiary)",
				children: connected ? online ? "Online" : "Connecting..." : "Disconnected"
			})]
		})]
	});
}
var ACTIVITY_ICONS = {
	message: IconMessage2,
	connection: IconBolt,
	ai_reply: IconChartBar,
	error: IconAlertTriangle,
	broadcast: IconMessageCircle
};
function ActivityRow({ entry }) {
	const Icon = ACTIVITY_ICONS[entry.type];
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center gap-3 rounded-md px-2 py-1.5 transition-colors hover:bg-(--chrome-action-hover)",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "inline-flex size-6 items-center justify-center rounded-full bg-(--ui-row-active-background)",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-3 text-(--ui-text-secondary)" })
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "min-w-0 flex-1 truncate text-sm",
				children: entry.description
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "shrink-0 text-xs text-(--ui-text-tertiary)",
				children: formatRelativeTime(entry.timestamp)
			})
		]
	});
}
function formatRelativeTime(timestamp) {
	const diff = Date.now() - new Date(timestamp).getTime();
	const mins = Math.floor(diff / 6e4);
	if (mins < 1) return "now";
	if (mins < 60) return `${mins}m ago`;
	const hours = Math.floor(mins / 60);
	if (hours < 24) return `${hours}h ago`;
	return `${Math.floor(hours / 24)}d ago`;
}
//#endregion
//#region src/app/messaging/unified-inbox.tsx
var FILTERS = [
	{
		id: "all",
		label: "All",
		count: (msgs) => msgs.filter((m) => !m.archived).length
	},
	{
		id: "unread",
		label: "Unread",
		count: (msgs) => msgs.filter((m) => !m.read && !m.archived).length
	},
	{
		id: "important",
		label: "Important",
		count: (msgs) => msgs.filter((m) => m.important).length
	},
	{
		id: "pinned",
		label: "Pinned",
		count: (msgs) => msgs.filter((m) => m.pinned).length
	},
	{
		id: "ai-only",
		label: "AI Only",
		count: (msgs) => msgs.filter((m) => m.aiReplied).length
	},
	{
		id: "archived",
		label: "Archived",
		count: (msgs) => msgs.filter((m) => m.archived).length
	}
];
var PLATFORMS = [
	{
		id: "all",
		label: "All"
	},
	{
		id: "telegram",
		label: "Telegram"
	},
	{
		id: "whatsapp",
		label: "WhatsApp"
	},
	{
		id: "discord",
		label: "Discord"
	},
	{
		id: "slack",
		label: "Slack"
	},
	{
		id: "gmail",
		label: "Gmail"
	},
	{
		id: "outlook",
		label: "Outlook"
	},
	{
		id: "teams",
		label: "Teams"
	},
	{
		id: "signal",
		label: "Signal"
	},
	{
		id: "sms",
		label: "SMS"
	},
	{
		id: "webhook",
		label: "Webhook"
	}
];
function UnifiedInbox() {
	const state = useStore($communications);
	const filtered = getFilteredMessages();
	FILTERS.find((f) => f.id === state.inboxFilter);
	const selectedMsg = state.selectedConversation ? state.messages.find((m) => m.conversationId === state.selectedConversation) : null;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full min-h-0",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex w-72 min-w-0 shrink-0 flex-col border-r border-(--ui-stroke-tertiary)",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex shrink-0 flex-col gap-2 border-b border-(--ui-stroke-tertiary) px-3 py-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						className: "h-7 text-xs",
						onChange: (e) => setInboxSearch(e.target.value),
						placeholder: "Search messages...",
						value: state.inboxSearch
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex flex-wrap gap-1",
						children: PLATFORMS.slice(0, 6).map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: cn("rounded px-1.5 py-0.5 text-[0.65rem] font-medium transition-colors", state.selectedPlatformFilter === p.id ? "bg-primary/10 text-primary" : "text-(--ui-text-tertiary) hover:text-foreground"),
							onClick: () => setPlatformFilter(p.id),
							type: "button",
							children: p.label
						}, p.id))
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex shrink-0 gap-0.5 border-b border-(--ui-stroke-tertiary) px-2 py-1.5",
					children: FILTERS.map((f) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: cn("rounded px-1.5 py-0.5 text-[0.65rem] font-medium transition-colors", state.inboxFilter === f.id ? "bg-primary/10 text-primary" : "text-(--ui-text-tertiary) hover:text-foreground"),
						onClick: () => setInboxFilter(f.id),
						type: "button",
						children: [f.label, /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "ml-1 opacity-60",
							children: f.count(state.messages)
						})]
					}, f.id))
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "min-h-0 flex-1 overflow-y-auto",
					children: [filtered.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex flex-col items-center justify-center py-16 text-center",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "No messages"
						})
					}), filtered.map((msg) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(MessageRow, {
						message: msg,
						onSelect: () => {
							selectConversation(msg.conversationId);
							markMessageRead(msg.id);
						},
						selected: msg.conversationId === state.selectedConversation
					}, msg.id))]
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex min-h-0 flex-1 flex-col",
			children: selectedMsg ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ConversationDetail, { message: selectedMsg }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex flex-1 items-center justify-center",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm text-(--ui-text-tertiary)",
					children: "Select a conversation"
				})
			})
		})]
	});
}
function MessageRow({ message, selected, onSelect }) {
	const meta = getPlatformMeta(message.platform);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		className: cn("flex w-full flex-col gap-0.5 border-b border-(--ui-stroke-tertiary) px-3 py-2 text-left transition-colors", selected && "bg-(--ui-row-active-background)", !message.read && !selected && "bg-primary/[0.02]"),
		onClick: onSelect,
		type: "button",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "inline-grid size-5 shrink-0 place-items-center rounded text-[0.55rem] font-bold",
						style: {
							backgroundColor: `color-mix(in srgb, ${meta?.color ?? "#71717A"} 20%, transparent)`,
							color: meta?.color ?? "#71717A"
						},
						children: meta?.name[0] ?? "?"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: cn("min-w-0 flex-1 truncate text-sm", !message.read && "font-semibold"),
						children: message.senderName
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "shrink-0 text-[0.6rem] text-(--ui-text-tertiary)",
						children: formatTime(message.timestamp)
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: cn("truncate pl-7 text-xs", message.read ? "text-(--ui-text-tertiary)" : "text-foreground"),
				children: message.content
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-1.5 pl-7",
				children: [
					message.important && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-[0.55rem] text-amber-500",
						children: "★"
					}),
					message.aiReplied && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						className: "px-1 py-0 text-[0.5rem]",
						variant: "default",
						children: "AI"
					}),
					message.pinned && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-[0.55rem] text-(--ui-text-tertiary)",
						children: "📌"
					}),
					message.direction === "outgoing" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "text-[0.55rem] text-(--ui-text-tertiary)",
						children: [
							message.status === "sent" && "✓",
							message.status === "delivered" && "✓✓",
							message.status === "read" && "✓✓",
							message.status === "failed" && "✗"
						]
					})
				]
			})
		]
	});
}
function ConversationDetail({ message }) {
	const meta = getPlatformMeta(message.platform);
	const allMessages = useStore($communications).messages.filter((m) => m.conversationId === message.conversationId);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex shrink-0 items-center gap-3 border-b border-(--ui-stroke-tertiary) px-4 py-2.5",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "inline-grid size-6 place-items-center rounded text-[0.6rem] font-bold",
					style: {
						backgroundColor: `color-mix(in srgb, ${meta?.color ?? "#71717A"} 20%, transparent)`,
						color: meta?.color ?? "#71717A"
					},
					children: meta?.name[0] ?? "?"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "text-sm font-medium",
					children: message.senderName
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-xs text-(--ui-text-tertiary)",
				children: meta?.name
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "ml-auto flex items-center gap-1",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => toggleImportantMessage(message.id),
						size: "xs",
						variant: "ghost",
						children: message.important ? "★" : "☆"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => togglePinMessage(message.id),
						size: "xs",
						variant: "ghost",
						children: message.pinned ? "📌" : "📍"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => archiveMessage(message.id),
						size: "xs",
						variant: "ghost",
						children: "🗑"
					})
				]
			})
		]
	}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "min-h-0 flex-1 overflow-y-auto px-4 py-3",
		children: allMessages.map((msg) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: cn("mb-3 flex", msg.direction === "outgoing" ? "justify-end" : "justify-start"),
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: cn("max-w-[70%] rounded-lg px-3 py-2", msg.direction === "outgoing" ? "bg-primary/10 text-foreground" : "bg-(--ui-row-active-background) text-foreground"),
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm",
						children: msg.content
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mt-1 flex items-center justify-end gap-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-[0.55rem] text-(--ui-text-tertiary)",
							children: formatTime(msg.timestamp)
						}), msg.direction === "outgoing" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "text-[0.55rem] text-(--ui-text-tertiary)",
							children: [
								msg.status === "sent" && "✓",
								msg.status === "delivered" && "✓✓",
								msg.status === "read" && "✓✓",
								msg.status === "failed" && "✗"
							]
						})]
					}),
					msg.aiReplied && msg.aiResponse && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mt-2 rounded-md border border-primary/20 bg-primary/5 px-2 py-1.5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-[0.6rem] font-medium text-primary",
							children: "AI Reply"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-0.5 text-xs text-(--ui-text-secondary)",
							children: msg.aiResponse
						})]
					}),
					msg.attachments.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mt-2 flex flex-wrap gap-1",
						children: msg.attachments.map((att, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "rounded bg-(--ui-row-active-background) px-1.5 py-0.5 text-[0.55rem] text-(--ui-text-tertiary)",
							children: [
								att.type,
								" · ",
								att.name
							]
						}, i))
					})
				]
			})
		}, msg.id))
	})] });
}
function formatTime(timestamp) {
	const d = new Date(timestamp);
	const now = /* @__PURE__ */ new Date();
	if (d.toDateString() === now.toDateString()) return d.toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit"
	});
	return d.toLocaleDateString([], {
		month: "short",
		day: "numeric"
	});
}
//#endregion
//#region src/app/messaging/index.tsx
var TAB_ICONS = {
	dashboard: IconChartBar,
	platforms: IconMessageCircle,
	inbox: IconMessage2,
	ai: IconBolt,
	automation: IconChartBar,
	voice: IconWaveSine,
	media: IconPhoto,
	notifications: IconVolume2,
	settings: IconSettings
};
var PILL_TONE = {
	good: "bg-primary/10 text-primary",
	muted: "bg-muted text-muted-foreground",
	warn: "bg-amber-500/10 text-amber-600 dark:text-amber-300",
	bad: "bg-destructive/10 text-destructive"
};
var stateLabel = (state) => state ? state.replace(/_/g, " ") : "unknown";
function stateTone({ enabled, state }) {
	if (!enabled) return "muted";
	if (state === "connected") return "good";
	if (state === "fatal" || state === "startup_failed") return "bad";
	return "warn";
}
var trimEdits = (edits) => Object.fromEntries(Object.entries(edits).map(([k, v]) => [k, v.trim()]).filter(([, v]) => v));
var FIELD_COPY = {
	TELEGRAM_PROXY: { advanced: true },
	DISCORD_REPLY_TO_MODE: { advanced: true },
	DISCORD_ALLOW_ALL_USERS: { advanced: true },
	DISCORD_HOME_CHANNEL: { advanced: true },
	DISCORD_HOME_CHANNEL_NAME: { advanced: true },
	BLUEBUBBLES_ALLOW_ALL_USERS: { advanced: true },
	MATTERMOST_ALLOW_ALL_USERS: { advanced: true },
	MATTERMOST_HOME_CHANNEL: { advanced: true },
	QQ_ALLOW_ALL_USERS: { advanced: true },
	QQBOT_HOME_CHANNEL: { advanced: true },
	QQBOT_HOME_CHANNEL_NAME: { advanced: true },
	WHATSAPP_ENABLED: { advanced: true },
	WHATSAPP_MODE: { advanced: true }
};
function fieldCopy(field) {
	const copy = FIELD_COPY[field.key] || {};
	return {
		label: field.prompt || field.key,
		help: field.description,
		placeholder: field.prompt || "",
		advanced: Boolean(copy.advanced || field.advanced)
	};
}
var TABS = [
	{
		id: "dashboard",
		label: "Dashboard"
	},
	{
		id: "platforms",
		label: "Platforms"
	},
	{
		id: "inbox",
		label: "Inbox"
	},
	{
		id: "ai",
		label: "AI Features"
	},
	{
		id: "automation",
		label: "Automation"
	},
	{
		id: "voice",
		label: "Voice"
	},
	{
		id: "media",
		label: "Media"
	},
	{
		id: "notifications",
		label: "Notifications"
	},
	{
		id: "settings",
		label: "Settings"
	}
];
function MessagingView({ setStatusbarItemGroup: _setStatusbarItemGroup, ...props }) {
	const [platforms, setPlatforms] = (0, import_react.useState)(null);
	const [edits, setEdits] = (0, import_react.useState)({});
	const [query, setQuery] = (0, import_react.useState)("");
	const [refreshing, setRefreshing] = (0, import_react.useState)(false);
	const [saving, setSaving] = (0, import_react.useState)(null);
	const [showAdvanced, setShowAdvanced] = (0, import_react.useState)(false);
	const hubTab = useStore($communications).activeTab;
	const connectState = useStore($communications);
	const platformIds = (0, import_react.useMemo)(() => platforms?.map((p) => p.id) ?? [], [platforms]);
	const [selectedId, setSelectedId] = (0, import_react.useState)(platformIds[0] ?? "");
	const refreshPlatforms = (0, import_react.useCallback)(async (silent = false) => {
		if (!silent) setRefreshing(true);
		try {
			const result = await getMessagingPlatforms();
			setPlatforms(result.platforms);
			const meta = getAllPlatformMeta();
			for (const p of result.platforms) {
				const m = meta.find((m) => m.id === p.id);
				if (m) setPlatformConnection(m.id, {
					connected: p.state === "connected",
					online: p.state === "connected",
					name: m.name,
					icon: m.icon,
					color: m.color
				});
			}
		} catch (err) {
			if (!silent) notifyError(err, "Failed to load platforms");
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
	const visiblePlatforms = (0, import_react.useMemo)(() => {
		if (!platforms) return [];
		const q = query.trim().toLowerCase();
		if (!q) return platforms;
		return platforms.filter((p) => [
			p.id,
			p.name,
			p.description,
			p.state
		].filter(Boolean).some((v) => String(v).toLowerCase().includes(q)));
	}, [platforms, query]);
	const selected = (0, import_react.useMemo)(() => {
		if (!platforms) return null;
		return platforms.find((p) => p.id === selectedId) || platforms[0] || null;
	}, [platforms, selectedId]);
	(0, import_react.useEffect)(() => {
		if (platformIds.length > 0 && !platformIds.includes(selectedId)) setSelectedId(platformIds[0]);
	}, [platformIds, selectedId]);
	async function handleToggle(platform, enabled) {
		setSaving(`enabled:${platform.id}`);
		try {
			await updateMessagingPlatform(platform.id, { enabled });
			setPlatforms((current) => current?.map((row) => row.id === platform.id ? {
				...row,
				enabled,
				state: enabled ? row.configured ? "pending_restart" : "not_configured" : "disabled"
			} : row) ?? current);
			setPlatformStatus(platform.id, enabled, enabled);
			notify({
				kind: "success",
				title: enabled ? `${platform.name} enabled` : `${platform.name} disabled`,
				message: "Restart gateway to apply"
			});
		} catch (err) {
			notifyError(err, `Failed to update ${platform.name}`);
		} finally {
			setSaving(null);
		}
	}
	async function handleSave(platform) {
		const env = trimEdits(edits[platform.id] || {});
		if (Object.keys(env).length === 0) return;
		setSaving(`env:${platform.id}`);
		try {
			await updateMessagingPlatform(platform.id, { env });
			setEdits((current) => ({
				...current,
				[platform.id]: {}
			}));
			await refreshPlatforms();
			notify({
				kind: "success",
				title: `Configuration saved for ${platform.name}`,
				message: "Restart gateway to reconnect"
			});
		} catch (err) {
			notifyError(err, `Failed to save ${platform.name}`);
		} finally {
			setSaving(null);
		}
	}
	async function handleClear(platform, key) {
		setSaving(`clear:${key}`);
		try {
			await updateMessagingPlatform(platform.id, { clear_env: [key] });
			setEdits((current) => ({
				...current,
				[platform.id]: {
					...current[platform.id] || {},
					[key]: ""
				}
			}));
			await refreshPlatforms();
			notify({
				kind: "success",
				title: `Cleared ${key}`,
				message: "Configuration updated"
			});
		} catch (err) {
			notifyError(err, `Failed to clear ${key}`);
		} finally {
			setSaving(null);
		}
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageSearchShell, {
		...props,
		onSearchChange: setQuery,
		searchHidden: (platforms?.length ?? 0) === 0 || hubTab !== "platforms",
		searchPlaceholder: "Search platforms...",
		searchValue: query,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex h-full min-w-0 flex-col overflow-hidden bg-(--ui-chat-surface-background)",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
						className: "text-lg font-semibold tracking-tight",
						children: "Communications Hub"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "mt-0.5 text-xs text-(--ui-text-tertiary)",
						children: [
							connectState.platformConnections.filter((p) => p.connected).length,
							" connected · ",
							getCommsStats().messagesToday,
							" messages today"
						]
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [hubTab === "dashboard" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => clearActivity(),
							size: "xs",
							variant: "ghost",
							children: "Clear Activity"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							disabled: refreshing,
							onClick: () => void refreshPlatforms(),
							size: "sm",
							variant: "ghost",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconActivity, { className: cn("size-3.5", refreshing && "animate-spin") })
						})]
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex shrink-0 items-center gap-0.5 overflow-x-auto border-b border-(--ui-stroke-tertiary) px-3",
					children: TABS.map((tab) => {
						const Icon = TAB_ICONS[tab.id] || IconMessageCircle;
						return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: cn("flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors", hubTab === tab.id ? "border-primary text-foreground" : "border-transparent text-(--ui-text-secondary) hover:text-foreground"),
							onClick: () => setCommsTab(tab.id),
							type: "button",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-3.5" }), tab.label]
						}, tab.id);
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "min-h-0 flex-1",
					children: [
						hubTab === "dashboard" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DashboardView, {}),
						hubTab === "platforms" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "grid h-full min-h-0 grid-cols-1 lg:grid-cols-[14rem_minmax(0,1fr)]",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("aside", {
								className: "min-h-0 overflow-y-auto border-r border-(--ui-stroke-tertiary) p-2",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
									className: "space-y-1",
									children: visiblePlatforms.map((platform) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
										className: cn("flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left transition-colors", selected?.id === platform.id ? "bg-(--ui-row-active-background) text-foreground" : "text-(--ui-text-secondary) hover:bg-(--ui-row-hover-background) hover:text-foreground"),
										onClick: () => setSelectedId(platform.id),
										type: "button",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PlatformAvatar, {
											platformId: platform.id,
											platformName: platform.name
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
											className: "flex min-w-0 flex-1 items-center justify-between gap-2",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "truncate text-sm font-normal",
												children: platform.name
											}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone: stateTone(platform) })]
										})]
									}) }, platform.id))
								})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("main", {
								className: "min-h-0 overflow-hidden",
								children: selected && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PlatformDetail, {
									edits: edits[selected.id] || {},
									onClear: (key) => void handleClear(selected, key),
									onEdit: (key, value) => setEdits((current) => ({
										...current,
										[selected.id]: {
											...current[selected.id] || {},
											[key]: value
										}
									})),
									onSave: () => void handleSave(selected),
									onShowAdvanced: setShowAdvanced,
									onToggle: (enabled) => void handleToggle(selected, enabled),
									platform: selected,
									saving,
									showAdvanced
								})
							})]
						}),
						hubTab === "inbox" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(UnifiedInbox, {}),
						hubTab === "ai" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AIFeaturesPanel, {}),
						hubTab === "automation" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AutomationCommsPanel, {}),
						hubTab === "voice" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(VoicePanel, {}),
						hubTab === "media" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(MediaPanel, {}),
						hubTab === "notifications" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(NotificationsPanel, {}),
						hubTab === "settings" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SettingsSecurityPanel, {})
					]
				})
			]
		})
	});
}
function PlatformDetail({ edits, onClear, onEdit, onSave, onToggle, platform, saving, showAdvanced, onShowAdvanced }) {
	const hasEdits = Object.keys(trimEdits(edits)).length > 0;
	const requiredFields = platform.env_vars.filter((f) => f.required);
	const optionalFields = platform.env_vars.filter((f) => !f.required && !fieldCopy(f).advanced);
	const advancedFields = platform.env_vars.filter((f) => !f.required && fieldCopy(f).advanced);
	const hiddenCount = advancedFields.length;
	const isSavingEnv = saving === `env:${platform.id}`;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full min-h-0 flex-col",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "min-h-0 flex-1 overflow-y-auto",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mx-auto max-w-2xl space-y-5 px-5 py-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
						className: "flex items-start gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PlatformAvatar, {
							platformId: platform.id,
							platformName: platform.name
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0 flex-1",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
									className: "text-sm font-semibold tracking-tight",
									children: platform.name
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "mt-1 text-xs leading-relaxed text-(--ui-text-tertiary)",
									children: platform.description
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "mt-3 flex flex-wrap items-center gap-2",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Pill, {
											tone: stateTone(platform),
											children: stateLabel(platform.state)
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SetupPill, {
											active: platform.configured,
											children: platform.configured ? "Credentials Set" : "Needs Setup"
										}),
										!platform.gateway_running && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SetupPill, {
											active: false,
											children: "Gateway Stopped"
										})
									]
								})
							]
						})]
					}),
					platform.error_message && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-start gap-2 rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconAlertTriangle, { className: "mt-0.5 size-3.5 shrink-0" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: platform.error_message })]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SectionTitle, { children: "Credentials" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mt-3",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							asChild: true,
							size: "sm",
							variant: "textStrong",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("a", {
								href: platform.docs_url,
								rel: "noreferrer",
								target: "_blank",
								children: ["Setup Guide", /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconExternalLink, { className: "size-3.5" })]
							})
						})
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SectionTitle, { children: "Required" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mt-3 grid gap-1",
						children: requiredFields.length > 0 ? requiredFields.map((field) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(MessagingField, {
							edits,
							field,
							onClear,
							onEdit,
							saving
						}, field.key)) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "No credentials needed"
						})
					})] }),
					optionalFields.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SectionTitle, { children: "Optional" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mt-3 grid gap-1",
						children: optionalFields.map((field) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(MessagingField, {
							edits,
							field,
							onClear,
							onEdit,
							saving
						}, field.key))
					})] }),
					hiddenCount > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: "flex w-full items-center justify-between gap-2 py-0.5 text-left text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground transition-colors hover:text-foreground",
						onClick: () => onShowAdvanced(!showAdvanced),
						type: "button",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
							"Advanced (",
							hiddenCount,
							")"
						] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DisclosureCaret, {
							open: showAdvanced,
							size: "0.875rem"
						})]
					}), showAdvanced && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mt-3 grid gap-1",
						children: advancedFields.map((field) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(MessagingField, {
							edits,
							field,
							onClear,
							onEdit,
							saving
						}, field.key))
					})] })
				]
			})
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("footer", {
			className: "bg-(--ui-chat-surface-background) px-5 py-2.5",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mx-auto flex max-w-2xl flex-wrap items-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
					"aria-label": platform.enabled ? `Disable ${platform.name}` : `Enable ${platform.name}`,
					checked: platform.enabled,
					disabled: saving === `enabled:${platform.id}`,
					onCheckedChange: onToggle,
					size: "xs"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "ml-auto flex items-center gap-2",
					children: [hasEdits && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-xs text-muted-foreground",
						children: "Unsaved changes"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						disabled: !hasEdits || isSavingEnv,
						onClick: onSave,
						size: "sm",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconDeviceFloppy, {}), isSavingEnv ? "Saving..." : "Save"]
					})]
				})]
			})
		})]
	});
}
function MessagingField({ edits, field, onClear, onEdit, saving }) {
	const copy = fieldCopy(field);
	const fieldId = `messaging-field-${field.key}`;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
		action: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center gap-2",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
					className: CREDENTIAL_CONTROL_CLASS,
					id: fieldId,
					onChange: (event) => onEdit(field.key, event.target.value),
					placeholder: field.is_set ? field.redacted_value || "Replace value" : copy.placeholder,
					type: field.is_password ? "password" : "text",
					value: edits[field.key] || ""
				}),
				field.url && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					asChild: true,
					className: "size-8 shrink-0",
					variant: "ghost",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("a", {
						href: field.url,
						rel: "noreferrer",
						target: "_blank",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconExternalLink, { className: "size-3.5" })
					})
				}),
				field.is_set && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					className: "size-8 shrink-0",
					disabled: saving === `clear:${field.key}`,
					onClick: () => onClear(field.key),
					variant: "ghost",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTrash, { className: "size-3.5" })
				})
			]
		}),
		description: copy.help,
		title: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
			className: "flex flex-wrap items-center gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
				htmlFor: fieldId,
				children: copy.label
			}), field.is_set && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-[0.66rem] font-medium text-primary",
				children: "Saved"
			})]
		})
	});
}
function SectionTitle({ children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
		className: "text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground",
		children
	});
}
function Pill({ children, tone }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
		className: cn("inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-[0.66rem] font-medium", PILL_TONE[tone]),
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusDot, { tone }), children]
	});
}
function SetupPill({ active, children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		className: cn("inline-flex items-center rounded-full px-2 py-0.5 text-[0.66rem] font-medium", PILL_TONE[active ? "good" : "muted"]),
		children
	});
}
//#endregion
export { MessagingView };

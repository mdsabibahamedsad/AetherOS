import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Qa as atom, Xa as init_nanostores, Ya as useStore, ao as require_jsx_runtime, oo as require_react } from "./index-B_yd1pEX.js";
import { S as updateAutomationRule, T as updateSecurity, _ as setPlatformFilter, a as clearActivity, c as getFilteredMessages, d as removeAutomationRule, f as selectConversation, h as setInboxSearch, i as archiveMessage, m as setInboxFilter, n as addActivity, r as addAutomationRule, t as $communications, u as markMessageRead, v as setPlatformStatus, w as updateNotificationConfig, x as updateAIConfig, y as toggleImportantMessage } from "./communications-BBoTQPGb.js";
//#region src/app/communications-hub/activity-log.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
function ActivityLog() {
	const activities = useStore($communications).activityFeed;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-sm font-semibold",
				children: "Activity Log"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
				className: "flex items-center gap-1 rounded-md px-3 py-1.5 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)",
				onClick: clearActivity,
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-clear-all" }), "Clear"]
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "min-h-0 flex-1 overflow-y-auto",
			children: activities.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex h-full items-center justify-center",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "text-center",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-history text-3xl text-(--ui-text-tertiary)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-2 text-sm text-(--ui-text-tertiary)",
						children: "No activity yet"
					})]
				})
			}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "relative ml-6 border-l border-(--ui-stroke-tertiary)",
				children: activities.map((a, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "relative ml-4 pb-4 pl-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: `absolute -left-6 mt-1.5 size-3 rounded-full border-2 border-(--ui-stroke-tertiary) ${a.type === "message" ? "bg-blue-500" : a.type === "connection" ? "bg-green-500" : a.type === "ai_reply" ? "bg-purple-500" : a.type === "error" ? "bg-red-500" : "bg-(--ui-text-tertiary)"}` }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-start gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0 flex-1",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-xs",
								children: a.description
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "text-[10px] text-(--ui-text-tertiary)",
								children: [a.platformName, /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "ml-2",
									children: new Date(a.timestamp).toLocaleString()
								})]
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: `rounded-md px-1.5 py-0.5 text-[10px] ${a.type === "message" ? "bg-blue-500/10 text-blue-500" : a.type === "connection" ? "bg-green-500/10 text-green-500" : a.type === "error" ? "bg-red-500/10 text-red-500" : "bg-purple-500/10 text-purple-500"}`,
							children: a.type
						})]
					})]
				}, a.id))
			})
		})]
	});
}
//#endregion
//#region src/store/communications-ai.ts
init_nanostores();
var $commsAI = /* @__PURE__ */ atom({
	mode: "suggest",
	draftResult: null,
	currentSummary: null,
	suggestions: [],
	selectedStyle: "professional",
	customInstructions: "",
	targetLanguage: "",
	loading: false,
	history: []
});
var patch$3 = (update) => $commsAI.set({
	...$commsAI.get(),
	...update
});
function setAssistantMode(mode) {
	patch$3({ mode });
}
function setDraftStyle(style) {
	patch$3({ selectedStyle: style });
}
function setCustomInstructions(instructions) {
	patch$3({ customInstructions: instructions });
}
function setTargetLanguage(lang) {
	patch$3({ targetLanguage: lang });
}
function generateDraft(messages, style = "professional", customInstructions = "", language = "") {
	const lastMsg = messages[messages.length - 1];
	const draft = {
		content: generateDraftText(lastMsg?.content || "", lastMsg?.senderName || "", style, customInstructions),
		style,
		toneNotes: getToneNotes(style, customInstructions),
		translationFrom: "",
		translationTo: language,
		requiresApproval: true
	};
	patch$3({
		draftResult: draft,
		mode: "draft",
		selectedStyle: style,
		customInstructions,
		targetLanguage: language
	});
	addHistory("assistant", `Drafted a ${style} reply: "${draft.content.substring(0, 60)}..."`);
}
function generateSummary(messages) {
	if (!messages.length) {
		patch$3({ currentSummary: {
			summary: "No messages to summarize.",
			keyPoints: [],
			actionItems: [],
			sentiment: "neutral",
			participants: [],
			messageCount: 0
		} });
		return;
	}
	const participants = [...new Set(messages.map((m) => m.senderName))];
	const contentText = messages.map((m) => m.content).join(" ");
	const keyPoints = extractKeyPoints(contentText);
	const actionItems = extractActionItems(contentText);
	const sentiment = detectSentiment(contentText);
	patch$3({
		currentSummary: {
			summary: `Conversation with ${participants.join(", ")} (${messages.length} messages).${contentText.includes("?") ? " Contains questions needing responses." : ""}${actionItems.length ? ` ${actionItems.length} action items identified.` : ""}`,
			keyPoints,
			actionItems,
			sentiment,
			participants,
			messageCount: messages.length
		},
		mode: "summarize"
	});
	addHistory("assistant", `Generated summary for ${messages.length} messages (${sentiment} sentiment)`);
}
function detectPendingRequests(messages) {
	const patterns = [
		/(?:can|could|would|will)\s+(?:you|someone)\s+(.+?)\?/gi,
		/(?:please|pls)\s+(.+?)(?:\.|$)/gi,
		/(?:need|require|request)\s+(.+?)(?:\.|$)/gi
	];
	const requests = [];
	for (const msg of messages) for (const pattern of patterns) {
		const matches = msg.content.matchAll(pattern);
		for (const m of matches) requests.push(`${m[1].trim()} — from ${msg.senderName}`);
	}
	return requests;
}
function classifyPriority(messages) {
	const result = {
		urgent: [],
		important: [],
		normal: [],
		spam: []
	};
	for (const msg of messages) {
		const c = msg.content.toLowerCase();
		if (/urgent|asap|emergency|critical/i.test(c)) result.urgent.push(msg);
		else if (/important|deadline|required|must/i.test(c)) result.important.push(msg);
		else if (/spam|unsubscribe|offer|discount|free.*click/i.test(c)) result.spam.push(msg);
		else result.normal.push(msg);
	}
	return result;
}
function extractTasks(messages) {
	const tasks = [];
	const patterns = [
		/(?:I\s+(?:will|need to|have to|must)\s+)(.+?)(?:\.|,|$)/gi,
		/(?:please|pls)\s+(.+?)(?:\.|,|$)/gi,
		/(?:action\s*item[s]?[:\s]+)(.+?)(?:\.|$)/gi,
		/(?:todo|to-do|to do)[:\s]+(.+?)(?:\.|,|$)/gi
	];
	for (const msg of messages) for (const pattern of patterns) {
		const matches = msg.content.matchAll(pattern);
		for (const m of matches) if (m[1].trim().length > 5) tasks.push({
			task: m[1].trim(),
			from: msg.senderName,
			messageId: msg.id
		});
	}
	return tasks;
}
function addHistory(role, content) {
	const history = $commsAI.get().history;
	patch$3({ history: [...history, {
		role,
		content,
		timestamp: (/* @__PURE__ */ new Date()).toISOString()
	}].slice(-50) });
}
function clearAssistantHistory() {
	patch$3({
		draftResult: null,
		currentSummary: null,
		suggestions: [],
		history: []
	});
}
function generateDraftText(content, sender, style, custom) {
	const cl = content.toLowerCase();
	const isQuestion = content.includes("?");
	const isMeeting = /meet|schedule|call|appointment/i.test(cl);
	const isUrgent = /urgent|asap|important|deadline/i.test(cl);
	const isThankYou = /thanks|thank you|appreciate/i.test(cl);
	if (style === "short") {
		if (isQuestion) return `Thanks for your message, ${sender}. I'll look into this and get back to you shortly.`;
		return `Got it, ${sender}. I'll take care of this.`;
	}
	if (style === "professional") {
		if (isMeeting) return `Dear ${sender},\n\nThank you for reaching out. I would be happy to schedule a meeting. Please let me know what time works best for you.\n\nBest regards`;
		if (isUrgent) return `Dear ${sender},\n\nThank you for bringing this to my attention. I understand the urgency and will prioritize this matter.\n\nBest regards`;
		if (isThankYou) return `Dear ${sender},\n\nYou're welcome! Happy to help. Let me know if there's anything else I can assist with.\n\nBest regards`;
		return `Dear ${sender},\n\nThank you for your message. I will review the details and get back to you promptly.\n\nBest regards`;
	}
	if (style === "friendly") {
		if (isThankYou) return `Hey ${sender}!\n\nYou're very welcome! Always happy to help out. Talk soon!`;
		if (isMeeting) return `Hey ${sender}!\n\nSounds great! I'd love to meet up. Just let me know when works for you!`;
		return `Hey ${sender}!\n\nThanks for reaching out! I'll get back to you as soon as I can.`;
	}
	if (style === "casual") {
		if (isQuestion) return `Hey ${sender},\n\nGood question! Let me check on that and get back to you.`;
		return `Hey ${sender},\n\nThanks for the message. I'll handle it!`;
	}
	if (style === "detailed") {
		const parts = [`Hello ${sender},`];
		if (isQuestion) parts.push(`\n\nThank you for your detailed question. I have reviewed the information you provided and would like to address each point. I will conduct a thorough review and provide a comprehensive response.`);
		else parts.push(`\n\nThank you for reaching out. I have carefully reviewed your message and will take the appropriate actions.`);
		parts.push(`\n\nPlease don't hesitate to reach out if you have any additional questions.`);
		parts.push(`\n\nBest regards`);
		return parts.join("");
	}
	return `Hi ${sender},\n\nThank you for your message. I will get back to you shortly.`;
}
function getToneNotes(style, custom) {
	let base = {
		professional: "Use formal language, proper salutations, and professional closing.",
		casual: "Use conversational language, contractions, and a relaxed tone.",
		friendly: "Use warm, personal language with positive expressions.",
		short: "Keep response under 2-3 sentences. Direct and concise.",
		detailed: "Provide comprehensive response with examples and context.",
		custom: "Follow custom instructions."
	}[style] || "Natural conversational tone.";
	if (custom) base += ` Additional instructions: ${custom}`;
	return base;
}
function extractKeyPoints(text) {
	const points = [];
	const sentences = text.split(/[.!?]+/);
	for (const s of sentences) {
		const st = s.trim();
		if (st.length > 20 && /important|key|critical|note|remember|significant|must|required/i.test(st)) points.push(st);
	}
	return points.slice(0, 5);
}
function extractActionItems(text) {
	const items = [];
	for (const pattern of [
		/(?:I\s+(?:will|need to|have to|must)\s+)(.+?)(?:\.|,|$)/gi,
		/(?:please|pls)\s+(.+?)(?:\.|,|$)/gi,
		/(?:action\s*item[s]?[:\s]+)(.+?)(?:\.|$)/gi,
		/(?:todo|to-do|to do)[:\s]+(.+?)(?:\.|$)/gi,
		/(?:don't forget|remember)\s+to\s+(.+?)(?:\.|,|$)/gi
	]) {
		const matches = text.matchAll(pattern);
		for (const m of matches) if (m[1].trim().length > 5) items.push(m[1].trim());
	}
	return items.slice(0, 8);
}
function detectSentiment(text) {
	const positive = [
		"great",
		"awesome",
		"happy",
		"thanks",
		"love",
		"excellent",
		"perfect",
		"wonderful",
		"amazing",
		"good"
	];
	const negative = [
		"bad",
		"terrible",
		"awful",
		"hate",
		"angry",
		"frustrated",
		"disappointed",
		"poor",
		"worst",
		"unacceptable"
	];
	const tl = text.toLowerCase();
	const pos = positive.filter((w) => tl.includes(w)).length;
	const neg = negative.filter((w) => tl.includes(w)).length;
	if (pos > neg) return "positive";
	if (neg > pos) return "negative";
	return "neutral";
}
//#endregion
//#region src/app/communications-hub/ai-assistant.tsx
var STYLES = [
	{
		id: "professional",
		label: "Professional"
	},
	{
		id: "casual",
		label: "Casual"
	},
	{
		id: "friendly",
		label: "Friendly"
	},
	{
		id: "short",
		label: "Short"
	},
	{
		id: "detailed",
		label: "Detailed"
	}
];
function CommsAIAssistant() {
	const commsAi = useStore($commsAI);
	useStore($communications);
	const messages = getFilteredMessages();
	const [customPrompt, setCustomPrompt] = (0, import_react.useState)("");
	const priority = classifyPriority(messages);
	const tasks = extractTasks(messages);
	const pendingRequests = detectPendingRequests(messages);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-sm font-semibold",
					children: "AI Message Assistant"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: "flex items-center gap-1 rounded-md px-2 py-1 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)",
					onClick: clearAssistantHistory,
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-clear-all" }), "Clear History"]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-h-0 flex-1 space-y-3 overflow-y-auto p-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid grid-cols-2 gap-2",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: "rounded-lg border border-(--ui-stroke-tertiary) p-3 text-left text-xs hover:bg-(--ui-row-hover-background)",
								onClick: () => {
									generateDraft(messages);
									setAssistantMode("draft");
								},
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-comment text-sm" }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "mt-1 font-medium",
										children: "Draft Reply"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-(--ui-text-tertiary)",
										children: "Generate a professional reply"
									})
								]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: "rounded-lg border border-(--ui-stroke-tertiary) p-3 text-left text-xs hover:bg-(--ui-row-hover-background)",
								onClick: () => {
									generateSummary(messages);
									setAssistantMode("summarize");
								},
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-summary text-sm" }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "mt-1 font-medium",
										children: "Summarize"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-(--ui-text-tertiary)",
										children: "Summarize conversations"
									})
								]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: "rounded-lg border border-(--ui-stroke-tertiary) p-3 text-left text-xs hover:bg-(--ui-row-hover-background)",
								onClick: () => setAssistantMode("analyze"),
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-warning text-sm" }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "mt-1 font-medium",
										children: "Analyze Priority"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-(--ui-text-tertiary)",
										children: "Find urgent & important messages"
									})
								]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: "rounded-lg border border-(--ui-stroke-tertiary) p-3 text-left text-xs hover:bg-(--ui-row-hover-background)",
								onClick: () => setAssistantMode("compose"),
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-edit text-sm" }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "mt-1 font-medium",
										children: "Compose Message"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-(--ui-text-tertiary)",
										children: "Write a new message from scratch"
									})
								]
							})
						]
					}),
					commsAi.mode === "analyze" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "text-xs font-medium",
								children: "Message Priority Analysis"
							}),
							priority.urgent.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "flex items-center gap-1 text-xs font-medium text-red-500",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-warning" }),
									" Urgent (",
									priority.urgent.length,
									")"
								]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
								className: "mt-1 space-y-0.5 pl-4",
								children: priority.urgent.map((m) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
									className: "text-xs text-(--ui-text-tertiary)",
									children: [
										m.senderName,
										": ",
										m.content.substring(0, 80),
										"..."
									]
								}, m.id))
							})] }),
							priority.important.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "flex items-center gap-1 text-xs font-medium text-amber-500",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-star-full" }),
									" Important (",
									priority.important.length,
									")"
								]
							}) }),
							priority.spam.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "text-xs text-(--ui-text-tertiary)",
								children: [priority.spam.length, " potential spam messages detected"]
							}),
							pendingRequests.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "text-xs font-medium",
									children: "Pending Requests"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
									className: "mt-1 space-y-0.5 pl-4",
									children: pendingRequests.map((r, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
										className: "text-xs text-(--ui-text-tertiary)",
										children: ["• ", r]
									}, i))
								})]
							})
						]
					}),
					commsAi.mode === "draft" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "flex flex-wrap gap-1",
								children: STYLES.map((s) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: `rounded-md px-2 py-1 text-[10px] ${commsAi.selectedStyle === s.id ? "bg-primary text-white" : "bg-(--ui-bg-quaternary) text-(--ui-text-tertiary)"}`,
									onClick: () => setDraftStyle(s.id),
									children: s.label
								}, s.id))
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								className: "h-7 w-full rounded border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
								onChange: (e) => setCustomInstructions(e.target.value),
								placeholder: "Custom instructions (optional)",
								type: "text",
								value: commsAi.customInstructions
							}),
							commsAi.draftResult && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "rounded-md bg-(--ui-bg-quaternary) p-3",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center justify-between",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-[10px] text-(--ui-text-tertiary)",
										children: commsAi.draftResult.toneNotes
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "rounded-md bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-500",
										children: "Requires approval"
									})]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "mt-2 whitespace-pre-wrap text-xs",
									children: commsAi.draftResult.content
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: "h-7 w-full rounded-md bg-primary text-xs text-white",
								onClick: () => generateDraft(messages, commsAi.selectedStyle, commsAi.customInstructions, commsAi.targetLanguage),
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-sparkle" }), " Generate Draft"]
							})
						]
					}),
					commsAi.mode === "summarize" && commsAi.currentSummary && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
								className: "flex items-center gap-1 text-xs font-medium",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-summary" }), " Conversation Summary"]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-xs text-(--ui-text-tertiary)",
								children: commsAi.currentSummary.summary
							}),
							commsAi.currentSummary.keyPoints.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-[10px] font-medium text-(--ui-text-tertiary)",
								children: "Key Points"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
								className: "mt-1 space-y-0.5 pl-3",
								children: commsAi.currentSummary.keyPoints.map((p, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
									className: "text-xs text-(--ui-text-tertiary)",
									children: ["• ", p]
								}, i))
							})] }),
							commsAi.currentSummary.actionItems.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-[10px] font-medium text-(--ui-text-tertiary)",
								children: "Action Items"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
								className: "mt-1 space-y-0.5 pl-3",
								children: commsAi.currentSummary.actionItems.map((a, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
									className: "flex items-center gap-1 text-xs",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-check text-green-500" }),
										" ",
										a
									]
								}, i))
							})] }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "text-[10px] text-(--ui-text-tertiary)",
								children: [
									"Sentiment: ",
									commsAi.currentSummary.sentiment,
									" | ",
									commsAi.currentSummary.messageCount,
									" messages | ",
									commsAi.currentSummary.participants.join(", ")
								]
							})
						]
					}),
					commsAi.history.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "text-xs font-medium",
							children: "Assistant History"
						}), commsAi.history.map((h, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: `rounded-lg p-2 text-xs ${h.role === "assistant" ? "bg-(--ui-bg-quaternary)" : "bg-primary/10"}`,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-1 text-[10px] text-(--ui-text-tertiary)",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `codicon codicon-${h.role === "assistant" ? "robot" : "person"}` }),
									h.role === "assistant" ? "AI Assistant" : "You",
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "ml-auto",
										children: new Date(h.timestamp).toLocaleTimeString()
									})
								]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-0.5",
								children: h.content
							})]
						}, i))]
					}),
					tasks.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-lg border border-(--ui-stroke-tertiary) p-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
							className: "flex items-center gap-1 text-xs font-medium",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-checklist" }),
								" Extracted Tasks (",
								tasks.length,
								")"
							]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
							className: "mt-1 space-y-0.5 pl-3",
							children: tasks.map((t, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
								className: "text-xs text-(--ui-text-tertiary)",
								children: [
									"• ",
									t.task,
									" ",
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "italic",
										children: ["— ", t.from]
									})
								]
							}, i))
						})]
					})
				]
			}),
			commsAi.mode === "compose" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "shrink-0 border-t border-(--ui-stroke-tertiary) p-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
					className: "w-full resize-none rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) p-2 text-xs outline-none focus:border-primary",
					placeholder: "Write your message here... or ask AI to help compose it",
					rows: 4
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-2 flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						className: "h-7 w-48 rounded border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
						onChange: (e) => setTargetLanguage(e.target.value),
						placeholder: "Translate to language (optional)",
						type: "text",
						value: commsAi.targetLanguage
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "rounded-md bg-(--ui-bg-quaternary) px-3 py-1.5 text-xs",
							children: "Preview"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "rounded-md bg-primary px-3 py-1.5 text-xs text-white",
							children: "Send"
						})]
					})]
				})]
			})
		]
	});
}
//#endregion
//#region src/app/communications-hub/automation-builder.tsx
var TRIGGER_OPTIONS = [
	{
		value: "message_received",
		label: "Message Received"
	},
	{
		value: "keyword_detected",
		label: "Keyword Detected"
	},
	{
		value: "sender_match",
		label: "Sender Match"
	},
	{
		value: "schedule",
		label: "Schedule"
	}
];
var ACTION_OPTIONS = [
	{
		value: "send_reply",
		label: "Send Reply"
	},
	{
		value: "generate_response",
		label: "Generate Response"
	},
	{
		value: "search_knowledge",
		label: "Search Knowledge"
	},
	{
		value: "notify",
		label: "Notify User"
	},
	{
		value: "run_agent",
		label: "Run Agent"
	}
];
var PLATFORM_OPTIONS = [
	{
		value: "all",
		label: "All Platforms"
	},
	{
		value: "telegram",
		label: "Telegram"
	},
	{
		value: "whatsapp",
		label: "WhatsApp"
	},
	{
		value: "discord",
		label: "Discord"
	},
	{
		value: "slack",
		label: "Slack"
	},
	{
		value: "gmail",
		label: "Gmail"
	},
	{
		value: "sms",
		label: "SMS"
	}
];
function AutomationBuilder() {
	const comms = useStore($communications);
	const [showBuilder, setShowBuilder] = (0, import_react.useState)(false);
	const [name, setName] = (0, import_react.useState)("");
	const [trigger, setTrigger] = (0, import_react.useState)("message_received");
	const [action, setAction] = (0, import_react.useState)("send_reply");
	const [platform, setPlatform] = (0, import_react.useState)("all");
	const [condition, setCondition] = (0, import_react.useState)("");
	const [requireApproval, setRequireApproval] = (0, import_react.useState)(true);
	const [keywords, setKeywords] = (0, import_react.useState)("");
	const handleCreate = () => {
		if (!name.trim()) return;
		const triggerConfig = {};
		if (trigger === "keyword_detected" && keywords.trim()) triggerConfig.keywords = keywords.split(",").map((k) => k.trim());
		addAutomationRule({
			name: name.trim(),
			platform,
			trigger,
			condition,
			action,
			requireApproval,
			enabled: true
		});
		addActivity({
			type: "ai_reply",
			platform,
			description: `Automation rule created: ${name}`,
			platformName: platform === "all" ? "All" : platform
		});
		setName("");
		setCondition("");
		setKeywords("");
		setShowBuilder(false);
	};
	const ruleExecutions = comms.activityFeed.filter((a) => a.type === "ai_reply").slice(0, 5);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-sm font-semibold",
					children: "Message Automation"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: "flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-xs text-white",
					onClick: () => setShowBuilder(!showBuilder),
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-add" }), "New Rule"]
				})]
			}),
			showBuilder && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "shrink-0 border-b border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) p-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid grid-cols-2 gap-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
									className: "text-[10px] font-medium text-(--ui-text-tertiary)",
									children: "Rule Name"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									className: "h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
									onChange: (e) => setName(e.target.value),
									placeholder: "e.g., Away Message",
									type: "text",
									value: name
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
									className: "text-[10px] font-medium text-(--ui-text-tertiary)",
									children: "Platform"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("select", {
									className: "h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
									onChange: (e) => setPlatform(e.target.value),
									value: platform,
									children: PLATFORM_OPTIONS.map((o) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: o.value,
										children: o.label
									}, o.value))
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
									className: "text-[10px] font-medium text-(--ui-text-tertiary)",
									children: "Trigger"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("select", {
									className: "h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
									onChange: (e) => setTrigger(e.target.value),
									value: trigger,
									children: TRIGGER_OPTIONS.map((o) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: o.value,
										children: o.label
									}, o.value))
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
									className: "text-[10px] font-medium text-(--ui-text-tertiary)",
									children: "Action"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("select", {
									className: "h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
									onChange: (e) => setAction(e.target.value),
									value: action,
									children: ACTION_OPTIONS.map((o) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: o.value,
										children: o.label
									}, o.value))
								})]
							}),
							trigger === "keyword_detected" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "col-span-2 space-y-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
									className: "text-[10px] font-medium text-(--ui-text-tertiary)",
									children: "Keywords (comma-separated)"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									className: "h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
									onChange: (e) => setKeywords(e.target.value),
									placeholder: "urgent, help, question",
									type: "text",
									value: keywords
								})]
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mt-2 space-y-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
							className: "text-[10px] font-medium text-(--ui-text-tertiary)",
							children: "Condition"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							className: "h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
							onChange: (e) => setCondition(e.target.value),
							placeholder: "e.g., contains 'urgent' OR sender is 'John'",
							type: "text",
							value: condition
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mt-2 flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
							className: "flex items-center gap-2 text-xs",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								checked: requireApproval,
								className: "rounded",
								onChange: (e) => setRequireApproval(e.target.checked),
								type: "checkbox"
							}), "Require approval before executing"]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "rounded-md px-3 py-1.5 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)",
								onClick: () => setShowBuilder(false),
								children: "Cancel"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "rounded-md bg-primary px-3 py-1.5 text-xs text-white",
								onClick: handleCreate,
								children: "Create Rule"
							})]
						})]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "min-h-0 flex-1 overflow-y-auto",
				children: comms.automationRules.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex h-full items-center justify-center text-sm text-(--ui-text-tertiary)",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "text-center",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-run-all text-3xl text-(--ui-text-tertiary)" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-2",
								children: "No automation rules yet"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-xs",
								children: "Create rules to automate repetitive communication"
							})
						]
					})
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "divide-y divide-(--ui-stroke-tertiary)",
					children: comms.automationRules.map((rule) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AutomationRuleRow, { rule }, rule.id))
				})
			}),
			ruleExecutions.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "shrink-0 border-t border-(--ui-stroke-tertiary) p-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-[10px] font-medium text-(--ui-text-tertiary)",
					children: "Recent Automation Activity"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "mt-1 space-y-1",
					children: ruleExecutions.map((a, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2 text-[10px] text-(--ui-text-tertiary)",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-sparkle text-xs" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "truncate",
								children: a.description
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "ml-auto shrink-0",
								children: new Date(a.timestamp).toLocaleTimeString()
							})
						]
					}, i))
				})]
			})
		]
	});
}
function AutomationRuleRow({ rule }) {
	const [isEnabled, setIsEnabled] = (0, import_react.useState)(rule.enabled);
	const handleToggle = () => {
		updateAutomationRule(rule.id, { enabled: !isEnabled });
		setIsEnabled(!isEnabled);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center gap-3 px-4 py-3",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: `size-2 shrink-0 rounded-full ${isEnabled ? "bg-green-500" : "bg-(--ui-text-tertiary)"}` }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0 flex-1",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-xs font-medium",
							children: rule.name
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "rounded-md bg-(--ui-bg-quaternary) px-1.5 py-0.5 text-[10px] text-(--ui-text-tertiary)",
							children: rule.platform === "all" ? "All" : rule.platform
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "rounded-md bg-(--ui-bg-quaternary) px-1.5 py-0.5 text-[10px] text-(--ui-text-tertiary)",
							children: rule.trigger
						})
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
					className: "mt-0.5 text-[10px] text-(--ui-text-tertiary)",
					children: [
						rule.action,
						" ",
						rule.condition ? `| ${rule.condition}` : "",
						rule.requireApproval ? " | Requires approval" : ""
					]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "relative inline-flex cursor-pointer items-center",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
					checked: isEnabled,
					className: "peer sr-only",
					onChange: handleToggle,
					type: "checkbox"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "h-4 w-7 rounded-full bg-(--ui-bg-quaternary) after:absolute after:left-[2px] after:top-[2px] after:size-3 after:rounded-full after:bg-white after:transition-all peer-checked:bg-primary peer-checked:after:translate-x-full" })]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
				className: "rounded p-1 text-xs text-(--ui-text-tertiary) hover:text-red-500",
				onClick: () => removeAutomationRule(rule.id),
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-trash" })
			})
		]
	});
}
//#endregion
//#region src/store/communications-contacts.ts
init_nanostores();
var generateId$1 = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
var $contacts = /* @__PURE__ */ atom({
	contacts: [],
	searchQuery: "",
	selectedContactId: null,
	loading: false,
	selectedTag: ""
});
var patch$2 = (update) => $contacts.set({
	...$contacts.get(),
	...update
});
function setContactSearch(query) {
	patch$2({ searchQuery: query });
}
function selectContact(id) {
	patch$2({ selectedContactId: id });
}
function setSelectedTag(tag) {
	patch$2({ selectedTag: tag });
}
function addContact(contact) {
	const newContact = {
		...contact,
		id: generateId$1(),
		createdAt: (/* @__PURE__ */ new Date()).toISOString(),
		updatedAt: (/* @__PURE__ */ new Date()).toISOString()
	};
	patch$2({ contacts: [...$contacts.get().contacts, newContact] });
}
function removeContact(id) {
	patch$2({ contacts: $contacts.get().contacts.filter((c) => c.id !== id) });
}
function getFilteredContacts() {
	const state = $contacts.get();
	let result = state.contacts;
	if (state.searchQuery) {
		const q = state.searchQuery.toLowerCase();
		result = result.filter((c) => c.name.toLowerCase().includes(q) || c.email.toLowerCase().includes(q) || c.phone.includes(q) || c.organization.toLowerCase().includes(q) || c.links.some((l) => l.username.toLowerCase().includes(q) || l.displayName.toLowerCase().includes(q)));
	}
	if (state.selectedTag) result = result.filter((c) => c.tags.includes(state.selectedTag));
	return result.sort((a, b) => a.name.localeCompare(b.name));
}
function getAllTags() {
	const tags = /* @__PURE__ */ new Set();
	for (const c of $contacts.get().contacts) for (const t of c.tags) tags.add(t);
	return Array.from(tags).sort();
}
//#endregion
//#region src/app/communications-hub/contacts.tsx
var PLATFORM_ICONS = {
	telegram: "send",
	whatsapp: "message-circle",
	discord: "message-circle",
	slack: "message-square-text",
	gmail: "mail",
	sms: "message-square-text"
};
function ContactsView({ onSelectConversation }) {
	const contacts = useStore($contacts);
	const filtered = getFilteredContacts();
	const tags = getAllTags();
	const [showAdd, setShowAdd] = (0, import_react.useState)(false);
	const [newName, setNewName] = (0, import_react.useState)("");
	const [newEmail, setNewEmail] = (0, import_react.useState)("");
	const [newPhone, setNewPhone] = (0, import_react.useState)("");
	const [mergeTarget, setMergeTarget] = (0, import_react.useState)(null);
	const handleAdd = () => {
		if (!newName.trim()) return;
		addContact({
			name: newName.trim(),
			email: newEmail,
			phone: newPhone,
			photoUrl: "",
			organization: "",
			tags: [],
			notes: "",
			links: [],
			conversationCount: 0,
			lastMessageAt: "",
			confidence: 1
		});
		setNewName("");
		setNewEmail("");
		setNewPhone("");
		setShowAdd(false);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex w-72 shrink-0 flex-col border-r border-(--ui-stroke-tertiary)",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "shrink-0 space-y-2 border-b border-(--ui-stroke-tertiary) p-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "relative",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-search absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-(--ui-text-tertiary)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							className: "h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) pl-7 pr-3 text-xs outline-none focus:border-primary",
							onChange: (e) => setContactSearch(e.target.value),
							placeholder: "Search contacts...",
							type: "text",
							value: contacts.searchQuery
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex flex-wrap gap-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: `rounded-md px-2 py-0.5 text-[10px] ${!contacts.selectedTag ? "bg-primary text-white" : "bg-(--ui-bg-quaternary) text-(--ui-text-tertiary)"}`,
							onClick: () => setSelectedTag(""),
							children: "All"
						}), tags.map((tag) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: `rounded-md px-2 py-0.5 text-[10px] ${contacts.selectedTag === tag ? "bg-primary text-white" : "bg-(--ui-bg-quaternary) text-(--ui-text-tertiary)"}`,
							onClick: () => setSelectedTag(tag),
							children: tag
						}, tag))]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: "flex w-full items-center justify-center gap-1 rounded-md border border-dashed border-(--ui-stroke-tertiary) px-3 py-1.5 text-xs text-(--ui-text-tertiary) hover:text-foreground",
						onClick: () => setShowAdd(!showAdd),
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-add" }), "Add Contact"]
					}),
					showAdd && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-1.5 rounded-md border border-(--ui-stroke-tertiary) p-2",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								className: "h-7 w-full rounded border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
								onChange: (e) => setNewName(e.target.value),
								placeholder: "Name",
								type: "text",
								value: newName
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								className: "h-7 w-full rounded border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
								onChange: (e) => setNewEmail(e.target.value),
								placeholder: "Email",
								type: "email",
								value: newEmail
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								className: "h-7 w-full rounded border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
								onChange: (e) => setNewPhone(e.target.value),
								placeholder: "Phone",
								type: "tel",
								value: newPhone
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "h-7 w-full rounded-md bg-primary text-xs text-white",
								onClick: handleAdd,
								children: "Save"
							})
						]
					})
				]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "min-h-0 flex-1 overflow-y-auto",
				children: filtered.map((c) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: `flex cursor-pointer items-center gap-3 px-3 py-2 transition-colors hover:bg-(--ui-row-hover-background) ${contacts.selectedContactId === c.id ? "bg-(--ui-row-active-background)" : ""}`,
					onClick: () => selectContact(c.id),
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex size-8 shrink-0 items-center justify-center rounded-full bg-(--ui-bg-quaternary) text-xs font-medium",
							children: c.photoUrl ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("img", {
								className: "size-8 rounded-full object-cover",
								src: c.photoUrl
							}) : c.name[0]?.toUpperCase()
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0 flex-1",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "truncate text-xs font-medium",
									children: c.name
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "truncate text-[10px] text-(--ui-text-tertiary)",
									children: c.email || c.phone || c.links.map((l) => l.displayName || l.username).join(", ")
								}),
								c.links.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "mt-0.5 flex gap-1",
									children: c.links.map((l, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: `codicon codicon-${PLATFORM_ICONS[l.provider] || "comment-discussion"} text-[10px] text-(--ui-text-tertiary)`,
										title: l.provider
									}, i))
								})
							]
						}),
						c.tags.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex shrink-0 gap-0.5",
							children: c.tags.slice(0, 2).map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "rounded bg-(--ui-bg-quaternary) px-1 py-0.5 text-[10px] text-(--ui-text-tertiary)",
								children: t
							}, t))
						})
					]
				}, c.id))
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "min-h-0 flex-1 overflow-y-auto p-4",
			children: contacts.selectedContactId ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ContactDetail, { contact: contacts.contacts.find((c) => c.id === contacts.selectedContactId) }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex h-full items-center justify-center text-sm text-(--ui-text-tertiary)",
				children: "Select a contact to view details"
			})
		})]
	});
}
function ContactDetail({ contact }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "max-w-lg space-y-4",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex size-12 items-center justify-center rounded-full bg-(--ui-bg-quaternary) text-lg font-medium",
					children: contact.photoUrl ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("img", {
						className: "size-12 rounded-full object-cover",
						src: contact.photoUrl
					}) : contact.name[0]?.toUpperCase()
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-sm font-semibold",
					children: contact.name
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-xs text-(--ui-text-tertiary)",
					children: contact.organization
				})] })]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-xs font-medium",
						children: "Contact Information"
					}),
					contact.email && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2 text-xs",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-mail text-(--ui-text-tertiary)" }), contact.email]
					}),
					contact.phone && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2 text-xs",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-call text-(--ui-text-tertiary)" }), contact.phone]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "text-xs text-(--ui-text-tertiary)",
						children: [contact.conversationCount, " conversations"]
					})
				]
			}),
			contact.links.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-xs font-medium",
					children: "Connected Accounts"
				}), contact.links.map((l, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2 text-xs",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `codicon codicon-${PLATFORM_ICONS[l.provider] || "comment-discussion"} text-(--ui-text-tertiary)` }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: l.displayName || l.username }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "text-(--ui-text-tertiary)",
							children: [
								"(",
								l.provider,
								")"
							]
						})
					]
				}, i))]
			}),
			contact.tags.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex flex-wrap gap-1",
				children: contact.tags.map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "rounded-md bg-(--ui-bg-quaternary) px-2 py-0.5 text-[10px]",
					children: t
				}, t))
			}),
			contact.notes && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "rounded-lg border border-(--ui-stroke-tertiary) p-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-xs font-medium",
					children: "Notes"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-1 text-xs text-(--ui-text-tertiary)",
					children: contact.notes
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex gap-2",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: "flex items-center gap-1 rounded-md px-3 py-1.5 text-xs text-red-500 hover:bg-red-500/10",
					onClick: () => removeContact(contact.id),
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-trash" }), "Remove"]
				})
			})
		]
	});
}
//#endregion
//#region src/app/communications-hub/conversation.tsx
function ConversationWorkspace() {
	const selectedConv = useStore($communications).selectedConversation;
	const messages = selectedConv ? getFilteredMessages().filter((m) => m.conversationId === selectedConv) : [];
	if (!selectedConv) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex h-full items-center justify-center",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "text-center",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-comment-discussion text-3xl text-(--ui-text-tertiary)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-2 text-sm text-(--ui-text-tertiary)",
				children: "Select a conversation to view messages"
			})]
		})
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ConversationContent, {
		conversationId: selectedConv,
		messages
	});
}
function ConversationContent({ messages, conversationId }) {
	const [showAiPanel, setShowAiPanel] = (0, import_react.useState)(false);
	const [replyText, setReplyText] = (0, import_react.useState)("");
	const [aiDraft, setAiDraft] = (0, import_react.useState)(null);
	useStore($commsAI);
	const handleSummarize = (0, import_react.useCallback)(() => {
		generateSummary(messages);
		setShowAiPanel(true);
	}, [messages]);
	const handleAiDraft = (0, import_react.useCallback)((style) => {
		generateDraft(messages, style);
		const draft = $commsAI.get().draftResult;
		if (draft) {
			setAiDraft(draft.content);
			setReplyText(draft.content);
		}
	}, [messages]);
	const urgent = classifyPriority(messages).urgent;
	const tasks = extractTasks(messages);
	const pending = detectPendingRequests(messages);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: "flex items-center gap-1 text-xs text-(--ui-text-tertiary) hover:text-foreground",
					onClick: () => selectConversation(null),
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-arrow-left" }), "Back to inbox"]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-1",
					children: [
						urgent.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "flex items-center gap-1 rounded-md bg-red-500/10 px-2 py-0.5 text-[10px] text-red-500",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-warning" }),
								urgent.length,
								" urgent"
							]
						}),
						tasks.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "flex items-center gap-1 rounded-md bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-500",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-checklist" }),
								tasks.length,
								" tasks"
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: "flex items-center gap-1 rounded-md px-2 py-1 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)",
							onClick: handleSummarize,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-summary" }), "Summarize"]
						})
					]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "min-h-0 flex-1 space-y-2 overflow-y-auto p-4",
				children: messages.map((msg) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: `flex ${msg.direction === "outgoing" ? "justify-end" : "justify-start"}`,
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: `max-w-[80%] rounded-lg px-3 py-2 ${msg.direction === "outgoing" ? "bg-primary text-white" : "bg-(--ui-bg-quaternary)"}`,
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-[10px] font-medium opacity-70",
									children: msg.senderName
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-[10px] opacity-50",
									children: formatTime$2(msg.timestamp)
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-1 text-xs",
								children: msg.content
							}),
							msg.attachments.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "mt-1 flex gap-1",
								children: msg.attachments.map((a, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "flex items-center gap-1 text-[10px] opacity-70",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `codicon codicon-${a.type === "image" ? "file-media" : a.type === "pdf" ? "file-pdf" : "file"}` }), a.name]
								}, i))
							}),
							msg.aiResponse && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-1 rounded bg-black/10 px-2 py-1 text-[10px] italic opacity-70",
								children: ["AI: ", msg.aiResponse]
							})
						]
					})
				}, msg.id))
			}),
			aiDraft && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "shrink-0 border-t border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-4 py-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "flex items-center gap-1 text-[10px] text-(--ui-text-tertiary)",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-robot" }), "AI Draft"]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "text-[10px] text-(--ui-text-tertiary) hover:text-foreground",
						onClick: () => {
							setAiDraft(null);
							setReplyText("");
						},
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-close" })
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-1 text-xs italic",
					children: aiDraft
				})]
			}),
			showAiPanel && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "shrink-0 border-t border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-4 py-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex flex-wrap gap-1",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "rounded-md bg-white/10 px-2 py-1 text-[10px] hover:bg-white/20",
							onClick: () => handleAiDraft("professional"),
							children: "Professional Reply"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "rounded-md bg-white/10 px-2 py-1 text-[10px] hover:bg-white/20",
							onClick: () => handleAiDraft("casual"),
							children: "Casual Reply"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "rounded-md bg-white/10 px-2 py-1 text-[10px] hover:bg-white/20",
							onClick: () => handleAiDraft("friendly"),
							children: "Friendly Reply"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "rounded-md bg-white/10 px-2 py-1 text-[10px] hover:bg-white/20",
							onClick: () => handleAiDraft("short"),
							children: "Short Reply"
						}),
						pending.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "flex items-center gap-1 rounded-md bg-amber-500/10 px-2 py-1 text-[10px] text-amber-500",
							children: [
								pending.length,
								" pending ",
								pending.length === 1 ? "request" : "requests"
							]
						})
					]
				}), tasks.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("details", {
					className: "mt-1",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("summary", {
						className: "cursor-pointer text-[10px] text-(--ui-text-tertiary) hover:text-foreground",
						children: [
							tasks.length,
							" task",
							tasks.length !== 1 ? "s" : "",
							" extracted"
						]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
						className: "mt-1 space-y-0.5 pl-3",
						children: tasks.map((t, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
							className: "text-[10px] text-(--ui-text-tertiary)",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-check text-[10px] text-green-500" }),
								" ",
								t.task,
								" ",
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "italic",
									children: ["— from ", t.from]
								})
							]
						}, i))
					})]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "shrink-0 border-t border-(--ui-stroke-tertiary) px-4 py-3",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex gap-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							className: "h-8 min-w-0 flex-1 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-3 text-xs outline-none focus:border-primary",
							onChange: (e) => setReplyText(e.target.value),
							placeholder: "Type a reply...",
							type: "text",
							value: replyText
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "flex h-8 items-center gap-1 rounded-md px-2.5 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)",
							onClick: () => setShowAiPanel(true),
							title: "AI Assistant",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-robot" })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: "flex h-8 items-center gap-1 rounded-md bg-primary px-3 text-xs text-white disabled:opacity-50",
							disabled: !replyText.trim(),
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-send" }), "Send"]
						})
					]
				})
			})
		]
	});
}
function formatTime$2(ts) {
	return new Date(ts).toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit"
	});
}
//#endregion
//#region src/app/communications-hub/inbox.tsx
var FILTERS = [
	{
		id: "all",
		label: "All"
	},
	{
		id: "unread",
		label: "Unread"
	},
	{
		id: "important",
		label: "Important"
	},
	{
		id: "pinned",
		label: "Pinned"
	},
	{
		id: "ai-only",
		label: "AI Replies"
	},
	{
		id: "archived",
		label: "Archived"
	}
];
var PLATFORMS = [
	{
		id: "all",
		label: "All Platforms",
		icon: "globe"
	},
	{
		id: "telegram",
		label: "Telegram",
		icon: "send"
	},
	{
		id: "whatsapp",
		label: "WhatsApp",
		icon: "message-circle"
	},
	{
		id: "discord",
		label: "Discord",
		icon: "message-circle"
	},
	{
		id: "slack",
		label: "Slack",
		icon: "message-square-text"
	},
	{
		id: "gmail",
		label: "Gmail",
		icon: "mail"
	},
	{
		id: "sms",
		label: "SMS",
		icon: "message-square-text"
	}
];
function InboxView({ onSelectConversation }) {
	const comms = useStore($communications);
	const messages = getFilteredMessages();
	const [searchInput, setSearchInput] = (0, import_react.useState)(comms.inboxSearch);
	const handleSearch = (value) => {
		setSearchInput(value);
		setInboxSearch(value);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "shrink-0 space-y-2 border-b border-(--ui-stroke-tertiary) p-3",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "relative",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-search absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-(--ui-text-tertiary)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						className: "h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) pl-7 pr-3 text-xs outline-none focus:border-primary",
						onChange: (e) => handleSearch(e.target.value),
						placeholder: "Search messages...",
						type: "text",
						value: searchInput
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex flex-wrap gap-1",
					children: FILTERS.map((f) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: `rounded-md px-2.5 py-1 text-xs transition-colors ${comms.inboxFilter === f.id ? "bg-primary text-white" : "bg-(--ui-bg-quaternary) text-(--ui-text-tertiary) hover:text-foreground"}`,
						onClick: () => setInboxFilter(f.id),
						children: f.label
					}, f.id))
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex flex-wrap gap-1",
					children: PLATFORMS.map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: `flex items-center gap-1 rounded-md px-2 py-0.5 text-xs transition-colors ${comms.selectedPlatformFilter === p.id ? "bg-(--ui-row-active-background) text-foreground" : "text-(--ui-text-tertiary) hover:text-foreground"}`,
						onClick: () => setPlatformFilter(p.id),
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `codicon codicon-${p.icon} text-xs` }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: p.label })]
					}, p.id))
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "min-h-0 flex-1 overflow-y-auto",
			children: messages.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex h-full items-center justify-center text-sm text-(--ui-text-tertiary)",
				children: "No messages found"
			}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "divide-y divide-(--ui-stroke-tertiary)",
				children: messages.map((msg) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(MessageRow, {
					message: msg,
					onSelect: () => onSelectConversation(msg.conversationId)
				}, msg.id))
			})
		})]
	});
}
function MessageRow({ message: msg, onSelect }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: `flex cursor-pointer items-start gap-3 px-4 py-3 transition-colors hover:bg-(--ui-row-hover-background) ${!msg.read ? "bg-(--ui-row-active-background)" : ""}`,
		onClick: () => {
			markMessageRead(msg.id);
			onSelect();
		},
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: `mt-1 size-2 shrink-0 rounded-full ${msg.priority === "urgent" ? "bg-red-500" : msg.priority === "high" ? "bg-amber-500" : !msg.read ? "bg-primary" : "bg-transparent"}` }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0 flex-1",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: `truncate text-xs ${!msg.read ? "font-semibold" : ""}`,
							children: msg.senderName
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "shrink-0 text-[10px] text-(--ui-text-tertiary)",
							children: formatTime$1(msg.timestamp)
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: `mt-0.5 truncate text-xs ${!msg.read ? "text-foreground" : "text-(--ui-text-tertiary)"}`,
						children: msg.content
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mt-1 flex items-center gap-2",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								className: "flex items-center gap-0.5 text-[10px] text-(--ui-text-tertiary)",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `codicon codicon-${getPlatformIcon(msg.platform)} text-[10px]` }), msg.platform]
							}),
							msg.important && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-star-full text-[10px] text-amber-500" }),
							msg.aiReplied && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-robot text-[10px] text-(--ui-text-tertiary)" }),
							msg.attachments.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-attach text-[10px] text-(--ui-text-tertiary)" })
						]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex shrink-0 flex-col gap-0.5",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					className: `rounded p-0.5 text-xs transition-colors hover:bg-(--ui-bg-quaternary) ${msg.important ? "text-amber-500" : "text-(--ui-text-tertiary)"}`,
					onClick: (e) => {
						e.stopPropagation();
						toggleImportantMessage(msg.id);
					},
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-star-full" })
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					className: "rounded p-0.5 text-xs text-(--ui-text-tertiary) transition-colors hover:bg-(--ui-bg-quaternary)",
					onClick: (e) => {
						e.stopPropagation();
						archiveMessage(msg.id);
					},
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-archive" })
				})]
			})
		]
	});
}
function getPlatformIcon(platform) {
	return {
		telegram: "send",
		whatsapp: "message-circle",
		discord: "message-circle",
		slack: "message-square-text",
		gmail: "mail",
		outlook: "mail",
		teams: "people",
		signal: "lock",
		sms: "message-square-text"
	}[platform] || "comment-discussion";
}
function formatTime$1(ts) {
	const date = new Date(ts);
	const diff = (/* @__PURE__ */ new Date()).getTime() - date.getTime();
	if (diff < 6e4) return "now";
	if (diff < 36e5) return `${Math.floor(diff / 6e4)}m`;
	if (diff < 864e5) return `${Math.floor(diff / 36e5)}h`;
	if (diff < 6048e5) return `${Math.floor(diff / 864e5)}d`;
	return date.toLocaleDateString();
}
//#endregion
//#region src/store/communications-notifications.ts
init_nanostores();
var $commsNotifications = /* @__PURE__ */ atom({
	items: [],
	rules: [
		{
			id: "rule_msg",
			name: "New Messages",
			category: "message",
			enabled: true,
			channels: ["desktop"],
			priority: "normal",
			sound: "default",
			quietHoursStart: "",
			quietHoursEnd: "",
			providerFilter: "all",
			minPriority: "low"
		},
		{
			id: "rule_mention",
			name: "Mentions",
			category: "mention",
			enabled: true,
			channels: ["desktop"],
			priority: "high",
			sound: "alert",
			quietHoursStart: "",
			quietHoursEnd: "",
			providerFilter: "all",
			minPriority: "low"
		},
		{
			id: "rule_urgent",
			name: "Urgent Messages",
			category: "urgent",
			enabled: true,
			channels: ["desktop", "sound"],
			priority: "urgent",
			sound: "critical",
			quietHoursStart: "",
			quietHoursEnd: "",
			providerFilter: "all",
			minPriority: "low"
		},
		{
			id: "rule_approval",
			name: "Approval Requests",
			category: "approval",
			enabled: true,
			channels: ["desktop"],
			priority: "high",
			sound: "alert",
			quietHoursStart: "",
			quietHoursEnd: "",
			providerFilter: "all",
			minPriority: "low"
		},
		{
			id: "rule_automation",
			name: "Automation Events",
			category: "automation",
			enabled: true,
			channels: ["desktop"],
			priority: "normal",
			sound: "default",
			quietHoursStart: "",
			quietHoursEnd: "",
			providerFilter: "all",
			minPriority: "low"
		},
		{
			id: "rule_error",
			name: "Errors & Failures",
			category: "error",
			enabled: true,
			channels: ["desktop"],
			priority: "high",
			sound: "alert",
			quietHoursStart: "",
			quietHoursEnd: "",
			providerFilter: "all",
			minPriority: "low"
		},
		{
			id: "rule_scheduled",
			name: "Scheduled Messages",
			category: "scheduled",
			enabled: true,
			channels: ["desktop"],
			priority: "normal",
			sound: "default",
			quietHoursStart: "",
			quietHoursEnd: "",
			providerFilter: "all",
			minPriority: "low"
		},
		{
			id: "rule_calendar",
			name: "Calendar Events",
			category: "calendar",
			enabled: true,
			channels: ["desktop"],
			priority: "normal",
			sound: "default",
			quietHoursStart: "",
			quietHoursEnd: "",
			providerFilter: "all",
			minPriority: "low"
		}
	],
	unreadCount: 0,
	filterCategory: "all",
	filterRead: "unread"
});
var patch$1 = (update) => $commsNotifications.set({
	...$commsNotifications.get(),
	...update
});
function setNotificationFilterCategory(cat) {
	patch$1({ filterCategory: cat });
}
function setNotificationFilterRead(filter) {
	patch$1({ filterRead: filter });
}
function markNotificationRead(id) {
	const state = $commsNotifications.get();
	patch$1({
		items: state.items.map((n) => n.id === id ? {
			...n,
			read: true
		} : n),
		unreadCount: Math.max(0, state.unreadCount - 1)
	});
}
function markAllNotificationsRead() {
	patch$1({
		items: $commsNotifications.get().items.map((n) => ({
			...n,
			read: true
		})),
		unreadCount: 0
	});
}
function getFilteredNotifications() {
	const state = $commsNotifications.get();
	let result = state.items;
	if (state.filterCategory !== "all") result = result.filter((n) => n.category === state.filterCategory);
	if (state.filterRead === "unread") result = result.filter((n) => !n.read);
	else if (state.filterRead === "read") result = result.filter((n) => n.read);
	return result.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
}
function updateNotificationRule(id, updates) {
	patch$1({ rules: $commsNotifications.get().rules.map((r) => r.id === id ? {
		...r,
		...updates
	} : r) });
}
function clearAllNotifications() {
	patch$1({
		items: [],
		unreadCount: 0
	});
}
//#endregion
//#region src/app/communications-hub/notifications.tsx
var CATEGORIES = [
	{
		id: "all",
		label: "All",
		icon: "globe"
	},
	{
		id: "message",
		label: "Messages",
		icon: "comment-discussion"
	},
	{
		id: "mention",
		label: "Mentions",
		icon: "mention"
	},
	{
		id: "urgent",
		label: "Urgent",
		icon: "warning"
	},
	{
		id: "approval",
		label: "Approvals",
		icon: "check"
	},
	{
		id: "automation",
		label: "Automation",
		icon: "run-all"
	},
	{
		id: "error",
		label: "Errors",
		icon: "error"
	}
];
function NotificationsView() {
	const state = useStore($commsNotifications);
	const filtered = getFilteredNotifications();
	const [showSettings, setShowSettings] = (0, import_react.useState)(false);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "text-sm font-semibold",
						children: "Notifications"
					}), state.unreadCount > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "rounded-full bg-primary px-2 py-0.5 text-[10px] text-white",
						children: state.unreadCount
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex gap-1",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: "flex items-center gap-1 rounded-md px-2 py-1 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)",
							onClick: markAllNotificationsRead,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-check-all" }), "Mark All Read"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: "flex items-center gap-1 rounded-md px-2 py-1 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)",
							onClick: () => setShowSettings(!showSettings),
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-gear" }), "Settings"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: "flex items-center gap-1 rounded-md px-2 py-1 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)",
							onClick: clearAllNotifications,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-clear-all" }), "Clear All"]
						})
					]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex shrink-0 items-center gap-2 border-b border-(--ui-stroke-tertiary) px-4 py-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex flex-wrap gap-1",
					children: CATEGORIES.map((cat) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: `flex items-center gap-1 rounded-md px-2 py-1 text-xs ${state.filterCategory === cat.id ? "bg-primary text-white" : "text-(--ui-text-tertiary) hover:text-foreground"}`,
						onClick: () => setNotificationFilterCategory(cat.id),
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `codicon codicon-${cat.icon} text-xs` }), cat.label]
					}, cat.id))
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "ml-auto flex gap-1",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: `rounded-md px-2 py-1 text-xs ${state.filterRead === "unread" ? "bg-(--ui-row-active-background) text-foreground" : "text-(--ui-text-tertiary)"}`,
							onClick: () => setNotificationFilterRead("unread"),
							children: "Unread"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: `rounded-md px-2 py-1 text-xs ${state.filterRead === "all" ? "bg-(--ui-row-active-background) text-foreground" : "text-(--ui-text-tertiary)"}`,
							onClick: () => setNotificationFilterRead("all"),
							children: "All"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: `rounded-md px-2 py-1 text-xs ${state.filterRead === "read" ? "bg-(--ui-row-active-background) text-foreground" : "text-(--ui-text-tertiary)"}`,
							onClick: () => setNotificationFilterRead("read"),
							children: "Read"
						})
					]
				})]
			}),
			showSettings ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(NotificationSettings, {}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "min-h-0 flex-1 overflow-y-auto",
				children: filtered.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex h-full items-center justify-center text-sm text-(--ui-text-tertiary)",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "text-center",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-bell text-3xl text-(--ui-text-tertiary)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-2",
							children: "No notifications"
						})]
					})
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "divide-y divide-(--ui-stroke-tertiary)",
					children: filtered.map((n) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: `flex cursor-pointer items-start gap-3 px-4 py-3 transition-colors hover:bg-(--ui-row-hover-background) ${!n.read ? "bg-(--ui-row-active-background)" : ""}`,
						onClick: () => markNotificationRead(n.id),
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: `flex size-8 shrink-0 items-center justify-center rounded-full ${n.priority === "urgent" ? "bg-red-500/20 text-red-500" : n.priority === "high" ? "bg-amber-500/20 text-amber-500" : "bg-(--ui-bg-quaternary) text-(--ui-text-tertiary)"}`,
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `codicon codicon-${getCategoryIcon(n.category)} text-sm` })
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "min-w-0 flex-1",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center justify-between gap-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: `truncate text-xs ${!n.read ? "font-semibold" : ""}`,
											children: n.title
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "shrink-0 text-[10px] text-(--ui-text-tertiary)",
											children: formatTime(n.createdAt)
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "mt-0.5 text-xs text-(--ui-text-tertiary)",
										children: n.body
									}),
									n.provider && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "mt-0.5 text-[10px] text-(--ui-text-tertiary)",
										children: n.provider
									})
								]
							}),
							!n.read && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "mt-1.5 size-2 shrink-0 rounded-full bg-primary" })
						]
					}, n.id))
				})
			})
		]
	});
}
function NotificationSettings() {
	const state = useStore($commsNotifications);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "min-h-0 flex-1 overflow-y-auto p-4",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "max-w-lg space-y-3",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "text-xs font-medium",
				children: "Notification Rules"
			}), state.rules.map((rule) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "rounded-lg border border-(--ui-stroke-tertiary) p-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs font-medium",
						children: rule.name
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "text-[10px] text-(--ui-text-tertiary)",
						children: [
							rule.category,
							" | ",
							rule.priority,
							" priority"
						]
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
						className: "relative inline-flex cursor-pointer items-center",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							checked: rule.enabled,
							className: "peer sr-only",
							onChange: () => updateNotificationRule(rule.id, { enabled: !rule.enabled }),
							type: "checkbox"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "h-4 w-7 rounded-full bg-(--ui-bg-quaternary) after:absolute after:left-[2px] after:top-[2px] after:size-3 after:rounded-full after:bg-white after:transition-all peer-checked:bg-primary peer-checked:after:translate-x-full" })]
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "mt-2 flex flex-wrap gap-1",
					children: rule.channels.map((ch) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "rounded-md bg-(--ui-bg-quaternary) px-1.5 py-0.5 text-[10px] text-(--ui-text-tertiary)",
						children: ch
					}, ch))
				})]
			}, rule.id))]
		})
	});
}
function getCategoryIcon(category) {
	return {
		message: "comment-discussion",
		mention: "mention",
		urgent: "warning",
		scheduled: "clock",
		automation: "run-all",
		approval: "check",
		calendar: "calendar",
		system: "settings-gear",
		error: "error"
	}[category] || "bell";
}
function formatTime(ts) {
	const date = new Date(ts);
	const diff = (/* @__PURE__ */ new Date()).getTime() - date.getTime();
	if (diff < 6e4) return "now";
	if (diff < 36e5) return `${Math.floor(diff / 6e4)}m`;
	if (diff < 864e5) return `${Math.floor(diff / 36e5)}h`;
	return date.toLocaleDateString();
}
//#endregion
//#region src/store/communications-scheduler.ts
init_nanostores();
var generateId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
var $scheduler = /* @__PURE__ */ atom({
	messages: [],
	viewFilter: "upcoming",
	loading: false
});
var patch = (update) => $scheduler.set({
	...$scheduler.get(),
	...update
});
function setSchedulerFilter(filter) {
	patch({ viewFilter: filter });
}
function scheduleMessage(msg) {
	const newMsg = {
		...msg,
		id: generateId(),
		createdAt: (/* @__PURE__ */ new Date()).toISOString()
	};
	patch({ messages: [...$scheduler.get().messages, newMsg] });
}
function cancelScheduledMessage(id) {
	patch({ messages: $scheduler.get().messages.map((m) => m.id === id && (m.status === "pending" || m.status === "scheduled") ? {
		...m,
		status: "cancelled"
	} : m) });
}
function pauseScheduledMessage(id) {
	patch({ messages: $scheduler.get().messages.map((m) => m.id === id && m.status === "scheduled" ? {
		...m,
		status: "paused"
	} : m) });
}
function resumeScheduledMessage(id) {
	patch({ messages: $scheduler.get().messages.map((m) => m.id === id && m.status === "paused" ? {
		...m,
		status: "scheduled"
	} : m) });
}
function rescheduleMessage(id, newTime) {
	patch({ messages: $scheduler.get().messages.map((m) => m.id === id ? {
		...m,
		scheduledAt: newTime,
		status: "scheduled"
	} : m) });
}
function approveScheduledMessage(id) {
	patch({ messages: $scheduler.get().messages.map((m) => m.id === id ? {
		...m,
		approved: true
	} : m) });
}
function getFilteredScheduledMessages() {
	const state = $scheduler.get();
	switch (state.viewFilter) {
		case "upcoming": return state.messages.filter((m) => m.status === "scheduled" || m.status === "pending").sort((a, b) => new Date(a.scheduledAt).getTime() - new Date(b.scheduledAt).getTime());
		case "history": return state.messages.filter((m) => m.status === "sent" || m.status === "failed" || m.status === "cancelled").sort((a, b) => new Date(b.scheduledAt).getTime() - new Date(a.scheduledAt).getTime());
		default: return [...state.messages].sort((a, b) => new Date(a.scheduledAt).getTime() - new Date(b.scheduledAt).getTime());
	}
}
//#endregion
//#region src/app/communications-hub/scheduler.tsx
function SchedulerView() {
	const scheduler = useStore($scheduler);
	useStore($contacts);
	const messages = getFilteredScheduledMessages();
	const [showSchedule, setShowSchedule] = (0, import_react.useState)(false);
	const [content, setContent] = (0, import_react.useState)("");
	const [recipientId, setRecipientId] = (0, import_react.useState)("");
	const [recipientName, setRecipientName] = (0, import_react.useState)("");
	const [provider, setProvider] = (0, import_react.useState)("telegram");
	const [date, setDate] = (0, import_react.useState)("");
	const [time, setTime] = (0, import_react.useState)("");
	const [recurrence, setRecurrence] = (0, import_react.useState)("none");
	const [requireApproval, setRequireApproval] = (0, import_react.useState)(true);
	const [editingId, setEditingId] = (0, import_react.useState)(null);
	const [editContent, setEditContent] = (0, import_react.useState)("");
	const handleSchedule = () => {
		if (!content.trim() || !date || !time) return;
		scheduleMessage({
			provider,
			accountId: "",
			recipientId,
			recipientName: recipientName || recipientId,
			content: content.trim(),
			scheduledAt: `${date}T${time}:00`,
			status: "scheduled",
			recurrence: recurrence === "none" ? "none" : recurrence,
			recurrenceConfig: {},
			attachments: [],
			requireApproval,
			approved: !requireApproval,
			templateId: "",
			parentId: "",
			sentAt: "",
			errorMessage: "",
			createdBy: "user"
		});
		setShowSchedule(false);
		setContent("");
		setRecipientId("");
		setRecipientName("");
		setDate("");
		setTime("");
	};
	const handleReschedule = (id) => {
		const newDate = prompt("New date (YYYY-MM-DD):");
		const newTime = prompt("New time (HH:MM):");
		if (newDate && newTime) rescheduleMessage(id, `${newDate}T${newTime}:00`);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex gap-1",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: `rounded-md px-2.5 py-1 text-xs ${scheduler.viewFilter === "upcoming" ? "bg-primary text-white" : "text-(--ui-text-tertiary) hover:text-foreground"}`,
							onClick: () => setSchedulerFilter("upcoming"),
							children: "Upcoming"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: `rounded-md px-2.5 py-1 text-xs ${scheduler.viewFilter === "all" ? "bg-primary text-white" : "text-(--ui-text-tertiary) hover:text-foreground"}`,
							onClick: () => setSchedulerFilter("all"),
							children: "All"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: `rounded-md px-2.5 py-1 text-xs ${scheduler.viewFilter === "history" ? "bg-primary text-white" : "text-(--ui-text-tertiary) hover:text-foreground"}`,
							onClick: () => setSchedulerFilter("history"),
							children: "History"
						})
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: "flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-xs text-white",
					onClick: () => setShowSchedule(!showSchedule),
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-add" }), "Schedule Message"]
				})]
			}),
			showSchedule && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "shrink-0 border-b border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) p-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid grid-cols-2 gap-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
									className: "text-[10px] font-medium text-(--ui-text-tertiary)",
									children: "Provider"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
									className: "h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
									onChange: (e) => setProvider(e.target.value),
									value: provider,
									children: [
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
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
											value: "sms",
											children: "SMS"
										})
									]
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
									className: "text-[10px] font-medium text-(--ui-text-tertiary)",
									children: "Recipient"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									className: "h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
									onChange: (e) => setRecipientId(e.target.value),
									placeholder: "Username or ID",
									type: "text",
									value: recipientId
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
									className: "text-[10px] font-medium text-(--ui-text-tertiary)",
									children: "Recipient Name"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									className: "h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
									onChange: (e) => setRecipientName(e.target.value),
									placeholder: "Display name",
									type: "text",
									value: recipientName
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
									className: "text-[10px] font-medium text-(--ui-text-tertiary)",
									children: "Recurrence"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
									className: "h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
									onChange: (e) => setRecurrence(e.target.value),
									value: recurrence,
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
											value: "none",
											children: "None"
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
											value: "daily",
											children: "Daily"
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
											value: "weekly",
											children: "Weekly"
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
											value: "monthly",
											children: "Monthly"
										})
									]
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
									className: "text-[10px] font-medium text-(--ui-text-tertiary)",
									children: "Date"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									className: "h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
									onChange: (e) => setDate(e.target.value),
									type: "date",
									value: date
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-1",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
									className: "text-[10px] font-medium text-(--ui-text-tertiary)",
									children: "Time"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									className: "h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none",
									onChange: (e) => setTime(e.target.value),
									type: "time",
									value: time
								})]
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mt-2",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
							className: "w-full resize-none rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) p-2 text-xs outline-none focus:border-primary",
							onChange: (e) => setContent(e.target.value),
							placeholder: "Message content...",
							rows: 3,
							value: content
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mt-2 flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
							className: "flex items-center gap-2 text-xs",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								checked: requireApproval,
								className: "rounded",
								onChange: (e) => setRequireApproval(e.target.checked),
								type: "checkbox"
							}), "Require approval before sending"]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "rounded-md px-3 py-1.5 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)",
								onClick: () => setShowSchedule(false),
								children: "Cancel"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "rounded-md bg-primary px-3 py-1.5 text-xs text-white",
								onClick: handleSchedule,
								children: "Schedule"
							})]
						})]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "min-h-0 flex-1 overflow-y-auto",
				children: messages.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex h-full items-center justify-center text-sm text-(--ui-text-tertiary)",
					children: "No scheduled messages"
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "divide-y divide-(--ui-stroke-tertiary)",
					children: messages.map((msg) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScheduledMessageRow, {
						message: msg,
						onApprove: () => approveScheduledMessage(msg.id),
						onCancel: () => cancelScheduledMessage(msg.id),
						onPause: () => pauseScheduledMessage(msg.id),
						onReschedule: () => handleReschedule(msg.id),
						onResume: () => resumeScheduledMessage(msg.id)
					}, msg.id))
				})
			})
		]
	});
}
function ScheduledMessageRow({ message: msg, onCancel, onPause, onResume, onReschedule, onApprove }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-start gap-3 px-4 py-3",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: `mt-1 size-2 shrink-0 rounded-full ${{
				scheduled: "text-blue-500",
				sent: "text-green-500",
				failed: "text-red-500",
				cancelled: "text-(--ui-text-tertiary)",
				paused: "text-amber-500",
				pending: "text-(--ui-text-tertiary)"
			}[msg.status]?.replace("text-", "bg-") || "bg-(--ui-text-tertiary)"}` }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0 flex-1",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-xs font-medium",
								children: msg.recipientName
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								className: "text-[10px] text-(--ui-text-tertiary)",
								children: ["via ", msg.provider]
							}),
							msg.recurrence !== "none" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "rounded-md bg-(--ui-bg-quaternary) px-1.5 py-0.5 text-[10px] text-(--ui-text-tertiary)",
								children: msg.recurrence
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-0.5 text-xs text-(--ui-text-tertiary)",
						children: msg.content
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mt-1 flex items-center gap-2 text-[10px] text-(--ui-text-tertiary)",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-clock" }),
							new Date(msg.scheduledAt).toLocaleString(),
							msg.status === "scheduled" && !msg.approved && msg.requireApproval && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "rounded-md bg-amber-500/10 px-1.5 py-0.5 text-amber-500",
								children: "Needs approval"
							})
						]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex shrink-0 gap-1",
				children: [msg.status === "scheduled" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
					msg.requireApproval && !msg.approved && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "rounded-md bg-green-500 px-2 py-1 text-xs text-white",
						onClick: onApprove,
						children: "Approve"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "rounded-md bg-(--ui-bg-quaternary) px-2 py-1 text-xs",
						onClick: onPause,
						children: "Pause"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "rounded-md bg-(--ui-bg-quaternary) px-2 py-1 text-xs",
						onClick: onReschedule,
						children: "Edit"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "rounded-md bg-red-500/10 px-2 py-1 text-xs text-red-500",
						onClick: onCancel,
						children: "Cancel"
					})
				] }), msg.status === "paused" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					className: "rounded-md bg-(--ui-bg-quaternary) px-2 py-1 text-xs",
					onClick: onResume,
					children: "Resume"
				})]
			})
		]
	});
}
//#endregion
//#region src/app/communications-hub/settings.tsx
var PLATFORM_NAMES = {
	telegram: "Telegram",
	whatsapp: "WhatsApp",
	discord: "Discord",
	slack: "Slack",
	gmail: "Gmail",
	outlook: "Outlook",
	teams: "Microsoft Teams",
	signal: "Signal",
	sms: "SMS Gateway",
	webhook: "Webhook",
	"custom-rest": "Custom REST API"
};
var PLATFORM_AUTH = {
	telegram: {
		method: "Bot Token or Account",
		description: "Connect via bot token from @BotFather or official account linking"
	},
	whatsapp: {
		method: "Business API",
		description: "Connect via WhatsApp Business API (official)"
	},
	discord: {
		method: "Bot Token",
		description: "Connect via Discord bot token from Developer Portal"
	},
	slack: {
		method: "OAuth",
		description: "Connect via Slack OAuth with required scopes"
	},
	gmail: {
		method: "OAuth 2.0",
		description: "Connect via Google OAuth with Gmail API scopes"
	},
	sms: {
		method: "API Key",
		description: "Connect via SMS gateway provider API key"
	}
};
function CommsSettings() {
	const comms = useStore($communications);
	const contacts = useStore($contacts);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "min-h-0 flex-1 overflow-y-auto p-4",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mx-auto max-w-2xl space-y-6",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "mb-3 text-sm font-semibold",
					children: "Connected Accounts"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "space-y-2",
					children: comms.platformConnections.map((pc) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between rounded-lg border border-(--ui-stroke-tertiary) p-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "flex size-8 items-center justify-center rounded-full",
								style: { backgroundColor: pc.color + "20" },
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: `codicon codicon-${pc.icon} text-sm`,
									style: { color: pc.color }
								})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-xs font-medium",
								children: pc.name
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-[10px] text-(--ui-text-tertiary)",
								children: pc.connected ? `Connected • ${pc.messagesToday} msgs today` : "Not connected"
							})] })]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex items-center gap-2",
							children: pc.connected ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								className: `flex items-center gap-1 text-[10px] ${pc.online ? "text-green-500" : "text-(--ui-text-tertiary)"}`,
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-primitive-dot" }), pc.online ? "Online" : "Offline"]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "rounded-md bg-red-500/10 px-2.5 py-1 text-xs text-red-500",
								onClick: () => setPlatformStatus(pc.id, false, false),
								children: "Disconnect"
							})] }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "rounded-md bg-primary px-2.5 py-1 text-xs text-white",
								onClick: () => setPlatformStatus(pc.id, true, true),
								children: "Connect"
							})
						})]
					}, pc.id))
				})] }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "mb-3 text-sm font-semibold",
					children: "Authentication Methods"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "space-y-2",
					children: Object.entries(PLATFORM_AUTH).map(([id, auth]) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "rounded-lg border border-(--ui-stroke-tertiary) p-3",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center justify-between",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-xs font-medium",
								children: PLATFORM_NAMES[id] || id
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-[10px] text-(--ui-text-tertiary)",
								children: auth.method
							})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-[10px] text-(--ui-text-tertiary)",
								children: auth.description
							})]
						})
					}, id))
				})] }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "mb-3 text-sm font-semibold",
					children: "AI Processing"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-3 rounded-lg border border-(--ui-stroke-tertiary) p-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToggleRow, {
							checked: comms.aiConfig.smartSuggestions,
							description: "Suggest AI replies for incoming messages",
							label: "Smart Suggestions",
							onChange: (v) => updateAIConfig({ smartSuggestions: v })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToggleRow, {
							checked: comms.aiConfig.autoReply,
							description: "Automatically reply to messages based on rules",
							label: "Auto Reply",
							onChange: (v) => updateAIConfig({ autoReply: v })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToggleRow, {
							checked: comms.aiConfig.sentimentAnalysis,
							description: "Detect message sentiment automatically",
							label: "Sentiment Analysis",
							onChange: (v) => updateAIConfig({ sentimentAnalysis: v })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToggleRow, {
							checked: comms.aiConfig.priorityDetection,
							description: "Classify messages by urgency automatically",
							label: "Priority Detection",
							onChange: (v) => updateAIConfig({ priorityDetection: v })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToggleRow, {
							checked: comms.aiConfig.taskExtraction,
							description: "Extract action items and tasks from messages",
							label: "Task Extraction",
							onChange: (v) => updateAIConfig({ taskExtraction: v })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToggleRow, {
							checked: comms.aiConfig.summarizeEnabled,
							description: "Generate conversation summaries",
							label: "Summarize Enabled",
							onChange: (v) => updateAIConfig({ summarizeEnabled: v })
						})
					]
				})] }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "mb-3 text-sm font-semibold",
					children: "Notification Preferences"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-3 rounded-lg border border-(--ui-stroke-tertiary) p-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToggleRow, {
							checked: comms.notificationConfig.desktopNotifications,
							description: "Show desktop notifications for new messages",
							label: "Desktop Notifications",
							onChange: (v) => updateNotificationConfig({ desktopNotifications: v })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToggleRow, {
							checked: comms.notificationConfig.soundEnabled,
							description: "Play notification sounds",
							label: "Sound",
							onChange: (v) => updateNotificationConfig({ soundEnabled: v })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToggleRow, {
							checked: comms.notificationConfig.doNotDisturb,
							description: "Silence all notifications",
							label: "Do Not Disturb",
							onChange: (v) => updateNotificationConfig({ doNotDisturb: v })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToggleRow, {
							checked: comms.notificationConfig.priorityMode,
							description: "Only show high priority and urgent notifications",
							label: "Priority Mode",
							onChange: (v) => updateNotificationConfig({ priorityMode: v })
						})
					]
				})] }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "mb-3 text-sm font-semibold",
					children: "Security & Privacy"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-3 rounded-lg border border-(--ui-stroke-tertiary) p-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToggleRow, {
							checked: comms.security.encryptedTokens,
							description: "Encrypt stored OAuth tokens and credentials",
							label: "Encrypted Token Storage",
							onChange: (v) => updateSecurity({ encryptedTokens: v })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToggleRow, {
							checked: comms.security.credentialVault,
							description: "Use system credential vault for password storage",
							label: "Credential Vault",
							onChange: (v) => updateSecurity({ credentialVault: v })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToggleRow, {
							checked: comms.security.permissionManager,
							description: "Require permission checks for sensitive operations",
							label: "Permission Manager",
							onChange: (v) => updateSecurity({ permissionManager: v })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToggleRow, {
							checked: comms.security.auditLog,
							description: "Log all communications activity for review",
							label: "Audit Log",
							onChange: (v) => updateSecurity({ auditLog: v })
						})
					]
				})] }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "mb-3 text-sm font-semibold",
					children: "Data Management"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "text-xs text-(--ui-text-tertiary)",
						children: [
							comms.messages.length,
							" messages stored | ",
							comms.conversations.length,
							" conversations | ",
							contacts.contacts.length,
							" contacts"
						]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "rounded-md bg-(--ui-bg-quaternary) px-3 py-1.5 text-xs text-(--ui-text-tertiary) hover:text-foreground",
							children: "Export Data"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "rounded-md bg-red-500/10 px-3 py-1.5 text-xs text-red-500 hover:bg-red-500/20",
							children: "Clear All Data"
						})]
					})]
				})] })
			]
		})
	});
}
function ToggleRow({ label, description, checked, onChange }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center justify-between",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "min-w-0 flex-1",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-xs font-medium",
				children: label
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-[10px] text-(--ui-text-tertiary)",
				children: description
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "relative ml-3 inline-flex cursor-pointer items-center",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				checked,
				className: "peer sr-only",
				onChange: (e) => onChange(e.target.checked),
				type: "checkbox"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "h-4 w-7 rounded-full bg-(--ui-bg-quaternary) after:absolute after:left-[2px] after:top-[2px] after:size-3 after:rounded-full after:bg-white after:transition-all peer-checked:bg-primary peer-checked:after:translate-x-full" })]
		})]
	});
}
//#endregion
//#region src/app/communications-hub/index.tsx
var TABS = [
	{
		id: "inbox",
		label: "Inbox",
		icon: "inbox"
	},
	{
		id: "conversation",
		label: "Conversation",
		icon: "comment-discussion"
	},
	{
		id: "contacts",
		label: "Contacts",
		icon: "organization"
	},
	{
		id: "scheduler",
		label: "Scheduled",
		icon: "clock"
	},
	{
		id: "ai",
		label: "AI Assistant",
		icon: "robot"
	},
	{
		id: "automation",
		label: "Automation",
		icon: "run-all"
	},
	{
		id: "notifications",
		label: "Notifications",
		icon: "bell"
	},
	{
		id: "activity",
		label: "Activity",
		icon: "history"
	},
	{
		id: "settings",
		label: "Settings",
		icon: "gear"
	}
];
function CommunicationsHub({ setStatusbarItemGroup: _ } = {}) {
	useStore($communications);
	const [activeTab, setActiveTab] = (0, import_react.useState)("inbox");
	const handleSelectConversation = (0, import_react.useCallback)((id) => {
		selectConversation(id);
		setActiveTab("conversation");
	}, []);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex shrink-0 items-center border-b border-(--ui-stroke-tertiary) bg-(--ui-sidebar-surface-background) px-4",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
				className: "mr-6 text-sm font-semibold tracking-tight",
				children: "Communications"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("nav", {
				className: "flex gap-1",
				children: TABS.map((tab) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: `flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs transition-colors duration-200 ${activeTab === tab.id ? "bg-(--ui-row-active-background) text-foreground" : "text-(--ui-text-tertiary) hover:text-foreground"}`,
					onClick: () => setActiveTab(tab.id),
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `codicon codicon-${tab.icon} text-sm` }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: tab.label })]
				}, tab.id))
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "min-h-0 flex-1 overflow-hidden",
			children: [
				activeTab === "inbox" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(InboxView, { onSelectConversation: handleSelectConversation }),
				activeTab === "conversation" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ConversationWorkspace, {}),
				activeTab === "contacts" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ContactsView, { onSelectConversation: handleSelectConversation }),
				activeTab === "scheduler" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SchedulerView, {}),
				activeTab === "ai" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CommsAIAssistant, {}),
				activeTab === "automation" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AutomationBuilder, {}),
				activeTab === "notifications" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(NotificationsView, {}),
				activeTab === "activity" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ActivityLog, {}),
				activeTab === "settings" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CommsSettings, {})
			]
		})]
	});
}
//#endregion
export { CommunicationsHub };

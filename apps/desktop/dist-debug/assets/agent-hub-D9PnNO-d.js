import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { C as Select, D as SelectValue, E as SelectTrigger, La as Button, O as Badge, P as Switch, Qa as atom, Ra as cn, T as SelectItem, Xa as init_nanostores, Ya as useStore, ao as require_jsx_runtime, jt as Textarea, k as Label, ni as Input, oo as require_react, w as SelectContent } from "./index-B_yd1pEX.js";
//#region src/store/agent-hub.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
init_nanostores();
var TEMPLATE_DEFAULTS = {
	coding: {
		description: "Write, review, and debug code across any language",
		systemPrompt: "You are a coding agent. Write clean, efficient, well-tested code. Review for bugs and security issues. Debug systematically.",
		tools: {
			fileSystem: true,
			git: true,
			shell: true,
			codeEditing: true,
			search: true
		},
		permissions: {
			internetAccess: true,
			filesystemAccess: true,
			terminalAccess: true
		}
	},
	research: {
		description: "Deep research across web sources with citation tracking",
		systemPrompt: "You are a research agent. Gather information from multiple sources, verify facts, and provide cited summaries.",
		tools: {
			browser: true,
			search: true,
			fileSystem: true
		},
		permissions: { internetAccess: true }
	},
	writing: {
		description: "Create and edit content with style and clarity",
		systemPrompt: "You are a writing agent. Help users create, edit, and refine written content with attention to tone, clarity, and structure.",
		tools: {
			fileSystem: true,
			search: true
		},
		permissions: { internetAccess: true }
	},
	automation: {
		description: "Automate repetitive tasks and workflows",
		systemPrompt: "You are an automation agent. Design and execute automated workflows, monitor their health, and handle failures gracefully.",
		tools: {
			shell: true,
			fileSystem: true,
			python: true,
			plugins: true
		},
		permissions: {
			internetAccess: true,
			filesystemAccess: true,
			terminalAccess: true
		}
	},
	"data-analyst": {
		description: "Analyze data, build charts, and derive insights",
		systemPrompt: "You are a data analyst. Analyze datasets, create visualizations, and provide data-driven insights.",
		tools: {
			python: true,
			fileSystem: true,
			search: true
		},
		permissions: {
			internetAccess: true,
			filesystemAccess: true
		}
	},
	devops: {
		description: "Manage infrastructure, deployments, and monitoring",
		systemPrompt: "You are a DevOps agent. Manage infrastructure, orchestrate deployments, monitor systems, and respond to incidents.",
		tools: {
			shell: true,
			git: true,
			fileSystem: true,
			plugins: true
		},
		permissions: {
			internetAccess: true,
			filesystemAccess: true,
			terminalAccess: true
		}
	},
	browser: {
		description: "Automate web browsing and data extraction",
		systemPrompt: "You are a browser agent. Navigate websites, extract data, fill forms, and automate web tasks.",
		tools: {
			browser: true,
			fileSystem: true
		},
		permissions: { internetAccess: true }
	},
	"file-manager": {
		description: "Organize, search, and manage files and directories",
		systemPrompt: "You are a file management agent. Organize files, search directories, manage storage, and maintain file systems.",
		tools: {
			fileSystem: true,
			search: true
		},
		permissions: { filesystemAccess: true }
	},
	support: {
		description: "Handle customer inquiries and support tickets",
		systemPrompt: "You are a customer support agent. Handle inquiries professionally, escalate when needed, and maintain conversation history.",
		tools: {
			search: true,
			fileSystem: true
		},
		permissions: { internetAccess: true }
	},
	assistant: {
		description: "General-purpose personal assistant for daily tasks",
		systemPrompt: "You are a personal assistant. Help with scheduling, information lookup, task management, and general questions.",
		tools: {
			search: true,
			browser: true,
			fileSystem: true
		},
		permissions: { internetAccess: true }
	},
	"social-media": {
		description: "Manage social media content and engagement",
		systemPrompt: "You are a social media agent. Create content, schedule posts, monitor engagement, and manage multiple platforms.",
		tools: {
			browser: true,
			search: true,
			plugins: true
		},
		permissions: { internetAccess: true }
	},
	email: {
		description: "Draft, organize, and manage email communications",
		systemPrompt: "You are an email assistant. Draft responses, organize inbox, manage filters, and handle email workflows.",
		tools: {
			search: true,
			fileSystem: true
		},
		permissions: { internetAccess: true }
	},
	knowledge: {
		description: "Build and maintain a searchable knowledge base",
		systemPrompt: "You are a knowledge agent. Collect, organize, and surface information from your knowledge base and external sources.",
		tools: {
			search: true,
			fileSystem: true,
			browser: true
		},
		permissions: {
			internetAccess: true,
			filesystemAccess: true
		}
	},
	voice: {
		description: "Process voice commands and audio input",
		systemPrompt: "You are a voice agent. Process spoken commands, transcribe audio, and respond with natural speech.",
		tools: {
			search: true,
			fileSystem: true,
			plugins: true
		},
		permissions: { internetAccess: true }
	},
	vision: {
		description: "Analyze images, screenshots, and visual data",
		systemPrompt: "You are a vision agent. Analyze images, extract text from screenshots, describe visual content, and process visual data.",
		tools: {
			fileSystem: true,
			search: true,
			python: true
		},
		permissions: {
			internetAccess: true,
			filesystemAccess: true
		}
	},
	custom: {
		description: "Fully customizable agent with your own configuration",
		systemPrompt: "You are a custom agent configured for specific tasks. Follow the instructions provided in your configuration.",
		tools: {
			fileSystem: true,
			search: true,
			shell: true
		},
		permissions: {
			internetAccess: true,
			filesystemAccess: true
		}
	}
};
var TEMPLATE_LABELS = {
	coding: "Coding Agent",
	research: "Research Agent",
	writing: "Writing Agent",
	automation: "Automation Agent",
	"data-analyst": "Data Analyst",
	devops: "DevOps Agent",
	browser: "Browser Agent",
	"file-manager": "File Manager",
	support: "Customer Support",
	assistant: "Personal Assistant",
	"social-media": "Social Media Manager",
	email: "Email Assistant",
	knowledge: "Knowledge Assistant",
	voice: "Voice Assistant",
	vision: "Vision Agent",
	custom: "Custom Agent"
};
function createDefaultAgent(template) {
	const t = TEMPLATE_DEFAULTS[template];
	const now = (/* @__PURE__ */ new Date()).toISOString();
	return {
		id: `agent-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
		name: TEMPLATE_LABELS[template],
		description: t.description,
		template,
		avatar: template.charAt(0).toUpperCase(),
		systemPrompt: t.systemPrompt,
		status: "created",
		createdAt: now,
		updatedAt: now,
		lastRunAt: null,
		runCount: 0,
		model: {
			provider: "",
			model: "",
			fallbackModel: null,
			temperature: .7,
			maxTokens: 4096,
			reasoningLevel: "off"
		},
		memory: {
			workingMemory: true,
			longTermMemory: true,
			knowledgeBase: false,
			conversationHistory: true,
			projectMemory: false
		},
		permissions: {
			internetAccess: t.permissions.internetAccess ?? false,
			filesystemAccess: t.permissions.filesystemAccess ?? false,
			terminalAccess: t.permissions.terminalAccess ?? false,
			browserAccess: t.permissions.browserAccess ?? false,
			pluginAccess: false,
			sandbox: true,
			executionLimit: 100,
			workspaceScope: "agent"
		},
		tools: {
			fileSystem: t.tools.fileSystem ?? false,
			browser: t.tools.browser ?? false,
			git: t.tools.git ?? false,
			shell: t.tools.shell ?? false,
			python: t.tools.python ?? false,
			search: t.tools.search ?? false,
			codeEditing: t.tools.codeEditing ?? false,
			mcpTools: false,
			plugins: t.tools.plugins ?? false,
			customTools: []
		},
		workspace: {
			path: "",
			isolated: true,
			maxStorageMb: 500
		}
	};
}
var $agentHub = /* @__PURE__ */ atom({
	agents: [
		createDefaultAgent("coding"),
		createDefaultAgent("research"),
		createDefaultAgent("assistant")
	].map((a, i) => ({
		...a,
		name: `${a.name} ${i + 1}`,
		status: "stopped"
	})),
	workflows: [],
	automations: [],
	tasks: [],
	selectedAgentId: null,
	selectedWorkflowId: null,
	editingAgent: null,
	searchQuery: "",
	filterStatus: "all",
	filterTemplate: "all"
});
var patch = (update) => $agentHub.set({
	...$agentHub.get(),
	...update
});
function setSearchQuery(query) {
	patch({ searchQuery: query });
}
function setFilterStatus(status) {
	patch({ filterStatus: status });
}
function setFilterTemplate(tpl) {
	patch({ filterTemplate: tpl });
}
function createAgent(template) {
	const agent = createDefaultAgent(template);
	patch({
		agents: [...$agentHub.get().agents, agent],
		selectedAgentId: agent.id
	});
	return agent;
}
function duplicateAgent(id) {
	const original = $agentHub.get().agents.find((a) => a.id === id);
	if (!original) return null;
	const now = (/* @__PURE__ */ new Date()).toISOString();
	const copy = {
		...original,
		id: `agent-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
		name: `${original.name} (copy)`,
		status: "created",
		createdAt: now,
		updatedAt: now,
		lastRunAt: null,
		runCount: 0
	};
	patch({ agents: [...$agentHub.get().agents, copy] });
	return copy;
}
function deleteAgent(id) {
	const state = $agentHub.get();
	patch({
		agents: state.agents.filter((a) => a.id !== id),
		selectedAgentId: state.selectedAgentId === id ? null : state.selectedAgentId
	});
}
function updateAgent(id, update) {
	patch({ agents: $agentHub.get().agents.map((a) => a.id === id ? {
		...a,
		...update,
		updatedAt: (/* @__PURE__ */ new Date()).toISOString()
	} : a) });
}
function setAgentStatus(id, status) {
	updateAgent(id, { status });
}
function setEditingAgent(agent) {
	patch({ editingAgent: agent });
}
function saveAgentConfig(config) {
	patch({
		agents: $agentHub.get().agents.map((a) => a.id === config.id ? {
			...config,
			updatedAt: (/* @__PURE__ */ new Date()).toISOString()
		} : a),
		editingAgent: null
	});
}
var WORKFLOW_AGENTS = [
	{
		role: "coordinator",
		label: "Coordinator",
		description: "Orchestrates the overall workflow"
	},
	{
		role: "planner",
		label: "Planner",
		description: "Creates execution plans"
	},
	{
		role: "executor",
		label: "Executor",
		description: "Carries out tasks"
	},
	{
		role: "reviewer",
		label: "Reviewer",
		description: "Reviews outputs for quality"
	},
	{
		role: "critic",
		label: "Critic",
		description: "Provides critical feedback"
	},
	{
		role: "researcher",
		label: "Researcher",
		description: "Gathers information"
	},
	{
		role: "coder",
		label: "Coder",
		description: "Writes and edits code"
	},
	{
		role: "manager",
		label: "Manager",
		description: "Manages sub-agent delegation"
	}
];
function getWorkflowAgentRoles() {
	return WORKFLOW_AGENTS;
}
function createWorkflow(name, type) {
	const now = (/* @__PURE__ */ new Date()).toISOString();
	const workflow = {
		id: `workflow-${Date.now()}`,
		name,
		description: "",
		type,
		agents: [],
		steps: [],
		enabled: false,
		createdAt: now,
		updatedAt: now
	};
	patch({ workflows: [...$agentHub.get().workflows, workflow] });
	return workflow;
}
function updateWorkflow(id, update) {
	patch({ workflows: $agentHub.get().workflows.map((w) => w.id === id ? {
		...w,
		...update,
		updatedAt: (/* @__PURE__ */ new Date()).toISOString()
	} : w) });
}
function deleteWorkflow(id) {
	patch({ workflows: $agentHub.get().workflows.filter((w) => w.id !== id) });
}
function addWorkflowAgent(workflowId, role, agentId) {
	const workflow = $agentHub.get().workflows.find((w) => w.id === workflowId);
	if (!workflow) return;
	const entry = {
		agentId,
		role,
		order: workflow.agents.length
	};
	updateWorkflow(workflowId, { agents: [...workflow.agents, entry] });
}
function removeWorkflowAgent(workflowId, agentId) {
	const workflow = $agentHub.get().workflows.find((w) => w.id === workflowId);
	if (!workflow) return;
	updateWorkflow(workflowId, { agents: workflow.agents.filter((a) => a.agentId !== agentId) });
}
function createAutomation(name, trigger) {
	const now = (/* @__PURE__ */ new Date()).toISOString();
	const rule = {
		id: `auto-${Date.now()}`,
		name,
		description: "",
		trigger,
		triggerConfig: {},
		workflowId: null,
		enabled: false,
		createdAt: now,
		lastTriggeredAt: null
	};
	patch({ automations: [...$agentHub.get().automations, rule] });
	return rule;
}
function updateAutomation(id, update) {
	patch({ automations: $agentHub.get().automations.map((a) => a.id === id ? {
		...a,
		...update
	} : a) });
}
function deleteAutomation(id) {
	patch({ automations: $agentHub.get().automations.filter((a) => a.id !== id) });
}
function updateTask(id, update) {
	patch({ tasks: $agentHub.get().tasks.map((t) => t.id === id ? {
		...t,
		...update
	} : t) });
}
//#endregion
//#region src/app/agent-hub/agent-config.tsx
var import_jsx_runtime = require_jsx_runtime();
var MODEL_PROVIDERS = [
	{
		slug: "",
		name: "Auto (use default)"
	},
	{
		slug: "openai",
		name: "OpenAI"
	},
	{
		slug: "anthropic",
		name: "Anthropic"
	},
	{
		slug: "gemini",
		name: "Google Gemini"
	},
	{
		slug: "openrouter",
		name: "OpenRouter"
	},
	{
		slug: "deepseek",
		name: "DeepSeek"
	},
	{
		slug: "mistral",
		name: "Mistral"
	},
	{
		slug: "groq",
		name: "Groq"
	},
	{
		slug: "ollama",
		name: "Ollama"
	},
	{
		slug: "local",
		name: "Local"
	}
];
var MODELS_BY_PROVIDER = {
	"": [],
	openai: [
		"gpt-4o",
		"gpt-4o-mini",
		"gpt-4-turbo",
		"gpt-3.5-turbo"
	],
	anthropic: [
		"claude-sonnet-4",
		"claude-haiku-3.5",
		"claude-opus-4"
	],
	gemini: [
		"gemini-2.5-pro",
		"gemini-2.5-flash",
		"gemini-2.0-flash"
	],
	openrouter: ["auto"],
	deepseek: ["deepseek-chat", "deepseek-reasoner"],
	mistral: [
		"mistral-large",
		"mistral-medium",
		"mistral-small"
	],
	groq: [
		"mixtral-8x7b",
		"llama3-70b",
		"llama3-8b"
	],
	ollama: [
		"llama3",
		"mistral",
		"codellama",
		"mixtral"
	],
	local: ["custom-model"]
};
function AgentConfigPanel({ agent, onBack }) {
	const [config, setConfig] = (0, import_react.useState)({ ...agent });
	const [activeSection, setActiveSection] = (0, import_react.useState)("general");
	const update = (update) => setConfig({
		...config,
		...update
	});
	const providerModels = MODELS_BY_PROVIDER[config.model.provider] || [];
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col overflow-hidden",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
			className: "flex shrink-0 items-center gap-3 border-b px-6 py-3",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					className: "text-muted-foreground hover:text-foreground",
					onClick: onBack,
					type: "button",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
						className: "h-5 w-5",
						fill: "none",
						stroke: "currentColor",
						strokeWidth: 2,
						viewBox: "0 0 24 24",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M19 12H5M12 19l-7-7 7-7" })
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex-1",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "font-semibold",
						children: config.name
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "text-xs text-muted-foreground",
						children: [
							TEMPLATE_LABELS[config.template],
							" · ",
							config.status
						]
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: onBack,
					size: "sm",
					variant: "outline",
					children: "Cancel"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => {
						saveAgentConfig(config);
						onBack();
					},
					size: "sm",
					children: "Save"
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex flex-1 overflow-hidden",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("nav", {
				className: "w-44 shrink-0 space-y-1 border-r p-3",
				children: [
					{
						id: "general",
						label: "General"
					},
					{
						id: "prompt",
						label: "System Prompt"
					},
					{
						id: "model",
						label: "Model"
					},
					{
						id: "memory",
						label: "Memory"
					},
					{
						id: "tools",
						label: "Tools"
					},
					{
						id: "permissions",
						label: "Permissions"
					},
					{
						id: "workspace",
						label: "Workspace"
					}
				].map((s) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					className: cn("w-full rounded-lg px-3 py-2 text-left text-sm transition-colors", activeSection === s.id ? "bg-accent font-medium" : "text-muted-foreground hover:bg-accent/50"),
					onClick: () => setActiveSection(s.id),
					type: "button",
					children: s.label
				}, s.id))
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex-1 overflow-y-auto p-6",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mx-auto max-w-2xl space-y-6",
					children: [
						activeSection === "general" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-4",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
									className: "text-sm font-medium text-muted-foreground uppercase tracking-wider",
									children: "General"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "space-y-2",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Name" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
										onChange: (e) => update({ name: e.target.value }),
										value: config.name
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "space-y-2",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Description" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
										onChange: (e) => update({ description: e.target.value }),
										value: config.description
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "space-y-2",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Type" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
										onValueChange: (v) => update({ template: v }),
										value: config.template,
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {}) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: Object.entries(TEMPLATE_LABELS).map(([key, label]) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
											value: key,
											children: label
										}, key)) })]
									})]
								})
							]
						}),
						activeSection === "prompt" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "text-sm font-medium text-muted-foreground uppercase tracking-wider",
								children: "System Prompt"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "System Prompt" }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-xs text-muted-foreground",
										children: "Defines the agent's behavior, personality, and constraints"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
										className: "font-mono text-sm resize-none",
										onChange: (e) => update({ systemPrompt: e.target.value }),
										rows: 12,
										value: config.systemPrompt
									})
								]
							})]
						}),
						activeSection === "model" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "text-sm font-medium text-muted-foreground uppercase tracking-wider",
								children: "Model Configuration"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "grid grid-cols-2 gap-4",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "space-y-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Provider" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
											onValueChange: (v) => update({ model: {
												...config.model,
												provider: v,
												model: ""
											} }),
											value: config.model.provider,
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: "Select provider" }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: MODEL_PROVIDERS.map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
												value: p.slug,
												children: p.name
											}, p.slug)) })]
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "space-y-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Model" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
											onValueChange: (v) => update({ model: {
												...config.model,
												model: v
											} }),
											value: config.model.model,
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: config.model.provider ? "Select model" : "Select provider first" }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: providerModels.map((m) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
												value: m,
												children: m
											}, m)) })]
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "space-y-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Fallback Model" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
											onValueChange: (v) => update({ model: {
												...config.model,
												fallbackModel: v || null
											} }),
											value: config.model.fallbackModel ?? "",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: "None" }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: providerModels.map((m) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
												value: m,
												children: m
											}, m)) })]
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "space-y-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Reasoning Level" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
											onValueChange: (v) => update({ model: {
												...config.model,
												reasoningLevel: v
											} }),
											value: config.model.reasoningLevel,
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {}) }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [
												/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
													value: "off",
													children: "Off"
												}),
												/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
													value: "low",
													children: "Low"
												}),
												/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
													value: "medium",
													children: "Medium"
												}),
												/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
													value: "high",
													children: "High"
												})
											] })]
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "space-y-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Temperature" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
											className: "font-mono",
											max: 2,
											min: 0,
											onChange: (e) => update({ model: {
												...config.model,
												temperature: parseFloat(e.target.value) || .7
											} }),
											step: .1,
											type: "number",
											value: config.model.temperature
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "space-y-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Max Tokens" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
											className: "font-mono",
											max: 128e3,
											min: 256,
											onChange: (e) => update({ model: {
												...config.model,
												maxTokens: parseInt(e.target.value) || 4096
											} }),
											step: 256,
											type: "number",
											value: config.model.maxTokens
										})]
									})
								]
							})]
						}),
						activeSection === "memory" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "text-sm font-medium text-muted-foreground uppercase tracking-wider",
								children: "Memory"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "space-y-3",
								children: [
									[
										"workingMemory",
										"Working Memory",
										"Retain context during active conversations"
									],
									[
										"longTermMemory",
										"Long-term Memory",
										"Remember information across sessions"
									],
									[
										"knowledgeBase",
										"Knowledge Base",
										"Build and query a searchable knowledge base"
									],
									[
										"conversationHistory",
										"Conversation History",
										"Store and reference past conversations"
									],
									[
										"projectMemory",
										"Project Memory",
										"Maintain project-specific context"
									]
								].map(([key, label, desc]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center justify-between rounded-lg border p-4",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, {
										className: "text-base",
										children: label
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-sm text-muted-foreground",
										children: desc
									})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
										checked: config.memory[key],
										onCheckedChange: (v) => update({ memory: {
											...config.memory,
											[key]: v
										} })
									})]
								}, key))
							})]
						}),
						activeSection === "tools" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-4",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
									className: "text-sm font-medium text-muted-foreground uppercase tracking-wider",
									children: "Allowed Tools"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "grid grid-cols-2 gap-3",
									children: [
										["fileSystem", "File System"],
										["browser", "Browser"],
										["git", "Git"],
										["shell", "Shell"],
										["python", "Python"],
										["search", "Search"],
										["codeEditing", "Code Editing"],
										["mcpTools", "MCP Tools"],
										["plugins", "Plugins"]
									].map(([key, label]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center justify-between rounded-lg border p-3",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, {
											className: "text-sm",
											children: label
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
											checked: config.tools[key],
											onCheckedChange: (v) => update({ tools: {
												...config.tools,
												[key]: v
											} })
										})]
									}, key))
								}),
								config.tools.customTools.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "flex flex-wrap gap-2",
									children: config.tools.customTools.map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										variant: "secondary",
										children: t
									}, t))
								})
							]
						}),
						activeSection === "permissions" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-4",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "text-sm font-medium text-muted-foreground uppercase tracking-wider",
								children: "Permissions"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-3",
								children: [[
									[
										"internetAccess",
										"Internet Access",
										"Allow network requests and API calls"
									],
									[
										"filesystemAccess",
										"Filesystem Access",
										"Allow reading and writing files"
									],
									[
										"terminalAccess",
										"Terminal Access",
										"Allow executing shell commands"
									],
									[
										"browserAccess",
										"Browser Access",
										"Allow automated web browsing"
									],
									[
										"pluginAccess",
										"Plugin Access",
										"Allow loading and using plugins"
									],
									[
										"sandbox",
										"Sandbox",
										"Run in isolated sandbox environment"
									]
								].map(([key, label, desc]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center justify-between rounded-lg border p-4",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, {
										className: "text-base",
										children: label
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-sm text-muted-foreground",
										children: desc
									})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
										checked: config.permissions[key],
										onCheckedChange: (v) => update({ permissions: {
											...config.permissions,
											[key]: v
										} })
									})]
								}, key)), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "space-y-2 pt-2",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Execution Limit (calls per run)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
										className: "font-mono max-w-[200px]",
										max: 1e3,
										min: 1,
										onChange: (e) => update({ permissions: {
											...config.permissions,
											executionLimit: parseInt(e.target.value) || 100
										} }),
										type: "number",
										value: config.permissions.executionLimit
									})]
								})]
							})]
						}),
						activeSection === "workspace" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-4",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
									className: "text-sm font-medium text-muted-foreground uppercase tracking-wider",
									children: "Workspace"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "space-y-2",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Workspace Path" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
										className: "font-mono text-sm",
										onChange: (e) => update({ workspace: {
											...config.workspace,
											path: e.target.value
										} }),
										placeholder: "~/aetheros/agents/my-agent",
										value: config.workspace.path
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center justify-between rounded-lg border p-4",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, {
										className: "text-base",
										children: "Isolated Workspace"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-sm text-muted-foreground",
										children: "Keep agent files separate from other agents"
									})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
										checked: config.workspace.isolated,
										onCheckedChange: (v) => update({ workspace: {
											...config.workspace,
											isolated: v
										} })
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "space-y-2",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Max Storage (MB)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
										className: "font-mono max-w-[200px]",
										onChange: (e) => update({ workspace: {
											...config.workspace,
											maxStorageMb: parseInt(e.target.value) || 500
										} }),
										type: "number",
										value: config.workspace.maxStorageMb
									})]
								})
							]
						})
					]
				})
			})]
		})]
	});
}
//#endregion
//#region src/app/agent-hub/agent-list.tsx
var STATUS_GLYPH = {
	running: {
		color: "bg-green-500",
		label: "Running"
	},
	stopped: {
		color: "bg-gray-400",
		label: "Stopped"
	},
	paused: {
		color: "bg-yellow-500",
		label: "Paused"
	},
	error: {
		color: "bg-red-500",
		label: "Error"
	},
	created: {
		color: "bg-blue-400",
		label: "Created"
	}
};
var TEMPLATES = Object.entries(TEMPLATE_LABELS);
var TEMPLATE_ICONS = {
	coding: "</>",
	research: "🔍",
	writing: "✎",
	automation: "⚡",
	"data-analyst": "📊",
	devops: "🔧",
	browser: "🌐",
	"file-manager": "📁",
	support: "💬",
	assistant: "👤",
	"social-media": "📱",
	email: "📧",
	knowledge: "📚",
	voice: "🎤",
	vision: "👁",
	custom: "✦"
};
function AgentList() {
	const state = useStore($agentHub);
	const [showCreate, setShowCreate] = (0, import_react.useState)(false);
	const filtered = (0, import_react.useMemo)(() => {
		let list = state.agents;
		if (state.searchQuery) {
			const q = state.searchQuery.toLowerCase();
			list = list.filter((a) => a.name.toLowerCase().includes(q) || a.description.toLowerCase().includes(q));
		}
		if (state.filterStatus !== "all") list = list.filter((a) => a.status === state.filterStatus);
		if (state.filterTemplate !== "all") list = list.filter((a) => a.template === state.filterTemplate);
		return list;
	}, [
		state.agents,
		state.searchQuery,
		state.filterStatus,
		state.filterTemplate
	]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-1 flex-col overflow-hidden",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex shrink-0 items-center gap-3 border-b px-6 py-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						className: "max-w-xs font-mono text-sm",
						onChange: (e) => setSearchQuery(e.target.value),
						placeholder: "Search agents...",
						value: state.searchQuery
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
						onValueChange: (v) => setFilterStatus(v),
						value: state.filterStatus,
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
							className: "w-32",
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
								value: "paused",
								children: "Paused"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
								value: "error",
								children: "Error"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
								value: "created",
								children: "Created"
							})
						] })]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
						onValueChange: (v) => setFilterTemplate(v),
						value: state.filterTemplate,
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
							className: "w-36",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
							value: "all",
							children: "All Types"
						}), TEMPLATES.map(([key, label]) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
							value: key,
							children: label
						}, key))] })]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "ml-auto flex gap-2",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => setShowCreate(!showCreate),
							size: "sm",
							variant: "default",
							children: "Create Agent"
						})
					})
				]
			}),
			showCreate && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid grid-cols-4 gap-2 border-b p-4",
				children: TEMPLATES.map(([key, label]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: "flex items-center gap-3 rounded-lg border p-3 text-left text-sm transition-all hover:border-primary/50 hover:bg-accent",
					onClick: () => {
						createAgent(key);
						setShowCreate(false);
					},
					type: "button",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-lg",
						children: TEMPLATE_ICONS[key] || "✦"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "font-medium",
						children: label
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "text-xs text-muted-foreground truncate",
						children: TEMPLATE_DEFAULTS[key].description
					})] })]
				}, key))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex-1 overflow-y-auto p-4",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "space-y-2",
					children: filtered.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "py-12 text-center text-sm text-muted-foreground",
						children: "No agents found. Create one to get started."
					}) : filtered.map((agent) => {
						const glyph = STATUS_GLYPH[agent.status] || STATUS_GLYPH.created;
						return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-4 rounded-xl border p-4 transition-all hover:bg-accent/30",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: cn("flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 ring-1 ring-primary/10 text-sm font-bold"),
									children: TEMPLATE_ICONS[agent.template] || agent.avatar
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "min-w-0 flex-1",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-2",
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "font-medium truncate",
												children: agent.name
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("h-2 w-2 rounded-full", glyph.color) }),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "text-xs text-muted-foreground",
												children: glyph.label
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
												className: "text-[10px] h-5",
												variant: "outline",
												children: TEMPLATE_LABELS[agent.template]
											})
										]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
										className: "text-xs text-muted-foreground truncate mt-0.5",
										children: [
											agent.description,
											" · ",
											agent.runCount,
											" runs · Last: ",
											agent.lastRunAt ? new Date(agent.lastRunAt).toLocaleDateString() : "Never"
										]
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-1",
									children: [
										agent.status === "running" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
											onClick: () => setAgentStatus(agent.id, "stopped"),
											size: "sm",
											variant: "outline",
											children: "Stop"
										}) : agent.status === "paused" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
											onClick: () => setAgentStatus(agent.id, "running"),
											size: "sm",
											variant: "outline",
											children: "Resume"
										}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
											className: "bg-green-600 hover:bg-green-700",
											onClick: () => setAgentStatus(agent.id, "running"),
											size: "sm",
											variant: "default",
											children: "Run"
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
											onClick: () => setEditingAgent(agent),
											size: "sm",
											variant: "ghost",
											children: "Config"
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
											onClick: () => duplicateAgent(agent.id),
											size: "sm",
											title: "Duplicate",
											variant: "ghost",
											children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("svg", {
												className: "h-4 w-4",
												fill: "none",
												stroke: "currentColor",
												strokeWidth: 2,
												viewBox: "0 0 24 24",
												children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
													height: "13",
													rx: "2",
													width: "13",
													x: "9",
													y: "9"
												}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" })]
											})
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
											className: "text-destructive hover:text-destructive",
											onClick: () => deleteAgent(agent.id),
											size: "sm",
											variant: "ghost",
											children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
												className: "h-4 w-4",
												fill: "none",
												stroke: "currentColor",
												strokeWidth: 2,
												viewBox: "0 0 24 24",
												children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" })
											})
										})
									]
								})
							]
						}, agent.id);
					})
				})
			})
		]
	});
}
//#endregion
//#region src/app/agent-hub/automation-builder.tsx
var TRIGGER_LABELS = {
	manual: "Manual",
	schedule: "Schedule",
	"file-change": "File Change",
	webhook: "Webhook",
	"git-commit": "Git Commit",
	email: "Email",
	startup: "Startup",
	shutdown: "Shutdown"
};
var TRIGGER_ICONS = {
	manual: "▶",
	schedule: "⏰",
	"file-change": "📁",
	webhook: "🔗",
	"git-commit": "📝",
	email: "📧",
	startup: "🟢",
	shutdown: "🔴"
};
var TRIGGER_DESCS = {
	manual: "Triggered manually by the user",
	schedule: "Runs on a cron schedule",
	"file-change": "Triggers when files are created or modified",
	webhook: "Triggered by an incoming webhook",
	"git-commit": "Runs on new git commits",
	email: "Triggered by incoming email",
	startup: "Runs when AetherOS starts",
	shutdown: "Runs when AetherOS shuts down"
};
function AutomationBuilder() {
	const state = useStore($agentHub);
	const [creating, setCreating] = (0, import_react.useState)(false);
	const [newName, setNewName] = (0, import_react.useState)("");
	const [newTrigger, setNewTrigger] = (0, import_react.useState)("manual");
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-1 flex-col overflow-hidden",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between border-b px-6 py-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-lg font-semibold",
					children: "Automation"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm text-muted-foreground",
					children: "Trigger agents and workflows automatically"
				})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => setCreating(true),
					size: "sm",
					children: "New Rule"
				})]
			}),
			creating && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "border-b p-4",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mx-auto max-w-lg space-y-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "font-medium",
							children: "Create Automation Rule"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "grid grid-cols-4 gap-3",
							children: Object.entries(TRIGGER_LABELS).map(([key, label]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: cn("flex flex-col items-center gap-1 rounded-lg border p-3 text-sm transition-all", newTrigger === key ? "border-primary/50 bg-primary/5" : ""),
								onClick: () => setNewTrigger(key),
								type: "button",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-lg",
										children: TRIGGER_ICONS[key]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-xs font-medium",
										children: label
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-[10px] text-muted-foreground text-center",
										children: TRIGGER_DESCS[key]
									})
								]
							}, key))
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex justify-end gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => setCreating(false),
								variant: "outline",
								children: "Cancel"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => {
									if (newName.trim()) {
										createAutomation(newName.trim(), newTrigger);
										setCreating(false);
										setNewName("");
									}
								},
								children: "Create"
							})]
						})
					]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex-1 overflow-y-auto p-6",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "mx-auto max-w-3xl space-y-3",
					children: state.automations.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "py-12 text-center text-sm text-muted-foreground",
						children: "No automation rules yet. Create one to automate your workflows."
					}) : state.automations.map((rule) => {
						const linkedWorkflow = state.workflows.find((w) => w.id === rule.workflowId);
						return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-4 rounded-xl border p-4 transition-all hover:bg-accent/30",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 ring-1 ring-primary/10 text-lg",
									children: TRIGGER_ICONS[rule.trigger]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex-1 min-w-0",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-2",
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "font-medium truncate",
												children: rule.name
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
												className: "text-[10px] h-5",
												variant: "outline",
												children: TRIGGER_LABELS[rule.trigger]
											}),
											linkedWorkflow && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
												className: "text-[10px] h-5",
												variant: "secondary",
												children: linkedWorkflow.name
											})
										]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
										className: "text-xs text-muted-foreground mt-0.5",
										children: [TRIGGER_DESCS[rule.trigger], rule.lastTriggeredAt && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [" · Last triggered: ", new Date(rule.lastTriggeredAt).toLocaleString()] })]
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-2",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
											onValueChange: (v) => updateAutomation(rule.id, { workflowId: v || null }),
											value: rule.workflowId ?? "",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
												className: "w-36",
												children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: "Link workflow" })
											}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
												value: "",
												children: "None"
											}), state.workflows.map((w) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
												value: w.id,
												children: w.name
											}, w.id))] })]
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
											checked: rule.enabled,
											onCheckedChange: (v) => updateAutomation(rule.id, { enabled: v })
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
											className: "text-destructive",
											onClick: () => deleteAutomation(rule.id),
											size: "sm",
											variant: "ghost",
											children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
												className: "h-4 w-4",
												fill: "none",
												stroke: "currentColor",
												strokeWidth: 2,
												viewBox: "0 0 24 24",
												children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" })
											})
										})
									]
								})
							]
						}, rule.id);
					})
				})
			})
		]
	});
}
//#endregion
//#region src/app/agent-hub/marketplace.tsx
var AGENT_TEMPLATES = [
	{
		name: "Code Reviewer Pro",
		category: "coding",
		downloads: "45K",
		rating: 4.8,
		author: "AetherOS Labs",
		description: "Automated code review with inline suggestions and best practice checks."
	},
	{
		name: "Web Scraper",
		category: "automation",
		downloads: "32K",
		rating: 4.6,
		author: "DataWorks",
		description: "Extract and structure data from any website."
	},
	{
		name: "GitHub PR Manager",
		category: "devops",
		downloads: "28K",
		rating: 4.7,
		author: "DevOps Inc",
		description: "Automate PR review, merge, and release workflows."
	},
	{
		name: "Content Writer Pro",
		category: "writing",
		downloads: "25K",
		rating: 4.5,
		author: "ContentLab",
		description: "Generate blog posts, articles, and social media content."
	},
	{
		name: "Database Analyst",
		category: "data-analyst",
		downloads: "18K",
		rating: 4.4,
		author: "DataViz",
		description: "Query, analyze, and visualize database data."
	},
	{
		name: "Crypto Trader",
		category: "automation",
		downloads: "15K",
		rating: 4.2,
		author: "FinTech AI",
		description: "Monitor markets and execute trades based on strategies."
	},
	{
		name: "Docker Manager",
		category: "devops",
		downloads: "14K",
		rating: 4.6,
		author: "InfraAI",
		description: "Manage Docker containers, images, and compose files."
	},
	{
		name: "Research Assistant Pro",
		category: "research",
		downloads: "12K",
		rating: 4.7,
		author: "ScholarAI",
		description: "Deep research with citation management and paper summaries."
	}
];
var WORKFLOW_TEMPLATES = [
	{
		name: "Code Review Pipeline",
		type: "sequential",
		downloads: "22K",
		description: "Write → Review → Refactor → Merge pipeline"
	},
	{
		name: "Research & Write",
		type: "coordinator",
		downloads: "18K",
		description: "Researcher gathers data, Writer produces content"
	},
	{
		name: "Data Pipeline",
		type: "parallel",
		downloads: "14K",
		description: "Parallel data collection from multiple sources"
	},
	{
		name: "DevOps Deploy",
		type: "sequential",
		downloads: "11K",
		description: "Build → Test → Deploy → Monitor pipeline"
	}
];
var CATEGORIES = [
	{
		id: "all",
		label: "All"
	},
	{
		id: "coding",
		label: "Coding"
	},
	{
		id: "automation",
		label: "Automation"
	},
	{
		id: "devops",
		label: "DevOps"
	},
	{
		id: "research",
		label: "Research"
	},
	{
		id: "writing",
		label: "Writing"
	},
	{
		id: "data-analyst",
		label: "Data"
	}
];
function Marketplace() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-1 flex-col overflow-hidden",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "border-b px-6 py-4",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-lg font-semibold",
				children: "Marketplace"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-muted-foreground",
				children: "Discover agent templates, workflows, and automation packs"
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex-1 overflow-y-auto p-6",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mx-auto max-w-5xl space-y-10",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-4",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center justify-between",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "text-sm font-medium text-muted-foreground uppercase tracking-wider",
								children: "Featured Agent Templates"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "flex gap-1",
								children: CATEGORIES.map((cat) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: cn("rounded-full px-3 py-1 text-xs font-medium transition-colors", cat.id === "all" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-accent"),
									type: "button",
									children: cat.label
								}, cat.id))
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "grid grid-cols-4 gap-4",
							children: AGENT_TEMPLATES.map((tmpl) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "group relative rounded-xl border p-4 transition-all hover:border-primary/30 hover:shadow-sm",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "mb-3 flex items-start justify-between",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
											className: "text-[10px] capitalize",
											variant: "outline",
											children: tmpl.category
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "flex items-center gap-1 text-xs text-yellow-500",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
												className: "h-3 w-3 fill-current",
												viewBox: "0 0 24 24",
												children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" })
											}), tmpl.rating]
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
										className: "font-medium text-sm",
										children: tmpl.name
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "mt-1 text-xs text-muted-foreground line-clamp-2",
										children: tmpl.description
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "mt-3 flex items-center justify-between",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
											className: "text-xs text-muted-foreground",
											children: [tmpl.downloads, " downloads"]
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
											size: "sm",
											variant: "outline",
											children: "Install"
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "mt-1 text-[10px] text-muted-foreground",
										children: ["by ", tmpl.author]
									})
								]
							}, tmpl.name))
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-4",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "text-sm font-medium text-muted-foreground uppercase tracking-wider",
							children: "Workflow Templates"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "grid grid-cols-4 gap-4",
							children: WORKFLOW_TEMPLATES.map((wf) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "rounded-xl border p-4 transition-all hover:border-primary/30",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "mb-3",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
											className: "text-[10px] capitalize",
											variant: "secondary",
											children: wf.type
										})
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
										className: "font-medium text-sm",
										children: wf.name
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "mt-1 text-xs text-muted-foreground",
										children: wf.description
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "mt-3 flex items-center justify-between",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
											className: "text-xs text-muted-foreground",
											children: [wf.downloads, " downloads"]
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
											size: "sm",
											variant: "outline",
											children: "Install"
										})]
									})
								]
							}, wf.name))
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border bg-gradient-to-br from-primary/5 to-primary/0 p-8 text-center",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "text-lg font-semibold",
								children: "Publish Your Agent"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-2 text-sm text-muted-foreground max-w-md mx-auto",
								children: "Created an amazing agent? Share it with the community on the AetherOS Marketplace."
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								className: "mt-4",
								children: "Submit Agent"
							})
						]
					})
				]
			})
		})]
	});
}
//#endregion
//#region src/app/agent-hub/monitoring-dashboard.tsx
function MonitoringDashboard() {
	const state = useStore($agentHub);
	const stats = (0, import_react.useMemo)(() => {
		const agents = state.agents;
		const tasks = state.tasks;
		return {
			running: agents.filter((a) => a.status === "running").length,
			totalRuns: agents.reduce((s, a) => s + a.runCount, 0),
			totalCost: tasks.reduce((s, t) => s + t.costUsd, 0),
			totalTokens: tasks.reduce((s, t) => s + t.inputTokens + t.outputTokens, 0)
		};
	}, [state.agents, state.tasks]);
	const recentTasks = (0, import_react.useMemo)(() => [...state.tasks].sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime()).slice(0, 8), [state.tasks]);
	const cpuUsage = Math.floor(Math.random() * 40) + 15;
	const ramUsage = Math.floor(Math.random() * 30) + 40;
	const gpuUsage = Math.floor(Math.random() * 50) + 10;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-1 flex-col overflow-hidden",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "border-b px-6 py-4",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-lg font-semibold",
				children: "Monitoring"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-muted-foreground",
				children: "Real-time agent and system monitoring"
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex-1 overflow-y-auto p-6",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mx-auto max-w-5xl space-y-8",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "grid grid-cols-4 gap-4",
						children: [
							{
								label: "Running Agents",
								value: String(stats.running),
								sub: `${state.agents.length} total`,
								color: "text-blue-600"
							},
							{
								label: "Total Runs",
								value: String(stats.totalRuns),
								sub: "all time",
								color: "text-green-600"
							},
							{
								label: "Token Usage",
								value: `${(stats.totalTokens / 1e3).toFixed(0)}K`,
								sub: "all agents",
								color: "text-purple-600"
							},
							{
								label: "Total Cost",
								value: `$${stats.totalCost.toFixed(2)}`,
								sub: "lifetime",
								color: "text-orange-600"
							}
						].map((s) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border p-4",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "text-xs text-muted-foreground",
									children: s.label
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: cn("mt-1 text-2xl font-bold", s.color),
									children: s.value
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "mt-0.5 text-xs text-muted-foreground",
									children: s.sub
								})
							]
						}, s.label))
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid grid-cols-3 gap-4",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "rounded-xl border p-5",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "mb-3 flex items-center justify-between",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
										className: "text-sm font-medium",
										children: "CPU"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: cn("text-sm font-mono", cpuUsage > 80 ? "text-destructive" : cpuUsage > 60 ? "text-yellow-600" : "text-green-600"),
										children: [cpuUsage, "%"]
									})]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "h-2 rounded-full bg-muted overflow-hidden",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: cn("h-full rounded-full transition-all", cpuUsage > 80 ? "bg-destructive" : cpuUsage > 60 ? "bg-yellow-500" : "bg-green-500"),
										style: { width: `${cpuUsage}%` }
									})
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "rounded-xl border p-5",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "mb-3 flex items-center justify-between",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
										className: "text-sm font-medium",
										children: "RAM"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: cn("text-sm font-mono", ramUsage > 80 ? "text-destructive" : ramUsage > 60 ? "text-yellow-600" : "text-green-600"),
										children: [ramUsage, "%"]
									})]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "h-2 rounded-full bg-muted overflow-hidden",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: cn("h-full rounded-full transition-all", ramUsage > 80 ? "bg-destructive" : ramUsage > 60 ? "bg-yellow-500" : "bg-blue-500"),
										style: { width: `${ramUsage}%` }
									})
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "rounded-xl border p-5",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "mb-3 flex items-center justify-between",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
										className: "text-sm font-medium",
										children: "GPU"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: cn("text-sm font-mono", gpuUsage > 80 ? "text-destructive" : gpuUsage > 60 ? "text-yellow-600" : "text-green-600"),
										children: [gpuUsage, "%"]
									})]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "h-2 rounded-full bg-muted overflow-hidden",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: cn("h-full rounded-full transition-all", gpuUsage > 80 ? "bg-destructive" : gpuUsage > 60 ? "bg-yellow-500" : "bg-purple-500"),
										style: { width: `${gpuUsage}%` }
									})
								})]
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border p-5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mb-4 flex items-center justify-between",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "text-sm font-medium text-muted-foreground uppercase tracking-wider",
								children: "Agent Status"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex gap-2 text-xs text-muted-foreground",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "flex items-center gap-1",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "h-2 w-2 rounded-full bg-green-500" }), " Running"]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "flex items-center gap-1",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "h-2 w-2 rounded-full bg-gray-400" }), " Stopped"]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "flex items-center gap-1",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "h-2 w-2 rounded-full bg-red-500" }), " Error"]
									})
								]
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "space-y-2",
							children: state.agents.slice(0, 6).map((agent) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-3 rounded-lg border px-4 py-2.5 text-sm",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("h-2.5 w-2.5 shrink-0 rounded-full", agent.status === "running" ? "bg-green-500" : agent.status === "error" ? "bg-red-500" : "bg-gray-400") }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "flex-1 truncate",
										children: agent.name
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "text-xs text-muted-foreground",
										children: [agent.runCount, " runs"]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-xs text-muted-foreground font-mono",
										children: agent.model.model || "—"
									})
								]
							}, agent.id))
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border p-5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider",
							children: "Recent Task Activity"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "space-y-2",
							children: recentTasks.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-sm text-muted-foreground",
								children: "No recent task activity"
							}) : recentTasks.map((task) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-3 rounded-lg border px-4 py-2.5 text-sm",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("h-2 w-2 shrink-0 rounded-full", task.status === "completed" ? "bg-green-500" : task.status === "failed" ? "bg-red-500" : task.status === "running" ? "bg-blue-500 animate-pulse" : "bg-gray-400") }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "flex-1 truncate",
										children: task.agentName
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-xs text-muted-foreground capitalize",
										children: task.status
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "text-xs text-muted-foreground font-mono",
										children: ["$", task.costUsd.toFixed(4)]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-xs text-muted-foreground",
										children: new Date(task.startedAt).toLocaleTimeString()
									})
								]
							}, task.id))
						})]
					})
				]
			})
		})]
	});
}
//#endregion
//#region src/app/agent-hub/multi-agent.tsx
var WORKFLOW_TYPE_LABELS = {
	sequential: "Sequential",
	parallel: "Parallel",
	coordinator: "Coordinator"
};
var WORKFLOW_TYPE_DESCS = {
	sequential: "Agents run one after another, each building on the previous result",
	parallel: "Agents run simultaneously, results merged at the end",
	coordinator: "A coordinator agent delegates to specialist sub-agents"
};
function MultiAgentWorkflow() {
	const state = useStore($agentHub);
	const [creating, setCreating] = (0, import_react.useState)(false);
	const [newName, setNewName] = (0, import_react.useState)("");
	const [newType, setNewType] = (0, import_react.useState)("sequential");
	const roles = getWorkflowAgentRoles();
	const availableAgents = state.agents.filter((a) => a.status !== "error");
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-1 flex-col overflow-hidden",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between border-b px-6 py-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-lg font-semibold",
					children: "Multi-Agent Workflows"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm text-muted-foreground",
					children: "Coordinate multiple agents to work together"
				})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => setCreating(true),
					size: "sm",
					children: "New Workflow"
				})]
			}),
			creating && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "border-b p-4",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mx-auto max-w-lg space-y-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "font-medium",
							children: "Create Workflow"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Name" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
								onChange: (e) => setNewName(e.target.value),
								placeholder: "My Workflow",
								value: newName
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Type" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "grid grid-cols-3 gap-2",
								children: Object.entries(WORKFLOW_TYPE_LABELS).map(([key, label]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
									className: cn("rounded-lg border p-3 text-left text-sm transition-all", newType === key ? "border-primary/50 bg-primary/5" : ""),
									onClick: () => setNewType(key),
									type: "button",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "font-medium",
										children: label
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "text-xs text-muted-foreground mt-1",
										children: WORKFLOW_TYPE_DESCS[key]
									})]
								}, key))
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex justify-end gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => setCreating(false),
								variant: "outline",
								children: "Cancel"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => {
									if (newName.trim()) {
										createWorkflow(newName.trim(), newType);
										setCreating(false);
										setNewName("");
									}
								},
								children: "Create"
							})]
						})
					]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex-1 overflow-y-auto p-6",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "mx-auto max-w-4xl space-y-4",
					children: state.workflows.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "py-12 text-center text-sm text-muted-foreground",
						children: "No workflows yet. Create one to coordinate multiple agents."
					}) : state.workflows.map((wf) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border p-5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center justify-between",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-3",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: cn("flex h-10 w-10 items-center justify-center rounded-lg", wf.type === "coordinator" ? "bg-purple-500/20 text-purple-600" : wf.type === "parallel" ? "bg-blue-500/20 text-blue-600" : "bg-green-500/20 text-green-600"),
									children: wf.type === "coordinator" ? "C" : wf.type === "parallel" ? "∥" : "→"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
									className: "font-medium",
									children: wf.name
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
									className: "text-xs text-muted-foreground",
									children: [
										WORKFLOW_TYPE_LABELS[wf.type],
										" · ",
										wf.agents.length,
										" agents · ",
										wf.steps.length,
										" steps"
									]
								})] })]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
									checked: wf.enabled,
									onCheckedChange: (v) => updateWorkflow(wf.id, { enabled: v })
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									className: "text-destructive",
									onClick: () => deleteWorkflow(wf.id),
									size: "sm",
									variant: "ghost",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
										className: "h-4 w-4",
										fill: "none",
										stroke: "currentColor",
										strokeWidth: 2,
										viewBox: "0 0 24 24",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" })
									})
								})]
							})]
						}), wf.agents.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-4 space-y-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-sm text-muted-foreground",
								children: "Add agents to this workflow"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "flex flex-wrap gap-2",
								children: roles.map((role) => {
									availableAgents.find((a) => wf.agents.some((wa) => wa.role === role.role && wa.agentId === a.id));
									return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
										className: "flex items-center gap-2 rounded-lg border px-3 py-2 text-xs hover:bg-accent",
										onClick: () => {
											const agent = availableAgents.find((a) => !wf.agents.some((wa) => wa.agentId === a.id));
											if (agent) addWorkflowAgent(wf.id, role.role, agent.id);
										},
										type: "button",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-medium",
											children: role.label
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
											className: "text-muted-foreground",
											children: ["— ", role.description]
										})]
									}, role.role);
								})
							})]
						}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-4 flex items-center gap-2",
							children: wf.agents.map((wa, i) => {
								const agent = state.agents.find((a) => a.id === wa.agentId);
								const role = roles.find((r) => r.role === wa.role);
								return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-2",
									children: [i > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: cn("text-muted-foreground", wf.type === "parallel" ? "mx-1" : "mx-2"),
										children: wf.type === "parallel" ? "∥" : "→"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm",
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
												className: "h-6 w-6 rounded bg-primary/10 flex items-center justify-center text-xs font-bold",
												children: agent?.name?.charAt(0) || "?"
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
												className: "text-xs font-medium",
												children: agent?.name || "Unknown"
											}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
												className: "text-[10px] text-muted-foreground",
												children: role?.label || wa.role
											})] }),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
												className: "text-muted-foreground hover:text-destructive ml-1",
												onClick: () => removeWorkflowAgent(wf.id, wa.agentId),
												type: "button",
												children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
													className: "h-3 w-3",
													fill: "none",
													stroke: "currentColor",
													strokeWidth: 2,
													viewBox: "0 0 24 24",
													children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M18 6L6 18M6 6l12 12" })
												})
											})
										]
									})]
								}, wa.agentId);
							})
						})]
					}, wf.id))
				})
			})
		]
	});
}
//#endregion
//#region src/app/agent-hub/task-manager.tsx
var STATUS_CONFIG = {
	running: {
		color: "text-blue-600",
		label: "Running",
		bg: "bg-blue-500/10 border-blue-500/30"
	},
	queued: {
		color: "text-yellow-600",
		label: "Queued",
		bg: "bg-yellow-500/10 border-yellow-500/30"
	},
	completed: {
		color: "text-green-600",
		label: "Completed",
		bg: "bg-green-500/10 border-green-500/30"
	},
	failed: {
		color: "text-red-600",
		label: "Failed",
		bg: "bg-red-500/10 border-red-500/30"
	},
	cancelled: {
		color: "text-gray-500",
		label: "Cancelled",
		bg: "bg-gray-500/10 border-gray-500/30"
	}
};
function TaskManager() {
	const state = useStore($agentHub);
	const [filter, setFilter] = (0, import_react.useState)("all");
	const [expanded, setExpanded] = (0, import_react.useState)(null);
	const filtered = (0, import_react.useMemo)(() => {
		if (filter === "all") return state.tasks;
		return state.tasks.filter((t) => t.status === filter);
	}, [state.tasks, filter]);
	const stats = (0, import_react.useMemo)(() => ({
		running: state.tasks.filter((t) => t.status === "running").length,
		queued: state.tasks.filter((t) => t.status === "queued").length,
		completed: state.tasks.filter((t) => t.status === "completed").length,
		failed: state.tasks.filter((t) => t.status === "failed").length
	}), [state.tasks]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-1 flex-col overflow-hidden",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "border-b px-6 py-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-lg font-semibold",
					children: "Task Manager"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm text-muted-foreground",
					children: "Monitor and manage agent task executions"
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid grid-cols-4 gap-4 border-b px-6 py-4",
				children: [
					{
						label: "Running",
						count: stats.running,
						color: "text-blue-600"
					},
					{
						label: "Queued",
						count: stats.queued,
						color: "text-yellow-600"
					},
					{
						label: "Completed",
						count: stats.completed,
						color: "text-green-600"
					},
					{
						label: "Failed",
						count: stats.failed,
						color: "text-red-600"
					}
				].map((s) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: cn("rounded-lg border p-3 text-center transition-all", filter === s.label.toLowerCase() ? "border-primary/50 bg-primary/5" : ""),
					onClick: () => setFilter(s.label.toLowerCase()),
					type: "button",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: cn("text-2xl font-bold", s.color),
						children: s.count
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "text-xs text-muted-foreground",
						children: s.label
					})]
				}, s.label))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex-1 overflow-y-auto p-4",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "mx-auto max-w-3xl space-y-2",
					children: filtered.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "py-12 text-center text-sm text-muted-foreground",
						children: "No tasks to display"
					}) : filtered.map((task) => {
						const cfg = STATUS_CONFIG[task.status] || STATUS_CONFIG.queued;
						return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: cn("rounded-xl border transition-all", cfg.bg),
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: "flex w-full items-center gap-4 p-4 text-left",
								onClick: () => setExpanded(expanded === task.id ? null : task.id),
								type: "button",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("h-2.5 w-2.5 shrink-0 rounded-full", task.status === "running" ? "bg-blue-500 animate-pulse" : task.status === "completed" ? "bg-green-500" : task.status === "failed" ? "bg-red-500" : "bg-gray-400") }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex-1 min-w-0",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "flex items-center gap-2",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "font-medium truncate",
												children: task.agentName
											}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
												className: cn("text-[10px] h-5", cfg.color),
												variant: "outline",
												children: cfg.label
											})]
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
											className: "text-xs text-muted-foreground mt-0.5",
											children: [
												"Started ",
												new Date(task.startedAt).toLocaleString(),
												task.duration !== null && ` · ${(task.duration / 1e3).toFixed(1)}s`
											]
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "text-right text-xs text-muted-foreground",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "font-mono",
											children: [task.inputTokens + task.outputTokens, " tokens"]
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "font-mono",
											children: ["$", task.costUsd.toFixed(4)]
										})]
									}),
									task.status === "running" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
										className: "text-destructive",
										onClick: (e) => {
											e.stopPropagation();
											updateTask(task.id, { status: "cancelled" });
										},
										size: "sm",
										variant: "ghost",
										children: "Cancel"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
										className: cn("h-4 w-4 text-muted-foreground transition-transform", expanded === task.id && "rotate-180"),
										fill: "none",
										stroke: "currentColor",
										strokeWidth: 2,
										viewBox: "0 0 24 24",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M6 9l6 6 6-6" })
									})
								]
							}), expanded === task.id && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "border-t px-4 py-3",
								children: [task.error && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "mb-3 rounded-lg bg-destructive/10 p-3 text-sm text-destructive",
									children: task.error
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "space-y-1",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-xs text-muted-foreground",
										children: "Logs"
									}), task.logs.length > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "max-h-40 space-y-1 overflow-y-auto rounded-lg bg-muted p-3 font-mono text-xs",
										children: task.logs.map((log, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: cn(log.level === "error" ? "text-destructive" : log.level === "warn" ? "text-yellow-600" : log.level === "debug" ? "text-muted-foreground" : ""),
											children: [
												/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
													className: "text-muted-foreground",
													children: [
														"[",
														new Date(log.timestamp).toLocaleTimeString(),
														"]"
													]
												}),
												" ",
												log.message
											]
										}, i))
									}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-xs text-muted-foreground",
										children: "No logs available"
									})]
								})]
							})]
						}, task.id);
					})
				})
			})
		]
	});
}
//#endregion
//#region src/app/agent-hub/index.tsx
var TABS = [
	{
		id: "agents",
		label: "Agents",
		icon: "🤖"
	},
	{
		id: "workflows",
		label: "Workflows",
		icon: "↗"
	},
	{
		id: "automation",
		label: "Automation",
		icon: "⚡"
	},
	{
		id: "tasks",
		label: "Tasks",
		icon: "📋"
	},
	{
		id: "monitor",
		label: "Monitor",
		icon: "📊"
	},
	{
		id: "marketplace",
		label: "Marketplace",
		icon: "🏪"
	}
];
function AgentHubView({ onClose }) {
	const state = useStore($agentHub);
	const [activeTab, setActiveTab] = (0, import_react.useState)("agents");
	const editing = state.editingAgent;
	if (editing) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AgentConfigPanel, {
		agent: editing,
		onBack: () => setEditingAgent(null)
	});
	const runningCount = state.agents.filter((a) => a.status === "running").length;
	const activeTasks = state.tasks.filter((t) => t.status === "running" || t.status === "queued").length;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col overflow-hidden bg-background",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
				className: "flex shrink-0 items-center justify-between border-b px-6 py-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex items-center gap-4",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
						className: "text-xl font-semibold",
						children: "Agent Hub"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "text-sm text-muted-foreground",
						children: [
							state.agents.length,
							" agents · ",
							runningCount,
							" running · ",
							activeTasks,
							" active tasks · ",
							state.workflows.length,
							" workflows"
						]
					})] })
				}), onClose && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					className: "text-muted-foreground hover:text-foreground",
					onClick: onClose,
					type: "button",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
						className: "h-5 w-5",
						fill: "none",
						stroke: "currentColor",
						strokeWidth: 2,
						viewBox: "0 0 24 24",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M18 6L6 18M6 6l12 12" })
					})
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex shrink-0 items-center gap-1 border-b px-4",
				children: TABS.map((tab) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: cn("flex items-center gap-1.5 border-b-2 px-4 py-3 text-sm font-medium transition-colors", activeTab === tab.id ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"),
					onClick: () => setActiveTab(tab.id),
					type: "button",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-xs",
						children: tab.icon
					}), tab.label]
				}, tab.id))
			}),
			activeTab === "agents" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AgentList, {}),
			activeTab === "workflows" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(MultiAgentWorkflow, {}),
			activeTab === "automation" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AutomationBuilder, {}),
			activeTab === "tasks" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TaskManager, {}),
			activeTab === "monitor" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(MonitoringDashboard, {}),
			activeTab === "marketplace" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Marketplace, {})
		]
	});
}
//#endregion
export { AgentHubView };

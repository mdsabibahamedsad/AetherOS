import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Ia as Codicon, La as Button, Qa as atom, Ra as cn, S as ScrollArea, Xa as init_nanostores, Ya as useStore, _t as Separator, ao as require_jsx_runtime, oo as require_react } from "./index-B_yd1pEX.js";
//#region src/store/automation.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
init_nanostores();
var TRIGGER_CONFIGS = [
	{
		kind: "application-started",
		label: "Application Started",
		description: "Triggers when the application launches",
		icon: "rocket",
		configFields: []
	},
	{
		kind: "agent-finished",
		label: "Agent Finished",
		description: "Triggers when an agent completes its task",
		icon: "check-circle",
		configFields: [{
			name: "agentId",
			label: "Agent",
			type: "select",
			required: true,
			description: "Select the agent to watch"
		}]
	},
	{
		kind: "timer",
		label: "Timer",
		description: "Triggers after a specified duration",
		icon: "timer",
		configFields: [{
			name: "duration",
			label: "Duration",
			type: "number",
			required: true,
			defaultValue: 60,
			placeholder: "Duration in seconds"
		}, {
			name: "unit",
			label: "Unit",
			type: "select",
			required: true,
			options: [
				{
					label: "Seconds",
					value: "seconds"
				},
				{
					label: "Minutes",
					value: "minutes"
				},
				{
					label: "Hours",
					value: "hours"
				}
			],
			defaultValue: "seconds"
		}]
	},
	{
		kind: "cron",
		label: "Cron",
		description: "Triggers on a cron schedule",
		icon: "calendar",
		configFields: [{
			name: "expression",
			label: "Cron Expression",
			type: "text",
			required: true,
			placeholder: "*/5 * * * *"
		}, {
			name: "timezone",
			label: "Timezone",
			type: "text",
			required: false,
			placeholder: "UTC"
		}]
	},
	{
		kind: "folder-changed",
		label: "Folder Changed",
		description: "Triggers when a folder is modified",
		icon: "folder",
		configFields: [{
			name: "path",
			label: "Folder Path",
			type: "text",
			required: true,
			placeholder: "/path/to/folder"
		}, {
			name: "recursive",
			label: "Recursive",
			type: "boolean",
			required: false,
			defaultValue: false
		}]
	},
	{
		kind: "file-created",
		label: "File Created",
		description: "Triggers when a file is created",
		icon: "file-add",
		configFields: [{
			name: "pattern",
			label: "File Pattern",
			type: "text",
			required: false,
			placeholder: "*.txt"
		}, {
			name: "path",
			label: "Directory",
			type: "text",
			required: true,
			placeholder: "/path/to/watch"
		}]
	},
	{
		kind: "git-push",
		label: "Git Push",
		description: "Triggers on git push events",
		icon: "git-commit",
		configFields: [{
			name: "repository",
			label: "Repository",
			type: "text",
			required: true,
			placeholder: "owner/repo"
		}, {
			name: "branch",
			label: "Branch",
			type: "text",
			required: false,
			placeholder: "main"
		}]
	},
	{
		kind: "webhook",
		label: "Webhook",
		description: "Triggers via incoming webhook",
		icon: "webhook",
		configFields: [{
			name: "url",
			label: "Webhook URL",
			type: "text",
			required: true,
			placeholder: "/webhook/my-endpoint"
		}, {
			name: "method",
			label: "HTTP Method",
			type: "select",
			required: false,
			options: [
				{
					label: "POST",
					value: "POST"
				},
				{
					label: "GET",
					value: "GET"
				},
				{
					label: "PUT",
					value: "PUT"
				}
			],
			defaultValue: "POST"
		}]
	},
	{
		kind: "http-request",
		label: "HTTP Request",
		description: "Triggers on an HTTP request to a local endpoint",
		icon: "globe",
		configFields: [{
			name: "port",
			label: "Port",
			type: "number",
			required: true,
			defaultValue: 8080
		}, {
			name: "path",
			label: "Path",
			type: "text",
			required: true,
			placeholder: "/webhook"
		}]
	},
	{
		kind: "email-received",
		label: "Email Received",
		description: "Triggers when an email is received",
		icon: "mail",
		configFields: [{
			name: "from",
			label: "From Address",
			type: "text",
			required: false,
			placeholder: "sender@example.com"
		}, {
			name: "subject",
			label: "Subject Filter",
			type: "text",
			required: false,
			placeholder: "Subject contains..."
		}]
	},
	{
		kind: "telegram-message",
		label: "Telegram Message",
		description: "Triggers on a Telegram message",
		icon: "send",
		configFields: [{
			name: "chatId",
			label: "Chat ID",
			type: "text",
			required: false
		}, {
			name: "command",
			label: "Command Filter",
			type: "text",
			required: false,
			placeholder: "/start"
		}]
	},
	{
		kind: "discord-message",
		label: "Discord Message",
		description: "Triggers on a Discord message",
		icon: "message-circle",
		configFields: [{
			name: "channelId",
			label: "Channel ID",
			type: "text",
			required: false
		}, {
			name: "contains",
			label: "Contains Text",
			type: "text",
			required: false
		}]
	},
	{
		kind: "slack-message",
		label: "Slack Message",
		description: "Triggers on a Slack message",
		icon: "message-square",
		configFields: [{
			name: "channel",
			label: "Channel",
			type: "text",
			required: false,
			placeholder: "#general"
		}]
	},
	{
		kind: "whatsapp-message",
		label: "WhatsApp Message",
		description: "Triggers on a WhatsApp message",
		icon: "message-circle",
		configFields: [{
			name: "number",
			label: "Phone Number",
			type: "text",
			required: false
		}]
	},
	{
		kind: "github-issue",
		label: "GitHub Issue",
		description: "Triggers on a GitHub issue event",
		icon: "issue-opened",
		configFields: [{
			name: "repository",
			label: "Repository",
			type: "text",
			required: true,
			placeholder: "owner/repo"
		}, {
			name: "action",
			label: "Action",
			type: "select",
			required: false,
			options: [
				{
					label: "Opened",
					value: "opened"
				},
				{
					label: "Closed",
					value: "closed"
				},
				{
					label: "Reopened",
					value: "reopened"
				}
			]
		}]
	},
	{
		kind: "github-pr",
		label: "GitHub PR",
		description: "Triggers on a GitHub pull request event",
		icon: "git-pull-request",
		configFields: [{
			name: "repository",
			label: "Repository",
			type: "text",
			required: true,
			placeholder: "owner/repo"
		}, {
			name: "action",
			label: "Action",
			type: "select",
			required: false,
			options: [
				{
					label: "Opened",
					value: "opened"
				},
				{
					label: "Closed",
					value: "closed"
				},
				{
					label: "Merged",
					value: "merged"
				},
				{
					label: "Review Requested",
					value: "review_requested"
				}
			]
		}]
	},
	{
		kind: "rss-feed",
		label: "RSS Feed",
		description: "Triggers on new RSS feed items",
		icon: "rss",
		configFields: [{
			name: "url",
			label: "Feed URL",
			type: "text",
			required: true,
			placeholder: "https://example.com/feed.xml"
		}, {
			name: "interval",
			label: "Check Interval (min)",
			type: "number",
			required: false,
			defaultValue: 15
		}]
	},
	{
		kind: "clipboard-changed",
		label: "Clipboard Changed",
		description: "Triggers when clipboard content changes",
		icon: "clipboard",
		configFields: [{
			name: "contains",
			label: "Contains Text",
			type: "text",
			required: false
		}]
	},
	{
		kind: "voice-command",
		label: "Voice Command",
		description: "Triggers on a voice command",
		icon: "mic",
		configFields: [{
			name: "command",
			label: "Command Phrase",
			type: "text",
			required: true,
			placeholder: "hey aetheros..."
		}]
	},
	{
		kind: "screen-capture",
		label: "Screen Capture",
		description: "Triggers on screen content change",
		icon: "screen",
		configFields: [{
			name: "region",
			label: "Screen Region",
			type: "text",
			required: false
		}, {
			name: "interval",
			label: "Check Interval (s)",
			type: "number",
			required: false,
			defaultValue: 30
		}]
	},
	{
		kind: "manual",
		label: "Manual Button",
		description: "Triggered manually by clicking a button",
		icon: "play",
		configFields: [{
			name: "buttonLabel",
			label: "Button Label",
			type: "text",
			required: false,
			defaultValue: "Run Workflow"
		}]
	}
];
var ACTION_CONFIGS = [
	{
		kind: "run-agent",
		label: "Run Agent",
		description: "Execute an AI agent",
		icon: "robot",
		category: "ai",
		configFields: [
			{
				name: "agentId",
				label: "Agent",
				type: "select",
				required: true
			},
			{
				name: "task",
				label: "Task Description",
				type: "textarea",
				required: true
			},
			{
				name: "waitForCompletion",
				label: "Wait For Completion",
				type: "boolean",
				required: false,
				defaultValue: true
			}
		]
	},
	{
		kind: "run-prompt",
		label: "Run Prompt",
		description: "Send a prompt to the AI model",
		icon: "message",
		category: "ai",
		configFields: [
			{
				name: "prompt",
				label: "Prompt",
				type: "textarea",
				required: true
			},
			{
				name: "model",
				label: "Model Override",
				type: "text",
				required: false
			},
			{
				name: "temperature",
				label: "Temperature",
				type: "number",
				required: false,
				defaultValue: .7
			}
		]
	},
	{
		kind: "call-model",
		label: "Call Model",
		description: "Call an AI model directly",
		icon: "brain",
		category: "ai",
		configFields: [
			{
				name: "provider",
				label: "Provider",
				type: "select",
				required: true
			},
			{
				name: "model",
				label: "Model",
				type: "select",
				required: true
			},
			{
				name: "systemPrompt",
				label: "System Prompt",
				type: "textarea",
				required: false
			},
			{
				name: "maxTokens",
				label: "Max Tokens",
				type: "number",
				required: false,
				defaultValue: 4096
			}
		]
	},
	{
		kind: "send-email",
		label: "Send Email",
		description: "Send an email message",
		icon: "mail",
		category: "communication",
		configFields: [
			{
				name: "to",
				label: "To",
				type: "text",
				required: true,
				placeholder: "recipient@example.com"
			},
			{
				name: "subject",
				label: "Subject",
				type: "text",
				required: true
			},
			{
				name: "body",
				label: "Body",
				type: "textarea",
				required: true
			}
		]
	},
	{
		kind: "send-telegram",
		label: "Send Telegram",
		description: "Send a Telegram message",
		icon: "send",
		category: "communication",
		configFields: [{
			name: "chatId",
			label: "Chat ID",
			type: "text",
			required: true
		}, {
			name: "text",
			label: "Message Text",
			type: "textarea",
			required: true
		}]
	},
	{
		kind: "send-discord",
		label: "Send Discord",
		description: "Send a Discord message",
		icon: "message-circle",
		category: "communication",
		configFields: [{
			name: "channelId",
			label: "Channel ID",
			type: "text",
			required: true
		}, {
			name: "content",
			label: "Message Content",
			type: "textarea",
			required: true
		}]
	},
	{
		kind: "send-slack",
		label: "Send Slack",
		description: "Send a Slack message",
		icon: "message-square",
		category: "communication",
		configFields: [{
			name: "channel",
			label: "Channel",
			type: "text",
			required: true,
			placeholder: "#general"
		}, {
			name: "text",
			label: "Message Text",
			type: "textarea",
			required: true
		}]
	},
	{
		kind: "send-whatsapp",
		label: "Send WhatsApp",
		description: "Send a WhatsApp message",
		icon: "message-circle",
		category: "communication",
		configFields: [{
			name: "to",
			label: "Phone Number",
			type: "text",
			required: true
		}, {
			name: "text",
			label: "Message",
			type: "textarea",
			required: true
		}]
	},
	{
		kind: "create-file",
		label: "Create File",
		description: "Create a new file",
		icon: "file-add",
		category: "file",
		configFields: [
			{
				name: "path",
				label: "File Path",
				type: "text",
				required: true
			},
			{
				name: "content",
				label: "Content",
				type: "code",
				required: true
			},
			{
				name: "overwrite",
				label: "Overwrite If Exists",
				type: "boolean",
				required: false,
				defaultValue: false
			}
		]
	},
	{
		kind: "delete-file",
		label: "Delete File",
		description: "Delete a file",
		icon: "trash",
		category: "file",
		configFields: [{
			name: "path",
			label: "File Path",
			type: "text",
			required: true
		}, {
			name: "permanent",
			label: "Permanent Delete",
			type: "boolean",
			required: false,
			defaultValue: false
		}]
	},
	{
		kind: "move-file",
		label: "Move File",
		description: "Move or rename a file",
		icon: "file-move",
		category: "file",
		configFields: [{
			name: "source",
			label: "Source Path",
			type: "text",
			required: true
		}, {
			name: "destination",
			label: "Destination Path",
			type: "text",
			required: true
		}]
	},
	{
		kind: "run-terminal",
		label: "Run Terminal",
		description: "Execute a terminal command",
		icon: "terminal",
		category: "code",
		configFields: [
			{
				name: "command",
				label: "Command",
				type: "code",
				required: true
			},
			{
				name: "workdir",
				label: "Working Directory",
				type: "text",
				required: false
			},
			{
				name: "timeout",
				label: "Timeout (s)",
				type: "number",
				required: false,
				defaultValue: 30
			}
		]
	},
	{
		kind: "run-python",
		label: "Run Python",
		description: "Execute Python code",
		icon: "code",
		category: "code",
		configFields: [{
			name: "code",
			label: "Python Code",
			type: "code",
			required: true
		}, {
			name: "requirements",
			label: "Requirements",
			type: "text",
			required: false
		}]
	},
	{
		kind: "run-docker",
		label: "Run Docker",
		description: "Execute a Docker container",
		icon: "container",
		category: "code",
		configFields: [
			{
				name: "image",
				label: "Image",
				type: "text",
				required: true,
				placeholder: "node:18"
			},
			{
				name: "command",
				label: "Command",
				type: "text",
				required: false
			},
			{
				name: "volumes",
				label: "Volumes",
				type: "text",
				required: false
			}
		]
	},
	{
		kind: "git-commit",
		label: "Git Commit",
		description: "Create a git commit",
		icon: "git-commit",
		category: "git",
		configFields: [
			{
				name: "message",
				label: "Commit Message",
				type: "text",
				required: true
			},
			{
				name: "path",
				label: "Repository Path",
				type: "text",
				required: false
			},
			{
				name: "addAll",
				label: "Add All Changes",
				type: "boolean",
				required: false,
				defaultValue: true
			}
		]
	},
	{
		kind: "git-push",
		label: "Git Push",
		description: "Push to git remote",
		icon: "git-push",
		category: "git",
		configFields: [{
			name: "remote",
			label: "Remote Name",
			type: "text",
			required: false,
			defaultValue: "origin"
		}, {
			name: "branch",
			label: "Branch",
			type: "text",
			required: false
		}]
	},
	{
		kind: "ocr",
		label: "OCR",
		description: "Extract text from images",
		icon: "scan",
		category: "ai",
		configFields: [{
			name: "imagePath",
			label: "Image Path",
			type: "text",
			required: true
		}, {
			name: "language",
			label: "Language",
			type: "text",
			required: false,
			defaultValue: "eng"
		}]
	},
	{
		kind: "vision-analysis",
		label: "Vision Analysis",
		description: "Analyze images with AI vision",
		icon: "eye",
		category: "ai",
		configFields: [{
			name: "imagePath",
			label: "Image Path",
			type: "text",
			required: true
		}, {
			name: "prompt",
			label: "Analysis Prompt",
			type: "textarea",
			required: false,
			defaultValue: "Describe this image in detail."
		}]
	},
	{
		kind: "speech-to-text",
		label: "Speech To Text",
		description: "Transcribe audio to text",
		icon: "mic",
		category: "ai",
		configFields: [{
			name: "audioPath",
			label: "Audio File Path",
			type: "text",
			required: true
		}, {
			name: "language",
			label: "Language",
			type: "text",
			required: false
		}]
	},
	{
		kind: "text-to-speech",
		label: "Text To Speech",
		description: "Convert text to speech",
		icon: "volume-up",
		category: "ai",
		configFields: [
			{
				name: "text",
				label: "Text",
				type: "textarea",
				required: true
			},
			{
				name: "voice",
				label: "Voice",
				type: "select",
				required: false
			},
			{
				name: "outputPath",
				label: "Output Path",
				type: "text",
				required: true
			}
		]
	},
	{
		kind: "web-search",
		label: "Web Search",
		description: "Search the web",
		icon: "search",
		category: "web",
		configFields: [{
			name: "query",
			label: "Search Query",
			type: "textarea",
			required: true
		}, {
			name: "numResults",
			label: "Number of Results",
			type: "number",
			required: false,
			defaultValue: 10
		}]
	},
	{
		kind: "open-browser",
		label: "Open Browser",
		description: "Open a browser window",
		icon: "globe",
		category: "web",
		configFields: [{
			name: "url",
			label: "URL",
			type: "text",
			required: true
		}, {
			name: "headless",
			label: "Headless Mode",
			type: "boolean",
			required: false,
			defaultValue: false
		}]
	},
	{
		kind: "close-browser",
		label: "Close Browser",
		description: "Close a browser window",
		icon: "x-circle",
		category: "web",
		configFields: []
	},
	{
		kind: "open-url",
		label: "Open URL",
		description: "Open a URL in the default browser",
		icon: "link",
		category: "web",
		configFields: [{
			name: "url",
			label: "URL",
			type: "text",
			required: true
		}]
	},
	{
		kind: "screenshot",
		label: "Screenshot",
		description: "Take a screenshot",
		icon: "camera",
		category: "web",
		configFields: [{
			name: "outputPath",
			label: "Output Path",
			type: "text",
			required: true
		}, {
			name: "fullPage",
			label: "Full Page",
			type: "boolean",
			required: false,
			defaultValue: false
		}]
	},
	{
		kind: "database-query",
		label: "Database Query",
		description: "Execute a database query",
		icon: "database",
		category: "data",
		configFields: [{
			name: "connection",
			label: "Connection String",
			type: "secret",
			required: true
		}, {
			name: "query",
			label: "SQL Query",
			type: "code",
			required: true
		}]
	},
	{
		kind: "http-request",
		label: "HTTP Request",
		description: "Make an HTTP request",
		icon: "globe",
		category: "web",
		configFields: [
			{
				name: "url",
				label: "URL",
				type: "text",
				required: true
			},
			{
				name: "method",
				label: "Method",
				type: "select",
				required: true,
				options: [
					{
						label: "GET",
						value: "GET"
					},
					{
						label: "POST",
						value: "POST"
					},
					{
						label: "PUT",
						value: "PUT"
					},
					{
						label: "DELETE",
						value: "DELETE"
					},
					{
						label: "PATCH",
						value: "PATCH"
					}
				]
			},
			{
				name: "headers",
				label: "Headers",
				type: "json",
				required: false
			},
			{
				name: "body",
				label: "Body",
				type: "textarea",
				required: false
			}
		]
	},
	{
		kind: "webhook",
		label: "Webhook",
		description: "Send a webhook",
		icon: "webhook",
		category: "integration",
		configFields: [{
			name: "url",
			label: "Webhook URL",
			type: "text",
			required: true
		}, {
			name: "payload",
			label: "Payload",
			type: "json",
			required: true
		}]
	},
	{
		kind: "delay",
		label: "Delay",
		description: "Wait for a duration",
		icon: "clock",
		category: "flow",
		configFields: [{
			name: "duration",
			label: "Duration",
			type: "number",
			required: true,
			defaultValue: 5
		}, {
			name: "unit",
			label: "Unit",
			type: "select",
			required: false,
			options: [
				{
					label: "Seconds",
					value: "seconds"
				},
				{
					label: "Minutes",
					value: "minutes"
				},
				{
					label: "Hours",
					value: "hours"
				}
			],
			defaultValue: "seconds"
		}]
	},
	{
		kind: "loop",
		label: "Loop",
		description: "Repeat actions multiple times",
		icon: "repeat",
		category: "flow",
		configFields: [{
			name: "count",
			label: "Iterations",
			type: "number",
			required: true,
			defaultValue: 3
		}, {
			name: "variable",
			label: "Loop Variable Name",
			type: "text",
			required: false,
			defaultValue: "item"
		}]
	},
	{
		kind: "merge",
		label: "Merge",
		description: "Merge multiple execution paths",
		icon: "merge",
		category: "flow",
		configFields: [{
			name: "strategy",
			label: "Merge Strategy",
			type: "select",
			required: true,
			options: [
				{
					label: "Wait All",
					value: "wait-all"
				},
				{
					label: "First Complete",
					value: "first-complete"
				},
				{
					label: "All Complete",
					value: "all-complete"
				}
			]
		}]
	},
	{
		kind: "split",
		label: "Split",
		description: "Split execution into parallel paths",
		icon: "split",
		category: "flow",
		configFields: [{
			name: "count",
			label: "Number of Branches",
			type: "number",
			required: true,
			defaultValue: 2
		}, {
			name: "mode",
			label: "Split Mode",
			type: "select",
			required: false,
			options: [{
				label: "Parallel",
				value: "parallel"
			}, {
				label: "Sequential",
				value: "sequential"
			}]
		}]
	},
	{
		kind: "switch",
		label: "Switch",
		description: "Conditional routing based on value",
		icon: "git-branch",
		category: "flow",
		configFields: [{
			name: "expression",
			label: "Switch Expression",
			type: "expression",
			required: true
		}, {
			name: "cases",
			label: "Cases",
			type: "json",
			required: true,
			defaultValue: { default: [] }
		}]
	},
	{
		kind: "if-else",
		label: "If Else",
		description: "Conditional branching",
		icon: "git-branch",
		category: "flow",
		configFields: [{
			name: "condition",
			label: "Condition",
			type: "expression",
			required: true
		}, {
			name: "elseBranch",
			label: "Else Branch Enabled",
			type: "boolean",
			required: false,
			defaultValue: true
		}]
	},
	{
		kind: "for-each",
		label: "For Each",
		description: "Iterate over a list",
		icon: "list",
		category: "flow",
		configFields: [{
			name: "items",
			label: "Items Source",
			type: "expression",
			required: true
		}, {
			name: "variable",
			label: "Item Variable",
			type: "text",
			required: true,
			defaultValue: "item"
		}]
	},
	{
		kind: "ai-decision",
		label: "AI Decision",
		description: "Let AI make a routing decision",
		icon: "brain",
		category: "ai",
		configFields: [{
			name: "context",
			label: "Decision Context",
			type: "textarea",
			required: true
		}, {
			name: "options",
			label: "Decision Options",
			type: "json",
			required: true,
			defaultValue: ["option_a", "option_b"]
		}]
	},
	{
		kind: "memory-read",
		label: "Memory Read",
		description: "Read from agent memory",
		icon: "database",
		category: "ai",
		configFields: [{
			name: "key",
			label: "Memory Key",
			type: "text",
			required: true
		}, {
			name: "namespace",
			label: "Namespace",
			type: "text",
			required: false,
			defaultValue: "default"
		}]
	},
	{
		kind: "memory-write",
		label: "Memory Write",
		description: "Write to agent memory",
		icon: "database-plus",
		category: "ai",
		configFields: [
			{
				name: "key",
				label: "Memory Key",
				type: "text",
				required: true
			},
			{
				name: "value",
				label: "Value",
				type: "expression",
				required: true
			},
			{
				name: "namespace",
				label: "Namespace",
				type: "text",
				required: false,
				defaultValue: "default"
			}
		]
	},
	{
		kind: "knowledge-search",
		label: "Knowledge Search",
		description: "Search the knowledge base",
		icon: "book",
		category: "ai",
		configFields: [{
			name: "query",
			label: "Search Query",
			type: "textarea",
			required: true
		}, {
			name: "maxResults",
			label: "Max Results",
			type: "number",
			required: false,
			defaultValue: 5
		}]
	},
	{
		kind: "plugin-action",
		label: "Plugin Action",
		description: "Execute a plugin action",
		icon: "puzzle",
		category: "integration",
		configFields: [
			{
				name: "plugin",
				label: "Plugin",
				type: "select",
				required: true
			},
			{
				name: "action",
				label: "Action",
				type: "select",
				required: true
			},
			{
				name: "params",
				label: "Parameters",
				type: "json",
				required: false
			}
		]
	},
	{
		kind: "mcp-tool",
		label: "MCP Tool",
		description: "Call an MCP tool",
		icon: "server",
		category: "integration",
		configFields: [
			{
				name: "server",
				label: "MCP Server",
				type: "select",
				required: true
			},
			{
				name: "tool",
				label: "Tool Name",
				type: "select",
				required: true
			},
			{
				name: "arguments",
				label: "Arguments",
				type: "json",
				required: false
			}
		]
	}
];
var CONDITION_CONFIGS = [
	{
		kind: "if",
		label: "If",
		description: "If condition is true",
		icon: "git-branch",
		configFields: [{
			name: "condition",
			label: "Condition Expression",
			type: "expression",
			required: true
		}]
	},
	{
		kind: "else",
		label: "Else",
		description: "Else branch",
		icon: "git-branch",
		configFields: []
	},
	{
		kind: "switch",
		label: "Switch",
		description: "Multi-way branch",
		icon: "list",
		configFields: [{
			name: "value",
			label: "Switch Value",
			type: "expression",
			required: true
		}]
	},
	{
		kind: "contains",
		label: "Contains",
		description: "String contains check",
		icon: "search",
		configFields: [{
			name: "value",
			label: "Value",
			type: "expression",
			required: true
		}, {
			name: "substring",
			label: "Substring",
			type: "text",
			required: true
		}]
	},
	{
		kind: "regex",
		label: "Regex",
		description: "Regular expression match",
		icon: "regex",
		configFields: [{
			name: "value",
			label: "Value",
			type: "expression",
			required: true
		}, {
			name: "pattern",
			label: "Pattern",
			type: "text",
			required: true,
			placeholder: "^[A-Z].*"
		}]
	},
	{
		kind: "equals",
		label: "Equals",
		description: "Equality check",
		icon: "equal",
		configFields: [{
			name: "left",
			label: "Left Value",
			type: "expression",
			required: true
		}, {
			name: "right",
			label: "Right Value",
			type: "expression",
			required: true
		}]
	},
	{
		kind: "greater",
		label: "Greater",
		description: "Greater than check",
		icon: "arrow-up",
		configFields: [{
			name: "left",
			label: "Left Value",
			type: "expression",
			required: true
		}, {
			name: "right",
			label: "Right Value",
			type: "expression",
			required: true
		}]
	},
	{
		kind: "less",
		label: "Less",
		description: "Less than check",
		icon: "arrow-down",
		configFields: [{
			name: "left",
			label: "Left Value",
			type: "expression",
			required: true
		}, {
			name: "right",
			label: "Right Value",
			type: "expression",
			required: true
		}]
	},
	{
		kind: "date",
		label: "Date",
		description: "Date comparison",
		icon: "calendar",
		configFields: [{
			name: "date",
			label: "Date",
			type: "text",
			required: true
		}, {
			name: "operator",
			label: "Operator",
			type: "select",
			required: true,
			options: [
				{
					label: "Before",
					value: "before"
				},
				{
					label: "After",
					value: "after"
				},
				{
					label: "Equals",
					value: "equals"
				}
			]
		}]
	},
	{
		kind: "time",
		label: "Time",
		description: "Time comparison",
		icon: "clock",
		configFields: [{
			name: "time",
			label: "Time",
			type: "text",
			required: true,
			placeholder: "09:00"
		}, {
			name: "operator",
			label: "Operator",
			type: "select",
			required: false,
			options: [
				{
					label: "Before",
					value: "before"
				},
				{
					label: "After",
					value: "after"
				},
				{
					label: "Between",
					value: "between"
				}
			]
		}]
	},
	{
		kind: "schedule",
		label: "Schedule",
		description: "Check if within schedule",
		icon: "calendar-check",
		configFields: [{
			name: "days",
			label: "Days of Week",
			type: "multiselect",
			required: false,
			options: [
				{
					label: "Mon",
					value: "1"
				},
				{
					label: "Tue",
					value: "2"
				},
				{
					label: "Wed",
					value: "3"
				},
				{
					label: "Thu",
					value: "4"
				},
				{
					label: "Fri",
					value: "5"
				},
				{
					label: "Sat",
					value: "6"
				},
				{
					label: "Sun",
					value: "0"
				}
			]
		}]
	},
	{
		kind: "model-output",
		label: "Model Output",
		description: "Check AI model output",
		icon: "message",
		configFields: [{
			name: "expected",
			label: "Expected Output Pattern",
			type: "text",
			required: true
		}, {
			name: "source",
			label: "Source Node ID",
			type: "text",
			required: true
		}]
	},
	{
		kind: "llm-decision",
		label: "LLM Decision",
		description: "Let LLM decide the branch",
		icon: "brain",
		configFields: [{
			name: "prompt",
			label: "Decision Prompt",
			type: "textarea",
			required: true
		}, {
			name: "branches",
			label: "Branch Names",
			type: "json",
			required: true,
			defaultValue: ["yes", "no"]
		}]
	}
];
function generateId() {
	return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}
function createDefaultPorts(nodeId, type) {
	const ports = [{
		id: `${nodeId}-in`,
		nodeId,
		type: "input",
		label: "In",
		dataType: "any"
	}, {
		id: `${nodeId}-out`,
		nodeId,
		type: "output",
		label: "Out",
		dataType: "any"
	}];
	if (type === "condition" || type === "switch") ports.push({
		id: `${nodeId}-out-false`,
		nodeId,
		type: "output",
		label: "False",
		dataType: "any"
	});
	if (type === "loop") ports.push({
		id: `${nodeId}-out-loop`,
		nodeId,
		type: "output",
		label: "Loop Body",
		dataType: "any"
	});
	return ports;
}
function createNode(type, kind, label, position) {
	const id = generateId();
	return {
		id,
		type,
		kind,
		label,
		description: "",
		position,
		size: {
			width: 200,
			height: 60
		},
		config: {
			label,
			description: ""
		},
		ports: createDefaultPorts(id, type),
		status: "idle"
	};
}
function createConnection(sourceNodeId, sourcePortId, targetNodeId, targetPortId) {
	return {
		id: generateId(),
		sourceNodeId,
		sourcePortId,
		targetNodeId,
		targetPortId
	};
}
function createDefaultWorkflow() {
	const now = (/* @__PURE__ */ new Date()).toISOString();
	const startNode = createNode("trigger", "manual", "Manual Trigger", {
		x: 300,
		y: 200
	});
	return {
		id: generateId(),
		name: "New Workflow",
		description: "",
		tags: [],
		owner: "",
		agentAssignment: "",
		nodes: [startNode],
		connections: [],
		variables: [],
		secrets: [],
		schedule: null,
		retryPolicy: {
			maxRetries: 3,
			retryDelay: 5,
			retryDelayUnit: "seconds",
			backoffMultiplier: 2,
			retryOnError: true,
			maxDuration: 3600
		},
		logging: true,
		createdAt: now,
		updatedAt: now,
		version: 1,
		enabled: false
	};
}
var INITIAL_WORKFLOW = createDefaultWorkflow();
var $automation = /* @__PURE__ */ atom({
	workflows: [INITIAL_WORKFLOW],
	executions: [],
	secrets: [],
	activeWorkflowId: INITIAL_WORKFLOW.id,
	canvasScale: 1,
	canvasPan: {
		x: 0,
		y: 0
	},
	selectedNodeIds: [],
	selectedConnectionIds: [],
	clipboard: null,
	history: [{
		nodes: INITIAL_WORKFLOW.nodes,
		connections: INITIAL_WORKFLOW.connections
	}],
	historyIndex: 0,
	showMiniMap: true,
	snapToGrid: true,
	gridSize: 20,
	nodeSearchQuery: "",
	editingNodeId: null,
	isDragging: false,
	isPanning: false,
	showNodePalette: true,
	showVariablesPanel: false,
	showSecretsPanel: false,
	showScheduler: false,
	showHistory: false,
	showTemplates: false,
	activeTab: "editor"
});
function patch(update) {
	$automation.set({
		...$automation.get(),
		...update
	});
}
function getActiveWorkflow() {
	const state = $automation.get();
	return state.workflows.find((w) => w.id === state.activeWorkflowId);
}
function pushHistory() {
	const state = $automation.get();
	const workflow = state.workflows.find((w) => w.id === state.activeWorkflowId);
	if (!workflow) return;
	const entry = {
		nodes: JSON.parse(JSON.stringify(workflow.nodes)),
		connections: JSON.parse(JSON.stringify(workflow.connections))
	};
	const history = state.history.slice(0, state.historyIndex + 1);
	history.push(entry);
	patch({
		history,
		historyIndex: history.length - 1
	});
}
function createWorkflow(name) {
	const workflow = {
		...createDefaultWorkflow(),
		id: generateId(),
		name,
		createdAt: (/* @__PURE__ */ new Date()).toISOString(),
		updatedAt: (/* @__PURE__ */ new Date()).toISOString()
	};
	patch({
		workflows: [...$automation.get().workflows, workflow],
		activeWorkflowId: workflow.id,
		activeTab: "editor"
	});
	return workflow;
}
function deleteWorkflow(id) {
	const remaining = $automation.get().workflows.filter((w) => w.id !== id);
	patch({
		workflows: remaining,
		activeWorkflowId: remaining.length > 0 ? remaining[0].id : null
	});
}
function setActiveWorkflow(id) {
	patch({
		activeWorkflowId: id,
		activeTab: "editor"
	});
}
function updateWorkflow(id, update) {
	patch({ workflows: $automation.get().workflows.map((w) => w.id === id ? {
		...w,
		...update,
		updatedAt: (/* @__PURE__ */ new Date()).toISOString()
	} : w) });
}
function setActiveTab(tab) {
	patch({ activeTab: tab });
}
function addNode(type, kind, label, position) {
	const workflow = getActiveWorkflow();
	if (!workflow) return;
	const node = createNode(type, kind, label, position);
	updateWorkflow(workflow.id, { nodes: [...workflow.nodes, node] });
	pushHistory();
	return node;
}
function setNodePosition(nodeId, position) {
	const workflow = getActiveWorkflow();
	if (!workflow) return;
	updateWorkflow(workflow.id, { nodes: workflow.nodes.map((n) => n.id === nodeId ? {
		...n,
		position
	} : n) });
}
function updateNodeConfig(nodeId, config) {
	const workflow = getActiveWorkflow();
	if (!workflow) return;
	updateWorkflow(workflow.id, { nodes: workflow.nodes.map((n) => n.id === nodeId ? {
		...n,
		config: {
			...n.config,
			...config
		}
	} : n) });
}
function setEditingNode(nodeId) {
	patch({ editingNodeId: nodeId });
}
function addConnection(sourceNodeId, sourcePortId, targetNodeId, targetPortId) {
	const workflow = getActiveWorkflow();
	if (!workflow) return;
	if (workflow.connections.some((c) => c.sourceNodeId === sourceNodeId && c.targetNodeId === targetNodeId)) return;
	const connection = createConnection(sourceNodeId, sourcePortId, targetNodeId, targetPortId);
	updateWorkflow(workflow.id, { connections: [...workflow.connections, connection] });
	pushHistory();
}
function selectNode(nodeId, multi = false) {
	const state = $automation.get();
	if (multi) patch({ selectedNodeIds: state.selectedNodeIds.includes(nodeId) ? state.selectedNodeIds.filter((id) => id !== nodeId) : [...state.selectedNodeIds, nodeId] });
	else patch({
		selectedNodeIds: [nodeId],
		selectedConnectionIds: []
	});
}
function selectConnection(connectionId) {
	patch({
		selectedConnectionIds: [connectionId],
		selectedNodeIds: []
	});
}
function selectAll() {
	const workflow = getActiveWorkflow();
	if (!workflow) return;
	patch({
		selectedNodeIds: workflow.nodes.map((n) => n.id),
		selectedConnectionIds: []
	});
}
function copySelection() {
	const state = $automation.get();
	const workflow = getActiveWorkflow();
	if (!workflow || state.selectedNodeIds.length === 0) return;
	const nodes = workflow.nodes.filter((n) => state.selectedNodeIds.includes(n.id));
	const nodeIds = new Set(nodes.map((n) => n.id));
	const connections = workflow.connections.filter((c) => nodeIds.has(c.sourceNodeId) && nodeIds.has(c.targetNodeId));
	patch({ clipboard: {
		nodes: JSON.parse(JSON.stringify(nodes)),
		connections: JSON.parse(JSON.stringify(connections))
	} });
}
function pasteClipboard() {
	const state = $automation.get();
	const workflow = getActiveWorkflow();
	if (!workflow || !state.clipboard) return;
	const idMap = /* @__PURE__ */ new Map();
	const newNodes = state.clipboard.nodes.map((n) => {
		const newId = generateId();
		idMap.set(n.id, newId);
		return {
			...n,
			id: newId,
			position: {
				x: n.position.x + 50,
				y: n.position.y + 50
			},
			status: "idle",
			ports: n.ports.map((p) => ({
				...p,
				id: generateId(),
				nodeId: newId
			}))
		};
	});
	const newConnections = state.clipboard.connections.map((c) => ({
		...c,
		id: generateId(),
		sourceNodeId: idMap.get(c.sourceNodeId) || c.sourceNodeId,
		targetNodeId: idMap.get(c.targetNodeId) || c.targetNodeId,
		sourcePortId: generateId(),
		targetPortId: generateId()
	}));
	updateWorkflow(workflow.id, {
		nodes: [...workflow.nodes, ...newNodes],
		connections: [...workflow.connections, ...newConnections]
	});
	patch({ selectedNodeIds: newNodes.map((n) => n.id) });
	pushHistory();
}
function deleteSelection() {
	const state = $automation.get();
	const workflow = getActiveWorkflow();
	if (!workflow) return;
	const nodeSet = new Set(state.selectedNodeIds);
	updateWorkflow(workflow.id, {
		nodes: workflow.nodes.filter((n) => !nodeSet.has(n.id)),
		connections: workflow.connections.filter((c) => !nodeSet.has(c.sourceNodeId) && !nodeSet.has(c.targetNodeId))
	});
	patch({ selectedNodeIds: [] });
	pushHistory();
}
function undo() {
	const state = $automation.get();
	if (state.historyIndex <= 0) return;
	const newIndex = state.historyIndex - 1;
	const entry = state.history[newIndex];
	const workflow = getActiveWorkflow();
	if (!workflow) return;
	updateWorkflow(workflow.id, {
		nodes: JSON.parse(JSON.stringify(entry.nodes)),
		connections: JSON.parse(JSON.stringify(entry.connections))
	});
	patch({ historyIndex: newIndex });
}
function redo() {
	const state = $automation.get();
	if (state.historyIndex >= state.history.length - 1) return;
	const newIndex = state.historyIndex + 1;
	const entry = state.history[newIndex];
	const workflow = getActiveWorkflow();
	if (!workflow) return;
	updateWorkflow(workflow.id, {
		nodes: JSON.parse(JSON.stringify(entry.nodes)),
		connections: JSON.parse(JSON.stringify(entry.connections))
	});
	patch({ historyIndex: newIndex });
}
function setCanvasScale(scale) {
	patch({ canvasScale: Math.max(.1, Math.min(3, scale)) });
}
function setCanvasPan(pan) {
	patch({ canvasPan: pan });
}
function setShowMiniMap(show) {
	patch({ showMiniMap: show });
}
function setSnapToGrid(snap) {
	patch({ snapToGrid: snap });
}
function setShowNodePalette(show) {
	patch({ showNodePalette: show });
}
function setShowVariablesPanel(show) {
	patch({ showVariablesPanel: show });
}
function autoLayout() {
	const workflow = getActiveWorkflow();
	if (!workflow || workflow.nodes.length === 0) return;
	const sorted = [...workflow.nodes];
	const layers = /* @__PURE__ */ new Map();
	const inDegree = /* @__PURE__ */ new Map();
	const adjacency = /* @__PURE__ */ new Map();
	sorted.forEach((n) => {
		inDegree.set(n.id, 0);
		adjacency.set(n.id, []);
	});
	workflow.connections.forEach((c) => {
		adjacency.get(c.sourceNodeId)?.push(c.targetNodeId);
		inDegree.set(c.targetNodeId, (inDegree.get(c.targetNodeId) || 0) + 1);
	});
	let queue = sorted.filter((n) => (inDegree.get(n.id) || 0) === 0);
	let layer = 0;
	while (queue.length > 0) {
		layers.set(layer, queue);
		const next = [];
		queue.forEach((n) => {
			adjacency.get(n.id)?.forEach((child) => {
				const deg = (inDegree.get(child) || 1) - 1;
				inDegree.set(child, deg);
				if (deg === 0) next.push(child);
			});
		});
		queue = next.map((id) => sorted.find((n) => n.id === id)).filter(Boolean);
		layer++;
	}
	new Map(sorted.map((n) => [n.id, n]));
	const updated = sorted.map((n) => {
		const l = [...layers.entries()].find(([_, nodes]) => nodes.some((nd) => nd.id === n.id))?.[0] ?? 0;
		const idx = layers.get(l)?.findIndex((nd) => nd.id === n.id) ?? 0;
		return {
			...n,
			position: {
				x: 100 + l * 250,
				y: 100 + idx * 120
			}
		};
	});
	updateWorkflow(workflow.id, { nodes: updated });
	pushHistory();
}
function addVariable(variable) {
	const workflow = getActiveWorkflow();
	if (!workflow) return;
	updateWorkflow(workflow.id, { variables: [...workflow.variables, variable] });
}
function deleteVariable(id) {
	const workflow = getActiveWorkflow();
	if (!workflow) return;
	updateWorkflow(workflow.id, { variables: workflow.variables.filter((v) => v.id !== id) });
}
function addSecret(name, description) {
	const entry = {
		id: generateId(),
		name,
		description,
		createdAt: (/* @__PURE__ */ new Date()).toISOString(),
		updatedAt: (/* @__PURE__ */ new Date()).toISOString(),
		maskedValue: "••••••••"
	};
	patch({ secrets: [...$automation.get().secrets, entry] });
	return entry;
}
function deleteSecret(id) {
	patch({ secrets: $automation.get().secrets.filter((s) => s.id !== id) });
}
function setWorkflowSchedule(schedule) {
	const workflow = getActiveWorkflow();
	if (!workflow) return;
	updateWorkflow(workflow.id, { schedule });
}
function duplicateWorkflow(id) {
	const original = $automation.get().workflows.find((w) => w.id === id);
	if (!original) return null;
	const copy = {
		...JSON.parse(JSON.stringify(original)),
		id: generateId(),
		name: `${original.name} (copy)`,
		createdAt: (/* @__PURE__ */ new Date()).toISOString(),
		updatedAt: (/* @__PURE__ */ new Date()).toISOString(),
		version: 1,
		enabled: false
	};
	patch({ workflows: [...$automation.get().workflows, copy] });
	return copy;
}
function toggleWorkflowEnabled(id) {
	const workflow = $automation.get().workflows.find((w) => w.id === id);
	if (!workflow) return;
	updateWorkflow(id, { enabled: !workflow.enabled });
}
function resetCanvas() {
	patch({
		canvasScale: 1,
		canvasPan: {
			x: 0,
			y: 0
		},
		selectedNodeIds: [],
		selectedConnectionIds: []
	});
}
function getTriggerConfigs() {
	return TRIGGER_CONFIGS;
}
function getActionConfigs() {
	return ACTION_CONFIGS;
}
function getConditionConfigs() {
	return CONDITION_CONFIGS;
}
function getActionConfigByKind(kind) {
	return ACTION_CONFIGS.find((a) => a.kind === kind);
}
function getTriggerConfigByKind(kind) {
	return TRIGGER_CONFIGS.find((t) => t.kind === kind);
}
function getConditionConfigByKind(kind) {
	return CONDITION_CONFIGS.find((c) => c.kind === kind);
}
function getNodeLabel(type, kind) {
	if (type === "trigger") return TRIGGER_CONFIGS.find((t) => t.kind === kind)?.label ?? kind;
	if (type === "action") return ACTION_CONFIGS.find((a) => a.kind === kind)?.label ?? kind;
	if (type === "condition") return CONDITION_CONFIGS.find((c) => c.kind === kind)?.label ?? kind;
	return kind;
}
function getNodeIcon(type, kind) {
	if (type === "trigger") return TRIGGER_CONFIGS.find((t) => t.kind === kind)?.icon ?? "circle";
	if (type === "action") return ACTION_CONFIGS.find((a) => a.kind === kind)?.icon ?? "circle";
	if (type === "condition") return CONDITION_CONFIGS.find((c) => c.kind === kind)?.icon ?? "circle";
	return "circle";
}
//#endregion
//#region src/app/automation/canvas/canvas-node.tsx
var import_jsx_runtime = require_jsx_runtime();
var TYPE_COLORS = {
	trigger: "border-emerald-500/50 bg-emerald-500/5",
	action: "border-blue-500/50 bg-blue-500/5",
	condition: "border-amber-500/50 bg-amber-500/5",
	variable: "border-purple-500/50 bg-purple-500/5",
	timer: "border-cyan-500/50 bg-cyan-500/5",
	loop: "border-violet-500/50 bg-violet-500/5",
	switch: "border-orange-500/50 bg-orange-500/5",
	merge: "border-pink-500/50 bg-pink-500/5",
	split: "border-rose-500/50 bg-rose-500/5"
};
var TYPE_ICON_COLORS = {
	trigger: "text-emerald-400",
	action: "text-blue-400",
	condition: "text-amber-400",
	variable: "text-purple-400",
	timer: "text-cyan-400",
	loop: "text-violet-400",
	switch: "text-orange-400",
	merge: "text-pink-400",
	split: "text-rose-400"
};
var STATUS_DOTS = {
	idle: "bg-(--ui-stroke-tertiary)",
	running: "bg-blue-400 animate-pulse",
	completed: "bg-green-400",
	failed: "bg-red-400",
	skipped: "bg-amber-400",
	waiting: "bg-cyan-400"
};
function CanvasNode({ node, isSelected, isEditing, onSelect, onDragStart, onPortMouseDown, onPortMouseUp, onDoubleClick }) {
	const icon = getNodeIcon(node.type, node.kind);
	const label = getNodeLabel(node.type, node.kind);
	const handleClick = (e) => {
		onSelect(e.shiftKey);
	};
	const handlePortMouseDown = (portId, e) => {
		e.stopPropagation();
		onPortMouseDown(portId, e);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: cn("absolute rounded-xl border-2 transition-shadow", TYPE_COLORS[node.type] || "border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background)", isSelected && "ring-2 ring-primary/50 shadow-lg shadow-primary/10", isEditing && "ring-2 ring-primary shadow-xl"),
		onClick: handleClick,
		onDoubleClick,
		onMouseDown: onDragStart,
		style: {
			left: node.position.x,
			top: node.position.y,
			width: node.size.width,
			height: node.size.height
		},
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex h-full items-center gap-2 px-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: cn("flex items-center gap-1.5 flex-1 min-w-0"),
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: cn("text-sm", TYPE_ICON_COLORS[node.type] || "text-(--ui-text-tertiary)"),
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: icon,
								size: "1rem"
							})
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "truncate text-xs font-medium text-foreground",
							children: label
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("inline-block h-2 w-2 rounded-full", STATUS_DOTS[node.status] || STATUS_DOTS.idle) }),
					node.error && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-red-400",
						title: node.error,
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "warning",
							size: "0.875rem"
						})
					})
				]
			}),
			node.ports.filter((p) => p.type === "input").map((port) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "absolute left-0 top-1/2 -translate-x-1/2 -translate-y-1/2",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: cn("h-3 w-3 cursor-crosshair rounded-full border-2 transition-all hover:scale-125 hover:border-primary border-(--ui-stroke-tertiary) bg-background"),
					onMouseDown: (e) => handlePortMouseDown(port.id, e),
					onMouseUp: () => onPortMouseUp(port.id),
					title: port.label
				})
			}, port.id)),
			node.ports.filter((p) => p.type === "output").map((port) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "absolute right-0 top-1/2 translate-x-1/2 -translate-y-1/2",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: cn("h-3 w-3 cursor-crosshair rounded-full border-2 transition-all hover:scale-125 hover:border-primary border-(--ui-stroke-tertiary) bg-background"),
					onMouseDown: (e) => handlePortMouseDown(port.id, e),
					onMouseUp: () => onPortMouseUp(port.id),
					title: port.label
				})
			}, port.id)),
			node.type === "condition" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "absolute right-0 top-[75%] translate-x-1/2 -translate-y-1/2",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "h-3 w-3 cursor-crosshair rounded-full border-2 border-amber-400/50 bg-background transition-all hover:scale-125 hover:border-amber-400",
					onMouseDown: (e) => {
						e.stopPropagation();
						const port = node.ports.find((p) => p.id.endsWith("-false"));
						if (port) handlePortMouseDown(port.id, e);
					},
					title: "False"
				})
			})
		]
	});
}
//#endregion
//#region src/app/automation/canvas/connection-line.tsx
function ConnectionLine({ connection, sourceNode, targetNode, isSelected, onClick }) {
	const sourceX = sourceNode.position.x + sourceNode.size.width;
	const sourceY = sourceNode.position.y + sourceNode.size.height / 2;
	const targetX = targetNode.position.x;
	const targetY = targetNode.position.y + targetNode.size.height / 2;
	const midX = (sourceX + targetX) / 2;
	const path = `M ${sourceX} ${sourceY} C ${midX} ${sourceY}, ${midX} ${targetY}, ${targetX} ${targetY}`;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("svg", {
		className: "pointer-events-none absolute inset-0 h-full w-full",
		style: { overflow: "visible" },
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				className: "transition-colors",
				d: path,
				fill: "none",
				stroke: isSelected ? "var(--color-primary)" : "var(--ui-stroke-tertiary)",
				strokeWidth: isSelected ? 2.5 : 1.5
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				className: "pointer-events-auto cursor-pointer",
				d: path,
				fill: "none",
				onClick,
				stroke: "transparent",
				strokeWidth: 12
			}),
			isSelected && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
				className: "pointer-events-auto cursor-pointer",
				cx: targetX,
				cy: targetY,
				fill: "var(--color-primary)",
				onClick,
				r: 4
			})
		]
	});
}
//#endregion
//#region src/app/automation/canvas/mini-map.tsx
function MiniMap() {
	const state = useStore($automation);
	const workflow = state.workflows.find((w) => w.id === state.activeWorkflowId);
	const { nodes, viewport } = (0, import_react.useMemo)(() => {
		if (!workflow || workflow.nodes.length === 0) return {
			nodes: [],
			viewport: {
				x: 0,
				y: 0,
				width: 200,
				height: 150
			}
		};
		const padding = 50;
		const minX = Math.min(...workflow.nodes.map((n) => n.position.x)) - padding;
		const minY = Math.min(...workflow.nodes.map((n) => n.position.y)) - padding;
		const maxX = Math.max(...workflow.nodes.map((n) => n.position.x + n.size.width)) + padding;
		const maxY = Math.max(...workflow.nodes.map((n) => n.position.y + n.size.height)) + padding;
		const canvasW = maxX - minX;
		const canvasH = maxY - minY;
		const scale = Math.min(150 / canvasW, 100 / canvasH, 1);
		return {
			nodes: workflow.nodes.map((n) => ({
				x: (n.position.x - minX) * scale,
				y: (n.position.y - minY) * scale,
				width: n.size.width * scale,
				height: n.size.height * scale,
				type: n.type
			})),
			viewport: {
				x: (-state.canvasPan.x / state.canvasScale - minX) * scale,
				y: (-state.canvasPan.y / state.canvasScale - minY) * scale,
				width: window.innerWidth / state.canvasScale * scale,
				height: window.innerHeight / state.canvasScale * scale
			}
		};
	}, [
		workflow,
		state.canvasScale,
		state.canvasPan
	]);
	if (!state.showMiniMap || !workflow || workflow.nodes.length === 0) return null;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "absolute bottom-12 right-3 overflow-hidden rounded-lg border bg-background/90 p-2 shadow-lg backdrop-blur-sm",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("svg", {
			className: "block",
			height: 150,
			width: 200,
			children: [nodes.map((node) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
				className: cn("fill-(--ui-stroke-tertiary)/50", node.type === "trigger" && "fill-emerald-500/30", node.type === "action" && "fill-blue-500/30", node.type === "condition" && "fill-amber-500/30"),
				height: Math.max(node.height, 4),
				rx: 2,
				width: Math.max(node.width, 4),
				x: node.x,
				y: node.y
			}, `${node.x}-${node.y}`)), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
				className: "opacity-50",
				fill: "none",
				height: viewport.height,
				rx: 2,
				stroke: "var(--color-primary)",
				strokeWidth: 1,
				width: viewport.width,
				x: viewport.x,
				y: viewport.y
			})]
		})
	});
}
//#endregion
//#region src/app/automation/canvas/workflow-canvas.tsx
function WorkflowCanvas() {
	const state = useStore($automation);
	const canvasRef = (0, import_react.useRef)(null);
	const [isPanning, setIsPanning] = (0, import_react.useState)(false);
	const [panStart, setPanStart] = (0, import_react.useState)({
		x: 0,
		y: 0
	});
	const [draggingNode, setDraggingNode] = (0, import_react.useState)(null);
	const [dragStart, setDragStart] = (0, import_react.useState)({
		x: 0,
		y: 0
	});
	const [nodeDragStart, setNodeDragStart] = (0, import_react.useState)({
		x: 0,
		y: 0
	});
	const [connecting, setConnecting] = (0, import_react.useState)(null);
	const [connectionEnd, setConnectionEnd] = (0, import_react.useState)(null);
	const [dropHighlight, setDropHighlight] = (0, import_react.useState)(false);
	const workflow = state.workflows.find((w) => w.id === state.activeWorkflowId);
	const nodeMap = new Map(workflow?.nodes.map((n) => [n.id, n]) ?? []);
	(0, import_react.useEffect)(() => {
		const handleKeyDown = (e) => {
			if ((e.metaKey || e.ctrlKey) && e.key === "=") {
				e.preventDefault();
				setCanvasScale(Math.min(3, state.canvasScale + .1));
			}
			if ((e.metaKey || e.ctrlKey) && e.key === "-") {
				e.preventDefault();
				setCanvasScale(Math.max(.1, state.canvasScale - .1));
			}
			if ((e.metaKey || e.ctrlKey) && e.key === "0") {
				e.preventDefault();
				setCanvasScale(1);
			}
		};
		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [state.canvasScale]);
	const handleWheel = (0, import_react.useCallback)((e) => {
		if (e.ctrlKey || e.metaKey) {
			e.preventDefault();
			const delta = -e.deltaY * .001;
			setCanvasScale(Math.max(.1, Math.min(3, state.canvasScale + delta)));
		} else setCanvasPan({
			x: state.canvasPan.x - e.deltaX,
			y: state.canvasPan.y - e.deltaY
		});
	}, [state.canvasScale, state.canvasPan]);
	const handleMouseDown = (0, import_react.useCallback)((e) => {
		if (e.target === canvasRef.current || e.target.closest("[data-canvas-bg]")) {
			if (e.button === 0 || e.button === 1) {
				setIsPanning(true);
				setPanStart({
					x: e.clientX - state.canvasPan.x,
					y: e.clientY - state.canvasPan.y
				});
			}
		}
	}, [state.canvasPan]);
	const handleMouseMove = (0, import_react.useCallback)((e) => {
		if (isPanning) setCanvasPan({
			x: e.clientX - panStart.x,
			y: e.clientY - panStart.y
		});
		if (draggingNode) {
			const dx = e.clientX - dragStart.x;
			const dy = e.clientY - dragStart.y;
			setNodePosition(draggingNode, {
				x: state.snapToGrid ? Math.round((nodeDragStart.x + dx) / state.gridSize) * state.gridSize : nodeDragStart.x + dx,
				y: state.snapToGrid ? Math.round((nodeDragStart.y + dy) / state.gridSize) * state.gridSize : nodeDragStart.y + dy
			});
		}
		if (connecting) {
			const rect = canvasRef.current?.getBoundingClientRect();
			if (rect) setConnectionEnd({
				x: (e.clientX - rect.left - state.canvasPan.x) / state.canvasScale,
				y: (e.clientY - rect.top - state.canvasPan.y) / state.canvasScale
			});
		}
	}, [
		isPanning,
		panStart,
		draggingNode,
		dragStart,
		nodeDragStart,
		connecting,
		state.canvasScale,
		state.canvasPan,
		state.snapToGrid,
		state.gridSize
	]);
	const handleMouseUp = (0, import_react.useCallback)(() => {
		setIsPanning(false);
		setDraggingNode(null);
		if (connecting) {
			setConnecting(null);
			setConnectionEnd(null);
		}
	}, [connecting]);
	const handleNodeDragStart = (0, import_react.useCallback)((nodeId, e) => {
		e.stopPropagation();
		setDraggingNode(nodeId);
		setDragStart({
			x: e.clientX,
			y: e.clientY
		});
		const node = nodeMap.get(nodeId);
		if (node) setNodeDragStart({
			x: node.position.x,
			y: node.position.y
		});
	}, [nodeMap]);
	const handlePortMouseDown = (0, import_react.useCallback)((nodeId, portId, e) => {
		e.stopPropagation();
		setConnecting({
			nodeId,
			portId
		});
		const rect = canvasRef.current?.getBoundingClientRect();
		if (rect) setConnectionEnd({
			x: (e.clientX - rect.left - state.canvasPan.x) / state.canvasScale,
			y: (e.clientY - rect.top - state.canvasPan.y) / state.canvasScale
		});
	}, [state.canvasPan, state.canvasScale]);
	const handleCanvasDrop = (0, import_react.useCallback)((e) => {
		e.preventDefault();
		setDropHighlight(false);
		const data = e.dataTransfer.getData("application/aetheros-node");
		if (!data || !canvasRef.current) return;
		try {
			const { type, kind, label } = JSON.parse(data);
			const rect = canvasRef.current.getBoundingClientRect();
			const x = (e.clientX - rect.left - state.canvasPan.x) / state.canvasScale;
			const y = (e.clientY - rect.top - state.canvasPan.y) / state.canvasScale;
			addNode(type, kind, label, {
				x: state.snapToGrid ? Math.round(x / state.gridSize) * state.gridSize : x,
				y: state.snapToGrid ? Math.round(y / state.gridSize) * state.gridSize : y
			});
		} catch {}
	}, [
		state.canvasScale,
		state.canvasPan,
		state.snapToGrid,
		state.gridSize
	]);
	const handleDragOver = (0, import_react.useCallback)((e) => {
		e.preventDefault();
		setDropHighlight(true);
	}, []);
	const handleDragLeave = (0, import_react.useCallback)(() => setDropHighlight(false), []);
	const handlePortMouseUp = (0, import_react.useCallback)((targetNodeId, targetPortId) => {
		if (connecting && connecting.nodeId !== targetNodeId) {
			const sourcePortIsOutput = connecting.portId.endsWith("-out");
			const targetPortIsInput = targetPortId.endsWith("-in");
			if (sourcePortIsOutput && targetPortIsInput) addConnection(connecting.nodeId, connecting.portId, targetNodeId, targetPortId);
		}
		setConnecting(null);
		setConnectionEnd(null);
	}, [connecting]);
	const canvasStyle = {
		transform: `translate(${state.canvasPan.x}px, ${state.canvasPan.y}px) scale(${state.canvasScale})`,
		transformOrigin: "0 0"
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "relative h-full w-full overflow-hidden",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: cn("absolute inset-0 cursor-grab", (isPanning || state.isPanning) && "cursor-grabbing", dropHighlight && "bg-primary/5"),
				"data-canvas-bg": true,
				onClick: () => {},
				onContextMenu: (e) => {
					e.preventDefault();
					selectAll();
				},
				onDragLeave: handleDragLeave,
				onDragOver: handleDragOver,
				onDrop: handleCanvasDrop,
				onMouseDown: handleMouseDown,
				onMouseLeave: handleMouseUp,
				onMouseMove: handleMouseMove,
				onMouseUp: handleMouseUp,
				onWheel: handleWheel,
				ref: canvasRef,
				style: {
					backgroundImage: state.snapToGrid ? `radial-gradient(circle, rgba(128,128,128,0.15) 1px, transparent 1px)` : void 0,
					backgroundSize: `${state.gridSize * state.canvasScale}px ${state.gridSize * state.canvasScale}px`,
					backgroundPosition: `${state.canvasPan.x}px ${state.canvasPan.y}px`
				},
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "absolute",
					style: canvasStyle,
					children: [
						workflow?.connections.map((conn) => {
							const source = nodeMap.get(conn.sourceNodeId);
							const target = nodeMap.get(conn.targetNodeId);
							if (!source || !target) return null;
							return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ConnectionLine, {
								connection: conn,
								isSelected: state.selectedConnectionIds.includes(conn.id),
								onClick: () => selectConnection(conn.id),
								sourceNode: source,
								targetNode: target
							}, conn.id);
						}),
						connecting && connectionEnd && (() => {
							const sourceNode = nodeMap.get(connecting.nodeId);
							if (!sourceNode) return null;
							return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
								className: "pointer-events-none absolute inset-0 h-full w-full",
								style: { overflow: "visible" },
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("line", {
									stroke: "var(--color-primary)",
									strokeDasharray: "5,5",
									strokeWidth: 2,
									x1: sourceNode.position.x + sourceNode.size.width,
									x2: connectionEnd.x,
									y1: sourceNode.position.y + sourceNode.size.height / 2,
									y2: connectionEnd.y
								})
							});
						})(),
						workflow?.nodes.map((node) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CanvasNode, {
							isEditing: state.editingNodeId === node.id,
							isSelected: state.selectedNodeIds.includes(node.id),
							node,
							onDoubleClick: () => setEditingNode(node.id),
							onDragStart: (e) => handleNodeDragStart(node.id, e),
							onPortMouseDown: (portId, e) => handlePortMouseDown(node.id, portId, e),
							onPortMouseUp: (portId) => handlePortMouseUp(node.id, portId),
							onSelect: (multi) => selectNode(node.id, multi)
						}, node.id))
					]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "absolute bottom-3 left-3 flex items-center gap-1 rounded-lg border bg-background/80 px-2 py-1 backdrop-blur-sm",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "rounded p-0.5 text-(--ui-text-tertiary) hover:text-foreground",
						onClick: () => setCanvasScale(state.canvasScale - .1),
						type: "button",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "zoom-out",
							size: "0.875rem"
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "min-w-[3rem] text-center text-xs tabular-nums text-(--ui-text-tertiary)",
						children: [Math.round(state.canvasScale * 100), "%"]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "rounded p-0.5 text-(--ui-text-tertiary) hover:text-foreground",
						onClick: () => setCanvasScale(state.canvasScale + .1),
						type: "button",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "zoom-in",
							size: "0.875rem"
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "mx-1 text-(--ui-stroke-tertiary)",
						children: "|"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "rounded p-0.5 text-xs text-(--ui-text-tertiary) hover:text-foreground",
						onClick: () => setCanvasScale(1),
						type: "button",
						children: "Reset"
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "absolute bottom-3 right-3 flex items-center gap-1",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: cn("rounded-lg border px-2 py-1 text-xs backdrop-blur-sm transition-colors", state.showNodePalette ? "bg-primary/10 text-primary border-primary/20" : "bg-background/80 text-(--ui-text-tertiary) border-(--ui-stroke-tertiary)"),
					onClick: () => setShowNodePalette(!state.showNodePalette),
					type: "button",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "mr-1 inline",
						name: "add",
						size: "0.75rem"
					}), "Nodes"]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(MiniMap, {})
		]
	});
}
//#endregion
//#region src/app/automation/nodes/action-config.tsx
function ActionConfigModal({ nodeId }) {
	const state = useStore($automation);
	const node = state.workflows.find((w) => w.id === state.activeWorkflowId)?.nodes.find((n) => n.id === nodeId);
	const config = node ? getActionConfigByKind(node.kind) : null;
	const [label, setLabel] = (0, import_react.useState)(() => node?.config.label || config?.label || "");
	const [description, setDescription] = (0, import_react.useState)(() => node?.config.description || "");
	const [configValues, setConfigValues] = (0, import_react.useState)(() => node?.config || {});
	if (!node || !config) return null;
	const handleSave = () => {
		updateNodeConfig(nodeId, {
			label,
			description,
			...configValues
		});
		setEditingNode(null);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "fixed inset-0 z-50 flex items-center justify-center bg-black/50",
		onClick: () => setEditingNode(null),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex max-h-[80vh] w-[540px] flex-col rounded-xl border bg-background shadow-xl",
			onClick: (e) => e.stopPropagation(),
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between border-b px-5 py-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-blue-400",
							name: "run-all",
							size: "1rem"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "text-base font-semibold",
							children: "Configure Action"
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "text-(--ui-text-tertiary) hover:text-foreground",
						onClick: () => setEditingNode(null),
						type: "button",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "close",
							size: "1rem"
						})
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
					className: "flex-1",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-4 p-5",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
								children: "Action Type"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: "text-blue-400",
										name: config.icon,
										size: "1rem"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-sm font-medium text-foreground",
										children: config.label
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "text-xs text-(--ui-text-tertiary)",
										children: ["— ", config.description]
									})
								]
							})] }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Separator, {}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
								children: "Display Label"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
								onChange: (e) => setLabel(e.target.value),
								type: "text",
								value: label
							})] }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
								children: "Description"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
								className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
								onChange: (e) => setDescription(e.target.value),
								rows: 2,
								value: description
							})] }),
							config.configFields.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Separator, {}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "text-xs font-medium text-(--ui-text-tertiary)",
									children: "Configuration"
								}),
								config.configFields.map((field) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
										className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
										children: [field.label, field.required && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "ml-1 text-red-400",
											children: "*"
										})]
									}),
									(field.type === "text" || field.type === "expression") && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
										className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
										onChange: (e) => setConfigValues({
											...configValues,
											[field.name]: e.target.value
										}),
										placeholder: field.placeholder,
										type: "text",
										value: configValues[field.name] ?? ""
									}),
									field.type === "number" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
										className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
										onChange: (e) => setConfigValues({
											...configValues,
											[field.name]: parseFloat(e.target.value)
										}),
										type: "number",
										value: configValues[field.name] ?? field.defaultValue ?? 0
									}),
									field.type === "boolean" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
										className: "flex items-center gap-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
											checked: configValues[field.name] ?? field.defaultValue ?? false,
											className: "rounded border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) text-primary focus:ring-primary",
											onChange: (e) => setConfigValues({
												...configValues,
												[field.name]: e.target.checked
											}),
											type: "checkbox"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-xs text-(--ui-text-tertiary)",
											children: field.label
										})]
									}),
									field.type === "select" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
										className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
										onChange: (e) => setConfigValues({
											...configValues,
											[field.name]: e.target.value
										}),
										value: configValues[field.name] ?? "",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
											value: "",
											children: "Select..."
										}), field.options?.map((opt) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
											value: opt.value,
											children: opt.label
										}, opt.value))]
									}),
									field.type === "textarea" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
										className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
										onChange: (e) => setConfigValues({
											...configValues,
											[field.name]: e.target.value
										}),
										placeholder: field.placeholder,
										rows: 3,
										value: configValues[field.name] ?? ""
									}),
									field.type === "code" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
										className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-[#1e1e2e] px-3 py-1.5 font-mono text-xs text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
										onChange: (e) => setConfigValues({
											...configValues,
											[field.name]: e.target.value
										}),
										placeholder: field.placeholder,
										rows: 5,
										value: configValues[field.name] ?? ""
									}),
									field.type === "json" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
										className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-[#1e1e2e] px-3 py-1.5 font-mono text-xs text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
										onChange: (e) => {
											try {
												setConfigValues({
													...configValues,
													[field.name]: JSON.parse(e.target.value)
												});
											} catch {}
										},
										rows: 4,
										value: JSON.stringify(configValues[field.name] ?? field.defaultValue ?? {}, null, 2)
									}),
									field.description && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "mt-0.5 text-[10px] text-(--ui-text-tertiary)",
										children: field.description
									})
								] }, field.name))
							] })
						]
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-end gap-2 border-t px-5 py-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => setEditingNode(null),
						size: "sm",
						variant: "ghost",
						children: "Cancel"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: handleSave,
						size: "sm",
						children: "Save"
					})]
				})
			]
		})
	});
}
//#endregion
//#region src/app/automation/nodes/condition-config.tsx
function ConditionConfigModal({ nodeId }) {
	const state = useStore($automation);
	const node = state.workflows.find((w) => w.id === state.activeWorkflowId)?.nodes.find((n) => n.id === nodeId);
	const config = node ? getConditionConfigByKind(node.kind) : null;
	const [label, setLabel] = (0, import_react.useState)(() => node?.config.label || config?.label || "");
	const [description, setDescription] = (0, import_react.useState)(() => node?.config.description || "");
	const [configValues, setConfigValues] = (0, import_react.useState)(() => node?.config || {});
	if (!node || !config) return null;
	const handleSave = () => {
		updateNodeConfig(nodeId, {
			label,
			description,
			...configValues
		});
		setEditingNode(null);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "fixed inset-0 z-50 flex items-center justify-center bg-black/50",
		onClick: () => setEditingNode(null),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex max-h-[80vh] w-[500px] flex-col rounded-xl border bg-background shadow-xl",
			onClick: (e) => e.stopPropagation(),
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between border-b px-5 py-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-amber-400",
							name: "git-branch",
							size: "1rem"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "text-base font-semibold",
							children: "Configure Condition"
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "text-(--ui-text-tertiary) hover:text-foreground",
						onClick: () => setEditingNode(null),
						type: "button",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "close",
							size: "1rem"
						})
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
					className: "flex-1",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-4 p-5",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
								children: "Condition Type"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: "text-amber-400",
										name: config.icon,
										size: "1rem"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-sm font-medium text-foreground",
										children: config.label
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "text-xs text-(--ui-text-tertiary)",
										children: ["— ", config.description]
									})
								]
							})] }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Separator, {}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
								children: "Display Label"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
								onChange: (e) => setLabel(e.target.value),
								type: "text",
								value: label
							})] }),
							config.configFields.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Separator, {}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "text-xs font-medium text-(--ui-text-tertiary)",
									children: "Configuration"
								}),
								config.configFields.map((field) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
										className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
										children: [field.label, field.required && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "ml-1 text-red-400",
											children: "*"
										})]
									}),
									(field.type === "text" || field.type === "expression") && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
										className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
										onChange: (e) => setConfigValues({
											...configValues,
											[field.name]: e.target.value
										}),
										placeholder: field.placeholder,
										type: "text",
										value: configValues[field.name] ?? ""
									}),
									field.type === "textarea" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
										className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
										onChange: (e) => setConfigValues({
											...configValues,
											[field.name]: e.target.value
										}),
										placeholder: field.placeholder,
										rows: 3,
										value: configValues[field.name] ?? ""
									}),
									field.type === "select" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
										className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
										onChange: (e) => setConfigValues({
											...configValues,
											[field.name]: e.target.value
										}),
										value: configValues[field.name] ?? "",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
											value: "",
											children: "Select..."
										}), field.options?.map((opt) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
											value: opt.value,
											children: opt.label
										}, opt.value))]
									}),
									field.type === "json" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
										className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-[#1e1e2e] px-3 py-1.5 font-mono text-xs text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
										onChange: (e) => {
											try {
												setConfigValues({
													...configValues,
													[field.name]: JSON.parse(e.target.value)
												});
											} catch {}
										},
										rows: 4,
										value: JSON.stringify(configValues[field.name] ?? field.defaultValue ?? {}, null, 2)
									}),
									field.description && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "mt-0.5 text-[10px] text-(--ui-text-tertiary)",
										children: field.description
									})
								] }, field.name))
							] })
						]
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-end gap-2 border-t px-5 py-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => setEditingNode(null),
						size: "sm",
						variant: "ghost",
						children: "Cancel"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: handleSave,
						size: "sm",
						children: "Save"
					})]
				})
			]
		})
	});
}
//#endregion
//#region src/app/automation/nodes/trigger-config.tsx
function TriggerConfigModal({ nodeId }) {
	const state = useStore($automation);
	const workflow = state.workflows.find((w) => w.id === state.activeWorkflowId);
	const node = workflow?.nodes.find((n) => n.id === nodeId);
	const config = node ? getTriggerConfigByKind(node.kind) : null;
	const [label, setLabel] = (0, import_react.useState)(() => node?.config.label || config?.label || "");
	const [description, setDescription] = (0, import_react.useState)(() => node?.config.description || "");
	const [configValues, setConfigValues] = (0, import_react.useState)(() => node?.config || {});
	if (!node || !config || !workflow) return null;
	const handleSave = () => {
		updateNodeConfig(nodeId, {
			label,
			description,
			...configValues
		});
		setEditingNode(null);
	};
	getTriggerConfigs();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "fixed inset-0 z-50 flex items-center justify-center bg-black/50",
		onClick: () => setEditingNode(null),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex max-h-[80vh] w-[520px] flex-col rounded-xl border bg-background shadow-xl",
			onClick: (e) => e.stopPropagation(),
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between border-b px-5 py-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-emerald-400",
							name: "zap",
							size: "1rem"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "text-base font-semibold",
							children: "Configure Trigger"
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "text-(--ui-text-tertiary) hover:text-foreground",
						onClick: () => setEditingNode(null),
						type: "button",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "close",
							size: "1rem"
						})
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
					className: "flex-1",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-4 p-5",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
								children: "Trigger Type"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: "text-emerald-400",
										name: config.icon,
										size: "1rem"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-sm font-medium text-foreground",
										children: config.label
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "text-xs text-(--ui-text-tertiary)",
										children: ["— ", config.description]
									})
								]
							})] }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Separator, {}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
								children: "Display Label"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
								onChange: (e) => setLabel(e.target.value),
								type: "text",
								value: label
							})] }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
								children: "Description"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
								className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
								onChange: (e) => setDescription(e.target.value),
								rows: 2,
								value: description
							})] }),
							config.configFields.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Separator, {}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "text-xs font-medium text-(--ui-text-tertiary)",
									children: "Configuration"
								}),
								config.configFields.map((field) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
										className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
										children: [field.label, field.required && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "ml-1 text-red-400",
											children: "*"
										})]
									}),
									field.type === "text" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
										className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
										onChange: (e) => setConfigValues({
											...configValues,
											[field.name]: e.target.value
										}),
										placeholder: field.placeholder,
										type: "text",
										value: configValues[field.name] ?? ""
									}),
									field.type === "number" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
										className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
										onChange: (e) => setConfigValues({
											...configValues,
											[field.name]: parseFloat(e.target.value)
										}),
										placeholder: field.placeholder,
										type: "number",
										value: configValues[field.name] ?? field.defaultValue ?? 0
									}),
									field.type === "boolean" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
										className: "flex items-center gap-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
											checked: configValues[field.name] ?? field.defaultValue ?? false,
											className: "rounded border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) text-primary focus:ring-primary",
											onChange: (e) => setConfigValues({
												...configValues,
												[field.name]: e.target.checked
											}),
											type: "checkbox"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-xs text-(--ui-text-tertiary)",
											children: field.label
										})]
									}),
									field.type === "select" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
										className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
										onChange: (e) => setConfigValues({
											...configValues,
											[field.name]: e.target.value
										}),
										value: configValues[field.name] ?? "",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
											value: "",
											children: "Select..."
										}), field.options?.map((opt) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
											value: opt.value,
											children: opt.label
										}, opt.value))]
									}),
									field.type === "textarea" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
										className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
										onChange: (e) => setConfigValues({
											...configValues,
											[field.name]: e.target.value
										}),
										placeholder: field.placeholder,
										rows: 3,
										value: configValues[field.name] ?? ""
									}),
									field.description && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "mt-0.5 text-[10px] text-(--ui-text-tertiary)",
										children: field.description
									})
								] }, field.name))
							] })
						]
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-end gap-2 border-t px-5 py-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => setEditingNode(null),
						size: "sm",
						variant: "ghost",
						children: "Cancel"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: handleSave,
						size: "sm",
						children: "Save"
					})]
				})
			]
		})
	});
}
//#endregion
//#region src/app/automation/panels/node-palette.tsx
var PALETTE_TABS = [
	{
		id: "triggers",
		label: "Triggers",
		icon: "zap"
	},
	{
		id: "actions",
		label: "Actions",
		icon: "run-all"
	},
	{
		id: "conditions",
		label: "Conditions",
		icon: "git-branch"
	}
];
var CATEGORY_LABELS = {
	communication: "Communication",
	file: "File Operations",
	code: "Code Execution",
	git: "Git",
	ai: "AI & Models",
	web: "Web",
	data: "Data",
	flow: "Flow Control",
	integration: "Integration"
};
function NodePalette() {
	useStore($automation);
	const [activeTab, setActiveTab] = (0, import_react.useState)("triggers");
	const [searchQuery, setSearchQuery] = (0, import_react.useState)("");
	const [collapsedCategories, setCollapsedCategories] = (0, import_react.useState)(/* @__PURE__ */ new Set());
	const triggers = getTriggerConfigs();
	const actions = getActionConfigs();
	const conditions = getConditionConfigs();
	const filteredTriggers = triggers.filter((t) => t.label.toLowerCase().includes(searchQuery.toLowerCase()) || t.description.toLowerCase().includes(searchQuery.toLowerCase()));
	const filteredActions = actions.filter((a) => a.label.toLowerCase().includes(searchQuery.toLowerCase()) || a.description.toLowerCase().includes(searchQuery.toLowerCase()));
	const filteredConditions = conditions.filter((c) => c.label.toLowerCase().includes(searchQuery.toLowerCase()) || c.description.toLowerCase().includes(searchQuery.toLowerCase()));
	const groupedActions = filteredActions.reduce((acc, a) => {
		const cat = a.category || "other";
		if (!acc[cat]) acc[cat] = [];
		acc[cat].push(a);
		return acc;
	}, {});
	const handleDragStart = (e, type, kind, label) => {
		e.dataTransfer.setData("application/aetheros-node", JSON.stringify({
			type,
			kind,
			label
		}));
		e.dataTransfer.effectAllowed = "copy";
	};
	const toggleCategory = (cat) => {
		const next = new Set(collapsedCategories);
		if (next.has(cat)) next.delete(cat);
		else next.add(cat);
		setCollapsedCategories(next);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex w-64 flex-col border-r border-(--ui-stroke-tertiary) bg-(--ui-sidebar-surface-background)",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex items-center gap-0.5 border-b border-(--ui-stroke-tertiary) px-2 py-1.5",
				children: PALETTE_TABS.map((tab) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: cn("flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium transition-colors", activeTab === tab.id ? "bg-(--ui-control-hover-background) text-foreground" : "text-(--ui-text-tertiary) hover:text-foreground"),
					onClick: () => setActiveTab(tab.id),
					type: "button",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						name: tab.icon,
						size: "0.75rem"
					}), tab.label]
				}, tab.id))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "border-b border-(--ui-stroke-tertiary) px-2 py-1.5",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
					className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-2 py-1 text-xs text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
					onChange: (e) => setSearchQuery(e.target.value),
					placeholder: "Search nodes...",
					type: "text",
					value: searchQuery
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
				className: "flex-1",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-0.5 p-2",
					children: [
						activeTab === "triggers" && filteredTriggers.map((trigger) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DraggableNodeButton, {
							description: trigger.description,
							icon: trigger.icon,
							kind: trigger.kind,
							label: trigger.label,
							onDragStart: handleDragStart,
							type: "trigger"
						}, trigger.kind)),
						activeTab === "actions" && Object.entries(groupedActions).map(([cat, catActions]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: "flex w-full items-center gap-1 px-1 py-1 text-[10px] font-semibold uppercase tracking-wider text-(--ui-text-tertiary)",
							onClick: () => toggleCategory(cat),
							type: "button",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: collapsedCategories.has(cat) ? "chevron-right" : "chevron-down",
								size: "0.625rem"
							}), CATEGORY_LABELS[cat] || cat]
						}), !collapsedCategories.has(cat) && catActions.map((action) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DraggableNodeButton, {
							description: action.description,
							icon: action.icon,
							kind: action.kind,
							label: action.label,
							onDragStart: handleDragStart,
							type: "action"
						}, action.kind))] }, cat)),
						activeTab === "conditions" && filteredConditions.map((condition) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DraggableNodeButton, {
							description: condition.description,
							icon: condition.icon,
							kind: condition.kind,
							label: condition.label,
							onDragStart: handleDragStart,
							type: "condition"
						}, condition.kind)),
						activeTab === "actions" && Object.keys(groupedActions).length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "py-4 text-center text-[11px] text-(--ui-text-tertiary)",
							children: "No actions found"
						})
					]
				})
			})
		]
	});
}
function DraggableNodeButton({ type, kind, label, description, icon, onDragStart }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "group cursor-grab rounded-lg border border-transparent px-2 py-1.5 transition-colors hover:border-(--ui-stroke-tertiary) hover:bg-(--ui-control-hover-background) active:cursor-grabbing",
		draggable: true,
		onDragStart: (e) => onDragStart(e, type, kind, label),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-sm text-(--ui-text-tertiary) group-hover:text-foreground",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
					name: icon,
					size: "0.875rem"
				})
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "min-w-0 flex-1",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "truncate text-xs font-medium text-foreground",
					children: label
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "truncate text-[10px] text-(--ui-text-tertiary)",
					children: description
				})]
			})]
		})
	});
}
//#endregion
//#region src/app/automation/panels/secrets-panel.tsx
function SecretsPanel() {
	const state = useStore($automation);
	const [showNew, setShowNew] = (0, import_react.useState)(false);
	const [newName, setNewName] = (0, import_react.useState)("");
	const [newDescription, setNewDescription] = (0, import_react.useState)("");
	const [newValue, setNewValue] = (0, import_react.useState)("");
	const handleAdd = () => {
		if (!newName.trim() || !newValue.trim()) return;
		addSecret(newName.trim(), newDescription.trim());
		setNewName("");
		setNewDescription("");
		setNewValue("");
		setShowNew(false);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col overflow-hidden",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-6 py-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "text-amber-400",
						name: "lock",
						size: "1rem"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "text-base font-semibold",
						children: "Secrets Manager"
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					onClick: () => setShowNew(true),
					size: "sm",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "mr-1",
						name: "add",
						size: "0.875rem"
					}), "Add Secret"]
				})]
			}),
			showNew && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "border-b border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) p-6",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mx-auto max-w-lg space-y-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "text-sm font-medium",
							children: "New Secret"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							autoFocus: true,
							className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
							onChange: (e) => setNewName(e.target.value),
							placeholder: "Secret name (e.g., API_KEY)",
							type: "text",
							value: newName
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
							onChange: (e) => setNewDescription(e.target.value),
							placeholder: "Description (optional)",
							type: "text",
							value: newDescription
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
							onChange: (e) => setNewValue(e.target.value),
							placeholder: "Secret value",
							type: "password",
							value: newValue
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 text-[10px] text-(--ui-text-tertiary)",
							children: "Value is encrypted at rest and never exposed in the UI"
						})] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex justify-end gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => {
									setShowNew(false);
									setNewName("");
									setNewDescription("");
									setNewValue("");
								},
								size: "sm",
								variant: "ghost",
								children: "Cancel"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: handleAdd,
								size: "sm",
								children: "Save Secret"
							})]
						})
					]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
				className: "flex-1",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mx-auto max-w-2xl space-y-2 p-6",
					children: [state.secrets.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "py-12 text-center",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								className: "mx-auto mb-3 text-(--ui-text-tertiary)",
								name: "lock",
								size: "2rem"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-sm text-(--ui-text-tertiary)",
								children: "No secrets stored"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-xs text-(--ui-text-tertiary) mt-1",
								children: "Add API keys, passwords, and tokens securely"
							})
						]
					}), state.secrets.map((secret) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-3 rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "text-amber-400",
									name: "lock",
									size: "1rem"
								})
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex-1 min-w-0",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-2",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-sm font-medium text-foreground",
										children: secret.name
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "rounded bg-(--ui-stroke-tertiary) px-1.5 py-0.5 text-[9px] font-medium text-(--ui-text-tertiary)",
										children: "ENCRYPTED"
									})]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-2 text-xs text-(--ui-text-tertiary)",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: secret.maskedValue }),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "·" }),
										/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: ["Created ", new Date(secret.createdAt).toLocaleDateString()] })
									]
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: "rounded p-1.5 text-(--ui-text-tertiary) hover:text-destructive",
								onClick: () => deleteSecret(secret.id),
								type: "button",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									name: "trash",
									size: "0.875rem"
								})
							})
						]
					}, secret.id))]
				})
			})
		]
	});
}
//#endregion
//#region src/app/automation/panels/variables-panel.tsx
function VariablesPanel() {
	const state = useStore($automation);
	const workflow = state.workflows.find((w) => w.id === state.activeWorkflowId);
	const [showNew, setShowNew] = (0, import_react.useState)(false);
	const [newName, setNewName] = (0, import_react.useState)("");
	const [newScope, setNewScope] = (0, import_react.useState)("workflow");
	const [newType, setNewType] = (0, import_react.useState)("string");
	const [newValue, setNewValue] = (0, import_react.useState)("");
	const [editingId, setEditingId] = (0, import_react.useState)(null);
	if (!workflow) return null;
	const handleAdd = () => {
		if (!newName.trim()) return;
		addVariable({
			id: `var-${Date.now()}`,
			name: newName.trim(),
			scope: newScope,
			type: newType,
			value: newValue,
			description: "",
			encrypted: newScope === "secret"
		});
		setNewName("");
		setNewValue("");
		setShowNew(false);
	};
	const SCOPE_ICONS = {
		workflow: "type-hierarchy",
		global: "globe",
		session: "comment-discussion",
		environment: "terminal",
		secret: "lock",
		output: "output",
		input: "input"
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex w-72 flex-col border-l border-(--ui-stroke-tertiary) bg-(--ui-sidebar-surface-background)",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-3 py-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "text-xs font-semibold uppercase tracking-wider text-(--ui-text-tertiary)",
					children: "Variables"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-1",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "rounded p-0.5 text-(--ui-text-tertiary) hover:text-foreground",
						onClick: () => setShowNew(true),
						type: "button",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "add",
							size: "0.875rem"
						})
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "rounded p-0.5 text-(--ui-text-tertiary) hover:text-foreground",
						onClick: () => setShowVariablesPanel(false),
						type: "button",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "close",
							size: "0.875rem"
						})
					})]
				})]
			}),
			showNew && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "border-b border-(--ui-stroke-tertiary) p-3 space-y-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						autoFocus: true,
						className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-2 py-1 text-xs text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
						onChange: (e) => setNewName(e.target.value),
						placeholder: "Variable name",
						type: "text",
						value: newName
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
						className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-2 py-1 text-xs text-foreground focus:outline-none",
						onChange: (e) => setNewScope(e.target.value),
						value: newScope,
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "workflow",
								children: "Workflow"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "global",
								children: "Global"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "session",
								children: "Session"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "environment",
								children: "Environment"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "secret",
								children: "Secret"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "output",
								children: "Output"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "input",
								children: "Input"
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
						className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-2 py-1 text-xs text-foreground focus:outline-none",
						onChange: (e) => setNewType(e.target.value),
						value: newType,
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "string",
								children: "String"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "number",
								children: "Number"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "boolean",
								children: "Boolean"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "object",
								children: "Object"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "array",
								children: "Array"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "any",
								children: "Any"
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-2 py-1 text-xs text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
						onChange: (e) => setNewValue(e.target.value),
						placeholder: newScope === "secret" ? "••••••••" : "Default value",
						type: "text",
						value: newValue
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex justify-end gap-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => setShowNew(false),
							size: "sm",
							variant: "ghost",
							children: "Cancel"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: handleAdd,
							size: "sm",
							children: "Add"
						})]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
				className: "flex-1",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-1 p-2",
					children: [workflow.variables.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "py-6 text-center text-xs text-(--ui-text-tertiary)",
						children: "No variables yet"
					}), workflow.variables.map((v) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "group rounded-lg border border-transparent px-2 py-1.5 transition-colors hover:border-(--ui-stroke-tertiary)",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: cn("shrink-0", v.scope === "secret" ? "text-amber-400" : "text-(--ui-text-tertiary)"),
									name: SCOPE_ICONS[v.scope],
									size: "0.75rem"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "min-w-0 flex-1",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-1",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "truncate text-xs font-medium text-foreground",
											children: v.name
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "shrink-0 text-[9px] text-(--ui-text-tertiary)",
											children: v.type
										})]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "truncate text-[10px] text-(--ui-text-tertiary)",
										children: v.encrypted ? "••••••••" : String(v.value ?? "")
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									className: "shrink-0 rounded p-0.5 text-(--ui-text-tertiary) opacity-0 group-hover:opacity-100 hover:text-destructive",
									onClick: () => deleteVariable(v.id),
									type: "button",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: "trash",
										size: "0.75rem"
									})
								})
							]
						})
					}, v.id))]
				})
			})
		]
	});
}
//#endregion
//#region src/app/automation/panels/workflow-history.tsx
function WorkflowHistory() {
	const state = useStore($automation);
	const workflow = state.workflows.find((w) => w.id === state.activeWorkflowId);
	const [expandedId, setExpandedId] = (0, import_react.useState)(null);
	const [filter, setFilter] = (0, import_react.useState)("all");
	const executions = state.executions.filter((e) => filter === "all" ? true : e.status === filter);
	if (!workflow) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex h-full items-center justify-center",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-(--ui-text-tertiary)",
			children: "Select a workflow to view execution history"
		})
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col overflow-hidden",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-6 py-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "text-blue-400",
						name: "history",
						size: "1rem"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "text-base font-semibold",
						children: "Execution History"
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex items-center gap-1",
					children: [
						"all",
						"running",
						"completed",
						"failed"
					].map((f) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: cn("rounded-md px-2.5 py-1 text-xs font-medium transition-colors", filter === f ? "bg-(--ui-control-hover-background) text-foreground" : "text-(--ui-text-tertiary) hover:text-foreground"),
						onClick: () => setFilter(f),
						type: "button",
						children: f.charAt(0).toUpperCase() + f.slice(1)
					}, f))
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex items-center gap-4 border-b border-(--ui-stroke-tertiary) px-6 py-3",
				children: [
					{
						label: "Total Runs",
						value: state.executions.length,
						color: "text-(--ui-text-tertiary)"
					},
					{
						label: "Running",
						value: state.executions.filter((e) => e.status === "running").length,
						color: "text-blue-400"
					},
					{
						label: "Completed",
						value: state.executions.filter((e) => e.status === "completed").length,
						color: "text-green-400"
					},
					{
						label: "Failed",
						value: state.executions.filter((e) => e.status === "failed").length,
						color: "text-red-400"
					},
					{
						label: "Avg Duration",
						value: state.executions.filter((e) => e.duration).length > 0 ? `${Math.round(state.executions.filter((e) => e.duration).reduce((a, e) => a + (e.duration ?? 0), 0) / state.executions.filter((e) => e.duration).length)}s` : "—",
						color: "text-(--ui-text-tertiary)"
					}
				].map((stat) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "text-center",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: cn("text-lg font-semibold tabular-nums", stat.color),
						children: stat.value
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "text-[10px] text-(--ui-text-tertiary)",
						children: stat.label
					})]
				}, stat.label))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
				className: "flex-1",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-1 p-4",
					children: [executions.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "py-12 text-center",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								className: "mx-auto mb-3 text-(--ui-text-tertiary)",
								name: "history",
								size: "2rem"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-sm text-(--ui-text-tertiary)",
								children: "No execution history yet"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-xs text-(--ui-text-tertiary) mt-1",
								children: "Run the workflow to see results here"
							})
						]
					}), executions.map((exec) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border border-(--ui-stroke-tertiary) transition-all hover:bg-(--ui-control-hover-background)",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: "flex w-full items-center gap-4 px-4 py-3",
							onClick: () => setExpandedId(expandedId === exec.id ? null : exec.id),
							type: "button",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: cn("flex h-8 w-8 items-center justify-center rounded-lg", exec.status === "running" ? "bg-blue-500/10" : exec.status === "completed" ? "bg-green-500/10" : exec.status === "failed" ? "bg-red-500/10" : "bg-(--ui-stroke-tertiary)"),
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: exec.status === "running" ? "text-blue-400 animate-spin" : exec.status === "completed" ? "text-green-400" : exec.status === "failed" ? "text-red-400" : "text-(--ui-text-tertiary)",
										name: exec.status === "running" ? "sync" : exec.status === "completed" ? "check" : exec.status === "failed" ? "error" : "circle-slash",
										size: "1rem"
									})
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex-1 min-w-0 text-left",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-sm font-medium text-foreground",
											children: exec.workflowName
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: cn("rounded-full px-1.5 py-0.5 text-[9px] font-medium", exec.status === "running" ? "bg-blue-500/10 text-blue-400" : exec.status === "completed" ? "bg-green-500/10 text-green-400" : exec.status === "failed" ? "bg-red-500/10 text-red-400" : "bg-(--ui-stroke-tertiary) text-(--ui-text-tertiary)"),
											children: exec.status
										})]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-2 text-xs text-(--ui-text-tertiary)",
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: new Date(exec.startedAt).toLocaleString() }),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "·" }),
											/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
												exec.nodesExecuted,
												"/",
												exec.nodesTotal,
												" nodes"
											] }),
											exec.duration && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "·" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [exec.duration, "s"] })] })
										]
									})]
								}),
								exec.cost != null && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "text-xs tabular-nums text-(--ui-text-tertiary)",
									children: ["$", exec.cost.toFixed(4)]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "text-(--ui-text-tertiary)",
									name: expandedId === exec.id ? "chevron-up" : "chevron-down",
									size: "0.875rem"
								})
							]
						}), expandedId === exec.id && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "border-t border-(--ui-stroke-tertiary) px-4 py-3 space-y-3",
							children: [
								exec.error && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "rounded-lg bg-red-500/5 px-3 py-2",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-xs font-medium text-red-400",
										children: "Error"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-xs text-red-300",
										children: exec.error
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "grid grid-cols-4 gap-3",
									children: [
										{
											label: "Trigger",
											value: exec.trigger
										},
										{
											label: "Retries",
											value: String(exec.retryCount)
										},
										{
											label: "Model",
											value: exec.modelUsed ?? "—"
										},
										{
											label: "Cost",
											value: exec.cost != null ? `$${exec.cost.toFixed(4)}` : "—"
										}
									].map((d) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "rounded-lg bg-(--ui-control-hover-background) px-2 py-1.5",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
											className: "text-[10px] text-(--ui-text-tertiary)",
											children: d.label
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
											className: "text-xs font-medium text-foreground truncate",
											children: d.value
										})]
									}, d.label))
								}),
								exec.logs.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "mb-1 text-[10px] font-medium text-(--ui-text-tertiary)",
									children: "Logs"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "max-h-40 space-y-0.5 overflow-y-auto rounded-lg bg-[#1e1e2e] p-2 font-mono text-[10px]",
									children: exec.logs.map((log, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: cn("flex items-start gap-2", log.level === "error" ? "text-red-400" : log.level === "warn" ? "text-amber-400" : log.level === "debug" ? "text-(--ui-text-tertiary)" : "text-foreground/80"),
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "shrink-0 text-(--ui-text-tertiary)",
												children: new Date(log.timestamp).toLocaleTimeString()
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "shrink-0 text-[8px] uppercase",
												children: log.level
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "break-all",
												children: log.message
											})
										]
									}, i))
								})] })
							]
						})]
					}, exec.id))]
				})
			})
		]
	});
}
//#endregion
//#region src/app/automation/panels/workflow-scheduler.tsx
function WorkflowScheduler() {
	const state = useStore($automation);
	const workflow = state.workflows.find((w) => w.id === state.activeWorkflowId);
	if (!workflow) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex h-full items-center justify-center",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-(--ui-text-tertiary)",
			children: "Select a workflow to configure scheduling"
		})
	});
	const schedule = workflow.schedule;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col overflow-hidden",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-6 py-3",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
					className: "text-cyan-400",
					name: "calendar",
					size: "1rem"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-base font-semibold",
					children: "Workflow Schedule"
				})]
			})
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex-1 overflow-y-auto p-6",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mx-auto max-w-xl space-y-6",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border border-(--ui-stroke-tertiary) p-5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "mb-4 text-sm font-medium",
							children: "Schedule Type"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "grid grid-cols-4 gap-2",
							children: [
								"manual",
								"once",
								"hourly",
								"daily",
								"weekly",
								"monthly",
								"cron"
							].map((type) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: cn("rounded-lg border px-3 py-2 text-center text-xs transition-all", schedule?.type === type || !schedule && type === "manual" ? "border-primary/50 bg-primary/5 text-primary" : "border-(--ui-stroke-tertiary) text-(--ui-text-tertiary) hover:text-foreground"),
								onClick: () => setWorkflowSchedule(type === "manual" ? null : {
									type,
									cronExpression: type === "cron" ? "0 * * * *" : void 0
								}),
								type: "button",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "mb-1 text-sm",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: "mx-auto",
										name: type === "manual" ? "play" : type === "once" ? "circle" : type === "hourly" ? "clock" : type === "daily" ? "calendar" : type === "weekly" ? "calendar" : type === "monthly" ? "calendar" : "settings",
										size: "1rem"
									})
								}), type.charAt(0).toUpperCase() + type.slice(1)]
							}, type))
						})]
					}),
					schedule && schedule.type !== "manual" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border border-(--ui-stroke-tertiary) p-5",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "mb-3 text-sm font-medium",
								children: "Schedule Configuration"
							}),
							schedule.type === "cron" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-3",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
										className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
										children: "Cron Expression"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
										className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 font-mono text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
										onChange: (e) => setWorkflowSchedule({
											...schedule,
											cronExpression: e.target.value
										}),
										placeholder: "*/5 * * * *",
										type: "text",
										value: schedule.cronExpression ?? ""
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "mt-1 text-[10px] text-(--ui-text-tertiary)",
										children: "Format: minute hour day month weekday"
									})
								] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
									className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
									children: "Timezone"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
									onChange: (e) => setWorkflowSchedule({
										...schedule,
										timezone: e.target.value
									}),
									placeholder: "UTC",
									type: "text",
									value: schedule.timezone ?? "UTC"
								})] })]
							}),
							schedule.type === "once" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
								children: "Start Date & Time"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
								onChange: (e) => setWorkflowSchedule({
									...schedule,
									startDate: e.target.value
								}),
								type: "datetime-local",
								value: schedule.startDate?.slice(0, 16) ?? ""
							})] }),
							[
								"hourly",
								"daily",
								"weekly",
								"monthly"
							].includes(schedule.type) && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
									className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
									children: schedule.type === "monthly" ? "Day of Month" : schedule.type === "weekly" ? "Day of Week" : "Interval"
								}),
								schedule.type === "hourly" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-2",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-xs text-(--ui-text-tertiary)",
											children: "Every"
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
											className: "w-20 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
											min: 1,
											onChange: (e) => setWorkflowSchedule({
												...schedule,
												interval: parseInt(e.target.value) || 1
											}),
											type: "number",
											value: schedule.interval ?? 1
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-xs text-(--ui-text-tertiary)",
											children: "hours"
										})
									]
								}),
								schedule.type === "daily" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-2",
									children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-xs text-(--ui-text-tertiary)",
											children: "Every"
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
											className: "w-20 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
											min: 1,
											onChange: (e) => setWorkflowSchedule({
												...schedule,
												interval: parseInt(e.target.value) || 1
											}),
											type: "number",
											value: schedule.interval ?? 1
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-xs text-(--ui-text-tertiary)",
											children: "days"
										})
									]
								}),
								schedule.type === "weekly" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "flex items-center gap-1",
									children: [
										"Sun",
										"Mon",
										"Tue",
										"Wed",
										"Thu",
										"Fri",
										"Sat"
									].map((day, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
										className: cn("rounded-md px-2 py-1 text-xs font-medium transition-colors", (schedule.dayOfWeek ?? []).includes(i) ? "bg-primary/10 text-primary" : "bg-(--ui-control-hover-background) text-(--ui-text-tertiary)"),
										onClick: () => {
											const current = schedule.dayOfWeek ?? [];
											const next = current.includes(i) ? current.filter((d) => d !== i) : [...current, i];
											setWorkflowSchedule({
												...schedule,
												dayOfWeek: next
											});
										},
										type: "button",
										children: day
									}, day))
								}),
								schedule.type === "monthly" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									className: "w-20 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
									max: 31,
									min: 1,
									onChange: (e) => setWorkflowSchedule({
										...schedule,
										dayOfMonth: [parseInt(e.target.value) || 1]
									}),
									type: "number",
									value: schedule.dayOfMonth?.[0] ?? 1
								})
							] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
								children: "Time"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								className: "w-32 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
								onChange: (e) => setWorkflowSchedule({
									...schedule,
									startDate: `2024-01-01T${e.target.value}:00`
								}),
								type: "time",
								value: schedule.startDate?.slice(11, 16) ?? "09:00"
							})] })] }),
							schedule.type !== "cron" && schedule.type !== "once" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
								children: "Start Date"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
								onChange: (e) => setWorkflowSchedule({
									...schedule,
									startDate: e.target.value
								}),
								type: "date",
								value: schedule.startDate?.slice(0, 10) ?? ""
							})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
								children: "End Date (optional)"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
								onChange: (e) => setWorkflowSchedule({
									...schedule,
									endDate: e.target.value
								}),
								type: "date",
								value: schedule.endDate?.slice(0, 10) ?? ""
							})] })] })
						]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border border-(--ui-stroke-tertiary) p-5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "mb-3 text-sm font-medium",
							children: "Retry Policy"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "space-y-3",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-4",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex-1",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
											className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
											children: "Max Retries"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
											className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
											max: 10,
											min: 0,
											onChange: (e) => {},
											type: "number",
											value: workflow.retryPolicy.maxRetries
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex-1",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
											className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
											children: "Retry Delay"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
											className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
											min: 0,
											onChange: (e) => {},
											type: "number",
											value: workflow.retryPolicy.retryDelay
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex-1",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
											className: "mb-1 block text-xs font-medium text-(--ui-text-tertiary)",
											children: "Max Duration (s)"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
											className: "w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
											min: 0,
											onChange: (e) => {},
											type: "number",
											value: workflow.retryPolicy.maxDuration
										})]
									})
								]
							})
						})]
					})] }),
					(!schedule || schedule.type === "manual") && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border border-dashed border-(--ui-stroke-tertiary) p-8 text-center",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								className: "mx-auto mb-2 text-(--ui-text-tertiary)",
								name: "play",
								size: "2rem"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-sm text-(--ui-text-tertiary)",
								children: "Manual only"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-xs text-(--ui-text-tertiary) mt-1",
								children: "This workflow will only run when triggered manually"
							})
						]
					})
				]
			})
		})]
	});
}
//#endregion
//#region src/app/automation/templates/marketplace-view.tsx
var MARKETPLACE_ITEMS = [
	{
		id: "mp-1",
		name: "PR Auto Reviewer",
		description: "Automatically reviews GitHub PRs with AI and posts comments",
		author: "AetherOS Labs",
		icon: "git-pull-request",
		category: "Development",
		downloads: 1240,
		rating: 4.8,
		tags: [
			"github",
			"pr",
			"review"
		],
		type: "blueprint"
	},
	{
		id: "mp-2",
		name: "Email Digest Generator",
		description: "Generates daily email digests from multiple sources",
		author: "AetherOS Labs",
		icon: "mail",
		category: "Productivity",
		downloads: 892,
		rating: 4.6,
		tags: ["email", "digest"],
		type: "blueprint"
	},
	{
		id: "mp-3",
		name: "Social Media Cross-poster",
		description: "Cross-post content across Twitter, LinkedIn, and Mastodon",
		author: "Community",
		icon: "broadcast",
		category: "Social",
		downloads: 654,
		rating: 4.3,
		tags: ["social", "crosspost"],
		type: "workflow"
	},
	{
		id: "mp-4",
		name: "Code Review Checklist",
		description: "Generate code review checklists based on diff analysis",
		author: "AetherOS Labs",
		icon: "checklist",
		category: "Development",
		downloads: 2103,
		rating: 4.9,
		tags: [
			"code",
			"review",
			"checklist"
		],
		type: "template"
	},
	{
		id: "mp-5",
		name: "Incident Response Bot",
		description: "Automated incident response with Slack notifications",
		author: "Community",
		icon: "alert",
		category: "DevOps",
		downloads: 456,
		rating: 4.5,
		tags: [
			"incident",
			"response",
			"slack"
		],
		type: "blueprint"
	},
	{
		id: "mp-6",
		name: "Research Paper Collector",
		description: "Collects and summarizes research papers from arXiv",
		author: "AetherOS Labs",
		icon: "book",
		category: "Research",
		downloads: 789,
		rating: 4.7,
		tags: [
			"research",
			"papers",
			"arxiv"
		],
		type: "workflow"
	},
	{
		id: "mp-7",
		name: "Data Pipeline Builder",
		description: "Build ETL pipelines with drag-and-drop simplicity",
		author: "AetherOS Labs",
		icon: "database",
		category: "Data",
		downloads: 567,
		rating: 4.4,
		tags: [
			"etl",
			"data",
			"pipeline"
		],
		type: "blueprint"
	},
	{
		id: "mp-8",
		name: "Customer Feedback Analyzer",
		description: "Analyze customer feedback with sentiment analysis",
		author: "Community",
		icon: "comment-discussion",
		category: "Analytics",
		downloads: 345,
		rating: 4.2,
		tags: [
			"feedback",
			"sentiment",
			"analysis"
		],
		type: "template"
	},
	{
		id: "mp-9",
		name: "DevOps Monitoring Stack",
		description: "Complete monitoring stack with alerts and dashboards",
		author: "AetherOS Labs",
		icon: "dashboard",
		category: "DevOps",
		downloads: 1234,
		rating: 4.8,
		tags: [
			"monitoring",
			"devops",
			"alerts"
		],
		type: "blueprint"
	},
	{
		id: "mp-10",
		name: "SEO Content Optimizer",
		description: "Optimize content for search engines automatically",
		author: "Community",
		icon: "search",
		category: "Marketing",
		downloads: 234,
		rating: 4.1,
		tags: [
			"seo",
			"content",
			"optimize"
		],
		type: "workflow"
	},
	{
		id: "mp-11",
		name: "Invoice Processor",
		description: "Extract and process invoice data automatically",
		author: "AetherOS Labs",
		icon: "file-text",
		category: "Finance",
		downloads: 678,
		rating: 4.6,
		tags: [
			"invoice",
			"processing",
			"ocr"
		],
		type: "blueprint"
	},
	{
		id: "mp-12",
		name: "Meeting Transcriber",
		description: "Transcribe and summarize meetings from audio",
		author: "Community",
		icon: "mic",
		category: "Productivity",
		downloads: 901,
		rating: 4.5,
		tags: [
			"meeting",
			"transcribe",
			"summary"
		],
		type: "template"
	}
];
var CATEGORIES$1 = [
	"All",
	"Development",
	"DevOps",
	"Productivity",
	"Data",
	"Research",
	"Social",
	"Marketing",
	"Finance",
	"Analytics"
];
function MarketplaceView() {
	const [category, setCategory] = (0, import_react.useState)("All");
	const [searchQuery, setSearchQuery] = (0, import_react.useState)("");
	const filtered = MARKETPLACE_ITEMS.filter((item) => (category === "All" || item.category === category) && (item.name.toLowerCase().includes(searchQuery.toLowerCase()) || item.description.toLowerCase().includes(searchQuery.toLowerCase()) || item.tags.some((t) => t.includes(searchQuery.toLowerCase()))));
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col overflow-hidden",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-6 py-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "text-primary",
						name: "package",
						size: "1rem"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "text-base font-semibold",
						children: "Workflow Marketplace"
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex items-center gap-2",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						className: "w-56 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-xs text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
						onChange: (e) => setSearchQuery(e.target.value),
						placeholder: "Search marketplace...",
						type: "text",
						value: searchQuery
					})
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex items-center gap-1 border-b border-(--ui-stroke-tertiary) px-4 py-2 overflow-x-auto",
				children: CATEGORIES$1.map((cat) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					className: cn("shrink-0 rounded-md px-2.5 py-1 text-xs font-medium transition-colors", category === cat ? "bg-(--ui-control-hover-background) text-foreground" : "text-(--ui-text-tertiary) hover:text-foreground"),
					onClick: () => setCategory(cat),
					type: "button",
					children: cat
				}, cat))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
				className: "flex-1",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "p-6",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mb-6 grid grid-cols-4 gap-3",
							children: [
								{
									label: "Total Items",
									value: MARKETPLACE_ITEMS.length,
									icon: "package"
								},
								{
									label: "Blueprints",
									value: MARKETPLACE_ITEMS.filter((i) => i.type === "blueprint").length,
									icon: "type-hierarchy"
								},
								{
									label: "Templates",
									value: MARKETPLACE_ITEMS.filter((i) => i.type === "template").length,
									icon: "library"
								},
								{
									label: "Workflows",
									value: MARKETPLACE_ITEMS.filter((i) => i.type === "workflow").length,
									icon: "run-all"
								}
							].map((stat) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "rounded-xl border border-(--ui-stroke-tertiary) p-3 text-center",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: "mx-auto mb-1 text-primary",
										name: stat.icon,
										size: "1.25rem"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "text-lg font-semibold tabular-nums text-foreground",
										children: stat.value
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "text-[10px] text-(--ui-text-tertiary)",
										children: stat.label
									})
								]
							}, stat.label))
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "grid grid-cols-3 gap-3",
							children: filtered.map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "group relative rounded-xl border border-(--ui-stroke-tertiary) p-4 transition-all hover:border-primary/30 hover:shadow-lg",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-start gap-3",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
											className: cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-lg", item.type === "blueprint" ? "bg-primary/10" : item.type === "template" ? "bg-purple-500/10" : "bg-cyan-500/10"),
											children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
												className: item.type === "blueprint" ? "text-primary" : item.type === "template" ? "text-purple-400" : "text-cyan-400",
												name: item.icon,
												size: "1.25rem"
											})
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "min-w-0 flex-1",
											children: [
												/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
													className: "flex items-center gap-2",
													children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
														className: "truncate text-sm font-medium text-foreground",
														children: item.name
													}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
														className: cn("shrink-0 rounded px-1 py-0.5 text-[8px] font-medium uppercase", item.type === "blueprint" ? "bg-primary/10 text-primary" : item.type === "template" ? "bg-purple-500/10 text-purple-400" : "bg-cyan-500/10 text-cyan-400"),
														children: item.type
													})]
												}),
												/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
													className: "mt-0.5 text-xs text-(--ui-text-tertiary) line-clamp-2",
													children: item.description
												}),
												/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
													className: "mt-2 flex items-center gap-3 text-[10px] text-(--ui-text-tertiary)",
													children: [
														/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: ["by ", item.author] }),
														/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
															className: "flex items-center gap-0.5",
															children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
																className: "text-amber-400",
																name: "star-full",
																size: "0.625rem"
															}), item.rating]
														}),
														/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
															className: "flex items-center gap-0.5",
															children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
																name: "cloud-download",
																size: "0.625rem"
															}), item.downloads]
														})
													]
												})
											]
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "mt-3 flex flex-wrap gap-1",
										children: item.tags.map((tag) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "rounded bg-(--ui-stroke-tertiary) px-1.5 py-0.5 text-[9px] text-(--ui-text-tertiary)",
											children: tag
										}, tag))
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
										className: "mt-3 w-full opacity-0 group-hover:opacity-100 transition-opacity",
										size: "sm",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
											className: "mr-1",
											name: " cloud-download",
											size: "0.75rem"
										}), "Install"]
									})
								]
							}, item.id))
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-8 rounded-xl border border-dashed border-(--ui-stroke-tertiary) p-8 text-center",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "mx-auto mb-2 text-(--ui-text-tertiary)",
									name: "package",
									size: "2rem"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
									className: "text-sm font-medium text-foreground",
									children: "Publish Your Own"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "mt-1 text-xs text-(--ui-text-tertiary)",
									children: "Package your workflow as a blueprint and share it with the community"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
									className: "mt-3",
									size: "sm",
									variant: "outline",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: "mr-1",
										name: "upload",
										size: "0.875rem"
									}), "Publish to Marketplace"]
								})
							]
						})
					]
				})
			})
		]
	});
}
//#endregion
//#region src/app/automation/templates/templates-gallery.tsx
var TEMPLATES = [
	{
		id: "email-autoreply",
		name: "Email Auto Reply",
		description: "Automatically reply to incoming emails based on content",
		category: "Communication",
		icon: "mail",
		tags: [
			"email",
			"automation",
			"reply"
		],
		nodeCount: 5,
		popular: true
	},
	{
		id: "github-pr-review",
		name: "GitHub PR Review",
		description: "Auto-review pull requests with AI analysis",
		category: "Development",
		icon: "git-pull-request",
		tags: [
			"github",
			"pr",
			"review",
			"ai"
		],
		nodeCount: 7,
		popular: true
	},
	{
		id: "telegram-ai-bot",
		name: "Telegram AI Bot",
		description: "AI-powered Telegram bot for automated responses",
		category: "Messaging",
		icon: "send",
		tags: [
			"telegram",
			"bot",
			"ai"
		],
		nodeCount: 4,
		popular: true
	},
	{
		id: "discord-moderator",
		name: "Discord Moderator",
		description: "Automated Discord moderation with AI",
		category: "Messaging",
		icon: "message-circle",
		tags: [
			"discord",
			"moderation",
			"ai"
		],
		nodeCount: 6,
		popular: false
	},
	{
		id: "website-monitor",
		name: "Website Monitor",
		description: "Monitor websites for changes and get alerts",
		category: "Monitoring",
		icon: "globe",
		tags: [
			"monitor",
			"web",
			"alert"
		],
		nodeCount: 4,
		popular: true
	},
	{
		id: "research-pipeline",
		name: "Research Pipeline",
		description: "Automated research pipeline with web search and summarization",
		category: "Research",
		icon: "book",
		tags: [
			"research",
			"search",
			"summarize"
		],
		nodeCount: 8,
		popular: true
	},
	{
		id: "meeting-summary",
		name: "Meeting Summary",
		description: "Summarize meetings from notes or transcripts",
		category: "Productivity",
		icon: "comment-discussion",
		tags: [
			"meeting",
			"summary",
			"notes"
		],
		nodeCount: 3,
		popular: false
	},
	{
		id: "daily-report",
		name: "Daily Report",
		description: "Generate daily reports with key metrics",
		category: "Reporting",
		icon: "output",
		tags: [
			"report",
			"daily",
			"metrics"
		],
		nodeCount: 5,
		popular: false
	},
	{
		id: "youtube-summarizer",
		name: "YouTube Summarizer",
		description: "Summarize YouTube videos automatically",
		category: "Media",
		icon: "play",
		tags: [
			"youtube",
			"summary",
			"video"
		],
		nodeCount: 3,
		popular: false
	},
	{
		id: "social-media-poster",
		name: "Social Media Poster",
		description: "Schedule and post content to social media",
		category: "Social",
		icon: "broadcast",
		tags: [
			"social",
			"post",
			"schedule"
		],
		nodeCount: 5,
		popular: false
	},
	{
		id: "lead-generator",
		name: "Lead Generator",
		description: "Generate leads from web research",
		category: "Sales",
		icon: "person-add",
		tags: [
			"leads",
			"research",
			"crm"
		],
		nodeCount: 6,
		popular: false
	},
	{
		id: "customer-support",
		name: "Customer Support",
		description: "AI-powered customer support automation",
		category: "Support",
		icon: "comment-discussion",
		tags: [
			"support",
			"customer",
			"ai"
		],
		nodeCount: 7,
		popular: true
	},
	{
		id: "bug-reporter",
		name: "Bug Reporter",
		description: "Auto-report bugs with context and logs",
		category: "Development",
		icon: "bug",
		tags: [
			"bug",
			"report",
			"debug"
		],
		nodeCount: 4,
		popular: false
	},
	{
		id: "file-organizer",
		name: "File Organizer",
		description: "Automatically organize files by type and date",
		category: "Productivity",
		icon: "file-directory",
		tags: [
			"files",
			"organize",
			"cleanup"
		],
		nodeCount: 5,
		popular: false
	},
	{
		id: "backup-workflow",
		name: "Backup Workflow",
		description: "Automated backup with scheduling and notifications",
		category: "DevOps",
		icon: "archive",
		tags: [
			"backup",
			"schedule",
			"notification"
		],
		nodeCount: 6,
		popular: false
	}
];
var CATEGORIES = ["All", ...new Set(TEMPLATES.map((t) => t.category))];
function TemplatesGallery() {
	const [category, setCategory] = (0, import_react.useState)("All");
	const [searchQuery, setSearchQuery] = (0, import_react.useState)("");
	const filtered = TEMPLATES.filter((t) => (category === "All" || t.category === category) && (t.name.toLowerCase().includes(searchQuery.toLowerCase()) || t.description.toLowerCase().includes(searchQuery.toLowerCase()) || t.tags.some((tag) => tag.includes(searchQuery.toLowerCase()))));
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col overflow-hidden",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-6 py-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "text-purple-400",
						name: "library",
						size: "1rem"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "text-base font-semibold",
						children: "Workflow Templates"
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
					className: "w-56 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-xs text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
					onChange: (e) => setSearchQuery(e.target.value),
					placeholder: "Search templates...",
					type: "text",
					value: searchQuery
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex items-center gap-1 border-b border-(--ui-stroke-tertiary) px-4 py-2",
				children: CATEGORIES.map((cat) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					className: cn("rounded-md px-2.5 py-1 text-xs font-medium transition-colors", category === cat ? "bg-(--ui-control-hover-background) text-foreground" : "text-(--ui-text-tertiary) hover:text-foreground"),
					onClick: () => setCategory(cat),
					type: "button",
					children: cat
				}, cat))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
				className: "flex-1",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid grid-cols-3 gap-3 p-4",
					children: filtered.map((tmpl) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "group relative cursor-pointer rounded-xl border border-(--ui-stroke-tertiary) p-4 transition-all hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5",
						children: [
							tmpl.popular && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "absolute right-2 top-2 rounded-full bg-primary/10 px-1.5 py-0.5 text-[9px] font-medium text-primary",
								children: "Popular"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: cn("mb-3 flex h-10 w-10 items-center justify-center rounded-lg", tmpl.category === "Communication" ? "bg-green-500/10" : tmpl.category === "Development" ? "bg-blue-500/10" : tmpl.category === "Messaging" ? "bg-cyan-500/10" : tmpl.category === "Monitoring" ? "bg-amber-500/10" : tmpl.category === "Research" ? "bg-purple-500/10" : tmpl.category === "Productivity" ? "bg-pink-500/10" : tmpl.category === "Reporting" ? "bg-orange-500/10" : "bg-(--ui-control-hover-background)"),
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: tmpl.category === "Communication" ? "text-green-400" : tmpl.category === "Development" ? "text-blue-400" : tmpl.category === "Messaging" ? "text-cyan-400" : tmpl.category === "Monitoring" ? "text-amber-400" : tmpl.category === "Research" ? "text-purple-400" : tmpl.category === "Productivity" ? "text-pink-400" : tmpl.category === "Reporting" ? "text-orange-400" : "text-(--ui-text-tertiary)",
									name: tmpl.icon,
									size: "1.25rem"
								})
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "mb-1 text-sm font-medium text-foreground",
								children: tmpl.name
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mb-3 text-xs text-(--ui-text-tertiary) line-clamp-2",
								children: tmpl.description
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center justify-between",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "flex flex-wrap gap-1",
									children: tmpl.tags.slice(0, 3).map((tag) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "rounded bg-(--ui-stroke-tertiary) px-1.5 py-0.5 text-[9px] text-(--ui-text-tertiary)",
										children: tag
									}, tag))
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "text-[10px] text-(--ui-text-tertiary)",
									children: [tmpl.nodeCount, " nodes"]
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								className: "mt-3 w-full opacity-0 group-hover:opacity-100 transition-opacity",
								size: "sm",
								variant: "outline",
								children: "Use Template"
							})
						]
					}, tmpl.id))
				})
			})
		]
	});
}
//#endregion
//#region src/app/automation/index.tsx
var TABS = [
	{
		id: "editor",
		label: "Editor",
		icon: "type-hierarchy"
	},
	{
		id: "scheduler",
		label: "Schedule",
		icon: "calendar"
	},
	{
		id: "history",
		label: "History",
		icon: "history"
	},
	{
		id: "templates",
		label: "Templates",
		icon: "library"
	},
	{
		id: "secrets",
		label: "Secrets",
		icon: "lock"
	},
	{
		id: "marketplace",
		label: "Marketplace",
		icon: "package"
	}
];
function AutomationView() {
	const state = useStore($automation);
	const activeWorkflow = state.workflows.find((w) => w.id === state.activeWorkflowId);
	const [workflowName, setWorkflowName] = (0, import_react.useState)("");
	const [showCreateDialog, setShowCreateDialog] = (0, import_react.useState)(false);
	const [showDeleteConfirm, setShowDeleteConfirm] = (0, import_react.useState)(null);
	const handleKeyDown = (e) => {
		if ((e.metaKey || e.ctrlKey) && e.key === "z" && !e.shiftKey) {
			e.preventDefault();
			undo();
		}
		if ((e.metaKey || e.ctrlKey) && e.key === "z" && e.shiftKey) {
			e.preventDefault();
			redo();
		}
		if ((e.metaKey || e.ctrlKey) && e.key === "a") {
			e.preventDefault();
			selectAll();
		}
		if ((e.metaKey || e.ctrlKey) && e.key === "c") {
			e.preventDefault();
			copySelection();
		}
		if ((e.metaKey || e.ctrlKey) && e.key === "v") {
			e.preventDefault();
			pasteClipboard();
		}
		if (e.key === "Delete" || e.key === "Backspace") deleteSelection();
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col overflow-hidden bg-background",
		onKeyDown: handleKeyDown,
		tabIndex: 0,
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
				className: "flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
							className: "text-lg font-semibold tracking-tight",
							children: "Automation"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Separator, {
							className: "h-5",
							orientation: "vertical"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex items-center gap-1",
							children: TABS.map((tab) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								className: cn("flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors", state.activeTab === tab.id ? "bg-(--ui-control-hover-background) text-foreground" : "text-(--ui-text-tertiary) hover:text-foreground"),
								onClick: () => setActiveTab(tab.id),
								type: "button",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									name: tab.icon,
									size: "0.875rem"
								}), tab.label]
							}, tab.id))
						})
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex items-center gap-2",
					children: state.activeTab === "editor" && activeWorkflow && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: cn("rounded p-1 text-(--ui-text-tertiary) hover:text-foreground", state.snapToGrid && "text-foreground"),
							onClick: () => setSnapToGrid(!state.snapToGrid),
							title: "Toggle Snap to Grid",
							type: "button",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "grid",
								size: "0.875rem"
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: cn("rounded p-1 text-(--ui-text-tertiary) hover:text-foreground", state.showMiniMap && "text-foreground"),
							onClick: () => setShowMiniMap(!state.showMiniMap),
							title: "Toggle Mini Map",
							type: "button",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "map",
								size: "0.875rem"
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "rounded p-1 text-(--ui-text-tertiary) hover:text-foreground",
							onClick: autoLayout,
							title: "Auto Layout",
							type: "button",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "layout",
								size: "0.875rem"
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "rounded p-1 text-(--ui-text-tertiary) hover:text-foreground",
							onClick: resetCanvas,
							title: "Reset View",
							type: "button",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "screen-normal",
								size: "0.875rem"
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Separator, {
							className: "h-5",
							orientation: "vertical"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "rounded p-1 text-(--ui-text-tertiary) hover:text-foreground",
							onClick: undo,
							title: "Undo",
							type: "button",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "undo",
								size: "0.875rem"
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "rounded p-1 text-(--ui-text-tertiary) hover:text-foreground",
							onClick: redo,
							title: "Redo",
							type: "button",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "redo",
								size: "0.875rem"
							})
						})
					] })
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2 border-b border-(--ui-stroke-tertiary) px-4 py-1.5",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2 flex-1 min-w-0",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-(--ui-text-tertiary)",
							name: "run-all",
							size: "1rem"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("select", {
							className: "max-w-[240px] truncate rounded border-0 bg-transparent text-sm font-medium text-foreground focus:outline-none focus:ring-0",
							onChange: (e) => setActiveWorkflow(e.target.value || null),
							value: state.activeWorkflowId ?? "",
							children: state.workflows.map((w) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: w.id,
								children: w.name
							}, w.id))
						}),
						activeWorkflow && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: cn("inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium", activeWorkflow.enabled ? "bg-green-500/10 text-green-400" : "bg-(--ui-stroke-tertiary) text-(--ui-text-tertiary)"),
							children: activeWorkflow.enabled ? "Active" : "Disabled"
						})
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-1",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: "flex items-center gap-1 rounded-md bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground hover:opacity-90",
						onClick: () => setShowCreateDialog(true),
						type: "button",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "add",
							size: "0.875rem"
						}), "New"]
					}), activeWorkflow && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: cn("rounded-md px-2.5 py-1 text-xs font-medium transition-colors", activeWorkflow.enabled ? "bg-destructive/10 text-destructive hover:bg-destructive/20" : "bg-primary/10 text-primary hover:bg-primary/20"),
							onClick: () => toggleWorkflowEnabled(activeWorkflow.id),
							type: "button",
							children: activeWorkflow.enabled ? "Disable" : "Enable"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "rounded-md px-2 py-1 text-xs text-(--ui-text-tertiary) hover:text-foreground",
							onClick: () => {
								const d = duplicateWorkflow(activeWorkflow.id);
								if (d) setActiveWorkflow(d.id);
							},
							type: "button",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "copy",
								size: "0.875rem"
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							className: "rounded-md px-2 py-1 text-xs text-(--ui-text-tertiary) hover:text-destructive",
							onClick: () => setShowDeleteConfirm(activeWorkflow.id),
							type: "button",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								name: "trash",
								size: "0.875rem"
							})
						})
					] })]
				})]
			}),
			state.activeTab === "editor" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-1 overflow-hidden",
				children: [
					state.showNodePalette && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(NodePalette, {}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "relative flex-1 overflow-hidden",
						children: activeWorkflow ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(WorkflowCanvas, {}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex h-full items-center justify-center",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "text-center",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										className: "mx-auto mb-3 text-(--ui-text-tertiary)",
										name: "run-all",
										size: "2rem"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-sm text-(--ui-text-tertiary)",
										children: "No workflow selected"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
										className: "mt-3 rounded-md bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90",
										onClick: () => setShowCreateDialog(true),
										type: "button",
										children: "Create Workflow"
									})
								]
							})
						})
					}),
					state.showVariablesPanel && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(VariablesPanel, {}),
					state.showSecretsPanel && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SecretsPanel, {})
				]
			}),
			state.activeTab === "scheduler" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(WorkflowScheduler, {}),
			state.activeTab === "history" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(WorkflowHistory, {}),
			state.activeTab === "templates" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TemplatesGallery, {}),
			state.activeTab === "secrets" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SecretsPanel, {}),
			state.activeTab === "marketplace" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(MarketplaceView, {}),
			state.editingNodeId && activeWorkflow && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
				activeWorkflow.nodes.find((n) => n.id === state.editingNodeId)?.type === "trigger" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TriggerConfigModal, { nodeId: state.editingNodeId }),
				activeWorkflow.nodes.find((n) => n.id === state.editingNodeId)?.type === "action" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ActionConfigModal, { nodeId: state.editingNodeId }),
				activeWorkflow.nodes.find((n) => n.id === state.editingNodeId)?.type === "condition" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ConditionConfigModal, { nodeId: state.editingNodeId })
			] }),
			showCreateDialog && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "fixed inset-0 z-50 flex items-center justify-center bg-black/50",
				onClick: () => setShowCreateDialog(false),
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "w-96 rounded-xl border bg-background p-6 shadow-xl",
					onClick: (e) => e.stopPropagation(),
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "mb-4 text-base font-semibold",
							children: "Create Workflow"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							autoFocus: true,
							className: "mb-4 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-2 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary",
							onChange: (e) => setWorkflowName(e.target.value),
							onKeyDown: (e) => {
								if (e.key === "Enter" && workflowName.trim()) {
									const w = createWorkflow(workflowName.trim());
									setWorkflowName("");
									setShowCreateDialog(false);
									setActiveWorkflow(w.id);
								}
							},
							placeholder: "Enter workflow name...",
							type: "text",
							value: workflowName
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex justify-end gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => {
									setShowCreateDialog(false);
									setWorkflowName("");
								},
								size: "sm",
								variant: "ghost",
								children: "Cancel"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => {
									if (workflowName.trim()) {
										const w = createWorkflow(workflowName.trim());
										setWorkflowName("");
										setShowCreateDialog(false);
										setActiveWorkflow(w.id);
									}
								},
								size: "sm",
								children: "Create"
							})]
						})
					]
				})
			}),
			showDeleteConfirm && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "fixed inset-0 z-50 flex items-center justify-center bg-black/50",
				onClick: () => setShowDeleteConfirm(null),
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "w-80 rounded-xl border bg-background p-6 shadow-xl",
					onClick: (e) => e.stopPropagation(),
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "mb-2 text-base font-semibold",
							children: "Delete Workflow?"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mb-4 text-sm text-(--ui-text-tertiary)",
							children: "This action cannot be undone."
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex justify-end gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => setShowDeleteConfirm(null),
								size: "sm",
								variant: "ghost",
								children: "Cancel"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								onClick: () => {
									deleteWorkflow(showDeleteConfirm);
									setShowDeleteConfirm(null);
								},
								size: "sm",
								variant: "destructive",
								children: "Delete"
							})]
						})
					]
				})
			})
		]
	});
}
//#endregion
export { AutomationView };

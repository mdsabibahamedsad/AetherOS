import { Ia as Codicon, La as Button, Ra as cn, S as ScrollArea, ao as require_jsx_runtime, eo as useNavigate } from "./index-B_yd1pEX.js";
//#region src/app/ai-actions/index.tsx
var import_jsx_runtime = require_jsx_runtime();
var AI_ACTIONS = [
	{
		id: "new-chat",
		icon: "comment-discussion",
		label: "New Chat",
		description: "Start a conversation with the AI",
		route: "/new",
		color: "from-blue-500/20 to-blue-600/10",
		category: "Communication"
	},
	{
		id: "summarize",
		icon: "summary",
		label: "Summarize",
		description: "Summarize a document or conversation",
		route: "/new",
		color: "from-violet-500/20 to-violet-600/10",
		category: "Productivity"
	},
	{
		id: "analyze-code",
		icon: "code",
		label: "Analyze Code",
		description: "Review and analyze code",
		route: "/new",
		color: "from-emerald-500/20 to-emerald-600/10",
		category: "Development"
	},
	{
		id: "research",
		icon: "globe",
		label: "Research",
		description: "Search the web for information",
		route: "/new",
		color: "from-amber-500/20 to-amber-600/10",
		category: "Research"
	},
	{
		id: "translate",
		icon: "comment",
		label: "Translate",
		description: "Translate text between languages",
		route: "/new",
		color: "from-rose-500/20 to-rose-600/10",
		category: "Productivity"
	},
	{
		id: "explain",
		icon: "light-bulb",
		label: "Explain",
		description: "Explain a concept or topic",
		route: "/new",
		color: "from-cyan-500/20 to-cyan-600/10",
		category: "Learning"
	},
	{
		id: "brainstorm",
		icon: "beaker",
		label: "Brainstorm",
		description: "Generate creative ideas",
		route: "/new",
		color: "from-pink-500/20 to-pink-600/10",
		category: "Creative"
	},
	{
		id: "write",
		icon: "pencil",
		label: "Write",
		description: "Draft content, emails, or documents",
		route: "/new",
		color: "from-orange-500/20 to-orange-600/10",
		category: "Creative"
	},
	{
		id: "plan",
		icon: "list-ordered",
		label: "Plan",
		description: "Create a plan or outline",
		route: "/new",
		color: "from-teal-500/20 to-teal-600/10",
		category: "Productivity"
	},
	{
		id: "debug",
		icon: "bug",
		label: "Debug",
		description: "Debug code or troubleshoot issues",
		route: "/new",
		color: "from-red-500/20 to-red-600/10",
		category: "Development"
	}
];
var CATEGORIES = [
	"Communication",
	"Productivity",
	"Development",
	"Research",
	"Learning",
	"Creative"
];
function AiActionsView() {
	const navigate = useNavigate();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
		className: "h-full",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mx-auto max-w-5xl space-y-6 p-6",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
					className: "text-xl font-semibold tracking-tight",
					children: "AI Actions"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-1 text-sm text-(--ui-text-tertiary)",
					children: "Quick actions to get started with the AI assistant"
				})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: () => navigate("/new"),
					size: "sm",
					children: "New Chat"
				})]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-6",
				children: CATEGORIES.map((category) => {
					const items = AI_ACTIONS.filter((a) => a.category === category);
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "mb-3 text-xs font-semibold uppercase tracking-wider text-(--ui-text-tertiary)",
						children: category
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "grid gap-3 sm:grid-cols-2 lg:grid-cols-3",
						children: items.map((action) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: cn("group relative overflow-hidden rounded-xl border border-(--ui-stroke-tertiary) p-4 text-left transition-all hover:border-(--dt-ring) hover:shadow-sm", "bg-gradient-to-br", action.color),
							onClick: () => navigate(action.route),
							type: "button",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "mb-2 text-(--ui-text-tertiary) group-hover:text-foreground",
									name: action.icon,
									size: "1.25rem"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
									className: "text-sm font-medium",
									children: action.label
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "mt-0.5 text-xs text-(--ui-text-tertiary)",
									children: action.description
								})
							]
						}, action.id))
					})] }, category);
				})
			})]
		})
	});
}
//#endregion
export { AiActionsView };

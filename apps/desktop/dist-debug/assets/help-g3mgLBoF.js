import { Ia as Codicon, ao as require_jsx_runtime } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/app/help/index.tsx
var import_jsx_runtime = require_jsx_runtime();
function HelpView() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageHeader, {
			className: "w-full",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Help" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Documentation and support resources" })] })
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid gap-3 sm:grid-cols-2",
			children: [
				{
					icon: "book",
					label: "Documentation",
					desc: "Read the AetherOS documentation",
					url: "https://aetheros.ai/docs"
				},
				{
					icon: "comment-discussion",
					label: "Community",
					desc: "Join the AetherOS community",
					url: "https://discord.gg/aetheros"
				},
				{
					icon: "github",
					label: "GitHub",
					desc: "View the source code",
					url: "https://github.com/aetheros/aetheros"
				},
				{
					icon: "question",
					label: "FAQ",
					desc: "Frequently asked questions",
					url: "https://aetheros.ai/faq"
				},
				{
					icon: "report",
					label: "Report Issue",
					desc: "File a bug report or feature request",
					url: "https://github.com/aetheros/aetheros/issues"
				}
			].map((link) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("a", {
				className: "flex items-start gap-3 rounded-xl border border-(--ui-stroke-tertiary) p-4 transition-colors hover:bg-(--ui-control-hover-background)",
				href: link.url,
				rel: "noreferrer",
				target: "_blank",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
					className: "mt-0.5 shrink-0 text-(--ui-text-tertiary)",
					name: link.icon,
					size: "1.25rem"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-sm font-medium",
					children: link.label
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-0.5 text-xs text-(--ui-text-tertiary)",
					children: link.desc
				})] })]
			}, link.label))
		})
	});
}
//#endregion
export { HelpView };

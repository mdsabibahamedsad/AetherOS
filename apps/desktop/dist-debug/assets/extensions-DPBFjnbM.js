import { ao as require_jsx_runtime } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
import { EmptyState } from "./projects-Dtoe38iC.js";
//#region src/app/extensions/index.tsx
var import_jsx_runtime = require_jsx_runtime();
function ExtensionsList() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
		description: "Install and manage AetherOS extensions",
		icon: "extensions",
		title: "Extensions"
	});
}
function ExtensionsView() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageHeader, {
			className: "w-full",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Extensions" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Extend AetherOS with plugins and MCP servers" })] })
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ExtensionsList, {})
	});
}
//#endregion
export { ExtensionsView };

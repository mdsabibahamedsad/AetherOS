import { ao as require_jsx_runtime } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
import { EmptyState } from "./projects-Dtoe38iC.js";
//#region src/app/history/index.tsx
var import_jsx_runtime = require_jsx_runtime();
function HistoryView() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageHeader, {
			className: "w-full",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "History" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Session history and activity log" })] })
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
			description: "Past conversations and agent activity will appear here",
			icon: "history",
			title: "Session history"
		})
	});
}
//#endregion
export { HistoryView };
